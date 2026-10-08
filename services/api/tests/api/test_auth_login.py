from unittest.mock import patch

import pytest
from argon2 import PasswordHasher
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae.db.models import Session as StoredSession
from monetae.db.models import User
from monetae.services.auth import DUMMY_HASH, PASSWORD_HASHER, token_hash

from .conftest import PASSWORD, csrf_headers, login


def test_login_cookies_rotation_hashes_and_logs(
    client: TestClient, db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"method": "password", "email": "FIRST@example.test", "password": PASSWORD},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    token = client.cookies["monetae_session"]
    csrf = client.cookies["monetae_csrf"]
    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookies if c.startswith("monetae_session="))
    csrf_cookie = next(c for c in cookies if c.startswith("monetae_csrf="))
    assert all(flag in session_cookie for flag in ["HttpOnly", "Secure", "SameSite=lax", "Path=/"])
    assert all(flag in csrf_cookie for flag in ["Secure", "SameSite=lax", "Path=/"])
    assert "HttpOnly" not in csrf_cookie
    assert response.json()["csrf_token"] == csrf
    stored = db_session.scalar(select(StoredSession))
    assert stored is not None and stored.token_hash == token_hash(token)
    assert stored.token_hash != token.encode()
    assert token not in str(stored.__dict__)
    assert token not in caplog.text and PASSWORD not in caplog.text
    login(client)
    assert client.cookies["monetae_session"] != token
    assert client.cookies["monetae_csrf"] != csrf
    assert (
        db_session.scalar(
            select(StoredSession).where(StoredSession.token_hash == token_hash(token))
        )
        is not None
    )


def test_invalid_credentials_equal_and_dummy_verification(client: TestClient) -> None:
    with patch.object(PasswordHasher, "verify", side_effect=PASSWORD_HASHER.verify) as verify:
        first = client.post(
            "/api/v1/auth/login",
            json={"method": "password", "email": "first@example.test", "password": "incorrect"},
            headers=csrf_headers(client),
        )
        missing = client.post(
            "/api/v1/auth/login",
            json={"method": "password", "email": "missing@example.test", "password": "incorrect"},
            headers=csrf_headers(client),
        )
    assert first.status_code == missing.status_code == 401
    assert first.json() == missing.json()
    assert first.json()["code"] == "invalid_credentials"
    assert verify.call_count == 2
    assert verify.call_args_list[1].args[0] == DUMMY_HASH
    assert first.headers["content-type"] == "application/problem+json"


def test_rehash(client: TestClient, db_session: Session, auth_users: tuple[User, User]) -> None:
    user = auth_users[0]
    old = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash(PASSWORD)
    user.password_hash = old
    db_session.commit()
    login(client)
    db_session.refresh(user)
    assert user.password_hash is not None and user.password_hash != old
    assert not PASSWORD_HASHER.check_needs_rehash(user.password_hash)


def test_google_not_available_and_no_registration(client: TestClient, application: FastAPI) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"method": "google"}, headers=csrf_headers(client)
    )
    assert response.status_code == 501
    assert response.json()["code"] == "google_login_not_available"
    assert client.post("/api/v1/auth/register", headers=csrf_headers(client)).status_code == 404
