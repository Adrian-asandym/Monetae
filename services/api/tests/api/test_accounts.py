from fastapi.testclient import TestClient

from api.conftest import create_account, csrf_headers, login


def test_account_crud_archive_currency_and_deleted_name(client: TestClient) -> None:
    login(client)
    account_id = create_account(client, "Everyday")
    assert client.get(f"/api/v1/accounts/{account_id}").json()["balance"] == "12.50"
    assert client.get("/api/v1/accounts?limit=1").json()["items"][0]["name"] == "Everyday"
    duplicate = client.post(
        "/api/v1/accounts",
        json={"name": "everyday", "type": "cash", "currency": "PEN", "initial_balance": "0.00"},
        headers=csrf_headers(client),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate_name"

    currency_result = client.patch(
        f"/api/v1/accounts/{account_id}",
        json={"currency": "USD"},
        headers=csrf_headers(client),
    )
    assert currency_result.status_code == 409
    assert currency_result.json()["code"] == "account_currency_locked"

    updated = client.patch(
        f"/api/v1/accounts/{account_id}",
        json={"name": "Daily", "color": "blue"},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Daily"

    archived = client.post(
        f"/api/v1/accounts/{account_id}/archive", json={}, headers=csrf_headers(client)
    )
    assert archived.status_code == 200
    assert client.get("/api/v1/accounts").json()["items"] == []
    assert len(client.get("/api/v1/accounts?include_archived=true").json()["items"]) == 1
    assert (
        client.post(
            f"/api/v1/accounts/{account_id}/reactivate", headers=csrf_headers(client)
        ).status_code
        == 200
    )

    assert client.delete(f"/api/v1/accounts/{account_id}", headers=csrf_headers(client)).json() == {
        "success": True,
        "affected_count": 1,
    }
    assert (
        client.post(
            "/api/v1/accounts",
            json={"name": "Daily", "type": "cash", "currency": "PEN", "initial_balance": "0.00"},
            headers=csrf_headers(client),
        ).status_code
        == 201
    )


def test_account_validation_auth_and_csrf(client: TestClient) -> None:
    login(client)
    bad = client.post(
        "/api/v1/accounts",
        json={"name": "Wallet", "type": "invalid", "currency": "pen", "initial_balance": 2.0},
        headers=csrf_headers(client),
    )
    assert bad.status_code == 422
    assert bad.headers["content-type"].startswith("application/problem+json")
    assert bad.json()["errors"]

    no_csrf = client.post(
        "/api/v1/accounts",
        json={"name": "Wallet", "type": "cash", "currency": "PEN", "initial_balance": "0.00"},
        headers={"Origin": "https://testserver"},
    )
    assert no_csrf.status_code == 403


def test_unauthenticated_account_list_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/accounts")
    assert response.status_code == 401
