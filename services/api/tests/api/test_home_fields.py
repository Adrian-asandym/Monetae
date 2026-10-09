"""Contract 0.5 home fields against PostgreSQL with synthetic data only."""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from api.conftest import (
    add_movement,
    create_account,
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
from monetae.db.models import User


def test_default_account_persists_and_preferences_replace(
    client: TestClient, db_session: Session, auth_users: tuple[User, User]
) -> None:
    login(client)
    account = create_account(client)
    response = client.patch(
        "/api/v1/users/me",
        json={"preferences": {"default_account_id": account, "theme": "dark"}},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    assert response.json()["preferences"]["default_account_id"] == account
    assert client.get("/api/v1/users/me").json()["preferences"]["default_account_id"] == account
    db_session.refresh(auth_users[0])
    assert auth_users[0].preferences["default_account_id"] == account
    response = client.patch("/api/v1/users/me", json={"locale": "en"}, headers=csrf_headers(client))
    assert response.json()["preferences"]["default_account_id"] == account
    response = client.patch(
        "/api/v1/users/me", json={"preferences": {"theme": "light"}}, headers=csrf_headers(client)
    )
    assert response.status_code == 200
    assert response.json()["preferences"]["default_account_id"] is None
    db_session.refresh(auth_users[0])
    assert auth_users[0].preferences["default_account_id"] is None
    response = client.patch(
        "/api/v1/users/me",
        json={"preferences": {"default_account_id": None}},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert "theme" not in response.json()["preferences"]


@pytest.mark.parametrize("state", ["foreign", "missing", "archived", "deleted"])
def test_invalid_default_account_rejects_entire_patch(
    client: TestClient,
    application: FastAPI,
    db_session: Session,
    auth_users: tuple[User, User],
    state: str,
) -> None:
    login(client)
    active = create_account(client, "Active")
    response = client.patch(
        "/api/v1/users/me",
        json={"preferences": {"default_account_id": active}},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    before = client.get("/api/v1/users/me").json()
    if state == "missing":
        invalid = str(uuid4())
    elif state == "foreign":
        with TestClient(application, base_url="https://testserver") as other:
            login(other, "second@example.test")
            invalid = create_account(other)
    else:
        invalid = create_account(client, "Invalid")
        if state == "archived":
            response = client.post(
                f"/api/v1/accounts/{invalid}/archive", json={}, headers=csrf_headers(client)
            )
        else:
            response = client.delete(f"/api/v1/accounts/{invalid}", headers=csrf_headers(client))
        assert response.status_code == 200
    response = client.patch(
        "/api/v1/users/me",
        json={"locale": "en", "preferences": {"default_account_id": invalid}},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "account_not_found"
    assert response.headers["content-type"].startswith("application/problem+json")
    assert client.get("/api/v1/users/me").json() == before
    db_session.refresh(auth_users[0])
    assert auth_users[0].preferences["default_account_id"] == active
    assert auth_users[0].locale == "es"


@pytest.mark.parametrize("action", ["archive", "delete"])
def test_default_account_read_does_not_write_preferences(
    client: TestClient,
    db_session: Session,
    auth_users: tuple[User, User],
    action: str,
) -> None:
    login(client)
    account = create_account(client)
    response = client.patch(
        "/api/v1/users/me",
        json={"preferences": {"default_account_id": account}},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    if action == "archive":
        response = client.post(
            f"/api/v1/accounts/{account}/archive", json={}, headers=csrf_headers(client)
        )
    else:
        response = client.delete(f"/api/v1/accounts/{account}", headers=csrf_headers(client))
    assert response.status_code == 200
    assert client.get("/api/v1/users/me").json()["preferences"]["default_account_id"] is None
    db_session.refresh(auth_users[0])
    assert auth_users[0].preferences["default_account_id"] == account
    if action == "archive":
        response = client.post(
            f"/api/v1/accounts/{account}/reactivate", headers=csrf_headers(client)
        )
        assert response.status_code == 200
        assert client.get("/api/v1/users/me").json()["preferences"]["default_account_id"] == account


@pytest.mark.parametrize("value", ["invalid", 1, True, {}, []])
def test_default_account_uuid_validation_is_strict(client: TestClient, value: object) -> None:
    login(client)
    response = client.patch(
        "/api/v1/users/me",
        json={"preferences": {"default_account_id": value}},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422


def test_account_counts_all_posted_types_and_user_isolation(
    client: TestClient,
    application: FastAPI,
) -> None:
    login(client)
    account, target = create_account(client), create_account(client, "Target")
    assert client.get(f"/api/v1/accounts/{account}").json()["transaction_count"] == 0
    create_transaction(client, account, kind="income", amount="100.00")
    deleted = create_transaction(client, account)
    client.delete(f"/api/v1/transactions/{deleted}", headers=csrf_headers(client))
    create_transaction(client, account, status="scheduled")
    transfer = create_transfer(client, account, target)
    loan = create_loan(client, create_person(client), account)
    add_movement(client, loan, payment_payload(target, "50.00"))
    add_movement(
        client,
        loan,
        {
            "kind": "interest",
            "amount_in_loan_currency": "10.00",
            "occurred_at": "2026-10-03T12:00:00Z",
        },
    )
    expected = {account: 3, target: 2}
    listed = client.get("/api/v1/accounts").json()["items"]
    assert {r["id"]: r["transaction_count"] for r in listed} == expected
    for account_id, count in expected.items():
        assert client.get(f"/api/v1/accounts/{account_id}").json()["transaction_count"] == count
    with TestClient(application, base_url="https://testserver") as other:
        login(other, "second@example.test")
        other_account = create_account(other)
        create_transaction(other, other_account, fx_rate_to_base="3.800000")
        rows = other.get("/api/v1/accounts").json()["items"]
        assert [(r["id"], r["transaction_count"]) for r in rows] == [(other_account, 1)]
        assert other.get(f"/api/v1/accounts/{account}").status_code == 404
    response = client.patch(
        f"/api/v1/accounts/{account}", json={"color": "blue"}, headers=csrf_headers(client)
    )
    assert response.json()["transaction_count"] == 3
    response = client.post(
        f"/api/v1/accounts/{account}/archive", json={}, headers=csrf_headers(client)
    )
    assert response.json()["transaction_count"] == 3
    response = client.post(f"/api/v1/accounts/{account}/reactivate", headers=csrf_headers(client))
    assert response.json()["transaction_count"] == 3
    client.delete(f"/api/v1/transfers/{transfer}", headers=csrf_headers(client))
    assert client.get(f"/api/v1/accounts/{account}").json()["transaction_count"] == 2
    assert client.get(f"/api/v1/accounts/{target}").json()["transaction_count"] == 1


def test_paginated_account_counts_use_constant_queries(
    client: TestClient, db_engine: Engine
) -> None:
    login(client)
    accounts = [create_account(client, f"Account {i:02}") for i in range(25)]
    for account in accounts:
        create_transaction(client, account)
    query_counts = []
    for limit in (1, 10, 25):
        with statements(db_engine) as queries:
            response = client.get("/api/v1/accounts", params={"limit": limit})
        assert response.status_code == 200
        assert len(response.json()["items"]) == limit
        assert all(row["transaction_count"] == 1 for row in response.json()["items"])
        assert (
            sum(
                "count(transactions.id)" in q.lower() and "sum(transactions.amount)" in q.lower()
                for q in queries
            )
            == 1
        )
        query_counts.append(len(queries))
    assert len(set(query_counts)) == 1
    assert query_counts[0] <= 5
    cursor = client.get("/api/v1/accounts", params={"limit": 10}).json()["next_cursor"]
    with statements(db_engine) as queries:
        response = client.get("/api/v1/accounts", params={"limit": 10, "cursor": cursor})
    assert response.status_code == 200
    assert len(queries) == query_counts[0]
    assert all(row["transaction_count"] == 1 for row in response.json()["items"])
    print(f"account pages: limits 1/10/25 and second page = {query_counts[0]} SQL statements")


def test_cumulative_net_three_months_continues_across_pages(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    create_transaction(
        client, account, kind="income", amount="999.00", occurred_at="2025-12-15T12:00:00Z"
    )
    create_transaction(
        client, account, kind="income", amount="100.00", occurred_at="2026-01-15T12:00:00Z"
    )
    create_transaction(client, account, amount="-30.00", occurred_at="2026-02-15T12:00:00Z")
    params = {"date_from": "2026-01-01", "date_to": "2026-03-31", "period": "monthly"}
    response = client.get("/api/v1/reports/cash-flow", params=params)
    assert response.status_code == 200
    rows = response.json()["items"]
    assert [r["net"]["report_amount"] for r in rows] == ["100.00", "-30.00", "0.00"]
    assert [r["cumulative_net"]["report_amount"] for r in rows] == ["100.00", "70.00", "70.00"]
    assert rows[-1]["cumulative_net"]["by_currency"] == [{"currency": "PEN", "amount": "70.00"}]
    first = client.get("/api/v1/reports/cash-flow", params={**params, "limit": 1}).json()
    second = client.get(
        "/api/v1/reports/cash-flow", params={**params, "limit": 2, "cursor": first["next_cursor"]}
    ).json()
    assert first["items"] + second["items"] == rows
    assert second["next_cursor"] is None


def test_cumulative_currency_and_unconverted_counts(
    client: TestClient, db_session: Session
) -> None:
    login(client)
    pen, usd = create_account(client), create_account(client, "USD", currency="USD")
    create_transaction(
        client, pen, kind="income", amount="100.00", occurred_at="2026-01-15T12:00:00Z"
    )
    create_transaction(
        client,
        usd,
        amount="-10.00",
        currency="USD",
        fx_rate_to_base="3.800000",
        occurred_at="2026-02-15T12:00:00Z",
    )
    create_transaction(client, pen, amount="-20.00", occurred_at="2026-03-15T12:00:00Z")
    # Both early months lack historical conversion, including the USD entry.
    rate(db_session, "2026-03-01", "0.250000")
    params = {
        "date_from": "2026-01-01",
        "date_to": "2026-04-30",
        "period": "monthly",
        "report_currency": "USD",
    }
    response = client.get("/api/v1/reports/cash-flow", params=params)
    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert [r["cumulative_net"]["report_amount"] for r in rows] == [
        "0.00",
        "0.00",
        "-5.00",
        "-5.00",
    ]
    assert [r["cumulative_net"]["unconverted_count"] for r in rows] == [1, 2, 2, 2]
    assert rows[1]["cumulative_net"]["by_currency"] == [
        {"currency": "PEN", "amount": "100.00"},
        {"currency": "USD", "amount": "-10.00"},
    ]
    assert rows[-1]["cumulative_net"]["by_currency"] == [
        {"currency": "PEN", "amount": "80.00"},
        {"currency": "USD", "amount": "-10.00"},
    ]
    first = client.get("/api/v1/reports/cash-flow", params={**params, "limit": 2}).json()
    second = client.get(
        "/api/v1/reports/cash-flow", params={**params, "cursor": first["next_cursor"]}
    ).json()
    assert first["items"] + second["items"] == rows
    base = client.get(
        "/api/v1/reports/cash-flow", params={**params, "report_currency": "PEN"}
    ).json()["items"]
    assert [r["cumulative_net"]["report_amount"] for r in base] == [
        "100.00",
        "62.00",
        "42.00",
        "42.00",
    ]
    assert all(r["cumulative_net"]["unconverted_count"] == 0 for r in base)


def test_cumulative_net_rounds_once_after_accumulating(
    client: TestClient,
    db_session: Session,
) -> None:
    login(client)
    account = create_account(client)
    rate(db_session, "2026-01-01", "0.000005")
    for day in ("2026-01-15", "2026-02-15"):
        create_transaction(
            client, account, kind="income", amount="1000.00", occurred_at=f"{day}T12:00:00Z"
        )
    response = client.get(
        "/api/v1/reports/cash-flow",
        params={
            "date_from": "2026-01-01",
            "date_to": "2026-02-28",
            "report_currency": "USD",
        },
    )
    assert response.status_code == 200
    rows = response.json()["items"]
    assert [r["net"]["report_amount"] for r in rows] == ["0.01", "0.01"]
    assert [r["cumulative_net"]["report_amount"] for r in rows] == ["0.01", "0.01"]
