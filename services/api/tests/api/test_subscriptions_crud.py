import pytest
from fastapi.testclient import TestClient

from .conftest import (
    create_account,
    create_category,
    create_subscription,
    csrf_headers,
    login,
    scheduled_for,
    subscription_payload,
)


def test_crud_and_rematerialization(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    category = create_category(client)
    entity = create_subscription(client, account, category_id=category)
    original = scheduled_for(client, entity)
    assert len(original) == 1
    assert original[0]["amount"] == "-30.00"
    updated = client.patch(
        f"/api/v1/subscriptions/{entity}",
        json={
            "title": "Streaming",
            "amount": "45.00",
            "period": "weekly",
            "interval_count": 2,
            "next_due_on": "2026-11-15",
            "category_id": None,
            "reminder_days_before": 3,
        },
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200, updated.text
    current = scheduled_for(client, entity)
    assert len(current) == 1 and current[0]["id"] != original[0]["id"]
    assert current[0]["amount"] == "-45.00" and current[0]["category_id"] is None
    assert client.get(f"/api/v1/transactions/{original[0]['id']}").status_code == 404
    assert (
        client.delete(f"/api/v1/subscriptions/{entity}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert client.get(f"/api/v1/subscriptions/{entity}").status_code == 404
    assert client.get("/api/v1/subscriptions").json()["items"] == []
    assert client.get("/api/v1/transactions", params={"status": "scheduled"}).json()["items"] == []


@pytest.mark.parametrize(
    "patch",
    [
        {},
        {"title": " "},
        {"amount": "0.00"},
        {"interval_count": 367},
        {"period": "quarterly"},
        {"reminder_days_before": -1},
        {"amount": 3.5},
        {"currency": None},
        {"user_id": "fake"},
    ],
)
def test_strict_patch(client: TestClient, patch: dict[str, object]) -> None:
    login(client)
    entity = create_subscription(client, create_account(client))
    response = client.patch(
        f"/api/v1/subscriptions/{entity}", json=patch, headers=csrf_headers(client)
    )
    assert response.status_code == 422
    assert len(scheduled_for(client, entity)) == 1


def test_currency_and_account_changes(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    other = create_account(client, "Other")
    foreign = create_account(client, "Dollar", currency="USD")
    entity = create_subscription(client, account)
    for patch in [{"currency": "USD"}, {"account_id": foreign}]:
        response = client.patch(
            f"/api/v1/subscriptions/{entity}", json=patch, headers=csrf_headers(client)
        )
        assert response.status_code == 422
        assert response.json()["code"] == "currency_mismatch"
    response = client.patch(
        f"/api/v1/subscriptions/{entity}", json={"account_id": other}, headers=csrf_headers(client)
    )
    assert response.status_code == 200 and response.json()["account_id"] == other


@pytest.mark.parametrize(
    ("currency", "rate", "expected", "code"),
    [
        ("PEN", None, 201, None),
        ("PEN", "1.000000", 201, None),
        ("PEN", "3.800000", 422, "invalid_fx_rate"),
        ("USD", None, 422, "fx_rate_required"),
        ("USD", "3.800000", 201, None),
    ],
)
def test_provisional_rates(
    client: TestClient, currency: str, rate: str | None, expected: int, code: str | None
) -> None:
    login(client)
    account = create_account(client, currency=currency)
    values: dict[str, object] = {"currency": currency}
    if rate is not None:
        values["fx_rate_to_base"] = rate
    response = client.post(
        "/api/v1/subscriptions",
        json=subscription_payload(account, **values),
        headers=csrf_headers(client),
    )
    assert response.status_code == expected, response.text
    if code:
        assert response.json()["code"] == code
        assert client.get("/api/v1/subscriptions").json()["items"] == []
    else:
        assert "fx_rate_to_base" not in response.json()
        assert scheduled_for(client, response.json()["id"])[0]["fx_rate_to_base"] == (
            rate or "1.000000"
        )


def test_pagination_status_and_duplicate_titles(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    entities = {create_subscription(client, account) for _ in range(3)}
    page = client.get("/api/v1/subscriptions?limit=2").json()
    assert len(page["items"]) == 2
    last = client.get(
        "/api/v1/subscriptions", params={"limit": 2, "cursor": page["next_cursor"]}
    ).json()
    assert {item["id"] for item in page["items"] + last["items"]} == entities
    assert last["next_cursor"] is None
    assert client.get("/api/v1/subscriptions?status=all").status_code == 422
    assert (
        client.get(
            "/api/v1/subscriptions", params={"status": "archived", "cursor": page["next_cursor"]}
        ).status_code
        == 400
    )
    assert client.get("/api/v1/subscriptions?cursor=bad").status_code == 400
    assert client.get("/api/v1/subscriptions/totals").status_code == 200


def test_patch_provisional_rate_validation_and_rematerialization(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    base = create_subscription(client, account)
    invalid = client.patch(
        f"/api/v1/subscriptions/{base}",
        json={"fx_rate_to_base": "2.000000"},
        headers=csrf_headers(client),
    )
    assert invalid.status_code == 422 and invalid.json()["code"] == "invalid_fx_rate"
    foreign = create_subscription(
        client,
        create_account(client, "USD", currency="USD"),
        currency="USD",
        fx_rate_to_base="3.800000",
    )
    old = scheduled_for(client, foreign)[0]
    response = client.patch(
        f"/api/v1/subscriptions/{foreign}",
        json={"fx_rate_to_base": "3.950000"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    new = scheduled_for(client, foreign)[0]
    assert new["id"] != old["id"] and new["fx_rate_to_base"] == "3.950000"
    assert (
        client.patch(
            f"/api/v1/subscriptions/{foreign}",
            json={"title": "Updated"},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )
    assert scheduled_for(client, foreign)[0]["fx_rate_to_base"] == "3.950000"
