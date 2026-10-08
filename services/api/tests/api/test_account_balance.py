from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, event

from api.conftest import create_account, create_category, create_transaction, csrf_headers, login


@contextmanager
def statements(engine: Engine) -> Iterator[list[str]]:
    collected: list[str] = []

    def record(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        if not statement.startswith(("SAVEPOINT", "RELEASE SAVEPOINT", "ROLLBACK TO SAVEPOINT")):
            collected.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield collected
    finally:
        event.remove(engine, "before_cursor_execute", record)


def balance(client: TestClient, account: str) -> str:
    result = client.get(f"/api/v1/accounts/{account}")
    assert result.status_code == 200, result.text
    assert result.json()["initial_balance"] == "12.50"
    amount = result.json()["balance"]
    assert isinstance(amount, str)
    return amount


def test_balances_posted_deleted_scheduled_restored_and_multiple_currencies(
    client: TestClient,
) -> None:
    login(client)
    account = create_account(client)
    dollar = create_account(client, "Dollar")
    client.patch(
        f"/api/v1/accounts/{dollar}", json={"currency": "USD"}, headers=csrf_headers(client)
    )
    create_transaction(client, account, kind="income", amount="100.00")
    expense = create_transaction(client, account, amount="-30.00")
    create_transaction(client, account, kind="income", amount="999.00", status="scheduled")
    create_transaction(client, dollar, currency="USD", amount="-2.50", fx_rate_to_base="3.800000")
    assert balance(client, account) == "82.50"
    assert balance(client, dollar) == "10.00"
    client.delete(f"/api/v1/transactions/{expense}", headers=csrf_headers(client))
    assert balance(client, account) == "112.50"
    client.post(f"/api/v1/transactions/{expense}/restore", headers=csrf_headers(client))
    assert balance(client, account) == "82.50"
    listed = client.get("/api/v1/accounts").json()["items"]
    assert {row["id"]: row["balance"] for row in listed} == {account: "82.50", dollar: "10.00"}
    client.patch(
        f"/api/v1/transactions/{expense}", json={"amount": "-50.00"}, headers=csrf_headers(client)
    )
    assert balance(client, account) == "62.50"


def test_list_25_account_balances_uses_one_aggregate_query(
    client: TestClient, db_engine: Engine
) -> None:
    login(client)
    accounts = [create_account(client, f"Account {number:02}") for number in range(25)]
    for account in accounts:
        create_transaction(client, account)
    with statements(db_engine) as queries:
        response = client.get("/api/v1/accounts")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 25
    assert all(row["balance"] == "2.50" for row in response.json()["items"])
    aggregates = [q for q in queries if "sum(transactions.amount)" in q.lower()]
    assert len(aggregates) == 1
    assert len(queries) <= 5, queries
    assert not any("FOR UPDATE" in q.upper() or "FOR SHARE" in q.upper() for q in queries)


def test_account_and_base_currency_lock_includes_deleted_history(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    changed = client.patch(
        "/api/v1/users/me", json={"base_currency": "USD"}, headers=csrf_headers(client)
    )
    assert changed.status_code == 200 and changed.json()["report_currency"] == "PEN"
    assert (
        client.patch(
            "/api/v1/users/me", json={"base_currency": "PEN"}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    entity_id = create_transaction(client, account)
    for deleted in (False, True):
        if deleted:
            client.delete(f"/api/v1/transactions/{entity_id}", headers=csrf_headers(client))
        account_change = client.patch(
            f"/api/v1/accounts/{account}", json={"currency": "USD"}, headers=csrf_headers(client)
        )
        assert account_change.status_code == 409
        assert account_change.json()["code"] == "account_currency_locked"
        base_change = client.patch(
            "/api/v1/users/me", json={"base_currency": "USD"}, headers=csrf_headers(client)
        )
        assert (
            base_change.status_code == 409 and base_change.json()["code"] == "base_currency_locked"
        )
    # Un PATCH que conserva la moneda actual sigue permitido.
    assert (
        client.patch(
            f"/api/v1/accounts/{account}", json={"currency": "PEN"}, headers=csrf_headers(client)
        ).status_code
        == 200
    )


def test_account_and_category_delete_are_blocked_only_by_active_transactions(
    client: TestClient,
) -> None:
    login(client)
    account, category = create_account(client), create_category(client)
    entity_id = create_transaction(client, account, category_id=category)
    for resource, code in (
        (f"accounts/{account}", "account_in_use"),
        (f"categories/{category}", "category_in_use"),
    ):
        response = client.delete(f"/api/v1/{resource}", headers=csrf_headers(client))
        assert response.status_code == 409 and response.json()["code"] == code
    archived = client.post(
        f"/api/v1/accounts/{account}/archive", json={}, headers=csrf_headers(client)
    )
    assert archived.status_code == 200 and archived.json()["balance"] == "2.50"
    client.delete(f"/api/v1/transactions/{entity_id}", headers=csrf_headers(client))
    assert (
        client.delete(f"/api/v1/accounts/{account}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert (
        client.delete(f"/api/v1/categories/{category}", headers=csrf_headers(client)).status_code
        == 200
    )


def test_balances_and_currency_locks_ignore_other_users_history(
    client: TestClient, application: FastAPI
) -> None:
    login(client)
    account = create_account(client)
    create_transaction(client, account, kind="income", amount="100.00")
    with TestClient(application, base_url="https://testserver") as other:
        login(other, "second@example.test")
        other_account = create_account(other)
        changed = other.patch(
            f"/api/v1/accounts/{other_account}",
            json={"currency": "USD"},
            headers=csrf_headers(other),
        )
        assert changed.status_code == 200
        base = other.patch(
            "/api/v1/users/me", json={"base_currency": "PEN"}, headers=csrf_headers(other)
        )
        assert base.status_code == 200 and base.json()["report_currency"] == "USD"
        create_transaction(
            other, other_account, currency="USD", amount="-1.00", fx_rate_to_base="3.800000"
        )
        assert balance(other, other_account) == "11.50"
        assert len(other.get("/api/v1/accounts").json()["items"]) == 1
    assert balance(client, account) == "112.50"


def test_transfer_balances_conserve_same_currency_through_lifecycle(client: TestClient) -> None:
    from decimal import Decimal

    from api.conftest import create_transfer

    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    assert (balance(client, source), balance(client, target)) == ("12.50", "12.50")
    id = create_transfer(client, source, target)
    assert (balance(client, source), balance(client, target)) == ("2.50", "22.50")
    assert Decimal(balance(client, source)) + Decimal(balance(client, target)) == Decimal("25.00")
    client.patch(
        f"/api/v1/transfers/{id}",
        json={"from_amount": "5.00", "to_amount": "5.00"},
        headers=csrf_headers(client),
    )
    assert (balance(client, source), balance(client, target)) == ("7.50", "17.50")
    client.delete(f"/api/v1/transfers/{id}", headers=csrf_headers(client))
    assert (balance(client, source), balance(client, target)) == ("12.50", "12.50")
    client.post(f"/api/v1/transfers/{id}/restore", headers=csrf_headers(client))
    assert (balance(client, source), balance(client, target)) == ("7.50", "17.50")
