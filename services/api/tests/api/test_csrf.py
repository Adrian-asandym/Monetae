import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .conftest import PASSWORD, csrf_headers, login


@pytest.mark.parametrize("failure", ["missing", "tampered", "foreign", "null", "malformed"])
def test_login_csrf(client: TestClient, failure: str) -> None:
    headers = csrf_headers(client)
    if failure == "missing":
        del headers["X-CSRF-Token"]
    elif failure == "tampered":
        headers["X-CSRF-Token"] += "x"
    elif failure == "foreign":
        headers["Origin"] = "https://evil.example.test"
    elif failure == "null":
        headers["Origin"] = "null"
    else:
        headers["Origin"] = "https://[invalid"
    result = client.post(
        "/api/v1/auth/login",
        json={"method": "password", "email": "first@example.test", "password": PASSWORD},
        headers=headers,
    )
    assert result.status_code == 403
    assert result.json()["code"] == "csrf_failed"


def test_signed_token_and_session_binding(client: TestClient, application: FastAPI) -> None:
    login(client)
    own_token = client.cookies["monetae_csrf"]
    with TestClient(application, base_url="https://testserver") as other:
        login(other)
        foreign = other.cookies["monetae_csrf"]
    for token in [foreign, own_token[:-1] + ("a" if own_token[-1] != "a" else "b")]:
        client.cookies.set("monetae_csrf", token, domain="testserver.local", path="/")
        result = client.patch(
            "/api/v1/users/me",
            json={"locale": "en"},
            headers={"Origin": "https://testserver", "X-CSRF-Token": token},
        )
        assert result.status_code == 403 and result.json()["code"] == "csrf_failed"
    assert client.get("/api/v1/users/me").status_code == 200
    result = client.get("/api/v1/auth/csrf")
    assert (
        result.status_code == 200 and result.json()["csrf_token"] == client.cookies["monetae_csrf"]
    )


def test_get_exempt_and_csrf_endpoint_requires_session(client: TestClient) -> None:
    assert client.get("/api/v1/auth/csrf").status_code == 401
    assert client.cookies.get("monetae_csrf")
    login(client)
    assert (
        client.get("/api/v1/users/me", headers={"Origin": "https://evil.example.test"}).status_code
        == 200
    )
    assert client.post("/api/v1/auth/logout").status_code == 403
    assert client.get("/api/v1/users/me").status_code == 200


def test_referer_fallback_and_cors_origin(client: TestClient) -> None:
    headers = csrf_headers(client)
    del headers["Origin"]
    headers["Referer"] = "https://testserver/login?next=/"
    result = client.post(
        "/api/v1/auth/login",
        json={"method": "password", "email": "first@example.test", "password": PASSWORD},
        headers=headers,
    )
    assert result.status_code == 200
    headers = csrf_headers(client)
    headers["Origin"] = "https://web.example.test"
    assert (
        client.patch("/api/v1/users/me", json={"locale": "en"}, headers=headers).status_code == 200
    )
    headers["Origin"] = "https://evil.example.test"
    headers["Referer"] = "https://testserver/profile"
    assert (
        client.patch("/api/v1/users/me", json={"locale": "es"}, headers=headers).status_code == 403
    )


def test_cookie_issued_on_preflight_and_error(client: TestClient, application: FastAPI) -> None:
    client.cookies.clear()
    result = client.options(
        "/api/v1/health",
        headers={"Origin": "https://web.example.test", "Access-Control-Request-Method": "GET"},
    )
    assert result.status_code == 200 and client.cookies.get("monetae_csrf")
    client.cookies.clear()

    @application.get("/broken", response_model=None)
    def broken() -> None:
        raise RuntimeError("synthetic-sensitive-value")

    result = client.get("/broken")
    assert result.status_code == 500 and client.cookies.get("monetae_csrf")
    assert "synthetic-sensitive-value" not in result.text
