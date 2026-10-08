from collections.abc import Iterator
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


def create_account(client: TestClient, name: str = "Wallet") -> str:
    result = client.post(
        "/api/v1/accounts",
        json={"name": name, "type": "cash", "currency": "PEN", "initial_balance": "12.50"},
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
