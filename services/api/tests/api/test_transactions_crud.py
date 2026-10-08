from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.conftest import (
    create_account,
    create_category,
    create_transaction,
    csrf_headers,
    login,
    transaction_payload,
)


def test_transaction_crud_soft_delete_restore_and_nullable_fields(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    category = create_category(client)
    entity_id = create_transaction(client, account, category_id=category)
    url = f"/api/v1/transactions/{entity_id}"
    original = client.get(url).json()
    assert original["amount"] == "-10.00" and original["source"] == "web"
    assert original["fx_rate_to_base"] == "1.000000"
    assert "user_id" not in original and "raw_input" not in original
    updated = client.patch(
        url,
        json={"amount": "-20.00", "note": "changed", "category_id": None},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["note"] == "changed" and updated.json()["category_id"] is None
    assert updated.json()["fx_rate_to_base"] == original["fx_rate_to_base"]
    assert (
        client.patch(url, json={"note": None}, headers=csrf_headers(client)).json()["note"] is None
    )
    assert client.delete(url, headers=csrf_headers(client)).json()["affected_count"] == 1
    assert client.get(url).status_code == 404
    assert client.get(url + "?include_deleted=true").json()["deleted_at"] is not None
    assert client.get("/api/v1/transactions").json()["items"] == []
    assert len(client.get("/api/v1/transactions?include_deleted=true").json()["items"]) == 1
    restored = client.post(url + "/restore", headers=csrf_headers(client))
    assert restored.status_code == 200 and restored.json()["id"] == entity_id
    assert restored.json()["deleted_at"] is None


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"amount": "0.00"}, "invalid_amount"),
        ({"amount": "10.00"}, "invalid_amount"),
        ({"kind": "income", "amount": "-1.00"}, "invalid_amount"),
        ({"kind": "transfer"}, None),
        ({"kind": "loan"}, None),
        ({"currency": "USD"}, "currency_mismatch"),
        ({"fx_rate_to_base": "2.000000"}, "invalid_fx_rate"),
        ({"fx_rate_to_base": "0.000000"}, None),
        ({"fx_rate_to_base": "1.0"}, None),
        ({"amount": -1}, None),
        ({"amount": True}, None),
        ({"amount": "-1"}, None),
        ({"currency": "pen"}, None),
        ({"occurred_at": "2026-10-07T12:00:00"}, None),
        ({"status": "invalid"}, None),
        ({"fx_rate_source": "invalid"}, None),
        ({"user_id": str(uuid4())}, None),
        ({"source": "api"}, None),
        ({"is_initial_data": True}, None),
        ({"import_external_id": "synthetic"}, None),
        ({"transfer_group_id": str(uuid4())}, None),
    ],
)
def test_create_validation(
    client: TestClient, changes: dict[str, object], code: str | None
) -> None:
    login(client)
    account = create_account(client)
    response = client.post(
        "/api/v1/transactions",
        json=transaction_payload(account, **changes),
        headers=csrf_headers(client),
    )
    assert response.status_code == 422, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    if code is not None:
        assert response.json()["code"] == code
    assert client.get("/api/v1/transactions").json()["items"] == []


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"amount": None},
        {"account_id": None},
        {"kind": None},
        {"status": None},
        {"occurred_at": "2026-10-07T12:00:00"},
        {"tag_ids": None},
        {"source": "import"},
        {"is_initial_data": True},
        {"import_external_id": "x"},
        {"transfer_group_id": str(uuid4())},
        {"amount": "1.00"},
        {"kind": "income"},
    ],
)
def test_patch_validation(client: TestClient, changes: dict[str, object]) -> None:
    login(client)
    entity_id = create_transaction(client, create_account(client))
    response = client.patch(
        f"/api/v1/transactions/{entity_id}", json=changes, headers=csrf_headers(client)
    )
    assert response.status_code == 422
    assert client.get(f"/api/v1/transactions/{entity_id}").json()["amount"] == "-10.00"


def test_patch_kind_and_account_same_currency(client: TestClient) -> None:
    login(client)
    original = create_account(client)
    target = create_account(client, "Target")
    entity_id = create_transaction(client, original)
    response = client.patch(
        f"/api/v1/transactions/{entity_id}",
        json={"kind": "income", "amount": "20.00", "account_id": target},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200 and response.json()["account_id"] == target
    other = create_account(client, "Dollar")
    assert (
        client.patch(
            f"/api/v1/accounts/{other}", json={"currency": "USD"}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    mismatch = client.patch(
        f"/api/v1/transactions/{entity_id}",
        json={"account_id": other},
        headers=csrf_headers(client),
    )
    assert mismatch.status_code == 422 and mismatch.json()["code"] == "currency_mismatch"


@pytest.mark.parametrize("reference", ["account", "category"])
def test_restore_conflicts_with_deleted_reference(client: TestClient, reference: str) -> None:
    login(client)
    account, category = create_account(client), create_category(client)
    entity_id = create_transaction(client, account, category_id=category)
    client.delete(f"/api/v1/transactions/{entity_id}", headers=csrf_headers(client))
    resource = f"accounts/{account}" if reference == "account" else f"categories/{category}"
    assert client.delete(f"/api/v1/{resource}", headers=csrf_headers(client)).status_code == 200
    response = client.post(
        f"/api/v1/transactions/{entity_id}/restore", headers=csrf_headers(client)
    )
    assert response.status_code == 409 and response.json()["code"] == "restore_conflict"


def test_foreign_currency_keeps_historical_rate_and_scheduled_future(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    client.patch(
        f"/api/v1/accounts/{account}", json={"currency": "USD"}, headers=csrf_headers(client)
    )
    entity_id = create_transaction(
        client,
        account,
        currency="USD",
        fx_rate_to_base="3.800000",
        status="scheduled",
        occurred_at="2030-01-01T00:00:00-05:00",
    )
    updated = client.patch(
        f"/api/v1/transactions/{entity_id}", json={"title": "Changed"}, headers=csrf_headers(client)
    )
    assert updated.json()["fx_rate_to_base"] == "3.800000"
    assert updated.json()["status"] == "scheduled"


def test_transactions_require_session_and_csrf(client: TestClient) -> None:
    assert client.get("/api/v1/transactions").status_code == 401
    login(client)
    account = create_account(client)
    assert client.post("/api/v1/transactions", json=transaction_payload(account)).status_code == 403
