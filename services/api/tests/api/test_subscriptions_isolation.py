from fastapi.testclient import TestClient

from .conftest import (
    create_account,
    create_category,
    create_subscription,
    csrf_headers,
    login,
    subscription_payload,
    transaction_payload,
)


def test_every_operation_isolated_between_users(client: TestClient) -> None:
    login(client)
    account_a = create_account(client)
    category_a = create_category(client)
    entity_a = create_subscription(client, account_a)
    archived_a = create_subscription(client, account_a)
    assert (
        client.post(
            f"/api/v1/subscriptions/{archived_a}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    login(client, "second@example.test")
    account_b = create_account(client, currency="USD")
    entity_b = create_subscription(client, account_b, currency="USD")
    assert [r["id"] for r in client.get("/api/v1/subscriptions").json()["items"]] == [entity_b]
    assert client.get("/api/v1/subscriptions?status=archived").json()["items"] == []
    assert [r["currency"] for r in client.get("/api/v1/subscriptions/totals").json()["items"]] == [
        "USD"
    ]
    headers = csrf_headers(client)
    path = f"/api/v1/subscriptions/{entity_a}"
    for result in [
        client.get(path),
        client.patch(path, json={"title": "Changed"}, headers=headers),
        client.delete(path, headers=headers),
        client.post(path + "/archive", json={}, headers=headers),
        client.post(f"/api/v1/subscriptions/{archived_a}/reactivate", headers=headers),
    ]:
        assert result.status_code == 404, result.text
    for values in [
        {"account_id": account_a, "currency": "PEN", "fx_rate_to_base": "3.800000"},
        {"category_id": category_a},
    ]:
        result = client.post(
            "/api/v1/subscriptions",
            json={**subscription_payload(account_b, currency="USD"), **values},
            headers=headers,
        )
        assert result.status_code == 404, result.text
    expense = client.post(
        "/api/v1/transactions",
        json=transaction_payload(account_b, currency="USD", title="Netflix"),
        headers=headers,
    )
    assert expense.status_code == 201 and expense.json()["reactivation_suggestions"] == []
    login(client)
    assert client.get(f"/api/v1/subscriptions/{entity_a}").json()["title"] == "Netflix"
    assert client.get(f"/api/v1/subscriptions/{entity_b}").status_code == 404


def test_auth_csrf_and_injected_owner_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/subscriptions").status_code == 401
    assert client.get("/api/v1/subscriptions/totals").status_code == 401
    login(client)
    account = create_account(client)
    assert (
        client.post("/api/v1/subscriptions", json=subscription_payload(account)).status_code == 403
    )
    assert (
        client.post(
            "/api/v1/subscriptions",
            json=subscription_payload(account, user_id="foreign"),
            headers=csrf_headers(client),
        ).status_code
        == 422
    )
