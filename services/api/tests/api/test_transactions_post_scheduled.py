import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .conftest import create_account, create_transaction, create_transfer, csrf_headers, login
from .test_account_balance import balance


@pytest.mark.parametrize(
    "changes", [None, {"amount": "-20.00", "occurred_at": "2026-10-08T00:00:00Z", "title": "Paid"}]
)
def test_post_scheduled_changes_balance(
    client: TestClient, changes: dict[str, object] | None
) -> None:
    login(client)
    account = create_account(client)
    id = create_transaction(client, account, status="scheduled")
    assert balance(client, account) == "12.50"
    response = client.post(
        f"/api/v1/transactions/{id}/post", json=changes, headers=csrf_headers(client)
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "posted"
    assert balance(client, account) == ("-7.50" if changes else "2.50")
    if changes:
        assert all(response.json()[key] == value for key, value in changes.items())
    response = client.post(f"/api/v1/transactions/{id}/post", headers=csrf_headers(client))
    assert response.status_code == 409 and response.json()["code"] == "not_scheduled"
    assert (
        client.patch(
            f"/api/v1/transactions/{id}", json={"status": "scheduled"}, headers=csrf_headers(client)
        ).status_code
        == 409
    )


def test_foreign_rate_and_invalid_update_are_atomic(client: TestClient) -> None:
    login(client)
    account = create_account(client, currency="USD")
    id = create_transaction(
        client,
        account,
        currency="USD",
        amount="-100.00",
        fx_rate_to_base="3.700000",
        status="scheduled",
    )
    before = client.get(f"/api/v1/transactions/{id}").json()
    for body in (
        {"amount": "1.00"},
        {"fx_rate_to_base": "0.000000"},
        {"occurred_at": "2026-10-07"},
    ):
        assert (
            client.post(
                f"/api/v1/transactions/{id}/post", json=body, headers=csrf_headers(client)
            ).status_code
            == 422
        )
        assert client.get(f"/api/v1/transactions/{id}").json() == before
    response = client.post(
        f"/api/v1/transactions/{id}/post",
        json={"fx_rate_to_base": "3.800000", "amount": "-90.00"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200 and response.json()["fx_rate_to_base"] == "3.800000"
    assert balance(client, account) == "-77.50"


def test_transfer_and_deleted_rejected(client: TestClient) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    id = create_transfer(client, source, target)
    leg = client.get(f"/api/v1/transfers/{id}").json()["incoming_transaction_id"]
    response = client.post(f"/api/v1/transactions/{leg}/post", headers=csrf_headers(client))
    assert response.status_code == 409 and response.json()["code"] == "not_scheduled"
    id = create_transaction(client, source, status="scheduled")
    client.delete(f"/api/v1/transactions/{id}", headers=csrf_headers(client))
    assert (
        client.post(f"/api/v1/transactions/{id}/post", headers=csrf_headers(client)).status_code
        == 404
    )


def test_post_isolation(client: TestClient, application: FastAPI) -> None:
    login(client)
    id = create_transaction(client, create_account(client), status="scheduled")
    with TestClient(application, base_url="https://testserver") as other:
        login(other, "second@example.test")
        assert (
            other.post(f"/api/v1/transactions/{id}/post", headers=csrf_headers(other)).status_code
            == 404
        )
    assert client.get(f"/api/v1/transactions/{id}").json()["status"] == "scheduled"
