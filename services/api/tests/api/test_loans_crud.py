from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from monetae.db.models import Account, Person

from .conftest import (
    add_movement,
    create_account,
    create_loan,
    create_person,
    csrf_headers,
    loan_payload,
    login,
    payment_payload,
)


def test_create_atomic_metadata_idempotency_and_person_in_use(client: TestClient) -> None:
    login(client)
    account = create_account(client, initial_balance="0.00")
    person = create_person(client)
    payload = loan_payload(person, account, direction="borrowed")
    headers = {**csrf_headers(client), "Idempotency-Key": "loan-create"}
    first = client.post("/api/v1/loans", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    assert client.post("/api/v1/loans", json=payload, headers=headers).json() == first.json()
    assert len(client.get("/api/v1/transactions").json()["items"]) == 1
    assert (
        client.post(
            "/api/v1/loans", json={**payload, "note": "changed"}, headers=headers
        ).status_code
        == 409
    )
    loan = first.json()["id"]
    assert (
        client.delete(f"/api/v1/people/{person}", headers=csrf_headers(client)).json()["code"]
        == "person_in_use"
    )
    result = client.patch(
        f"/api/v1/loans/{loan}",
        json={"note": "updated", "due_on": "2026-11-01"},
        headers=csrf_headers(client),
    )
    assert result.status_code == 200 and result.json()["note"] == "updated"
    assert result.json()["due_on"] == "2026-11-01"
    assert (
        client.patch(
            f"/api/v1/loans/{loan}", json={"principal": "1.00"}, headers=csrf_headers(client)
        ).status_code
        == 422
    )
    invalid = loan_payload(person, account, principal="300.00")
    invalid["disbursement"] = payload["disbursement"]
    failed = client.post("/api/v1/loans", json=invalid, headers=csrf_headers(client))
    assert failed.status_code == 409 and failed.json()["code"] == "ledger_inconsistent"
    assert len(client.get("/api/v1/loans").json()["items"]) == 1
    assert client.get(f"/api/v1/accounts/{account}").json()["balance"] == "200.00"


def test_loan_delete_restore_preserves_previously_deleted_movements(client: TestClient) -> None:
    login(client)
    account = create_account(client, initial_balance="0.00")
    person = create_person(client)
    loan = create_loan(client, person, account)
    payment = add_movement(client, loan, payment_payload(account, "50.00"))
    path = f"/api/v1/loans/{loan}"
    assert (
        client.delete(f"{path}/movements/{payment['id']}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert client.delete(path, headers=csrf_headers(client)).status_code == 200
    assert client.get(path).status_code == 404
    assert not client.get("/api/v1/transactions").json()["items"]
    assert len(client.get("/api/v1/transactions?include_deleted=true").json()["items"]) == 2
    assert client.get(f"/api/v1/accounts/{account}").json()["balance"] == "0.00"
    assert client.post(f"{path}/restore", headers=csrf_headers(client)).status_code == 200
    assert client.get(path).json()["outstanding"] == "200.00"
    assert len(client.get(f"{path}/movements").json()["items"]) == 1
    assert len(client.get("/api/v1/transactions").json()["items"]) == 1
    assert client.get(f"/api/v1/accounts/{account}").json()["balance"] == "-200.00"


def test_restore_conflict_person_and_account_are_atomic(
    client: TestClient, db_session: Session
) -> None:
    login(client)
    account = create_account(client)
    person = create_person(client)
    loan = create_loan(client, person, account)
    path = f"/api/v1/loans/{loan}"
    client.delete(path, headers=csrf_headers(client))
    assert (
        client.delete(f"/api/v1/people/{person}", headers=csrf_headers(client)).status_code == 200
    )
    assert (
        client.post(f"{path}/restore", headers=csrf_headers(client)).json()["code"]
        == "restore_conflict"
    )
    row = db_session.get(Person, UUID(person))
    assert row is not None
    row.deleted_at = None
    db_session.flush()
    assert (
        client.delete(f"/api/v1/accounts/{account}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert (
        client.post(f"{path}/restore", headers=csrf_headers(client)).json()["code"]
        == "restore_conflict"
    )
    assert client.get(path).status_code == 404
    assert not client.get("/api/v1/transactions").json()["items"]
    account_row = db_session.get(Account, UUID(account))
    assert account_row is not None
    account_row.deleted_at = None
    db_session.flush()
    assert client.post(f"{path}/restore", headers=csrf_headers(client)).status_code == 200
