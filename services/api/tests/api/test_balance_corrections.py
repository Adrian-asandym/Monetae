"""Atomic pairs, independent ledger edits, filtering and report classification."""

from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.conftest import (
    FakeClock,
    create_account,
    create_category,
    create_transaction,
    csrf_headers,
    login,
    transfer_payload,
)
from api.test_budgets import assign as assign_budget
from api.test_budgets import create_budget
from api.test_goals import assign as assign_goal
from api.test_goals import create_goal
from api.test_reports_statistics import report
from monetae.api.schemas.balance_corrections import BalanceCorrectionCreate
from monetae.db.models import Transaction, User
from monetae.services.auth import AuthError
from monetae.services.balance_corrections import BalanceCorrectionService

ROOT = "/api/v1/balance-corrections"


def create(client: TestClient, outgoing: str, incoming: str, **values: object) -> dict[str, object]:
    response = client.post(
        ROOT, json=transfer_payload(outgoing, incoming, **values), headers=csrf_headers(client)
    )
    assert response.status_code == 201, response.text
    result: dict[str, object] = response.json()
    return result


def test_pair_idempotence_default_title_and_system_categories(client: TestClient) -> None:
    login(client)
    outgoing, incoming = create_account(client), create_account(client, "Bank")
    payload = transfer_payload(outgoing, incoming)
    del payload["title"]
    headers = {**csrf_headers(client), "Idempotency-Key": "correction-key"}
    response = client.post(ROOT, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    pair = response.json()
    assert client.post(ROOT, json=payload, headers=headers).json() == pair
    assert (
        client.post(ROOT, json={**payload, "note": "changed"}, headers=headers).status_code == 409
    )
    categories = {c["id"]: c for c in client.get("/api/v1/categories").json()["items"]}
    for direction, kind, amount in (
        ("outgoing", "expense", "-10.00"),
        ("incoming", "income", "10.00"),
    ):
        leg = pair[direction]
        assert leg["title"] == "Transferir saldo" and leg["amount"] == amount
        assert leg["kind"] == kind and leg["status"] == "posted"
        assert leg["transfer_group_id"] == pair["group_id"]
        category = categories[leg["category_id"]]
        assert category["system_key"] == f"balance_correction_{kind}"
        assert category["is_system"] and category["name"] == "Corrección de saldo"
        assert (
            client.patch(
                f"/api/v1/categories/{category['id']}",
                json={"name": "rename"},
                headers=csrf_headers(client),
            ).status_code
            == 409
        )
        assert (
            client.delete(
                f"/api/v1/categories/{category['id']}", headers=csrf_headers(client)
            ).status_code
            == 409
        )
    assert client.get("/api/v1/transfers").json()["items"] == []
    for method in ("get", "patch", "delete"):
        # Separate calls retain the familiar TestClient typed signatures.
        url = f"/api/v1/transfers/{pair['group_id']}"
        if method == "get":
            status = client.get(url).status_code
        elif method == "patch":
            status = client.patch(
                url, json={"title": "changed"}, headers=csrf_headers(client)
            ).status_code
        else:
            status = client.delete(url, headers=csrf_headers(client)).status_code
        assert status == 404
    assert len(client.get("/api/v1/transactions").json()["items"]) == 2


def test_deferred_arrival_edit_delete_restore_and_role_guard(client: TestClient) -> None:
    login(client)
    a, b = create_account(client), create_account(client, "Bank")
    pair = client.post(
        ROOT,
        json=transfer_payload(a, b, to_occurred_at="2026-10-09T12:00:00Z"),
        headers=csrf_headers(client),
    ).json()
    outgoing, incoming = pair["outgoing"], pair["incoming"]
    assert outgoing["status"] == "posted" and incoming["status"] == "scheduled"
    assert outgoing["occurred_at"] != incoming["occurred_at"]
    for changes in (
        {"category_id": None},
        {"category_id": create_category(client)},
        {"kind": "income"},
        {"kind": "income", "amount": "10.00"},
        {"category_id": incoming["category_id"]},
    ):
        response = client.patch(
            f"/api/v1/transactions/{outgoing['id']}", json=changes, headers=csrf_headers(client)
        )
        assert response.status_code == 422, response.text
    response = client.patch(
        f"/api/v1/transactions/{incoming['id']}",
        json={
            "occurred_at": "2026-10-08T18:00:00Z",
            "amount": "12.00",
            "title": "Edited arrival",
            "note": "Synthetic note",
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    assert client.get(f"/api/v1/transactions/{outgoing['id']}").json() == outgoing
    assert client.get(ROOT).json()["items"][0]["implicit_rate"] == "1.200000"
    assert (
        client.delete(
            f"/api/v1/transactions/{outgoing['id']}", headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert client.get(ROOT).json()["items"] == []
    assert client.get(f"/api/v1/transactions/{incoming['id']}").status_code == 200
    assert (
        client.post(
            f"/api/v1/transactions/{outgoing['id']}/restore", headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert len(client.get(ROOT).json()["items"]) == 1
    response = client.post(
        "/api/v1/transactions/batch",
        json={
            "transaction_ids": [outgoing["id"]],
            "action": "edit",
            "changes": {"category_id": None},
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "case", ["same", "foreign", "archived", "arrival", "rate", "amount", "group"]
)
def test_invalid_pair_has_no_legs(client: TestClient, case: str) -> None:
    login(client)
    a, b = create_account(client), create_account(client, "Bank")
    payload = transfer_payload(a, b)
    expected = 422
    if case == "same":
        payload["to_account_id"] = a
    elif case == "foreign":
        client.post("/api/v1/auth/logout", headers=csrf_headers(client))
        login(client, "second@example.test")
        payload["to_account_id"] = create_account(client, currency="USD")
        client.post("/api/v1/auth/logout", headers=csrf_headers(client))
        login(client)
        expected = 404
    elif case == "archived":
        assert (
            client.post(
                f"/api/v1/accounts/{b}/archive", json={}, headers=csrf_headers(client)
            ).status_code
            == 200
        )
    elif case == "arrival":
        payload["to_occurred_at"] = "2026-10-06T12:00:00Z"
    elif case == "rate":
        payload["to_fx_rate_to_base"] = "2.000000"
    elif case == "amount":
        payload["from_amount"] = "0.00"
    else:
        payload["transfer_group_id"] = str(uuid4())
    response = client.post(ROOT, json=payload, headers=csrf_headers(client))
    assert response.status_code == expected, response.text
    assert client.get("/api/v1/transactions").json()["items"] == []


def test_second_leg_failure_rolls_back_direct_service(
    client: TestClient,
    db_session: Session,
    auth_users: tuple[User, User],
    clock: FakeClock,
) -> None:
    login(client)
    a, b = create_account(client), create_account(client, "Bank")
    payload = BalanceCorrectionCreate.model_validate(
        transfer_payload(a, b, to_fx_rate_to_base="2.000000")
    )
    service = BalanceCorrectionService(db_session, "test-secret", clock)
    with pytest.raises(AuthError, match="historical exchange rate"):
        service.create(auth_users[0].id, payload)
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.user_id == auth_users[0].id)
        )
        == 0
    )


def test_multicurrency_pagination_filters_and_isolation(client: TestClient) -> None:
    login(client)
    a, b = create_account(client), create_account(client, "USD", currency="USD")
    for day in (5, 6, 7):
        create(
            client,
            a,
            b,
            from_amount="38.00",
            to_amount="10.00",
            to_fx_rate_to_base="3.800000",
            occurred_at=f"2026-10-0{day}T12:00:00Z",
        )
    filters = {
        "from_account_id": a,
        "to_account_id": b,
        "from_currency": "PEN",
        "to_currency": "USD",
        "limit": 1,
    }
    first = client.get(ROOT, params=filters).json()
    assert first["items"][0]["implicit_rate"] == "0.263158"
    assert first["items"][0]["outgoing"]["occurred_at"].startswith("2026-10-07")
    second = client.get(ROOT, params={**filters, "cursor": first["next_cursor"]}).json()
    assert first["items"][0]["group_id"] != second["items"][0]["group_id"]
    third = client.get(ROOT, params={**filters, "cursor": second["next_cursor"]}).json()
    assert third["next_cursor"] is None
    assert client.get(ROOT, params={**filters, "from_currency": "USD"}).json()["items"] == []
    assert client.get(ROOT, params={"cursor": first["next_cursor"]}).status_code == 400
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    login(client, "second@example.test")
    assert client.get(ROOT).json()["items"] == []
    assert client.get(ROOT, params={**filters, "cursor": first["next_cursor"]}).status_code == 400
    id = first["items"][0]["outgoing"]["id"]
    assert (
        client.patch(
            f"/api/v1/transactions/{id}", json={"title": "Foreign"}, headers=csrf_headers(client)
        ).status_code
        == 404
    )


def test_reports_budgets_goals_and_account_balance(client: TestClient) -> None:
    login(client)
    a, b = create_account(client), create_account(client, "Bank")
    pair = client.post(ROOT, json=transfer_payload(a, b), headers=csrf_headers(client)).json()
    expense = create_category(client)
    purchase = create_transaction(client, a, category_id=expense)
    budget = create_budget(client)
    assert client.get(f"/api/v1/budgets/{budget}").json()["spent_amount"] == "10.00"
    manual = create_budget(client, name="Manual", scope="selected")
    assign_budget(client, manual, [pair["outgoing"]["id"]])
    assert client.get(f"/api/v1/budgets/{manual}").json()["spent_amount"] == "0.00"
    for endpoint in ("cash-flow", "categories"):
        entries = report(client, endpoint)
        assert len(entries) == 1
        if endpoint == "cash-flow":
            assert cast(dict[str, object], entries[0]["net"])["report_amount"] == "-10.00"
            assert (
                cast(dict[str, object], entries[0]["cumulative_net"])["report_amount"] == "-10.00"
            )
        else:
            assert entries[0]["category_id"] == expense
    accounts = {c["id"]: c for c in client.get("/api/v1/accounts").json()["items"]}
    assert accounts[a]["balance"] == "-7.50" and accounts[a]["transaction_count"] == 2
    assert accounts[b]["balance"] == "22.50" and accounts[b]["transaction_count"] == 1
    goal = create_goal(client)
    assign_goal(client, goal, [pair["incoming"]["id"]])
    assert client.get(f"/api/v1/goals/{goal}").json()["progress_amount"] == "10.00"
    assign_goal(client, goal, [pair["incoming"]["id"], pair["outgoing"]["id"], purchase])
    assert client.get(f"/api/v1/goals/{goal}").json()["progress_amount"] == "-10.00"


def test_future_both_legs_and_multicurrency_rate_validation(client: TestClient) -> None:
    login(client)
    a, b = create_account(client), create_account(client, "USD", currency="USD")
    pair = client.post(
        ROOT,
        json=transfer_payload(
            a, b, occurred_at="2026-11-01T00:00:00Z", to_fx_rate_to_base="3.800000"
        ),
        headers=csrf_headers(client),
    ).json()
    assert pair["outgoing"]["status"] == pair["incoming"]["status"] == "scheduled"
    assert pair["incoming"]["fx_rate_to_base"] == "3.800000"
    categories = list(client.get("/api/v1/categories").json()["items"])
    assert len([c for c in categories if c["system_key"].startswith("balance_correction")]) == 2


@pytest.mark.parametrize(
    ("from_amount", "to_amount", "expected"),
    [
        ("9999999999999999.99", "0.01", "0.000000"),
        ("0.01", "9999999999999999.99", "999999999999999999.000000"),
    ],
)
def test_computed_rate_extremes(
    client: TestClient, from_amount: str, to_amount: str, expected: str
) -> None:
    login(client)
    a, b = create_account(client), create_account(client, "Bank")
    create(client, a, b, from_amount=from_amount, to_amount=to_amount)
    response = client.get(ROOT)
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["implicit_rate"] == expected


def test_unlinked_corrections_excluded_by_category(client: TestClient) -> None:
    login(client)
    a = create_account(client)
    category = next(
        c["id"]
        for c in client.get("/api/v1/categories").json()["items"]
        if c["system_key"] == "balance_correction_expense"
    )
    create_transaction(client, a, category_id=category)
    budget = create_budget(client)
    assert client.get(f"/api/v1/budgets/{budget}").json()["spent_amount"] == "0.00"
    assert report(client, "categories") == []
    cash = report(client, "cash-flow")
    assert all(cast(dict[str, object], r["net"])["report_amount"] == "0.00" for r in cash)
    account = client.get(f"/api/v1/accounts/{a}").json()
    assert account["balance"] == "2.50" and account["transaction_count"] == 1
