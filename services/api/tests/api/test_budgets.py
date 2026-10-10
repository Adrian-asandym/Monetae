"""Budget contract, cash classification, reversible selection and isolation."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from api.conftest import (
    FakeClock,
    add_movement,
    create_account,
    create_category,
    create_loan,
    create_person,
    create_transaction,
    create_transfer,
    csrf_headers,
    login,
    payment_payload,
)
from api.test_account_balance import statements
from api.test_reports_statistics import rate
from monetae.db.models import Budget, BudgetCategory, BudgetTransaction, User

ROOT = "/api/v1/budgets"


def payload(**values: object) -> dict[str, object]:
    return {
        "name": "Synthetic budget",
        "period": "monthly",
        "start_on": "2026-10-01",
        "amount": "100.00",
        "currency": "PEN",
        "scope": "all",
        **values,
    }


def create_budget(client: TestClient, **values: object) -> str:
    result = client.post(ROOT, json=payload(**values), headers=csrf_headers(client))
    assert result.status_code == 201, result.text
    entity_id = result.json()["id"]
    assert isinstance(entity_id, str)
    return entity_id


def assign(client: TestClient, budget: str, ids: list[str]) -> None:
    result = client.put(
        f"{ROOT}/{budget}/transactions", json={"transaction_ids": ids}, headers=csrf_headers(client)
    )
    assert result.status_code == 200, result.text


def test_crud_partial_categories_and_soft_delete(client: TestClient, db_session: Session) -> None:
    login(client)
    category = create_category(client)
    transaction = create_transaction(client, create_account(client), category_id=category)
    budget = create_budget(
        client, color="#abcdef", category_limits=[{"category_id": category, "limit_amount": "0.00"}]
    )
    initial = client.get(f"{ROOT}/{budget}").json()
    assert initial["spent_amount"] == "10.00"
    assert initial["remaining_amount"] == "90.00"
    response = client.patch(
        f"{ROOT}/{budget}", json={"name": "Renamed", "color": None}, headers=csrf_headers(client)
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["name"] == "Renamed" and updated["color"] is None
    assert updated["amount"] == initial["amount"]
    assert updated["category_limits"] == initial["category_limits"]
    assert (
        client.patch(
            f"{ROOT}/{budget}", json={"category_limits": []}, headers=csrf_headers(client)
        ).json()["category_limits"]
        == []
    )
    link = db_session.scalar(select(BudgetCategory).where(BudgetCategory.budget_id == UUID(budget)))
    assert link is not None and link.deleted_at is not None
    assert (
        client.patch(
            f"{ROOT}/{budget}",
            json={"category_limits": initial["category_limits"]},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )
    db_session.refresh(link)
    assert link.deleted_at is None
    assert client.delete(f"{ROOT}/{budget}", headers=csrf_headers(client)).status_code == 200
    assert client.get(f"{ROOT}/{budget}").status_code == 404
    assert client.get(ROOT).json()["items"] == []
    row = db_session.get(Budget, UUID(budget))
    assert row is not None and row.deleted_at is not None
    assert client.get(f"/api/v1/transactions/{transaction}").status_code == 200


@pytest.mark.parametrize(
    "values",
    [
        {"amount": "0.00"},
        {"amount": 10},
        {"period": "yearly"},
        {"scope": "other"},
        {"period": "custom"},
        {"end_on": "2026-09-30"},
        {"color": "red"},
        {"user_id": str(uuid4())},
        {"category_limits": [{"category_id": str(uuid4()), "limit_amount": "-1.00"}]},
    ],
)
def test_create_validation(client: TestClient, values: dict[str, object]) -> None:
    login(client)
    assert (
        client.post(ROOT, json=payload(**values), headers=csrf_headers(client)).status_code == 422
    )
    assert client.get(ROOT).json()["items"] == []


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"name": None},
        {"amount": None},
        {"period": "custom"},
        {"start_on": "2027-01-01"},
        {"end_on": None},
        {"category_limits": None},
    ],
)
def test_patch_validation_is_atomic(client: TestClient, values: dict[str, object]) -> None:
    login(client)
    budget = create_budget(client, period="custom", end_on="2026-10-31")
    before = client.get(f"{ROOT}/{budget}").json()
    # Existing custom with end_on allows an unchanged period patch.
    if values == {"period": "custom"}:
        values = {"end_on": "2026-09-30"}
    response = client.patch(f"{ROOT}/{budget}", json=values, headers=csrf_headers(client))
    assert response.status_code == 422, response.text
    assert client.get(f"{ROOT}/{budget}").json() == before


def test_custom_patch_combines_stored_dates(client: TestClient) -> None:
    login(client)
    budget = create_budget(client)
    assert (
        client.patch(
            f"{ROOT}/{budget}", json={"period": "custom"}, headers=csrf_headers(client)
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"{ROOT}/{budget}",
            json={"period": "custom", "end_on": "2026-10-15"},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"{ROOT}/{budget}",
            json={"period": "weekly", "end_on": None},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )


def test_selection_replaces_restores_and_is_atomic(client: TestClient, db_session: Session) -> None:
    login(client)
    account = create_account(client)
    first = create_transaction(client, account)
    second = create_transaction(client, account, amount="-20.00")
    budget = create_budget(client, scope="selected")
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "0.00"
    assign(client, budget, [first])
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "10.00"
    link = db_session.scalar(
        select(BudgetTransaction).where(BudgetTransaction.transaction_id == UUID(first))
    )
    assert link is not None
    link_id = link.id
    assign(client, budget, [second])
    db_session.refresh(link)
    assert link.deleted_at is not None
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "20.00"
    assert (
        client.put(
            f"{ROOT}/{budget}/transactions",
            json={"transaction_ids": [first, str(uuid4())]},
            headers=csrf_headers(client),
        ).status_code
        == 404
    )
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "20.00"
    assign(client, budget, [first, second])
    db_session.refresh(link)
    assert link.id == link_id and link.deleted_at is None
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "30.00"
    assign(client, budget, [])
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "0.00"
    assert (
        client.patch(
            f"{ROOT}/{budget}", json={"scope": "all"}, headers=csrf_headers(client)
        ).json()["spent_amount"]
        == "30.00"
    )
    assign(client, budget, [first])
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "30.00"
    assert (
        client.patch(
            f"{ROOT}/{budget}", json={"scope": "selected"}, headers=csrf_headers(client)
        ).json()["spent_amount"]
        == "10.00"
    )


@pytest.mark.parametrize("size,duplicate", [(201, False), (2, True)])
def test_assignment_validation(client: TestClient, size: int, duplicate: bool) -> None:
    login(client)
    budget = create_budget(client)
    ids = [str(uuid4()) for _ in range(size)]
    if duplicate:
        ids[1] = ids[0]
    assert (
        client.put(
            f"{ROOT}/{budget}/transactions",
            json={"transaction_ids": ids},
            headers=csrf_headers(client),
        ).status_code
        == 422
    )


def test_duplicate_categories(client: TestClient) -> None:
    login(client)
    category = create_category(client)
    limits = [{"category_id": category, "limit_amount": "5.00"}] * 2
    assert (
        client.post(
            ROOT, json=payload(category_limits=limits), headers=csrf_headers(client)
        ).status_code
        == 422
    )
    budget = create_budget(client)
    assert (
        client.patch(
            f"{ROOT}/{budget}", json={"category_limits": limits}, headers=csrf_headers(client)
        ).status_code
        == 422
    )


def test_expenses_classification_category_and_selection(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    category = create_category(client)
    expense = create_transaction(client, account, amount="-120.00", category_id=category)
    create_transaction(client, account, kind="income", amount="300.00")
    create_transaction(client, account, status="scheduled", amount="-90.00")
    deleted = create_transaction(client, account, amount="-80.00")
    assert (
        client.delete(f"/api/v1/transactions/{deleted}", headers=csrf_headers(client)).status_code
        == 200
    )
    create_transfer(client, account, create_account(client, "Other"))
    borrowed = create_loan(client, create_person(client), account, direction="borrowed")
    add_movement(
        client,
        borrowed,
        {
            "kind": "interest",
            "amount_in_loan_currency": "10.00",
            "occurred_at": "2026-10-02T12:00:00Z",
        },
    )
    movement = add_movement(client, borrowed, payment_payload(account, "100.00"))
    lent = create_loan(client, create_person(client, "Lender"), account)
    add_movement(
        client,
        lent,
        {
            "kind": "interest",
            "amount_in_loan_currency": "5.00",
            "occurred_at": "2026-10-02T12:00:00Z",
        },
    )
    add_movement(client, lent, payment_payload(account, "100.00"))
    budget = create_budget(client)
    current = client.get(f"{ROOT}/{budget}").json()
    assert current["spent_amount"] == "130.00" and current["remaining_amount"] == "-30.00"
    assert current["report_total"]["by_currency"] == [{"currency": "PEN", "amount": "130.00"}]
    loan_transaction = movement["transaction_id"]
    assert isinstance(loan_transaction, str)
    assign(client, budget, [loan_transaction])
    response = client.patch(
        f"{ROOT}/{budget}", json={"scope": "selected"}, headers=csrf_headers(client)
    )
    assert response.json()["spent_amount"] == "10.00"
    limits = [{"category_id": category, "limit_amount": "50.00"}]
    assert (
        client.patch(
            f"{ROOT}/{budget}", json={"category_limits": limits}, headers=csrf_headers(client)
        ).json()["spent_amount"]
        == "0.00"
    )
    assign(client, budget, [expense, loan_transaction])
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "120.00"
    interest = next(
        c["id"]
        for c in client.get("/api/v1/categories").json()["items"]
        if c["system_key"] == "interest_expense"
    )
    assert (
        client.patch(
            f"{ROOT}/{budget}",
            json={"category_limits": [{"category_id": interest, "limit_amount": "10.00"}]},
            headers=csrf_headers(client),
        ).json()["spent_amount"]
        == "10.00"
    )


def test_lima_period_boundaries(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    create_transaction(client, account, occurred_at="2026-10-01T04:59:59Z", amount="-50.00")
    create_transaction(client, account, occurred_at="2026-11-01T04:59:59Z", amount="-10.00")
    create_transaction(client, account, occurred_at="2026-11-01T05:00:00Z", amount="-60.00")
    budget = create_budget(client)
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "10.00"


def test_missing_historical_rate_and_conversion(client: TestClient, db_session: Session) -> None:
    login(client)
    usd = create_account(client, currency="USD")
    create_transaction(client, usd, currency="USD", amount="-10.00", fx_rate_to_base="4.000000")
    budget = create_budget(client, currency="USD")
    before = client.get(f"{ROOT}/{budget}").json()
    assert before["spent_amount"] == "0.00"
    assert before["report_total"]["unconverted_count"] == 1
    assert before["report_total"]["by_currency"] == [{"currency": "USD", "amount": "10.00"}]
    rate(db_session, "2026-10-08", "0.300000")
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "0.00"
    rate(db_session, "2026-10-06", "0.250000")
    after = client.get(f"{ROOT}/{budget}").json()
    assert after["spent_amount"] == "10.00" and after["report_total"]["unconverted_count"] == 0
    pen = create_budget(client)
    assert client.get(f"{ROOT}/{pen}").json()["spent_amount"] == "40.00"


def test_isolation_each_route_and_foreign_references(
    client: TestClient, db_session: Session, auth_users: tuple[User, User]
) -> None:
    login(client)
    category = create_category(client)
    transaction = create_transaction(client, create_account(client))
    budget = create_budget(client)
    login(client, "second@example.test")
    assert client.get(ROOT).json()["items"] == []
    assert client.get(f"{ROOT}/{budget}").status_code == 404
    assert (
        client.patch(
            f"{ROOT}/{budget}", json={"name": "Foreign"}, headers=csrf_headers(client)
        ).status_code
        == 404
    )
    assert client.delete(f"{ROOT}/{budget}", headers=csrf_headers(client)).status_code == 404
    assert (
        client.put(
            f"{ROOT}/{budget}/transactions",
            json={"transaction_ids": []},
            headers=csrf_headers(client),
        ).status_code
        == 404
    )
    limits = [{"category_id": category, "limit_amount": "10.00"}]
    assert (
        client.post(
            ROOT, json=payload(category_limits=limits), headers=csrf_headers(client)
        ).status_code
        == 404
    )
    own = create_budget(client, scope="selected")
    row = db_session.get(Budget, UUID(own))
    assert row is not None and row.user_id == auth_users[1].id
    assert (
        client.patch(
            f"{ROOT}/{own}", json={"category_limits": limits}, headers=csrf_headers(client)
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"{ROOT}/{own}/transactions",
            json={"transaction_ids": [transaction]},
            headers=csrf_headers(client),
        ).status_code
        == 404
    )
    login(client)
    assert [r["id"] for r in client.get(ROOT).json()["items"]] == [budget]
    assert client.get(f"{ROOT}/{own}").status_code == 404


def test_deleted_body_references(client: TestClient) -> None:
    login(client)
    category = create_category(client)
    transaction = create_transaction(client, create_account(client))
    assert (
        client.delete(f"/api/v1/categories/{category}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert (
        client.delete(
            f"/api/v1/transactions/{transaction}", headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert (
        client.post(
            ROOT,
            json=payload(category_limits=[{"category_id": category, "limit_amount": "0.00"}]),
            headers=csrf_headers(client),
        ).status_code
        == 404
    )
    budget = create_budget(client)
    assert (
        client.put(
            f"{ROOT}/{budget}/transactions",
            json={"transaction_ids": [transaction]},
            headers=csrf_headers(client),
        ).status_code
        == 404
    )


def test_pagination_and_constant_queries(client: TestClient, db_engine: Engine) -> None:
    login(client)
    create_transaction(client, create_account(client))
    ids = [create_budget(client, name=f"Budget {n}") for n in range(8)]
    with statements(db_engine) as one:
        first = client.get(ROOT, params={"limit": 1})
    with statements(db_engine) as many:
        page = client.get(ROOT, params={"limit": 200})
    assert len(one) == len(many), (one, many)
    assert len(many) <= 6
    assert all(row["spent_amount"] == "10.00" for row in page.json()["items"])
    cursor = first.json()["next_cursor"]
    found = [first.json()["items"][0]["id"]]
    while cursor:
        response = client.get(ROOT, params={"limit": 2, "cursor": cursor})
        assert response.status_code == 200, response.text
        found.extend(row["id"] for row in response.json()["items"])
        cursor = response.json()["next_cursor"]
    assert found == [row["id"] for row in page.json()["items"]]
    assert set(found) == set(ids) and len(found) == len(ids)
    print(f"budget list: limit=1 and limit=200 each use {len(many)} SQL statements")
    assert client.get(ROOT, params={"cursor": "garbage"}).status_code == 400
    login(client, "second@example.test")
    assert client.get(ROOT, params={"cursor": first.json()["next_cursor"]}).status_code == 400


def test_security_session_csrf_origin(client: TestClient) -> None:
    assert client.get(ROOT).status_code == 401
    login(client)
    budget = create_budget(client)
    for method, path, data in [
        ("POST", ROOT, payload()),
        ("PATCH", f"{ROOT}/{budget}", {"name": "Changed"}),
        ("DELETE", f"{ROOT}/{budget}", None),
        ("PUT", f"{ROOT}/{budget}/transactions", {"transaction_ids": []}),
    ]:
        assert client.request(method, path, json=data).status_code == 403
        headers = {**csrf_headers(client), "Origin": "https://evil.example.test"}
        assert client.request(method, path, json=data, headers=headers).status_code == 403


def test_200_assignments_allowed(client: TestClient, db_session: Session) -> None:
    from sqlalchemy import text

    login(client)
    account = create_account(client)
    owner = client.get("/api/v1/users/me").json()["id"]
    transaction_ids = list(
        db_session.scalars(
            text("""
        INSERT INTO transactions (user_id, account_id, currency, kind, amount,
            occurred_at, status, title, fx_rate_to_base, fx_rate_source, source)
        SELECT :owner, :account, 'PEN', 'expense', -1.00,
            '2026-10-07T12:00:00Z', 'posted', 'Synthetic assignment boundary', 1, 'manual', 'web'
        FROM generate_series(1, 200) RETURNING id
    """),
            {"owner": owner, "account": account},
        )
    )
    budget = create_budget(client, scope="selected")
    assign(client, budget, [str(entity_id) for entity_id in transaction_ids])
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "200.00"


def test_user_timezone_today_and_expense_date(
    client: TestClient, db_session: Session, auth_users: tuple[User, User], clock: FakeClock
) -> None:
    from datetime import UTC, datetime

    login(client)
    auth_users[0].timezone = "Asia/Tokyo"
    db_session.flush()
    clock.value = datetime(2026, 10, 7, 16, tzinfo=UTC)  # October 8 in Tokyo, October 7 in Lima.
    # Refresh login after advancing beyond the session's inactivity threshold.
    login(client)
    account = create_account(client)
    create_transaction(client, account, amount="-30.00", occurred_at="2026-10-07T14:59:59Z")
    create_transaction(client, account, amount="-10.00", occurred_at="2026-10-07T15:00:00Z")
    budget = create_budget(client, period="daily")
    assert client.get(f"{ROOT}/{budget}").json()["spent_amount"] == "10.00"
