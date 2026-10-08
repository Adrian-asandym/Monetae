from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae.db.models import LoginAttempt

from .conftest import FakeClock, csrf_headers, login


def fail(client: TestClient, email: str = "first@example.test") -> int:
    response = client.post(
        "/api/v1/auth/login",
        json={"method": "password", "email": email, "password": "wrong"},
        headers=csrf_headers(client),
    )
    return int(response.status_code)


def test_email_limit_success_and_window(client: TestClient, clock: FakeClock) -> None:
    for _ in range(4):
        assert fail(client) == 401
    login(client)
    assert fail(client, "FIRST@example.test") == 401
    response = client.post(
        "/api/v1/auth/login",
        json={"method": "password", "email": "first@example.test", "password": "wrong"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 429 and response.json()["code"] == "too_many_attempts"
    assert response.headers["Retry-After"] == "900"
    clock.advance(minutes=15)
    login(client)


def test_ip_limit_and_purge(client: TestClient, clock: FakeClock, db_session: Session) -> None:
    for index in range(20):
        assert fail(client, f"unknown{index}@example.test") == 401
    assert fail(client, "another@example.test") == 429
    clock.advance(minutes=15)
    assert fail(client, "another@example.test") == 401
    clock.advance(days=8)
    assert fail(client, "new@example.test") == 401
    rows = db_session.scalars(select(LoginAttempt)).all()
    assert len(rows) == 1 and rows[0].attempted_at == clock.now()
