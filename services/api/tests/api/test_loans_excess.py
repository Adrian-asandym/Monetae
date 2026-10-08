from decimal import Decimal

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


@pytest.mark.parametrize("handling", ["adjustment", "income_expense"])
@pytest.mark.parametrize("direction", ["lent", "borrowed"])
def test_excess_rejected_then_handled_atomically(
    client: TestClient, handling: str, direction: str
) -> None:
    login(client)
    account = create_account(client, currency="USD", initial_balance="0.00")
    loan = create_loan(
        client,
        create_person(client),
        account,
        principal="50.00",
        direction=direction,
        currency="USD",
        disbursement={
            **payment_payload(
                account,
                "50.00",
                account_currency="USD",
                fx_rate_to_base="3.800000",
                occurred_at="2026-10-01T00:00:00Z",
            ),
            "kind": "disbursement",
        },
    )
    path = f"/api/v1/loans/{loan}/movements"
    payload = payment_payload(account, "60.00", account_currency="USD", fx_rate_to_base="3.800000")
    headers = {**csrf_headers(client), "Idempotency-Key": "rejected"}
    rejected = client.post(path, json=payload, headers=headers)
    assert rejected.status_code == 422 and rejected.headers["content-type"].startswith(
        "application/problem+json"
    )
    assert rejected.json()["code"] == "loan_overpayment"
    assert rejected.json()["excess_amount"] == "10.00"
    assert rejected.json()["currency"] == "USD"
    assert [item["action"] for item in rejected.json()["options"]] == [
        "adjustment",
        "income_expense",
    ]
    assert len(client.get(path).json()["items"]) == 1
    assert len(client.get("/api/v1/transactions").json()["items"]) == 1
    headers["Idempotency-Key"] = "accepted"
    payload["excess_handling"] = handling
    response = client.post(path, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["amount_in_loan_currency"] == ("60.00" if handling == "adjustment" else "50.00")
    assert result["side_effects"][0]["amount"] == "10.00"
    assert result["side_effects"][0]["kind"] == (
        "adjustment" if handling == "adjustment" else "income" if direction == "lent" else "expense"
    )
    assert client.post(path, json=payload, headers=headers).json() == result
    assert client.get(f"/api/v1/loans/{loan}").json()["outstanding"] == "0.00"
    assert client.get(f"/api/v1/accounts/{account}").json()["balance"] == (
        "10.00" if direction == "lent" else "-10.00"
    )
    movements = client.get(path).json()["items"]
    if handling == "adjustment":
        assert [m["kind"] for m in movements] == ["disbursement", "adjustment", "payment"]
        assert movements[1]["occurred_at"] == movements[2]["occurred_at"]
    assert len(client.get("/api/v1/transactions", params={"loan_id": loan}).json()["items"]) == 2


def test_foreign_excess_retains_rounding_cent(client: TestClient) -> None:
    login(client)
    usd = create_account(client, name="USD", currency="USD", initial_balance="0.00")
    pen = create_account(client, name="PEN", initial_balance="0.00")
    loan = create_loan(
        client,
        create_person(client),
        usd,
        currency="USD",
        principal="50.00",
        disbursement={
            **payment_payload(
                usd,
                "50.00",
                account_currency="USD",
                fx_rate_to_base="3.800000",
                occurred_at="2026-10-01T00:00:00Z",
            ),
            "kind": "disbursement",
        },
    )
    result = add_movement(
        client,
        loan,
        payment_payload(
            pen,
            "60.00",
            account_amount="228.01",
            fx_rate_applied="3.800000",
            excess_handling="income_expense",
        ),
    )
    assert result["account_amount"] == "190.00"
    effects = result["side_effects"]
    assert isinstance(effects, list)
    assert effects[0]["amount"] == "38.01"
    txns = client.get("/api/v1/transactions", params={"account_id": pen}).json()["items"]
    assert sum((Decimal(t["amount"]) for t in txns), Decimal(0)) == Decimal("228.01")
    assert client.get(f"/api/v1/accounts/{pen}").json()["balance"] == "228.01"


def test_settled_income_excess_rejected_and_adjustment_allowed(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    loan = create_loan(client, create_person(client), account, principal="50.00")
    add_movement(client, loan, payment_payload(account, "50.00"))
    path = f"/api/v1/loans/{loan}/movements"
    headers = {**csrf_headers(client), "Idempotency-Key": "settled"}
    payload = payment_payload(account, "10.00", excess_handling="income_expense")
    result = client.post(path, json=payload, headers=headers)
    assert result.status_code == 409 and result.json()["code"] == "loan_already_settled"
    assert len(client.get(path).json()["items"]) == 2
    payload["excess_handling"] = "adjustment"
    # Un fallo no consume la clave como éxito.
    response = client.post(path, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    assert response.json()["running_balance"] == "0.00"
    assert response.json()["side_effects"][0]["kind"] == "adjustment"
    assert len(client.get(path).json()["items"]) == 4
