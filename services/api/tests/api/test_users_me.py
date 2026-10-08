import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .conftest import csrf_headers, login


def test_profile_isolation_and_updates(client: TestClient, application: FastAPI) -> None:
    login(client)
    first = client.get("/api/v1/users/me").json()
    assert first["email"] == "first@example.test" and first["report_currency"] == "PEN"
    assert first["preferences"] == {} and not first["locked"]
    assert "password_hash" not in first and "user_id" not in first
    changes = {
        "locale": "en",
        "timezone": "UTC",
        "report_currency": "USD",
        "lock_after_minutes": 3,
        "preferences": {
            "theme": "dark",
            "accent_color": None,
            "home_widgets": ["loans", "balance"],
        },
    }
    updated = client.patch("/api/v1/users/me", json=changes, headers=csrf_headers(client))
    assert updated.status_code == 200
    for key, value in changes.items():
        assert updated.json()[key] == value
    assert (
        client.patch(
            "/api/v1/users/me", json={"lock_after_minutes": None}, headers=csrf_headers(client)
        ).json()["lock_after_minutes"]
        is None
    )
    with TestClient(application, base_url="https://testserver") as other:
        login(other, "second@example.test")
        second = other.get("/api/v1/users/me").json()
        assert second["id"] != first["id"] and second["preferences"] == {}
        assert second["email"] == "second@example.test"
    result = client.patch(
        "/api/v1/users/me", json={"base_currency": "USD"}, headers=csrf_headers(client)
    )
    assert result.status_code == 200 and result.json()["base_currency"] == "USD"
    assert result.json()["report_currency"] == "USD"


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"locale": "fr"},
        {"locale": None},
        {"user_id": "x"},
        {"lock_after_minutes": "5"},
        {"lock_after_minutes": True},
        {"lock_after_minutes": 0},
        {"report_currency": "pen"},
        {"timezone": "Unknown/Zone"},
        {"preferences": {"secret": "x"}},
        {"preferences": {"home_widgets": ["a", "a"]}},
        {"preferences": {"theme": None}},
    ],
)
def test_strict_patch(client: TestClient, changes: dict[str, object]) -> None:
    login(client)
    assert (
        client.patch("/api/v1/users/me", json=changes, headers=csrf_headers(client)).status_code
        == 422
    )
