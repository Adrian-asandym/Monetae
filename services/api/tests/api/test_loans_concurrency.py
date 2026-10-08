"""Carreras HTTP con conexiones PostgreSQL y commits reales, sin savepoints compartidos."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Barrier, Event
from time import perf_counter
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from monetae.api.main import create_app
from monetae.api.schemas.loans import PaymentRequest
from monetae.config import Settings
from monetae.db.models import (
    Account,
    Category,
    IdempotencyKey,
    Loan,
    LoanMovement,
    LoginAttempt,
    Person,
    Transaction,
    TransactionTag,
    User,
)
from monetae.db.models import (
    Session as SessionRow,
)
from monetae.services.auth import AuthService, SystemClock
from monetae.services.loans import LoanService

from .conftest import (
    PASSWORD,
    create_account,
    create_loan,
    create_person,
    csrf_headers,
    loan_payload,
    login,
    payment_payload,
)


@contextmanager
def committed_clients(
    engine: Engine, database_url: str
) -> Iterator[tuple[FastAPI, TestClient, TestClient, UUID]]:
    settings = Settings(
        environment="test", database_url=database_url, cors_origins=["https://testserver"]
    )
    app = create_app(settings)
    email = f"loan-concurrency-{uuid4().hex}@example.test"
    with Session(engine) as db:
        user_id = AuthService(db, settings, SystemClock()).create_user(email, PASSWORD).id
        db.commit()
    try:
        with (
            TestClient(app, base_url="https://testserver") as first,
            TestClient(app, base_url="https://testserver") as second,
        ):
            login(first, email)
            login(second, email)
            yield app, first, second, user_id
    finally:
        with Session(engine) as db:
            db.execute(delete(LoginAttempt).where(LoginAttempt.email_lower == email))
            for model in (
                LoanMovement,
                Loan,
                TransactionTag,
                IdempotencyKey,
                Transaction,
                SessionRow,
                Category,
                Account,
                Person,
            ):
                db.execute(delete(model).where(model.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            db.commit()


@pytest.mark.parametrize("amount", ["150.00", "100.00"])
def test_concurrent_payments_serialize_without_negative_balance(
    db_engine: Engine, database_url: str, amount: str
) -> None:
    with committed_clients(db_engine, database_url) as (_, first, second, _):
        account = create_account(first, initial_balance="0.00")
        loan = create_loan(first, create_person(first), account)
        barrier = Barrier(2)

        def send(client: TestClient) -> tuple[int, str]:
            headers = csrf_headers(client)
            barrier.wait(timeout=5)
            response = client.post(
                f"/api/v1/loans/{loan}/movements",
                json=payment_payload(account, amount),
                headers=headers,
            )
            return response.status_code, response.text

        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(send, first), pool.submit(send, second)
            results = [a.result(timeout=15), b.result(timeout=15)]
        assert sorted(code for code, _ in results) == (
            [201, 422] if amount == "150.00" else [201, 201]
        ), results
        assert first.get(f"/api/v1/loans/{loan}/balance").json()["outstanding"] == (
            "50.00" if amount == "150.00" else "0.00"
        )
        assert first.get(f"/api/v1/accounts/{account}").json()["balance"] == (
            "-50.00" if amount == "150.00" else "0.00"
        )


@pytest.mark.parametrize("operation", ["loan", "movement"])
def test_concurrent_idempotency_creates_one_effect(
    db_engine: Engine, database_url: str, operation: str
) -> None:
    with committed_clients(db_engine, database_url) as (_, first, second, user_id):
        account = create_account(first)
        person = create_person(first)
        loan = create_loan(first, person, account) if operation == "movement" else None
        path = f"/api/v1/loans/{loan}/movements" if loan else "/api/v1/loans"
        payload = payment_payload(account, "50.00") if loan else loan_payload(person, account)
        barrier = Barrier(2)

        def send(client: TestClient) -> tuple[int, str]:
            headers = {**csrf_headers(client), "Idempotency-Key": "concurrent-loan"}
            barrier.wait(timeout=5)
            response = client.post(path, json=payload, headers=headers)
            return response.status_code, response.text

        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(send, first), pool.submit(send, second)
            results = [a.result(timeout=15), b.result(timeout=15)]
        assert results[0] == results[1] and results[0][0] == 201, results
        with Session(db_engine) as db:
            assert (
                db.scalar(select(func.count()).select_from(Loan).where(Loan.user_id == user_id))
                == 1
            )
            assert db.scalar(
                select(func.count())
                .select_from(LoanMovement)
                .where(LoanMovement.user_id == user_id)
            ) == (2 if loan else 1)
            assert db.scalar(
                select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)
            ) == (2 if loan else 1)
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(IdempotencyKey)
                    .where(IdempotencyKey.user_id == user_id)
                )
                == 1
            )


def test_reads_do_not_wait_for_loan_write_in_flight(db_engine: Engine, database_url: str) -> None:
    with committed_clients(db_engine, database_url) as (_, first, _, user_id):
        account = create_account(first)
        loan = create_loan(first, create_person(first), account)
        ready, release = Event(), Event()

        def write() -> None:
            with Session(db_engine) as db:
                service = LoanService(db, "test")
                payload = PaymentRequest.model_validate(payment_payload(account, "50.00"))
                service.add_movement(user_id, UUID(loan), payload)
                ready.set()
                assert release.wait(timeout=10)
                db.rollback()

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(write)
            try:
                assert ready.wait(timeout=5)
                for path in (
                    f"/api/v1/loans/{loan}",
                    f"/api/v1/loans/{loan}/balance",
                    f"/api/v1/loans/{loan}/movements",
                    "/api/v1/loans",
                    "/api/v1/loans/summary",
                    "/api/v1/transactions",
                ):
                    start = perf_counter()
                    response = first.get(path)
                    elapsed_ms = (perf_counter() - start) * 1000
                    assert response.status_code == 200, response.text
                    assert elapsed_ms < 750, (path, elapsed_ms)
                assert first.get(f"/api/v1/loans/{loan}").json()["outstanding"] == "200.00"
            finally:
                release.set()
                future.result(timeout=10)
