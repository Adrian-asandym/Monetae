"""Budget/goal history uses report membership and preserves ledger transactions."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.conftest import (
    add_movement,
    create_account,
    create_category,
    create_loan,
    create_person,
    create_tag,
    create_transaction,
    create_transfer,
    csrf_headers,
    login,
    payment_payload,
    transfer_payload,
)
from api.test_budgets import assign as assign_budget
from api.test_budgets import create_budget
from api.test_goals import assign as assign_goal
from api.test_goals import create_goal
from api.test_transactions_filters import ids
from monetae.db.models import GoalTransaction, User
from monetae.reports.queries import ENTRY_SQL

ROOT = "/api/v1/transactions"
RANGE = {"date_from": "2026-10-01T05:00:00Z", "date_to": "2026-11-01T05:00:00Z"}


@pytest.mark.parametrize("scope", ["all", "selected"])
@pytest.mark.parametrize("with_categories", [False, True])
def test_budget_history_cycle_sum_selection_categories_and_dates(
    client: TestClient, scope: str, with_categories: bool
) -> None:
    login(client)
    account = create_account(client)
    category = create_category(client)
    first = create_transaction(
        client, account, category_id=category, occurred_at=RANGE["date_from"]
    )
    last = create_transaction(
        client, account, category_id=category, amount="-20.00", occurred_at="2026-11-01T04:59:59Z"
    )
    outside = create_transaction(
        client, account, category_id=category, occurred_at=RANGE["date_to"]
    )
    before = create_transaction(
        client, account, category_id=category, occurred_at="2026-10-01T04:59:59Z"
    )
    unselected = create_transaction(client, account, category_id=category, amount="-40.00")
    uncategorized = create_transaction(client, account, amount="-50.00")
    limits = [{"category_id": category, "limit_amount": "100.00"}] if with_categories else []
    budget = create_budget(client, scope=scope, category_limits=limits)
    assign_budget(client, budget, [first, last, outside, before, uncategorized])
    expected = {first, last}
    total = Decimal("30.00")
    if scope == "all":
        expected.add(unselected)
        total += Decimal("40.00")
    if not with_categories:
        expected.add(uncategorized)
        total += Decimal("50.00")
    assert ids(client, budget_id=budget) == expected | {outside, before}
    assert ids(client, budget_id=budget, **RANGE) == expected
    rows = client.get(ROOT, params={"budget_id": budget, **RANGE}).json()["items"]
    report = client.get(f"/api/v1/budgets/{budget}").json()
    assert abs(sum((Decimal(row["amount"]) for row in rows), Decimal(0))) == total
    assert Decimal(report["spent_amount"]) == total
    assert not ids(client, budget_id=budget, kind="income")
    assert not ids(client, budget_id=budget, status="scheduled")
    # A removed selection stops contributing and restoring it restores history.
    if scope == "selected":
        assign_budget(client, budget, [last])
        assert ids(client, budget_id=budget) == {last}
        assign_budget(client, budget, [first, last])
        assert ids(client, budget_id=budget) == {first, last}


@pytest.mark.parametrize("scope", ["all", "selected"])
@pytest.mark.parametrize("category_filter", ["none", "ordinary", "interest"])
def test_budget_report_membership_interest_and_exclusions(
    client: TestClient,
    db_session: Session,
    auth_users: tuple[User, User],
    scope: str,
    category_filter: str,
) -> None:
    login(client)
    account, other = create_account(client), create_account(client, "Other")
    category = create_category(client)
    expense = create_transaction(client, account, category_id=category, amount="-120.00")
    income = create_transaction(client, account, kind="income", amount="300.00")
    scheduled = create_transaction(client, account, status="scheduled")
    deleted = create_transaction(client, account)
    assert client.delete(f"{ROOT}/{deleted}", headers=csrf_headers(client)).status_code == 200
    create_transfer(client, account, other)
    correction = client.post(
        "/api/v1/balance-corrections",
        json=transfer_payload(account, other),
        headers=csrf_headers(client),
    )
    assert correction.status_code == 201, correction.text
    corrections = [correction.json()[side]["id"] for side in ("outgoing", "incoming")]
    person = create_person(client)
    capital_loan = create_loan(client, person, account, direction="borrowed")
    capital = add_movement(client, capital_loan, payment_payload(account, "50.00"))
    capital_id = capital["transaction_id"]
    assert isinstance(capital_id, str)
    borrowed = create_loan(client, person, account, direction="borrowed")
    add_movement(
        client,
        borrowed,
        {
            "kind": "interest",
            "amount_in_loan_currency": "10.00",
            "occurred_at": "2026-10-02T10:00:00Z",
        },
    )
    payment = add_movement(client, borrowed, payment_payload(account, "100.00"))
    payment_id = payment["transaction_id"]
    assert isinstance(payment_id, str)
    lent = create_loan(client, person, account)
    add_movement(
        client,
        lent,
        {
            "kind": "interest",
            "amount_in_loan_currency": "5.00",
            "occurred_at": "2026-10-02T10:00:00Z",
        },
    )
    add_movement(client, lent, payment_payload(account, "100.00"))
    interest = next(
        row["id"]
        for row in client.get("/api/v1/categories").json()["items"]
        if row["system_key"] == "interest_expense"
    )
    limits = (
        []
        if category_filter == "none"
        else [
            {
                "category_id": category if category_filter == "ordinary" else interest,
                "limit_amount": "100.00",
            }
        ]
    )
    budget = create_budget(client, scope=scope, category_limits=limits)
    # Include excluded kinds deliberately, proving selection cannot override classification.
    assign_budget(
        client,
        budget,
        [expense, income, scheduled, capital_id, payment_id, *corrections],
    )
    expected = {expense, payment_id}
    spent = "130.00"
    if category_filter == "ordinary":
        expected, spent = {expense}, "120.00"
    elif category_filter == "interest":
        expected, spent = {payment_id}, "10.00"
    assert ids(client, budget_id=budget, **RANGE) == expected
    # include_deleted does not expand the set of entries contributing to a report.
    assert ids(client, budget_id=budget, include_deleted="true", **RANGE) == expected
    assert client.get(f"/api/v1/budgets/{budget}").json()["spent_amount"] == spent
    if payment_id in expected:
        rows = client.get(ROOT, params={"budget_id": budget, "kind": "loan"}).json()["items"]
        assert len(rows) == 1 and rows[0]["amount"] == "-100.00"
        assert rows[0] == client.get(f"{ROOT}/{payment_id}").json()
        assert ids(client, budget_id=budget, person_id=person, loan_id=borrowed) == {payment_id}
    # Independently apply the report's original membership predicate to ENTRY_SQL.
    contributing = db_session.scalars(
        text(
            "WITH entries AS ("
            + ENTRY_SQL
            + """
        ) SELECT e.transaction_id FROM entries e JOIN budgets b ON b.id = :budget_id
        WHERE b.user_id = :user_id AND b.deleted_at IS NULL AND e.kind = 'expense'
        AND (b.scope = 'all' OR EXISTS (SELECT 1 FROM budget_transactions bt
             WHERE bt.user_id = :user_id AND bt.budget_id = b.id
             AND bt.transaction_id = e.transaction_id AND bt.deleted_at IS NULL))
        AND (NOT EXISTS (SELECT 1 FROM budget_categories bc WHERE bc.user_id = :user_id
             AND bc.budget_id = b.id AND bc.deleted_at IS NULL)
             OR EXISTS (SELECT 1 FROM budget_categories bc WHERE bc.user_id = :user_id
             AND bc.budget_id = b.id AND bc.deleted_at IS NULL AND bc.category_id = e.category_id))
        """
        ),
        {
            "user_id": auth_users[0].id,
            "budget_id": UUID(budget),
            "start_at": RANGE["date_from"],
            "end_at": RANGE["date_to"],
            "categories": True,
            "account_id": None,
            "person_id": None,
        },
    )
    assert {str(transaction_id) for transaction_id in contributing} == expected
    if category_filter == "ordinary":
        response = client.patch(
            f"/api/v1/budgets/{budget}", json={"category_limits": []}, headers=csrf_headers(client)
        )
        assert response.status_code == 200, response.text
        assert ids(client, budget_id=budget) == {expense, payment_id}


@pytest.mark.parametrize("kind", ["save", "spend"])
def test_goal_history_signed_progress_transfers_corrections_and_live_links(
    client: TestClient, db_session: Session, auth_users: tuple[User, User], kind: str
) -> None:
    login(client)
    account, other = create_account(client), create_account(client, "Other")
    goal = create_goal(client, kind=kind)
    income = create_transaction(client, account, kind="income", amount="100.00")
    expense = create_transaction(client, account, amount="-20.00")
    scheduled = create_transaction(client, account, status="scheduled")
    deleted = create_transaction(client, account)
    removed = create_transaction(client, account)
    transfer = create_transfer(client, account, other)
    transfer_out = client.get(f"/api/v1/transfers/{transfer}").json()["outgoing_transaction_id"]
    correction = client.post(
        "/api/v1/balance-corrections",
        json=transfer_payload(account, other),
        headers=csrf_headers(client),
    )
    assert correction.status_code == 201, correction.text
    correction_in = correction.json()["incoming"]["id"]
    expected = {income, expense, transfer_out, correction_in}
    assign_goal(client, goal, [*expected, scheduled, deleted, removed])
    assign_goal(client, goal, [*expected, scheduled, deleted])
    assert client.delete(f"{ROOT}/{deleted}", headers=csrf_headers(client)).status_code == 200
    # Even a legacy link cannot make a loan contribute to GOAL_SQL.
    loan = create_loan(client, create_person(client), account)
    loan_transaction = client.get(ROOT, params={"loan_id": loan}).json()["items"][0]["id"]
    db_session.add(
        GoalTransaction(
            user_id=auth_users[0].id, goal_id=UUID(goal), transaction_id=UUID(loan_transaction)
        )
    )
    db_session.flush()
    assert ids(client, goal_id=goal, include_deleted="true") == expected
    assert ids(client, goal_id=goal, status="scheduled") == set()
    rows = client.get(ROOT, params={"goal_id": goal}).json()["items"]
    total = sum((Decimal(row["amount"]) for row in rows), Decimal(0))
    assert total == Decimal("80.00")
    progress = client.get(f"/api/v1/goals/{goal}").json()["progress_amount"]
    assert Decimal(progress) == total * (1 if kind == "save" else -1)


@pytest.mark.parametrize("resource", ["budgets", "goals"])
def test_history_resource_ownership_missing_deleted_and_session(
    client: TestClient, resource: str
) -> None:
    parameter = "budget_id" if resource == "budgets" else "goal_id"
    assert client.get(ROOT, params={parameter: str(uuid4())}).status_code == 401
    login(client)
    factory = create_budget if resource == "budgets" else create_goal
    own = factory(client)
    deleted = factory(client)
    assert (
        client.delete(f"/api/v1/{resource}/{deleted}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert client.get(ROOT, params={parameter: str(uuid4())}).status_code == 404
    assert (
        client.get(ROOT, params={parameter: deleted, "include_deleted": "true"}).status_code == 404
    )
    login(client, "second@example.test")
    foreign = factory(client)
    assert client.get(ROOT, params={parameter: own}).status_code == 404
    login(client)
    assert client.get(ROOT, params={parameter: foreign}).status_code == 404
    assert ids(client, **{parameter: own}) == set()


@pytest.mark.parametrize("resource", ["budgets", "goals"])
def test_combined_history_categories_filters_pagination_and_cursor_scope(
    client: TestClient, resource: str
) -> None:
    login(client)
    account, other_account = create_account(client), create_account(client, "Other")
    categories = [create_category(client, name) for name in ("A", "B", "C")]
    tag = create_tag(client)
    expected = {
        create_transaction(client, account, category_id=category, tag_ids=[tag], title="Match")
        for category in categories[:2]
        for _ in range(3)
    }
    wrong_category = create_transaction(
        client, account, category_id=categories[2], tag_ids=[tag], title="Match"
    )
    create_transaction(
        client, other_account, category_id=categories[0], tag_ids=[tag], title="Match"
    )
    create_transaction(client, account, category_id=categories[0], tag_ids=[tag], title="Different")
    create_transaction(client, account, category_id=categories[0], title="Match")
    budget, goal = create_budget(client), create_goal(client)
    assign_goal(client, goal, [*expected, wrong_category])
    params = [
        ("budget_id", budget),
        ("goal_id", goal),
        ("account_id", account),
        ("category_id", categories[0]),
        ("category_id", categories[1]),
        ("currency", "PEN"),
        ("kind", "expense"),
        ("status", "posted"),
        ("tag_ids", tag),
        ("q", "Match"),
        ("limit", "2"),
        *RANGE.items(),
    ]
    collected: list[str] = []
    cursor = None
    first_cursor = None
    while True:
        response = client.get(ROOT, params=[*params, *([("cursor", cursor)] if cursor else [])])
        assert response.status_code == 200, response.text
        page = response.json()
        collected.extend(row["id"] for row in page["items"])
        cursor = page["next_cursor"]
        first_cursor = first_cursor or cursor
        if cursor is None:
            break
    assert set(collected) == expected and len(collected) == len(expected)
    replacement = create_budget(client) if resource == "budgets" else create_goal(client)
    parameter = "budget_id" if resource == "budgets" else "goal_id"
    changed = [(key, replacement if key == parameter else value) for key, value in params]
    response = client.get(ROOT, params=[*changed, ("cursor", first_cursor)])
    assert response.status_code == 400 and response.json()["code"] == "invalid_cursor"
