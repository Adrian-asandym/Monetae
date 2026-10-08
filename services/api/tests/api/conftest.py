from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from monetae.api.main import create_app
from monetae.api.security import database
from monetae.config import Settings
from monetae.db.models import User
from monetae.services.auth import AuthService

PASSWORD = "synthetic-password-123"


class FakeClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 10, 7, 12, tzinfo=UTC)

    def now(self) -> datetime:
        return self.value

    def advance(self, **parts: int) -> None:
        self.value += timedelta(**parts)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def application(db_session: Session, clock: FakeClock) -> FastAPI:
    app = create_app(
        Settings(
            environment="test",
            session_idle_minutes=10,
            session_absolute_days=1,
            cors_origins=["https://web.example.test"],
        )
    )
    app.state.clock = clock

    def override() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except BaseException:
            db_session.rollback()
            raise

    app.dependency_overrides[database] = override
    return app


@pytest.fixture
def auth_users(db_session: Session, application: FastAPI, clock: FakeClock) -> tuple[User, User]:
    service = AuthService(db_session, application.state.settings, clock)
    first = service.create_user("first@example.test", PASSWORD)
    second = service.create_user("second@example.test", PASSWORD, "USD", "en")
    db_session.commit()
    return first, second


@pytest.fixture
def client(application: FastAPI, auth_users: tuple[User, User]) -> Iterator[TestClient]:
    with TestClient(application, base_url="https://testserver") as client:
        yield client


def csrf_headers(client: TestClient) -> dict[str, str]:
    if not client.cookies.get("monetae_csrf"):
        client.get("/api/v1/health")
    return {"X-CSRF-Token": client.cookies["monetae_csrf"], "Origin": "https://testserver"}


def login(client: TestClient, email: str = "first@example.test", password: str = PASSWORD) -> None:
    result = client.post(
        "/api/v1/auth/login",
        json={"method": "password", "email": email, "password": password},
        headers=csrf_headers(client),
    )
    assert result.status_code == 200, result.text


def create_account(client: TestClient, name: str = "Wallet", **values: object) -> str:
    result = client.post(
        "/api/v1/accounts",
        json={
            "name": name,
            "type": "cash",
            "currency": "PEN",
            "initial_balance": "12.50",
            **values,
        },
        headers=csrf_headers(client),
    )
    assert result.status_code == 201, result.text
    entity_id = result.json()["id"]
    assert isinstance(entity_id, str)
    return entity_id


def create_category(client: TestClient, name: str = "Food", **values: object) -> str:
    result = client.post(
        "/api/v1/categories",
        json={"name": name, "kind": "expense", **values},
        headers=csrf_headers(client),
    )
    assert result.status_code == 201, result.text
    entity_id = result.json()["id"]
    assert isinstance(entity_id, str)
    return entity_id


def create_person(client: TestClient, name: str = "Morgan") -> str:
    result = client.post("/api/v1/people", json={"name": name}, headers=csrf_headers(client))
    assert result.status_code == 201, result.text
    entity_id = result.json()["id"]
    assert isinstance(entity_id, str)
    return entity_id


def create_tag(client: TestClient, name: str = "Travel") -> str:
    result = client.post("/api/v1/tags", json={"name": name}, headers=csrf_headers(client))
    assert result.status_code == 201, result.text
    entity_id = result.json()["id"]
    assert isinstance(entity_id, str)
    return entity_id


def transaction_payload(account_id: str, **values: object) -> dict[str, object]:
    return {
        "account_id": account_id,
        "kind": "expense",
        "amount": "-10.00",
        "currency": "PEN",
        "occurred_at": "2026-10-07T12:00:00Z",
        "status": "posted",
        "title": "Synthetic purchase",
        "fx_rate_to_base": "1.000000",
        "fx_rate_source": "manual",
        **values,
    }


def create_transaction(client: TestClient, account_id: str, **values: object) -> str:
    response = client.post(
        "/api/v1/transactions",
        json=transaction_payload(account_id, **values),
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    entity_id = response.json()["id"]
    assert isinstance(entity_id, str)
    return entity_id


def transfer_payload(from_account: str, to_account: str, **values: object) -> dict[str, object]:
    return {
        "from_account_id": from_account,
        "to_account_id": to_account,
        "from_amount": "10.00",
        "to_amount": "10.00",
        "from_fx_rate_to_base": "1.000000",
        "to_fx_rate_to_base": "1.000000",
        "fx_rate_source": "manual",
        "occurred_at": "2026-10-07T12:00:00Z",
        "title": "Synthetic transfer",
        **values,
    }


def create_transfer(
    client: TestClient, from_account: str, to_account: str, **values: object
) -> str:
    response = client.post(
        "/api/v1/transfers",
        json=transfer_payload(from_account, to_account, **values),
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    entity_id = response.json()["id"]
    assert isinstance(entity_id, str)
    return entity_id


def loan_payload(person_id: str, account_id: str, **values: object) -> dict[str, object]:
    principal = values.get("principal", "200.00")
    currency = values.get("currency", "PEN")
    return {
        "person_id": person_id,
        "direction": "lent",
        "currency": currency,
        "principal": principal,
        "opened_on": "2026-10-01",
        "disbursement": {
            "kind": "disbursement",
            "amount_in_loan_currency": principal,
            "account_id": account_id,
            "account_amount": principal,
            "account_currency": currency,
            "fx_rate_to_base": "1.000000",
            "fx_rate_source": "manual",
            "occurred_at": "2026-10-01T12:00:00Z",
        },
        **values,
    }


def create_loan(client: TestClient, person_id: str, account_id: str, **values: object) -> str:
    response = client.post(
        "/api/v1/loans",
        json=loan_payload(person_id, account_id, **values),
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    entity_id = response.json()["id"]
    assert isinstance(entity_id, str)
    return entity_id


def payment_payload(account_id: str, amount: str, **values: object) -> dict[str, object]:
    return {
        "kind": "payment",
        "amount_in_loan_currency": amount,
        "account_id": account_id,
        "account_amount": amount,
        "account_currency": "PEN",
        "fx_rate_to_base": "1.000000",
        "fx_rate_source": "manual",
        "occurred_at": "2026-10-02T12:00:00Z",
        **values,
    }


def add_movement(
    client: TestClient, loan_id: str, payload: Mapping[str, object]
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/loans/{loan_id}/movements", json=payload, headers=csrf_headers(client)
    )
    assert response.status_code == 201, response.text
    result: dict[str, object] = response.json()
    return result


def subscription_payload(account_id: str, **values: object) -> dict[str, object]:
    return {
        "title": "Netflix",
        "amount": "30.00",
        "currency": "PEN",
        "account_id": account_id,
        "period": "monthly",
        "next_due_on": "2026-11-01",
        **values,
    }


def create_subscription(client: TestClient, account_id: str, **values: object) -> str:
    response = client.post(
        "/api/v1/subscriptions",
        json=subscription_payload(account_id, **values),
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    entity_id = response.json()["id"]
    assert isinstance(entity_id, str)
    return entity_id


def scheduled_for(client: TestClient, subscription_id: str) -> list[dict[str, object]]:
    subscription = client.get(f"/api/v1/subscriptions/{subscription_id}").json()
    response = client.get("/api/v1/transactions", params={"status": "scheduled", "limit": 200})
    assert response.status_code == 200, response.text
    items: list[dict[str, object]] = response.json()["items"]
    return [
        item for item in items if item["recurring_rule_id"] == subscription["recurring_rule_id"]
    ]
