"""Carreras HTTP con sesiones reales independientes y lecturas MVCC."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Barrier
from time import perf_counter
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, select, text, update
from sqlalchemy.orm import Session

from monetae.api.main import create_app
from monetae.api.schemas.subscriptions import SubscriptionCreate, SubscriptionUpdate
from monetae.db.models import Account, RecurringRule, Subscription, Transaction, TransactionTag
from monetae.services.subscriptions import SubscriptionService

from .conftest import csrf_headers, subscription_payload
from .test_session_concurrency import AuthData
from .test_session_concurrency import committed_auth as committed_auth  # noqa: F401 -- fixture


@dataclass(frozen=True)
class SubscriptionData:
    auth: AuthData
    subscription_id: UUID
    rule_id: UUID
    transaction_id: UUID


@pytest.fixture
def committed_subscription(
    db_engine: Engine, committed_auth: AuthData
) -> Iterator[SubscriptionData]:
    auth = committed_auth
    with Session(db_engine) as db:
        account = Account(user_id=auth.user_id, name="Synthetic", type="cash", currency="PEN")
        db.add(account)
        db.flush()
        service = SubscriptionService(db, auth.settings.secret_key, auth.clock)
        row = service.create(
            auth.user_id, SubscriptionCreate.model_validate(subscription_payload(str(account.id)))
        )
        rule_id = row.recurring_rule_id
        assert rule_id is not None
        transaction_id = db.scalar(
            select(Transaction.id).where(
                Transaction.user_id == auth.user_id, Transaction.recurring_rule_id == rule_id
            )
        )
        assert transaction_id is not None
        data = SubscriptionData(auth, row.id, rule_id, transaction_id)
        db.commit()
    try:
        yield data
    finally:
        with Session(db_engine) as db:
            db.execute(delete(TransactionTag).where(TransactionTag.user_id == auth.user_id))
            db.execute(delete(Transaction).where(Transaction.user_id == auth.user_id))
            db.execute(
                update(RecurringRule)
                .where(RecurringRule.user_id == auth.user_id)
                .values(subscription_id=None)
            )
            for model in (Subscription, RecurringRule, Account):
                db.execute(delete(model).where(model.user_id == auth.user_id))
            db.commit()


def test_simultaneous_archive_and_post_are_atomic(
    db_engine: Engine, database_url: str, committed_subscription: SubscriptionData
) -> None:
    data = committed_subscription
    app = create_app(data.auth.settings.model_copy(update={"database_url": database_url}))
    app.state.clock = data.auth.clock
    barrier = Barrier(2)
    with (
        TestClient(app, base_url="https://testserver") as archive_client,
        TestClient(app, base_url="https://testserver") as post_client,
    ):
        for client, token in zip((archive_client, post_client), data.auth.tokens, strict=True):
            client.cookies.set("monetae_session", token)
            assert client.get("/api/v1/subscriptions").status_code == 200
        archive_headers, post_headers = csrf_headers(archive_client), csrf_headers(post_client)

        def archive() -> int:
            barrier.wait(timeout=5)
            response = archive_client.post(
                f"/api/v1/subscriptions/{data.subscription_id}/archive",
                json={},
                headers=archive_headers,
            )
            status: int = response.status_code
            return status

        def post() -> int:
            barrier.wait(timeout=5)
            response = post_client.post(
                f"/api/v1/transactions/{data.transaction_id}/post", headers=post_headers
            )
            status: int = response.status_code
            return status

        with ThreadPoolExecutor(max_workers=2) as pool:
            archived, posted = pool.submit(archive), pool.submit(post)
            assert archived.result(timeout=10) == 200
            assert posted.result(timeout=10) in {200, 404}
    with Session(db_engine) as db:
        subscription = db.get(Subscription, data.subscription_id)
        rule = db.get(RecurringRule, data.rule_id)
        assert subscription is not None and subscription.status == "archived"
        assert rule is not None and not rule.active
        rows = list(
            db.scalars(
                select(Transaction).where(
                    Transaction.user_id == data.auth.user_id,
                    Transaction.recurring_rule_id == rule.id,
                )
            )
        )
        assert len(rows) in {1, 2}
        assert all(row.deleted_at is not None or row.status == "posted" for row in rows)
        assert len([row for row in rows if row.status == "posted"]) <= 1


def test_http_reads_do_not_wait_for_subscription_write(
    db_engine: Engine, database_url: str, committed_subscription: SubscriptionData
) -> None:
    data = committed_subscription
    app = create_app(data.auth.settings.model_copy(update={"database_url": database_url}))
    app.state.clock = data.auth.clock
    paths = [
        "/api/v1/subscriptions",
        f"/api/v1/subscriptions/{data.subscription_id}",
        "/api/v1/subscriptions/totals",
        "/api/v1/transactions",
    ]
    with Session(db_engine) as writer, TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("monetae_session", data.auth.tokens[0])
        for path in paths:
            assert client.get(path).status_code == 200
        SubscriptionService(writer, data.auth.settings.secret_key, data.auth.clock).update(
            data.auth.user_id,
            data.subscription_id,
            SubscriptionUpdate(amount="60.00", title="Uncommitted"),
        )
        for path in paths:
            start = perf_counter()
            with ThreadPoolExecutor(max_workers=1) as pool:
                response = pool.submit(client.get, path).result(timeout=2)
            elapsed = perf_counter() - start
            assert response.status_code == 200, response.text
            assert elapsed < 0.300, f"{path} blocked for {elapsed * 1000:.1f} ms"
            assert "Uncommitted" not in response.text
            print(f"{path}: {elapsed * 1000:.1f} ms with write uncommitted")
        writer.rollback()


@pytest.mark.parametrize("first", ["archive", "post"])
def test_each_serialized_order_finishes_without_deadlock(
    db_engine: Engine, database_url: str, committed_subscription: SubscriptionData, first: str
) -> None:
    from monetae.services.transactions import TransactionService

    data = committed_subscription
    app = create_app(data.auth.settings.model_copy(update={"database_url": database_url}))
    app.state.clock = data.auth.clock
    with Session(db_engine) as writer, TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("monetae_session", data.auth.tokens[0])
        headers = csrf_headers(client)
        writer.execute(text("SET LOCAL statement_timeout = '5s'"))
        if first == "archive":
            SubscriptionService(writer, data.auth.settings.secret_key, data.auth.clock).archive(
                data.auth.user_id, data.subscription_id, None
            )
            path = f"/api/v1/transactions/{data.transaction_id}/post"
        else:
            TransactionService(writer, data.auth.settings.secret_key).post(
                data.auth.user_id, data.transaction_id
            )
            path = f"/api/v1/subscriptions/{data.subscription_id}/archive"
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                client.post, path, headers=headers, json={} if first == "post" else None
            )
            writer.commit()
            assert future.result(timeout=5).status_code == (404 if first == "archive" else 200)
        assert (
            client.get("/api/v1/transactions", params={"status": "scheduled"}).json()["items"] == []
        )


def test_concurrent_patches_preserve_independent_fields(
    db_engine: Engine, committed_subscription: SubscriptionData
) -> None:
    data = committed_subscription
    barrier = Barrier(2)

    def patch(payload: SubscriptionUpdate) -> None:
        with Session(db_engine) as db:
            db.execute(text("SET LOCAL lock_timeout = '3s'"))
            db.execute(text("SET LOCAL statement_timeout = '5s'"))
            service = SubscriptionService(db, data.auth.settings.secret_key, data.auth.clock)
            service.get(data.auth.user_id, data.subscription_id)
            barrier.wait(timeout=5)
            service.update(data.auth.user_id, data.subscription_id, payload)
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(patch, SubscriptionUpdate(amount="60.00"))
        two = pool.submit(patch, SubscriptionUpdate(title="Updated"))
        one.result(timeout=10)
        two.result(timeout=10)
    with Session(db_engine) as db:
        row = db.get(Subscription, data.subscription_id)
        rule = db.get(RecurringRule, data.rule_id)
        assert row is not None and row.title == "Updated" and row.amount == 60
        assert rule is not None and rule.title == "Updated" and rule.amount == -60
        live = list(
            db.scalars(
                select(Transaction).where(
                    Transaction.user_id == data.auth.user_id,
                    Transaction.recurring_rule_id == data.rule_id,
                    Transaction.status == "scheduled",
                    Transaction.deleted_at.is_(None),
                )
            )
        )
        assert len(live) == 1 and live[0].title == "Updated" and live[0].amount == -60
