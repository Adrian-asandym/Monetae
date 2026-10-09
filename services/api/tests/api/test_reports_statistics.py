"""Statistical report integration against PostgreSQL, using synthetic data only."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.conftest import (
    add_movement,
    create_account,
    create_category,
    create_loan,
    create_person,
    create_subscription,
    create_transaction,
    create_transfer,
    csrf_headers,
    login,
    payment_payload,
    scheduled_for,
)
from monetae.db.models import ExchangeRate, User

RANGE = {"date_from": "2026-10-01", "date_to": "2026-10-31"}
ENDPOINTS = ("cash-flow", "categories")


def report(client: TestClient, endpoint: str, **params: str | int) -> list[dict[str, object]]:
    response = client.get(f"/api/v1/reports/{endpoint}", params={**RANGE, **params})
    assert response.status_code == 200, response.text
    items: list[dict[str, object]] = response.json()["items"]
    return items


def rate(db: Session, day: str, amount: str, source: str = "manual", target: str = "USD") -> None:
    db.add(
        ExchangeRate(
            from_currency="PEN",
            to_currency=target,
            rate=Decimal(amount),
            as_of=date.fromisoformat(day),
            source=source,
        )
    )
    db.commit()


def test_base_income_expense_and_excluded_entries(client: TestClient) -> None:
    login(client)
    wallet = create_account(client)
    bank = create_account(client, "Bank")
    income = create_category(client, "Salary", kind="income")
    expense = create_category(client)
    create_transaction(client, wallet, kind="income", amount="1000.37", category_id=income)
    create_transaction(client, wallet, amount="-100.12", category_id=expense)
    create_transaction(client, wallet, amount="-20.05")
    create_transaction(client, wallet, kind="income", amount="999.00", status="scheduled")
    deleted = create_transaction(client, wallet, amount="-999.00")
    assert (
        client.delete(f"/api/v1/transactions/{deleted}", headers=csrf_headers(client)).status_code
        == 200
    )
    create_transfer(client, wallet, bank)
    create_loan(client, create_person(client), wallet)
    flow = report(client, "cash-flow")[0]
    assert flow["income"] == {
        "by_currency": [{"currency": "PEN", "amount": "1000.37"}],
        "report_currency": "PEN",
        "report_amount": "1000.37",
        "unconverted_count": 0,
    }
    assert flow["expense"] == {
        "by_currency": [{"currency": "PEN", "amount": "120.17"}],
        "report_currency": "PEN",
        "report_amount": "120.17",
        "unconverted_count": 0,
    }
    assert flow["net"] == {
        "by_currency": [{"currency": "PEN", "amount": "880.20"}],
        "report_currency": "PEN",
        "report_amount": "880.20",
        "unconverted_count": 0,
    }
    categories = client.get("/api/v1/reports/categories", params=RANGE).json()["items"]
    assert [(r["category_id"], r["total"]["report_amount"]) for r in categories] == [
        (income, "1000.37"),
        (expense, "100.12"),
        (None, "20.05"),
    ]


@pytest.mark.parametrize(
    "direction,kind,key",
    [
        ("lent", "income", "interest_income"),
        ("borrowed", "expense", "interest_expense"),
    ],
)
def test_paid_interest_date_system_category_and_payment_account(
    client: TestClient,
    direction: str,
    kind: str,
    key: str,
) -> None:
    login(client)
    wallet = create_account(client)
    bank = create_account(client, "Bank")
    person = create_person(client)
    loan = create_loan(client, person, wallet, direction=direction)
    add_movement(
        client,
        loan,
        {
            "kind": "interest",
            "amount_in_loan_currency": "10.00",
            "occurred_at": "2026-10-01T13:00:00Z",
        },
    )
    add_movement(client, loan, payment_payload(bank, "100.00", occurred_at="2026-10-07T04:30:00Z"))
    add_movement(
        client, loan, payment_payload(wallet, "110.00", occurred_at="2026-10-08T12:00:00Z")
    )
    assert client.get(f"/api/v1/loans/{loan}/balance").json()["status"] == "settled"
    system = next(
        c for c in client.get("/api/v1/categories").json()["items"] if c["system_key"] == key
    )
    rows = client.get("/api/v1/reports/categories", params={**RANGE, "period": "daily"}).json()[
        "items"
    ]
    assert len(rows) == 1
    assert rows[0]["start_on"] == rows[0]["end_on"] == "2026-10-06"
    assert rows[0]["category_id"] == system["id"] and rows[0]["kind"] == kind
    assert rows[0]["total"]["report_amount"] == "10.00"
    for endpoint in ENDPOINTS:
        response = client.get(f"/api/v1/reports/{endpoint}", params={**RANGE, "account_id": bank})
        assert response.status_code == 200, response.text
        if endpoint == "cash-flow":
            assert response.json()["items"][0][kind]["report_amount"] == "10.00"
        else:
            assert response.json()["items"] == [
                dict(rows[0], start_on="2026-10-01", end_on="2026-10-31")
            ]
    assert (
        client.get("/api/v1/reports/categories", params={**RANGE, "account_id": wallet}).json()[
            "items"
        ]
        == []
    )


@pytest.mark.parametrize("direction,kind", [("lent", "income"), ("borrowed", "expense")])
def test_cross_currency_interest_uses_payment_currency(
    client: TestClient,
    direction: str,
    kind: str,
) -> None:
    login(client)
    dollar = create_account(client, "USD", currency="USD")
    wallet = create_account(client)
    person = create_person(client)
    loan = create_loan(
        client, person, dollar, direction=direction, principal="100.00", currency="USD"
    )
    add_movement(
        client,
        loan,
        {
            "kind": "interest",
            "amount_in_loan_currency": "5.00",
            "occurred_at": "2026-10-01T13:00:00Z",
        },
    )
    add_movement(
        client,
        loan,
        payment_payload(wallet, "105.00", account_amount="399.00", fx_rate_applied="3.800000"),
    )
    rows = client.get("/api/v1/reports/categories", params=RANGE).json()["items"]
    assert len(rows) == 1 and rows[0]["kind"] == kind
    assert rows[0]["total"] == {
        "by_currency": [{"currency": "PEN", "amount": "19.00"}],
        "report_currency": "PEN",
        "report_amount": "19.00",
        "unconverted_count": 0,
    }
    assert (
        client.get("/api/v1/reports/cash-flow", params=RANGE).json()["items"][0][kind]
        == rows[0]["total"]
    )


def test_writeoff_unpaid_interest_deleted_movement_and_deleted_loan_do_not_count(
    client: TestClient,
) -> None:
    login(client)
    wallet = create_account(client)
    person = create_person(client)
    loan = create_loan(client, person, wallet)
    add_movement(
        client,
        loan,
        {
            "kind": "interest",
            "amount_in_loan_currency": "10.00",
            "occurred_at": "2026-10-01T13:00:00Z",
        },
    )
    add_movement(
        client,
        loan,
        {
            "kind": "write_off",
            "amount_in_loan_currency": "10.00",
            "interest_part": "10.00",
            "principal_part": "0.00",
            "occurred_at": "2026-10-02T12:00:00Z",
        },
    )
    assert report(client, "categories") == []
    add_movement(
        client,
        loan,
        {
            "kind": "interest",
            "amount_in_loan_currency": "10.00",
            "occurred_at": "2026-10-03T12:00:00Z",
        },
    )
    payment = add_movement(
        client, loan, payment_payload(wallet, "10.00", occurred_at="2026-10-04T12:00:00Z")
    )
    assert len(report(client, "categories")) == 1
    assert (
        client.delete(
            f"/api/v1/loans/{loan}/movements/{payment['id']}", headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert report(client, "categories") == []
    add_movement(client, loan, payment_payload(wallet, "10.00", occurred_at="2026-10-04T12:00:00Z"))
    assert client.delete(f"/api/v1/loans/{loan}", headers=csrf_headers(client)).status_code == 200
    assert report(client, "categories") == []


def test_archived_subscription_keeps_historical_expense(client: TestClient) -> None:
    login(client)
    wallet = create_account(client)
    category = create_category(client)
    sub = create_subscription(client, wallet, category_id=category, next_due_on="2026-10-01")
    scheduled = scheduled_for(client, sub)[0]
    posted = client.post(
        f"/api/v1/transactions/{scheduled['id']}/post", headers=csrf_headers(client)
    )
    assert posted.status_code == 200, posted.text
    assert (
        client.post(
            f"/api/v1/subscriptions/{sub}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    rows = client.get("/api/v1/reports/categories", params=RANGE).json()["items"]
    assert len(rows) == 1 and rows[0]["category_id"] == category
    assert rows[0]["total"]["report_amount"] == "30.00"


def test_multicurrency_historical_rates_missing_rates_and_manual_priority(
    client: TestClient,
    db_session: Session,
) -> None:
    login(client)
    wallet = create_account(client)
    dollar = create_account(client, "USD", currency="USD")
    create_transaction(client, wallet, amount="-100.00", occurred_at="2026-10-01T12:00:00Z")
    create_transaction(
        client,
        dollar,
        currency="USD",
        amount="-10.00",
        fx_rate_to_base="4.000000",
        occurred_at="2026-10-07T04:30:00Z",
    )
    create_transaction(client, wallet, amount="-10.00", occurred_at="2026-10-08T12:00:00Z")
    assert client.get("/api/v1/reports/cash-flow", params=RANGE).json()["items"][0]["expense"] == {
        "by_currency": [
            {"currency": "PEN", "amount": "110.00"},
            {"currency": "USD", "amount": "10.00"},
        ],
        "report_currency": "PEN",
        "report_amount": "150.00",
        "unconverted_count": 0,
    }
    rate(db_session, "2026-10-03", "0.250000")
    rate(db_session, "2026-10-07", "0.100000")
    rate(db_session, "2026-10-08", "0.200000", "auto:synthetic")
    rate(db_session, "2026-10-08", "0.300000")
    rate(db_session, "2026-11-01", "0.900000")
    for endpoint in ENDPOINTS:
        response = client.get(
            f"/api/v1/reports/{endpoint}", params={**RANGE, "report_currency": "USD"}
        )
        assert response.status_code == 200, response.text
        row = response.json()["items"][0]
        total = row["expense"] if endpoint == "cash-flow" else row["total"]
        assert total["report_amount"] == "13.00" and total["unconverted_count"] == 1
        assert total["by_currency"] == [
            {"currency": "PEN", "amount": "110.00"},
            {"currency": "USD", "amount": "10.00"},
        ]
        if endpoint == "cash-flow":
            assert row["net"]["report_amount"] == "-13.00" and row["net"]["unconverted_count"] == 1


def test_round_half_up_only_after_sum_and_no_direct_currency_shortcut(
    client: TestClient,
    db_session: Session,
    auth_users: tuple[User, User],
) -> None:
    login(client)
    wallet = create_account(client)
    for _ in range(3):
        create_transaction(client, wallet, amount="-0.01", fx_rate_to_base="1.000000")
    rate(db_session, "2026-10-01", "0.500000")
    auth_users[0].report_currency = "USD"
    db_session.commit()
    for endpoint in ENDPOINTS:
        response = client.get(f"/api/v1/reports/{endpoint}", params=RANGE)
        total = response.json()["items"][0]["expense" if endpoint == "cash-flow" else "total"]
        assert total["report_currency"] == "USD" and total["report_amount"] == "0.02"
    dollar = create_account(client, "USD", currency="USD")
    create_transaction(client, dollar, currency="USD", amount="-1.00", fx_rate_to_base="4.000000")
    # Even when original == report, contract requires original -> stored base -> historical report.
    assert (
        client.get("/api/v1/reports/cash-flow", params=RANGE).json()["items"][0]["expense"][
            "report_amount"
        ]
        == "2.02"
    )


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_person_filter_only_their_interest(client: TestClient, endpoint: str) -> None:
    login(client)
    wallet = create_account(client)
    persons = [create_person(client, name) for name in ("Morgan", "Taylor")]
    for person, amount in zip(persons, ("10.00", "20.00"), strict=True):
        loan = create_loan(client, person, wallet)
        add_movement(
            client,
            loan,
            {
                "kind": "interest",
                "amount_in_loan_currency": amount,
                "occurred_at": "2026-10-01T13:00:00Z",
            },
        )
        add_movement(client, loan, payment_payload(wallet, amount))
    create_transaction(client, wallet, kind="income", amount="999.00")
    response = client.get(f"/api/v1/reports/{endpoint}", params={**RANGE, "person_id": persons[0]})
    assert response.status_code == 200, response.text
    total = response.json()["items"][0]["income" if endpoint == "cash-flow" else "total"]
    assert total["report_amount"] == "10.00"


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_isolation_and_foreign_or_missing_filters(client: TestClient, endpoint: str) -> None:
    login(client)
    wallet = create_account(client)
    person = create_person(client)
    create_transaction(client, wallet, kind="income", amount="123.00")
    loan = create_loan(client, person, wallet)
    add_movement(
        client,
        loan,
        {
            "kind": "interest",
            "amount_in_loan_currency": "5.00",
            "occurred_at": "2026-10-01T13:00:00Z",
        },
    )
    add_movement(client, loan, payment_payload(wallet, "5.00"))
    login(client, "second@example.test")
    rows = report(client, endpoint)
    if endpoint == "cash-flow":
        assert rows[0]["income"] == {
            "by_currency": [],
            "report_currency": "USD",
            "report_amount": "0.00",
            "unconverted_count": 0,
        }
    else:
        assert rows == []
    for field, entity_id in (
        ("account_id", wallet),
        ("person_id", person),
        ("account_id", "00000000-0000-0000-0000-000000000001"),
        ("person_id", "00000000-0000-0000-0000-000000000001"),
    ):
        response = client.get(f"/api/v1/reports/{endpoint}", params={**RANGE, field: entity_id})
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/problem+json"


def test_interest_paid_into_foreign_account_uses_both_stored_rates(client: TestClient) -> None:
    login(client)
    wallet = create_account(client)
    dollar = create_account(client, "USD", currency="USD")
    loan = create_loan(client, create_person(client), wallet)
    add_movement(
        client,
        loan,
        {
            "kind": "interest",
            "amount_in_loan_currency": "10.00",
            "occurred_at": "2026-10-01T13:00:00Z",
        },
    )
    add_movement(
        client,
        loan,
        payment_payload(
            dollar,
            "210.00",
            account_currency="USD",
            account_amount="52.50",
            fx_rate_applied="0.250000",
            fx_rate_to_base="4.000000",
        ),
    )
    for endpoint in ENDPOINTS:
        response = client.get(f"/api/v1/reports/{endpoint}", params=RANGE)
        assert response.status_code == 200, response.text
        total = response.json()["items"][0]["income" if endpoint == "cash-flow" else "total"]
        assert total == {
            "by_currency": [{"currency": "USD", "amount": "2.50"}],
            "report_currency": "PEN",
            "report_amount": "10.00",
            "unconverted_count": 0,
        }
        missing = client.get(
            f"/api/v1/reports/{endpoint}", params={**RANGE, "report_currency": "EUR"}
        )
        total = missing.json()["items"][0]["income" if endpoint == "cash-flow" else "total"]
        assert total["report_amount"] == "0.00" and total["unconverted_count"] == 1


def test_missing_rate_counts_entries_before_daily_preaggregation(client: TestClient) -> None:
    login(client)
    wallet = create_account(client)
    for _ in range(3):
        create_transaction(client, wallet, amount="-10.00")
    for endpoint in ENDPOINTS:
        response = client.get(
            f"/api/v1/reports/{endpoint}", params={**RANGE, "report_currency": "USD"}
        )
        assert response.status_code == 200, response.text
        total = response.json()["items"][0]["expense" if endpoint == "cash-flow" else "total"]
        assert total == {
            "by_currency": [{"currency": "PEN", "amount": "30.00"}],
            "report_currency": "USD",
            "report_amount": "0.00",
            "unconverted_count": 3,
        }
