from fastapi.testclient import TestClient

from .conftest import (
    add_movement,
    create_account,
    create_loan,
    create_person,
    csrf_headers,
    login,
    payment_payload,
)


def test_edit_delete_restore_validate_whole_ledger_and_rollback(client: TestClient) -> None:
    login(client)
    account = create_account(client, initial_balance="0.00")
    other = create_account(client, name="Other", initial_balance="0.00")
    loan = create_loan(client, create_person(client), account)
    path = f"/api/v1/loans/{loan}/movements"
    interest_payload = {
        "kind": "interest",
        "amount_in_loan_currency": "10.00",
        "occurred_at": "2026-10-02T00:00:00Z",
    }
    interest = add_movement(client, loan, interest_payload)
    first = add_movement(client, loan, payment_payload(account, "100.00"))
    second = add_movement(
        client, loan, payment_payload(account, "110.00", occurred_at="2026-10-03T00:00:00Z")
    )
    before = client.get(path).json()
    for method, target, payload in [
        ("DELETE", interest["id"], None),
        ("PUT", interest["id"], {**interest_payload, "amount_in_loan_currency": "5.00"}),
        ("PUT", first["id"], payment_payload(other, "150.00")),
    ]:
        result = client.request(
            method, f"{path}/{target}", json=payload, headers=csrf_headers(client)
        )
        assert result.status_code == 409, result.text
        assert result.json()["code"] == "ledger_inconsistent"
        assert isinstance(result.json()["movement_index"], int)
        assert client.get(path).json() == before
        assert client.get(f"/api/v1/accounts/{account}").json()["balance"] == "10.00"
        assert client.get(f"/api/v1/accounts/{other}").json()["balance"] == "0.00"
    # Pago conserva su secuencia aunque cambie la cuenta.
    response = client.put(
        f"{path}/{first['id']}", json=payment_payload(other, "100.00"), headers=csrf_headers(client)
    )
    assert response.status_code == 200, response.text
    assert response.json()["account_id"] == other
    assert response.json()["transaction_id"] == first["transaction_id"]
    assert client.get(f"/api/v1/accounts/{account}").json()["balance"] == "-90.00"
    assert client.get(f"/api/v1/accounts/{other}").json()["balance"] == "100.00"
    assert client.delete(f"{path}/{second['id']}", headers=csrf_headers(client)).status_code == 200
    replacement = add_movement(
        client, loan, payment_payload(other, "110.00", occurred_at="2026-10-04T00:00:00Z")
    )
    result = client.post(f"{path}/{second['id']}/restore", headers=csrf_headers(client))
    assert result.status_code == 409 and result.json()["code"] == "ledger_inconsistent"
    assert client.get(f"/api/v1/loans/{loan}").json()["status"] == "settled"
    assert (
        client.delete(f"{path}/{replacement['id']}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert (
        client.post(f"{path}/{second['id']}/restore", headers=csrf_headers(client)).status_code
        == 200
    )
    assert client.get(f"/api/v1/loans/{loan}").json()["status"] == "settled"


def test_disbursement_edit_updates_principal_and_cannot_be_deleted(client: TestClient) -> None:
    login(client)
    account = create_account(client, initial_balance="0.00")
    loan = create_loan(client, create_person(client), account)
    path = f"/api/v1/loans/{loan}/movements"
    disbursement = client.get(path).json()["items"][0]
    add_movement(client, loan, payment_payload(account, "200.00"))
    invalid = {
        **payment_payload(account, "100.00", occurred_at="2026-10-01T12:00:00Z"),
        "kind": "disbursement",
    }
    assert (
        client.put(
            f"{path}/{disbursement['id']}", json=invalid, headers=csrf_headers(client)
        ).status_code
        == 409
    )
    assert client.get(f"/api/v1/loans/{loan}").json()["principal"] == "200.00"
    valid = {**invalid, "amount_in_loan_currency": "250.00", "account_amount": "250.00"}
    result = client.put(f"{path}/{disbursement['id']}", json=valid, headers=csrf_headers(client))
    assert result.status_code == 200, result.text
    loan_row = client.get(f"/api/v1/loans/{loan}").json()
    assert loan_row["principal"] == "250.00" and loan_row["outstanding"] == "50.00"
    assert client.get(f"/api/v1/accounts/{account}").json()["balance"] == "-50.00"
    assert (
        client.delete(f"{path}/{disbursement['id']}", headers=csrf_headers(client)).status_code
        == 409
    )
    result = client.put(
        f"{path}/{disbursement['id']}",
        json=payment_payload(account, "250.00"),
        headers=csrf_headers(client),
    )
    assert result.status_code == 422 and result.json()["code"] == "movement_kind_immutable"


def test_changing_date_revalidates_and_adjustments_only_touch_capital(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    loan = create_loan(client, create_person(client), account)
    interest_payload = {
        "kind": "interest",
        "amount_in_loan_currency": "10.00",
        "occurred_at": "2026-10-02T00:00:00Z",
    }
    interest = add_movement(client, loan, interest_payload)
    add_movement(client, loan, payment_payload(account, "10.00"))
    result = client.put(
        f"/api/v1/loans/{loan}/movements/{interest['id']}",
        json={**interest_payload, "occurred_at": "2026-10-03T00:00:00Z"},
        headers=csrf_headers(client),
    )
    assert result.status_code == 409 and result.json()["movement_index"] == 1
    add_movement(
        client,
        loan,
        {
            "kind": "adjustment",
            "amount_in_loan_currency": "-200.00",
            "occurred_at": "2026-10-04T00:00:00Z",
        },
    )
    assert client.get(f"/api/v1/loans/{loan}").json()["status"] == "settled"
