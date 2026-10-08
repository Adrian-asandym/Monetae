import pytest
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


def test_interest_proposals_payment_split_write_off_and_reopening(client: TestClient) -> None:
    login(client)
    account = create_account(client, initial_balance="0.00")
    loan = create_loan(client, create_person(client), account)
    path = f"/api/v1/loans/{loan}"
    proposal = client.post(
        f"{path}/interest-proposal", json={"percentage": "5.000000"}, headers=csrf_headers(client)
    )
    assert proposal.status_code == 200 and proposal.json()["amount_in_loan_currency"] == "10.00"
    assert len(client.get(f"{path}/movements").json()["items"]) == 1
    assert (
        client.post(
            f"{path}/interest-proposal",
            json={"percentage": "5.123456"},
            headers=csrf_headers(client),
        ).status_code
        == 422
    )
    interest = {
        "kind": "interest",
        "amount_in_loan_currency": "10.00",
        "occurred_at": "2026-10-02T00:00:00Z",
    }
    add_movement(client, loan, interest)
    assert client.get(f"/api/v1/accounts/{account}").json()["balance"] == "-200.00"
    proposal = client.post(
        f"{path}/payment-proposal",
        json={"amount_in_loan_currency": "50.00"},
        headers=csrf_headers(client),
    )
    assert proposal.json()["interest_part"] == "10.00"
    assert proposal.json()["principal_part"] == "40.00"
    payment = add_movement(client, loan, payment_payload(account, "50.00"))
    assert payment["interest_part"] == "10.00" and payment["principal_part"] == "40.00"
    write_off = add_movement(
        client,
        loan,
        {
            "kind": "write_off",
            "amount_in_loan_currency": "160.00",
            "interest_part": "0.00",
            "principal_part": "160.00",
            "occurred_at": "2026-10-03T00:00:00Z",
        },
    )
    assert write_off["transaction_id"] is None
    assert client.get(path).json()["status"] == "settled"
    assert client.get(f"/api/v1/accounts/{account}").json()["balance"] == "-150.00"
    add_movement(client, loan, {**interest, "occurred_at": "2026-10-04T00:00:00Z"})
    assert client.get(path).json()["status"] == "open"
    assert client.get(path).json()["outstanding"] == "10.00"


@pytest.mark.parametrize(
    "changes",
    [
        {"amount_in_loan_currency": "0.00"},
        {"amount_in_loan_currency": 10},
        {"account_amount": "50.00"},
        {"fx_rate_applied": "1.000000"},
        {"interest_part": "0.00"},
        {"interest_part": None},
        {"occurred_at": "2026-10-02T00:00:00"},
        {"account_currency": "USD"},
        {"fx_rate_to_base": "2.000000"},
    ],
)
def test_invalid_movements_leave_no_effects(client: TestClient, changes: dict[str, object]) -> None:
    login(client)
    account = create_account(client)
    loan = create_loan(client, create_person(client), account)
    result = client.post(
        f"/api/v1/loans/{loan}/movements",
        json=payment_payload(account, "10.00", **changes),
        headers=csrf_headers(client),
    )
    assert result.status_code == 422, result.text
    assert client.get(f"/api/v1/loans/{loan}").json()["outstanding"] == "200.00"
    assert len(client.get("/api/v1/transactions").json()["items"]) == 1


def test_adjustment_zero_negative_capital_and_duplicate_disbursement(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    loan = create_loan(client, create_person(client), account)
    for amount, expected in [("0.00", 422), ("-201.00", 409)]:
        result = client.post(
            f"/api/v1/loans/{loan}/movements",
            json={
                "kind": "adjustment",
                "amount_in_loan_currency": amount,
                "occurred_at": "2026-10-02T00:00:00Z",
            },
            headers=csrf_headers(client),
        )
        assert result.status_code == expected, result.text
    duplicate = {**payment_payload(account, "200.00"), "kind": "disbursement"}
    assert (
        client.post(
            f"/api/v1/loans/{loan}/movements", json=duplicate, headers=csrf_headers(client)
        ).status_code
        == 409
    )
    assert client.get(f"/api/v1/loans/{loan}").json()["outstanding"] == "200.00"


def test_movements_idempotency_and_loan_transaction_edit_guards(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    loan = create_loan(client, create_person(client), account)
    path = f"/api/v1/loans/{loan}/movements"
    headers = {**csrf_headers(client), "Idempotency-Key": "payment"}
    first = client.post(path, json=payment_payload(account, "10.00"), headers=headers)
    assert first.status_code == 201
    assert (
        client.post(path, json=payment_payload(account, "10.00"), headers=headers).json()
        == first.json()
    )
    assert (
        client.post(path, json=payment_payload(account, "11.00"), headers=headers).json()["code"]
        == "idempotency_conflict"
    )
    tx_id = first.json()["transaction_id"]
    for method, body in [("PATCH", {"amount": "12.00"}), ("DELETE", None)]:
        result = client.request(
            method, f"/api/v1/transactions/{tx_id}", json=body, headers=csrf_headers(client)
        )
        assert result.status_code == 409 and result.json()["code"] == "transaction_flow_required"
    result = client.post(
        "/api/v1/transactions/batch",
        json={"action": "delete", "transaction_ids": [tx_id]},
        headers=csrf_headers(client),
    )
    assert result.status_code == 409 and result.json()["code"] == "transaction_flow_required"


def test_explicit_payment_split_is_validated_without_silent_reallocation(
    client: TestClient,
) -> None:
    login(client)
    account = create_account(client)
    loan = create_loan(client, create_person(client), account)
    add_movement(
        client,
        loan,
        {
            "kind": "interest",
            "amount_in_loan_currency": "10.00",
            "occurred_at": "2026-10-02T00:00:00Z",
        },
    )
    path = f"/api/v1/loans/{loan}/movements"
    invalid = payment_payload(account, "50.00", interest_part="11.00", principal_part="39.00")
    result = client.post(path, json=invalid, headers=csrf_headers(client))
    assert result.status_code == 422
    assert client.get(f"/api/v1/loans/{loan}").json()["outstanding"] == "210.00"
    valid = payment_payload(account, "50.00", interest_part="5.00", principal_part="45.00")
    payment = add_movement(client, loan, valid)
    assert payment["interest_part"] == "5.00" and payment["principal_part"] == "45.00"
    proposal = client.post(
        f"/api/v1/loans/{loan}/payment-proposal",
        json={"amount_in_loan_currency": "10.00"},
        headers=csrf_headers(client),
    )
    assert (
        proposal.json()["interest_part"] == "5.00" and proposal.json()["principal_part"] == "5.00"
    )


def test_cross_currency_overflow_is_validation_error_without_partial_effects(
    client: TestClient,
) -> None:
    login(client)
    usd = create_account(client, name="USD", currency="USD")
    pen = create_account(client, name="PEN")
    loan = create_loan(
        client,
        create_person(client),
        usd,
        currency="USD",
        disbursement={
            **payment_payload(
                usd,
                "200.00",
                account_currency="USD",
                fx_rate_to_base="3.800000",
                occurred_at="2026-10-01T00:00:00Z",
            ),
            "kind": "disbursement",
        },
    )
    response = client.post(
        f"/api/v1/loans/{loan}/movements",
        json=payment_payload(
            pen, "10.00", account_amount="9999999999999999.99", fx_rate_applied="0.000001"
        ),
        headers=csrf_headers(client),
    )
    assert response.status_code == 422, response.text
    assert client.get(f"/api/v1/loans/{loan}").json()["outstanding"] == "200.00"
    assert len(client.get("/api/v1/transactions").json()["items"]) == 1
