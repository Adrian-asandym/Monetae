"""Ejemplos literales A–E del contrato y SPEC, exclusivamente datos sintéticos."""

import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from monetae import domain
from monetae.db.models import Loan
from monetae.services.loans import LoanService

from .conftest import create_account, create_person, csrf_headers, login

CONTRACT = json.loads((Path(__file__).resolve().parents[4] / "docs/api/openapi.json").read_text())


@pytest.mark.parametrize("scenario", list("ABCDE"))
def test_examples_http_accounts_and_history(
    client: TestClient, db_session: Session, scenario: str
) -> None:
    login(client)
    person_id = create_person(client)
    data = CONTRACT["x-loan-scenarios"][scenario]
    examples = CONTRACT["components"]["examples"]
    payload = json.loads(json.dumps(examples[f"{scenario}_loan_create"]["value"]))
    payload["person_id"] = person_id
    accounts: dict[str, str] = {}
    expected: dict[str, Decimal] = {}

    def mapped_cash(movement: dict[str, object]) -> None:
        if "account_id" not in movement:
            return
        original = str(movement["account_id"])
        if original not in accounts:
            accounts[original] = create_account(
                client,
                name=f"Account {len(accounts)}",
                currency=movement["account_currency"],
                initial_balance="0.00",
            )
            expected[accounts[original]] = Decimal(0)
        movement["account_id"] = accounts[original]

    mapped_cash(payload["disbursement"])
    response = client.post("/api/v1/loans", json=payload, headers=csrf_headers(client))
    assert response.status_code == 201, response.text
    loan_id = response.json()["id"]
    cash = payload["disbursement"]
    expected[cash["account_id"]] += Decimal(cash["account_amount"]) * (
        1 if data["direction"] == "borrowed" else -1
    )
    assert response.json()["outstanding"] == data["balances_after_each"][0]
    for index, name in enumerate(data["movement_examples"][1:], start=1):
        movement = json.loads(json.dumps(examples[name]["value"]))
        mapped_cash(movement)
        response = client.post(
            f"/api/v1/loans/{loan_id}/movements", json=movement, headers=csrf_headers(client)
        )
        assert response.status_code == 201, response.text
        assert response.json()["running_balance"] == data["balances_after_each"][index]
        if "account_id" in movement:
            expected[movement["account_id"]] += Decimal(movement["account_amount"]) * (
                1 if data["direction"] == "lent" else -1
            )
        balance = client.get(f"/api/v1/loans/{loan_id}/balance").json()
        assert balance["outstanding"] == data["balances_after_each"][index]
        for account_id, amount in expected.items():
            assert client.get(f"/api/v1/accounts/{account_id}").json()["balance"] == f"{amount:.2f}"
    transactions = client.get("/api/v1/transactions", params={"loan_id": loan_id}).json()["items"]
    assert len(transactions) == (
        3 if scenario in "AB" else 2 if scenario == "C" else 1 if scenario == "D" else 5
    )
    assert all(
        tx["kind"] == "loan" and tx["loan_id"] == loan_id and tx["category_id"] is None
        for tx in transactions
    )
    assert not client.get("/api/v1/transactions", params={"kind": "expense"}).json()["items"]
    loan_service = LoanService(db_session, "test")
    loan = db_session.get(Loan, UUID(loan_id))
    assert loan is not None
    recognized = domain.recognized_interest(
        domain.Direction(loan.direction),
        [loan_service.movement(loan, row) for row in loan_service.rows(loan)],
    )
    assert sum((item.amount.amount for item in recognized), Decimal(0)) == Decimal(
        "10.00" if scenario == "A" else "0.00"
    )
    if scenario != "D":
        assert client.get(f"/api/v1/loans/{loan_id}").json()["status"] == "settled"
        assert (
            client.get("/api/v1/loans", params={"status": "settled"}).json()["items"][0]["id"]
            == loan_id
        )
    assert not any(
        "settle" in path or "liquidar" in path
        for path in client.get("/openapi.json").json()["paths"]
    )
