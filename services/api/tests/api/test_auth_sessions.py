from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae.db.models import Session as StoredSession

from .conftest import FakeClock, csrf_headers, login


def test_idle_expiry_and_minute_touch(
    client: TestClient, db_session: Session, clock: FakeClock
) -> None:
    login(client)
    row = db_session.scalar(select(StoredSession))
    assert row is not None
    start = row.last_seen_at
    clock.advance(seconds=59)
    assert client.get("/api/v1/users/me").status_code == 200
    db_session.refresh(row)
    assert row.last_seen_at == start
    clock.advance(seconds=1)
    assert client.get("/api/v1/users/me").status_code == 200
    db_session.refresh(row)
    assert row.last_seen_at == clock.now()
    clock.advance(minutes=10)
    assert client.get("/api/v1/users/me").status_code == 401


def test_absolute_expiry(client: TestClient, db_session: Session, clock: FakeClock) -> None:
    login(client)
    row = db_session.scalar(select(StoredSession))
    assert row is not None
    clock.advance(hours=23, minutes=59)
    row.last_seen_at = clock.now()
    row.expires_at = clock.now().replace(day=9)
    db_session.commit()
    assert client.get("/api/v1/users/me").status_code == 200
    clock.advance(minutes=1)
    assert client.get("/api/v1/users/me").status_code == 401


def test_isolation_revoke_and_logout_all(client: TestClient, application: FastAPI) -> None:
    login(client)
    with (
        TestClient(application, base_url="https://testserver") as second,
        TestClient(application, base_url="https://testserver") as other,
    ):
        login(second)
        login(other, "second@example.test")
        own = client.get("/api/v1/auth/sessions").json()["items"]
        foreign = other.get("/api/v1/auth/sessions").json()["items"]
        assert len(own) == 2 and len(foreign) == 1
        assert not {r["id"] for r in own} & {r["id"] for r in foreign}
        assert (
            client.delete(
                "/api/v1/auth/sessions/" + foreign[0]["id"], headers=csrf_headers(client)
            ).status_code
            == 404
        )
        target = next(r["id"] for r in own if not r["is_current"])
        assert (
            client.delete(
                "/api/v1/auth/sessions/" + target, headers=csrf_headers(client)
            ).status_code
            == 200
        )
        assert second.get("/api/v1/users/me").status_code == 401
        login(second)
        result = client.post("/api/v1/auth/logout-all", headers=csrf_headers(client))
        assert result.status_code == 200 and result.json()["affected_count"] == 2
        assert client.get("/api/v1/users/me").status_code == 401
        assert second.get("/api/v1/users/me").status_code == 401
        assert other.get("/api/v1/users/me").status_code == 200


def test_logout_and_revoke_current(client: TestClient) -> None:
    login(client)
    result = client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert result.status_code == 200
    expired_cookie = next(
        value
        for value in result.headers.get_list("set-cookie")
        if value.startswith("monetae_session=")
    )
    assert all(
        flag in expired_cookie
        for flag in ["Max-Age=0", "expires=", "HttpOnly", "Secure", "SameSite=lax", "Path=/"]
    )
    assert client.cookies.get("monetae_session") is None
    assert client.get("/api/v1/users/me").status_code == 401
    login(client)
    row = client.get("/api/v1/auth/sessions").json()["items"][0]
    assert (
        client.delete(
            "/api/v1/auth/sessions/" + row["id"], headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert client.get("/api/v1/users/me").status_code == 401


def test_pagination(client: TestClient) -> None:
    for _ in range(3):
        login(client)
    first = client.get("/api/v1/auth/sessions?limit=2").json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    second = client.get(
        "/api/v1/auth/sessions", params={"limit": 2, "cursor": first["next_cursor"]}
    ).json()
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    assert client.get("/api/v1/auth/sessions?cursor=bad").status_code == 400
