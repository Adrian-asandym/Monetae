"""Sesiones PostgreSQL independientes: locks ordenados y lecturas MVCC."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Barrier
from time import perf_counter
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, select, text
from sqlalchemy.orm import Session

from monetae.api.main import create_app
from monetae.api.schemas.transactions import TransactionBatch, TransactionCreate, TransactionUpdate
from monetae.api.schemas.transfers import TransferCreate, TransferUpdate
from monetae.db.models import Account, Transaction, TransactionTag
from monetae.services.transactions import TransactionService
from monetae.services.transfers import TransferService

from .conftest import transaction_payload, transfer_payload
from .test_session_concurrency import AuthData
from .test_session_concurrency import committed_auth as committed_auth  # noqa: F401 -- fixture


@dataclass(frozen=True)
class LedgerData:
    auth: AuthData
    group_id: UUID
    transaction_ids: tuple[UUID, UUID]


@pytest.fixture
def committed_ledger(db_engine: Engine, committed_auth: AuthData) -> Iterator[LedgerData]:
    owner = committed_auth.user_id
    with Session(db_engine) as db:
        source = Account(user_id=owner, name="Source", type="cash", currency="PEN")
        target = Account(user_id=owner, name="Target", type="bank", currency="PEN")
        db.add_all([source, target])
        db.flush()
        transfers = TransferService(db, committed_auth.settings.secret_key)
        pair = transfers.create(
            owner, TransferCreate.model_validate(transfer_payload(str(source.id), str(target.id)))
        )
        group = pair.outgoing.transfer_group_id
        assert group is not None
        transactions = TransactionService(db, committed_auth.settings.secret_key)
        ids = tuple(
            transactions.create(
                owner, TransactionCreate.model_validate(transaction_payload(str(source.id)))
            ).id
            for _ in range(2)
        )
        data = LedgerData(committed_auth, group, (ids[0], ids[1]))
        db.commit()
    try:
        yield data
    finally:
        with Session(db_engine) as db:
            for model in (TransactionTag, Transaction, Account):
                db.execute(delete(model).where(model.user_id == owner))
            db.commit()


def test_concurrent_transfer_patches_serialize_without_lost_fields(
    db_engine: Engine,
    committed_ledger: LedgerData,
) -> None:
    data = committed_ledger
    barrier = Barrier(2)

    def patch(values: dict[str, object]) -> None:
        with Session(db_engine) as db:
            db.execute(text("SET LOCAL lock_timeout = '3s'"))
            db.execute(text("SET LOCAL statement_timeout = '5s'"))
            service = TransferService(db, data.auth.settings.secret_key)
            # Simula un snapshot ORM anterior al lock; expire_all debe recargarlo.
            service.get(data.auth.user_id, data.group_id)
            barrier.wait(timeout=5)
            service.update(data.auth.user_id, data.group_id, TransferUpdate.model_validate(values))
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(patch, {"from_amount": "20.00", "to_amount": "20.00", "title": "Changed"})
        two = pool.submit(patch, {"note": "Independent change"})
        one.result(timeout=10)
        two.result(timeout=10)
    with Session(db_engine) as db:
        pair = TransferService(db, data.auth.settings.secret_key).get(
            data.auth.user_id, data.group_id
        )
        assert pair.outgoing.amount == -pair.incoming.amount == -20
        for row in (pair.outgoing, pair.incoming):
            assert row.title == "Changed" and row.note == "Independent change"
            assert row.status == "posted" and row.deleted_at is None
        assert pair.outgoing.occurred_at == pair.incoming.occurred_at


def test_overlapping_batches_with_crossed_ids_do_not_deadlock(
    db_engine: Engine,
    committed_ledger: LedgerData,
) -> None:
    data = committed_ledger
    barrier = Barrier(2)

    def edit(ids: tuple[UUID, UUID], changes: dict[str, object]) -> None:
        with Session(db_engine) as db:
            db.execute(text("SET LOCAL lock_timeout = '3s'"))
            db.execute(text("SET LOCAL statement_timeout = '5s'"))
            barrier.wait(timeout=5)
            payload = TransactionBatch.model_validate(
                {
                    "transaction_ids": list(ids),
                    "action": "edit",
                    "changes": changes,
                }
            )
            assert (
                TransactionService(db, data.auth.settings.secret_key).batch(
                    data.auth.user_id, payload
                )
                == 2
            )
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(edit, data.transaction_ids, {"title": "Changed"})
        two = pool.submit(
            edit, (data.transaction_ids[1], data.transaction_ids[0]), {"note": "Independent change"}
        )
        one.result(timeout=10)
        two.result(timeout=10)
    with Session(db_engine) as db:
        rows = list(
            db.scalars(
                select(Transaction).where(
                    Transaction.user_id == data.auth.user_id,
                    Transaction.id.in_(data.transaction_ids),
                )
            )
        )
        assert len(rows) == 2
        assert all(row.title == "Changed" and row.note == "Independent change" for row in rows)


def test_http_reads_do_not_wait_for_inflight_writes(
    db_engine: Engine,
    database_url: str,
    committed_ledger: LedgerData,
) -> None:
    data = committed_ledger
    app = create_app(data.auth.settings.model_copy(update={"database_url": database_url}))
    app.state.clock = data.auth.clock
    with Session(db_engine) as writer, TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("monetae_session", data.auth.tokens[0])
        # Prepara el pool y las rutas antes de medir locks, no el primer connect DBAPI.
        for path in ("/api/v1/transfers", "/api/v1/transactions"):
            assert client.get(path).status_code == 200
        TransferService(writer, data.auth.settings.secret_key).update(
            data.auth.user_id, data.group_id, TransferUpdate(from_amount="20.00", to_amount="20.00")
        )
        TransactionService(writer, data.auth.settings.secret_key).update(
            data.auth.user_id, data.transaction_ids[0], TransactionUpdate(title="Uncommitted")
        )
        for path in ("/api/v1/transfers", "/api/v1/transactions"):
            start = perf_counter()
            with ThreadPoolExecutor(max_workers=1) as pool:
                response = pool.submit(client.get, path).result(timeout=2)
            elapsed = perf_counter() - start
            assert response.status_code == 200, response.text
            assert elapsed < 0.300, f"{path} blocked for {elapsed * 1000:.1f} ms"
            print(f"{path}: {elapsed * 1000:.1f} ms while writes are uncommitted")
            if path.endswith("transfers"):
                assert response.json()["items"][0]["from_amount"] == "10.00"
            else:
                assert all(row["title"] != "Uncommitted" for row in response.json()["items"])
        writer.rollback()
