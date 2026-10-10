"""Signed progress, atomic selections, ownership and bounded goal pages."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from api.conftest import (
    create_account,
    create_loan,
    create_person,
    create_transaction,
    create_transfer,
    csrf_headers,
    login,
)
from api.test_account_balance import statements
from api.test_reports_statistics import rate
from monetae.db.models import Goal, GoalTransaction, Transaction, User

ROOT = "/api/v1/goals"


def payload(**values: object) -> dict[str, object]:
    return {
        "name": "Synthetic goal",
        "kind": "save",
        "target_amount": "100.00",
        "currency": "PEN",
        **values,
    }


def create_goal(client: TestClient, **values: object) -> str:
    response = client.post(ROOT, json=payload(**values), headers=csrf_headers(client))
    assert response.status_code == 201, response.text
    entity_id = response.json()["id"]
    assert isinstance(entity_id, str)
    return entity_id


def assign(client: TestClient, goal: str, ids: list[str]) -> None:
    response = client.put(
        f"{ROOT}/{goal}/transactions", json={"transaction_ids": ids}, headers=csrf_headers(client)
    )
    assert response.status_code == 200, response.text


def test_crud_partial_and_soft_delete(client: TestClient, db_session: Session) -> None:
    login(client)
    custom = f"custom:{uuid4()}"
    goal = create_goal(client, color="#Abc123", icon=custom, due_on="2026-01-01")
    before = client.get(f"{ROOT}/{goal}").json()
    assert before["icon"] == custom and before["progress_amount"] == "0.00"
    response = client.patch(
        f"{ROOT}/{goal}",
        json={"name": "Renamed", "due_on": None, "color": None, "icon": None},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    after = response.json()
    assert after["name"] == "Renamed" and after["target_amount"] == before["target_amount"]
    assert after["due_on"] is after["color"] is after["icon"] is None
    transaction = create_transaction(client, create_account(client))
    assign(client, goal, [transaction])
    assert client.delete(f"{ROOT}/{goal}", headers=csrf_headers(client)).status_code == 200
    assert client.get(f"{ROOT}/{goal}").status_code == 404
    assert client.get(ROOT).json()["items"] == []
    row = db_session.get(Goal, UUID(goal))
    assert row is not None and row.deleted_at is not None
    assert client.get(f"/api/v1/transactions/{transaction}").status_code == 200
    assert (
        client.patch(
            f"{ROOT}/{goal}", json={"name": "Hidden"}, headers=csrf_headers(client)
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"{ROOT}/{goal}/transactions",
            json={"transaction_ids": []},
            headers=csrf_headers(client),
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "values",
    [
        {"name": ""},
        {"kind": "loan"},
        {"target_amount": "0.00"},
        {"target_amount": "-1.00"},
        {"target_amount": 10},
        {"currency": "pen"},
        {"color": "red"},
        {"icon": ""},
        {"icon": "x" * 65},
        {"due_on": "invalid"},
        {"user_id": str(uuid4())},
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
        {"kind": None},
        {"target_amount": None},
        {"currency": None},
        {"kind": "loan"},
        {"target_amount": "0.00"},
        {"color": "#ffff"},
        {"icon": ""},
    ],
)
def test_patch_validation_atomic(client: TestClient, values: dict[str, object]) -> None:
    login(client)
    goal = create_goal(client)
    before = client.get(f"{ROOT}/{goal}").json()
    assert (
        client.patch(f"{ROOT}/{goal}", json=values, headers=csrf_headers(client)).status_code == 422
    )
    assert client.get(f"{ROOT}/{goal}").json() == before


@pytest.mark.parametrize("kind,expected", [("save", "70.00"), ("spend", "-70.00")])
def test_signed_progress_transfers_and_all_dates(
    client: TestClient, db_session: Session, kind: str, expected: str
) -> None:
    login(client)
    account = create_account(client)
    income = create_transaction(
        client, account, kind="income", amount="100.00", occurred_at="2025-01-01T00:00:00Z"
    )
    expense = create_transaction(
        client, account, amount="-40.00", occurred_at="2027-01-01T00:00:00Z"
    )
    transfer = create_transfer(client, create_account(client, "Other"), account)
    legs = list(
        db_session.scalars(
            select(Transaction).where(Transaction.transfer_group_id == UUID(transfer))
        )
    )
    incoming = next(str(t.id) for t in legs if t.amount > 0)
    outgoing = next(str(t.id) for t in legs if t.amount < 0)
    goal = create_goal(client, kind=kind, due_on="2026-01-01")
    assign(client, goal, [income, expense, incoming])
    result = client.get(f"{ROOT}/{goal}").json()
    assert result["progress_amount"] == expected
    assert result["report_total"]["report_amount"] == expected
    assert result["report_total"]["by_currency"] == [{"currency": "PEN", "amount": expected}]
    assign(client, goal, [incoming, outgoing])
    assert client.get(f"{ROOT}/{goal}").json()["progress_amount"] == "0.00"


def test_spend_refund_negative_progress_and_patch_kind(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    ids = [
        create_transaction(client, account, amount="-40.00"),
        create_transaction(client, account, amount="-30.00"),
        create_transaction(client, account, kind="income", amount="20.00"),
    ]
    goal = create_goal(client, kind="spend")
    assign(client, goal, ids)
    assert client.get(f"{ROOT}/{goal}").json()["progress_amount"] == "50.00"
    assign(client, goal, [ids[-1]])
    assert client.get(f"{ROOT}/{goal}").json()["progress_amount"] == "-20.00"
    assert (
        client.patch(f"{ROOT}/{goal}", json={"kind": "save"}, headers=csrf_headers(client)).json()[
            "progress_amount"
        ]
        == "20.00"
    )


def test_selection_restore_exclusions_and_atomic_loan_rejection(
    client: TestClient, db_session: Session
) -> None:
    login(client)
    account = create_account(client)
    first = create_transaction(client, account)
    second = create_transaction(client, account, amount="-20.00")
    scheduled = create_transaction(client, account, status="scheduled", amount="-90.00")
    deleted = create_transaction(client, account, amount="-80.00")
    goal = create_goal(client, kind="spend")
    assign(client, goal, [first, scheduled, deleted])
    assert (
        client.delete(f"/api/v1/transactions/{deleted}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert client.get(f"{ROOT}/{goal}").json()["progress_amount"] == "10.00"
    link = db_session.scalar(
        select(GoalTransaction).where(GoalTransaction.transaction_id == UUID(first))
    )
    assert link is not None
    link_id = link.id
    assign(client, goal, [second])
    db_session.refresh(link)
    assert link.deleted_at is not None
    assert client.get(f"{ROOT}/{goal}").json()["progress_amount"] == "20.00"
    loan = create_loan(client, create_person(client), account)
    loan_transaction = client.get(f"/api/v1/loans/{loan}/movements").json()["items"][0][
        "transaction_id"
    ]
    before = client.get(f"{ROOT}/{goal}").json()
    response = client.put(
        f"{ROOT}/{goal}/transactions",
        json={"transaction_ids": [first, loan_transaction]},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422 and "loan_transaction_not_allowed" in response.text
    assert client.get(f"{ROOT}/{goal}").json() == before
    for invalid in [str(uuid4()), deleted]:
        assert (
            client.put(
                f"{ROOT}/{goal}/transactions",
                json={"transaction_ids": [first, invalid]},
                headers=csrf_headers(client),
            ).status_code
            == 404
        )
        assert client.get(f"{ROOT}/{goal}").json() == before
    assign(client, goal, [first, second])
    db_session.refresh(link)
    assert link.id == link_id and link.deleted_at is None
    assert client.get(f"{ROOT}/{goal}").json()["progress_amount"] == "30.00"
    assign(client, goal, [])
    assert client.get(f"{ROOT}/{goal}").json()["progress_amount"] == "0.00"


@pytest.mark.parametrize("size,duplicate", [(201, False), (2, True)])
def test_assignment_validation(client: TestClient, size: int, duplicate: bool) -> None:
    login(client)
    goal = create_goal(client)
    ids = [str(uuid4()) for _ in range(size)]
    if duplicate:
        ids[1] = ids[0]
    assert (
        client.put(
            f"{ROOT}/{goal}/transactions",
            json={"transaction_ids": ids},
            headers=csrf_headers(client),
        ).status_code
        == 422
    )


def test_200_assignments_allowed(client: TestClient, db_session: Session) -> None:
    login(client)
    account = create_account(client)
    owner = client.get("/api/v1/users/me").json()["id"]
    ids = list(
        db_session.scalars(
            text("""
        INSERT INTO transactions (user_id, account_id, currency, kind, amount,
            occurred_at, status, title, fx_rate_to_base, fx_rate_source, source)
        SELECT :owner, :account, 'PEN', 'expense', -1,
            '2026-10-07T12:00:00Z', 'posted', 'Synthetic boundary', 1, 'manual', 'web'
        FROM generate_series(1, 200) RETURNING id
    """),
            {"owner": owner, "account": account},
        )
    )
    goal = create_goal(client, kind="spend")
    assign(client, goal, [str(entity_id) for entity_id in ids])
    assert client.get(f"{ROOT}/{goal}").json()["progress_amount"] == "200.00"


def test_conversion_fixed_fx_and_missing_historical_rate(
    client: TestClient, db_session: Session
) -> None:
    login(client)
    usd = create_account(client, currency="USD")
    transaction = create_transaction(
        client, usd, currency="USD", amount="-10.00", fx_rate_to_base="4.000000"
    )
    pen = create_goal(client, kind="spend")
    assign(client, pen, [transaction])
    total = client.get(f"{ROOT}/{pen}").json()["report_total"]
    assert total["report_amount"] == "40.00" and total["unconverted_count"] == 0
    goal = create_goal(client, kind="spend", currency="USD")
    assign(client, goal, [transaction])
    before = client.get(f"{ROOT}/{goal}").json()
    assert before["progress_amount"] == "0.00"
    assert before["report_total"]["unconverted_count"] == 1
    assert before["report_total"]["by_currency"] == [{"currency": "USD", "amount": "10.00"}]
    rate(db_session, "2026-10-08", "0.500000")  # Future rates must not count.
    assert client.get(f"{ROOT}/{goal}").json() == before
    rate(db_session, "2026-10-06", "0.250000")
    after = client.get(f"{ROOT}/{goal}").json()
    assert after["progress_amount"] == "10.00" and after["report_total"]["unconverted_count"] == 0


def test_two_user_isolation_every_route(
    client: TestClient, db_session: Session, auth_users: tuple[User, User]
) -> None:
    login(client)
    goal = create_goal(client)
    transaction = create_transaction(client, create_account(client))
    assign(client, goal, [transaction])
    before = client.get(f"{ROOT}/{goal}").json()
    login(client, "second@example.test")
    assert client.get(ROOT).json()["items"] == []
    requests: list[tuple[str, str, dict[str, object] | None]] = [
        ("GET", f"{ROOT}/{goal}", None),
        ("PATCH", f"{ROOT}/{goal}", {"name": "Foreign"}),
        ("DELETE", f"{ROOT}/{goal}", None),
        ("PUT", f"{ROOT}/{goal}/transactions", {"transaction_ids": []}),
    ]
    for method, path, body in requests:
        assert (
            client.request(method, path, json=body, headers=csrf_headers(client)).status_code == 404
        )
    own = create_goal(client)
    row = db_session.get(Goal, UUID(own))
    assert row is not None and row.user_id == auth_users[1].id
    assert (
        client.put(
            f"{ROOT}/{own}/transactions",
            json={"transaction_ids": [transaction]},
            headers=csrf_headers(client),
        ).status_code
        == 404
    )
    assert client.get(f"{ROOT}/{own}").json()["progress_amount"] == "0.00"
    login(client)
    assert client.get(f"{ROOT}/{goal}").json() == before
    assert [r["id"] for r in client.get(ROOT).json()["items"]] == [goal]
    assert client.get(f"{ROOT}/{own}").status_code == 404


def test_pagination_and_constant_queries(client: TestClient, db_engine: Engine) -> None:
    login(client)
    transaction = create_transaction(client, create_account(client))
    ids = [create_goal(client, name=f"Goal {n}", kind="spend") for n in range(8)]
    for goal in ids:
        assign(client, goal, [transaction])
    with statements(db_engine) as one:
        first = client.get(ROOT, params={"limit": 1})
    with statements(db_engine) as many:
        page = client.get(ROOT, params={"limit": 200})
    assert len(one) == len(many) and len(many) <= 5, (one, many)
    assert all(r["progress_amount"] == "10.00" for r in page.json()["items"])
    found = [first.json()["items"][0]["id"]]
    cursor = first.json()["next_cursor"]
    while cursor:
        response = client.get(ROOT, params={"limit": 2, "cursor": cursor})
        assert response.status_code == 200
        found.extend(r["id"] for r in response.json()["items"])
        cursor = response.json()["next_cursor"]
    assert found == [r["id"] for r in page.json()["items"]]
    assert set(found) == set(ids) and len(found) == len(ids)
    print(f"goal list: limit=1 and limit=200 each use {len(many)} SQL statements")
    assert client.get(ROOT, params={"cursor": "garbage"}).status_code == 400
    login(client, "second@example.test")
    assert client.get(ROOT, params={"cursor": first.json()["next_cursor"]}).status_code == 400


def test_security_session_csrf_origin(client: TestClient) -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = [
        ("GET", ROOT, None),
        ("GET", f"{ROOT}/{uuid4()}", None),
        ("POST", ROOT, payload()),
    ]
    for method, path, body in requests:
        assert (
            client.request(method, path, json=body, headers=csrf_headers(client)).status_code == 401
        )
    login(client)
    goal = create_goal(client)
    for method, path, data in [
        ("POST", ROOT, payload()),
        ("PATCH", f"{ROOT}/{goal}", {"name": "Changed"}),
        ("DELETE", f"{ROOT}/{goal}", None),
        ("PUT", f"{ROOT}/{goal}/transactions", {"transaction_ids": []}),
    ]:
        assert client.request(method, path, json=data).status_code == 403
        assert (
            client.request(
                method,
                path,
                json=data,
                headers={**csrf_headers(client), "Origin": "https://evil.example.test"},
            ).status_code
            == 403
        )
