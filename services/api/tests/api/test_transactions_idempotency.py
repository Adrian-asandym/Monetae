from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from api.conftest import (
    PASSWORD,
    create_account,
    create_tag,
    csrf_headers,
    login,
    transaction_payload,
)
from monetae.api.main import create_app
from monetae.config import Settings
from monetae.db.models import Account, Category, IdempotencyKey, Transaction, TransactionTag, User
from monetae.db.models import Session as SessionRow
from monetae.services.auth import AuthService, SystemClock
from monetae.services.idempotency import IdempotencyService, StoredResponse


def test_same_key_returns_saved_status_and_body_despite_later_edit(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    payload = transaction_payload(account)
    headers = {**csrf_headers(client), "Idempotency-Key": "repeat"}
    original = client.post("/api/v1/transactions", json=payload, headers=headers)
    assert original.status_code == 201, original.text
    client.patch(
        f"/api/v1/transactions/{original.json()['id']}",
        json={"title": "changed"},
        headers=csrf_headers(client),
    )
    repeated = client.post(
        "/api/v1/transactions", json=dict(reversed(list(payload.items()))), headers=headers
    )
    assert repeated.status_code == 201 and repeated.json() == original.json()
    assert len(client.get("/api/v1/transactions").json()["items"]) == 1


def test_canonical_tags_timezone_and_defaults(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    a, b = create_tag(client, "A"), create_tag(client, "B")
    headers = {**csrf_headers(client), "Idempotency-Key": "canonical"}
    first = client.post(
        "/api/v1/transactions", json=transaction_payload(account, tag_ids=[a, b]), headers=headers
    )
    second = client.post(
        "/api/v1/transactions",
        json=transaction_payload(
            account,
            tag_ids=[b, a],
            note=None,
            category_id=None,
            occurred_at="2026-10-07T07:00:00-05:00",
        ),
        headers=headers,
    )
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()


def test_same_key_different_body_is_conflict(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    headers = {**csrf_headers(client), "Idempotency-Key": "conflict"}
    assert (
        client.post(
            "/api/v1/transactions", json=transaction_payload(account), headers=headers
        ).status_code
        == 201
    )
    changed = client.post(
        "/api/v1/transactions", json=transaction_payload(account, amount="-20.00"), headers=headers
    )
    assert changed.status_code == 409 and changed.json()["code"] == "idempotency_conflict"
    assert len(client.get("/api/v1/transactions").json()["items"]) == 1


def test_no_key_creates_independent_transactions(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    for _ in range(2):
        assert (
            client.post(
                "/api/v1/transactions",
                json=transaction_payload(account),
                headers=csrf_headers(client),
            ).status_code
            == 201
        )
    assert len(client.get("/api/v1/transactions").json()["items"]) == 2


@pytest.mark.parametrize("key", ["", "x" * 129])
def test_key_length_validation(client: TestClient, key: str) -> None:
    login(client)
    account = create_account(client)
    response = client.post(
        "/api/v1/transactions",
        json=transaction_payload(account),
        headers={**csrf_headers(client), "Idempotency-Key": key},
    )
    assert response.status_code == 422


def test_expired_key_ignored_and_retention_is_24_hours(
    client: TestClient, db_session: Session
) -> None:
    login(client)
    account = create_account(client)
    headers = {**csrf_headers(client), "Idempotency-Key": "expired"}
    first = client.post("/api/v1/transactions", json=transaction_payload(account), headers=headers)
    key = db_session.scalar(select(IdempotencyKey).where(IdempotencyKey.key == "expired"))
    assert key is not None and key.expires_at - key.created_at == timedelta(hours=24)
    key.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()
    second = client.post(
        "/api/v1/transactions", json=transaction_payload(account, title="new"), headers=headers
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert db_session.scalar(select(func.count()).select_from(IdempotencyKey)) == 1


def test_key_scope_is_user_and_operation(
    db_session: Session, auth_users: tuple[User, User]
) -> None:
    service = IdempotencyService(db_session)
    first = service.execute(
        auth_users[0].id, "shared", "create-a", {}, lambda: StoredResponse(201, {"a": 1})
    )
    other = service.execute(
        auth_users[1].id, "shared", "create-a", {}, lambda: StoredResponse(202, {"a": 2})
    )
    assert first.status == 201 and other.status == 202
    from monetae.services.auth import AuthError

    with pytest.raises(AuthError) as error:
        service.execute(auth_users[0].id, "shared", "create-b", {}, lambda: StoredResponse(201, {}))
    assert error.value.code == "idempotency_conflict"


def test_concurrent_same_key_two_http_requests_create_one_transaction(
    db_engine: Engine, database_url: str
) -> None:
    # Conexiones con commits reales: el fixture savepoint no modela esta carrera.
    settings = Settings(
        environment="test", database_url=database_url, cors_origins=["https://testserver"]
    )
    app = create_app(settings)
    email = f"concurrency-{uuid4().hex}@example.test"
    with Session(db_engine) as db:
        user = AuthService(db, settings, SystemClock()).create_user(email, PASSWORD)
        user_id = user.id
        db.commit()
    try:
        with (
            TestClient(app, base_url="https://testserver") as first,
            TestClient(app, base_url="https://testserver") as second,
        ):
            login(first, email)
            login(second, email)
            account = create_account(first)
            barrier = Barrier(2)
            payload = transaction_payload(account)
            headers_a = {**csrf_headers(first), "Idempotency-Key": "concurrent"}
            headers_b = {**csrf_headers(second), "Idempotency-Key": "concurrent"}

            def send(client: TestClient, headers: dict[str, str]) -> tuple[int, str]:
                barrier.wait(timeout=5)
                response = client.post("/api/v1/transactions", json=payload, headers=headers)
                return response.status_code, response.text

            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(send, first, headers_a)
                b = pool.submit(send, second, headers_b)
                results = [a.result(timeout=15), b.result(timeout=15)]
            assert results[0][0] == results[1][0] == 201, results
            assert results[0][1] == results[1][1]
            with Session(db_engine) as db:
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(Transaction)
                        .where(Transaction.user_id == user_id)
                    )
                    == 1
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(IdempotencyKey)
                        .where(IdempotencyKey.user_id == user_id)
                    )
                    == 1
                )
    finally:
        with Session(db_engine) as db:
            for model in (
                TransactionTag,
                IdempotencyKey,
                Transaction,
                SessionRow,
                Category,
                Account,
            ):
                db.execute(delete(model).where(model.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            db.commit()
