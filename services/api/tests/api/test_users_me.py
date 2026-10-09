import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from monetae.db.models import User

from .conftest import csrf_headers, login

DEFAULT_CARD = {
    "show_date": True,
    "show_time": False,
    "show_note": True,
    "show_tags": True,
    "show_account": False,
    "show_actions": False,
}


def test_profile_isolation_and_updates(client: TestClient, application: FastAPI) -> None:
    login(client)
    first = client.get("/api/v1/users/me").json()
    assert first["email"] == "first@example.test" and first["report_currency"] == "PEN"
    assert first["preferences"] == {"transaction_card": DEFAULT_CARD} and not first["locked"]
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
            "transaction_card": DEFAULT_CARD,
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
        assert second["id"] != first["id"]
        assert second["preferences"] == {"transaction_card": DEFAULT_CARD}
        assert second["email"] == "second@example.test"
    result = client.patch(
        "/api/v1/users/me", json={"base_currency": "USD"}, headers=csrf_headers(client)
    )
    assert result.status_code == 200 and result.json()["base_currency"] == "USD"
    assert result.json()["report_currency"] == "USD"


def test_legacy_preferences_include_card_defaults(
    client: TestClient, db_session: Session, auth_users: tuple[User, User]
) -> None:
    first, _ = auth_users
    first.preferences = {"theme": "dark", "home_widgets": ["balance"]}
    db_session.commit()
    login(client)
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json()["preferences"] == {
        "theme": "dark",
        "home_widgets": ["balance"],
        "transaction_card": DEFAULT_CARD,
    }
    db_session.refresh(first)
    assert "transaction_card" not in first.preferences


def test_card_preferences_replace_persist_and_isolate(
    client: TestClient,
    application: FastAPI,
    db_session: Session,
    auth_users: tuple[User, User],
) -> None:
    first, second = auth_users
    first.preferences = {
        "theme": "dark",
        "transaction_card": {"show_date": False, "show_account": True},
    }
    db_session.commit()
    login(client)
    response = client.patch(
        "/api/v1/users/me",
        json={"preferences": {"transaction_card": {"show_time": True, "show_actions": True}}},
        headers=csrf_headers(client),
    )
    expected = {"transaction_card": {**DEFAULT_CARD, "show_time": True, "show_actions": True}}
    assert response.status_code == 200
    assert response.json()["preferences"] == expected
    db_session.refresh(first)
    assert first.preferences == expected
    assert client.get("/api/v1/users/me").json()["preferences"] == expected
    with TestClient(application, base_url="https://testserver") as other:
        login(other, "second@example.test")
        assert other.get("/api/v1/users/me").json()["preferences"] == {
            "transaction_card": DEFAULT_CARD
        }
    db_session.refresh(second)
    assert second.preferences == {}
    # A profile PATCH without preferences leaves them intact.
    response = client.patch("/api/v1/users/me", json={"locale": "en"}, headers=csrf_headers(client))
    assert response.json()["preferences"] == expected
    # Supplying an empty preferences object replaces the saved card with defaults.
    response = client.patch(
        "/api/v1/users/me", json={"preferences": {}}, headers=csrf_headers(client)
    )
    assert response.json()["preferences"] == {"transaction_card": DEFAULT_CARD}
    db_session.refresh(first)
    assert first.preferences == {"transaction_card": DEFAULT_CARD}


@pytest.mark.parametrize("field", DEFAULT_CARD)
@pytest.mark.parametrize("value", ["true", 1, 0, None, [], {}])
def test_card_preferences_reject_non_booleans(
    client: TestClient, field: str, value: object
) -> None:
    login(client)
    response = client.patch(
        "/api/v1/users/me",
        json={"preferences": {"transaction_card": {field: value}}},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422


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
        {"preferences": {"transaction_card": {"unknown": True}}},
        {"preferences": {"transaction_card": None}},
    ],
)
def test_strict_patch(client: TestClient, changes: dict[str, object]) -> None:
    login(client)
    assert (
        client.patch("/api/v1/users/me", json=changes, headers=csrf_headers(client)).status_code
        == 422
    )
