from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from monetae.db.models import Account

from .conftest import (
    create_account,
    create_transfer,
    csrf_headers,
    login,
    transfer_payload,
)
from .test_account_balance import statements


def test_transfer_lifecycle_and_legs(client: TestClient) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    id = create_transfer(client, source, target, note="Synthetic note")
    transfer = client.get(f"/api/v1/transfers/{id}").json()
    assert transfer["implicit_rate"] == "1.000000"
    outgoing, incoming = transfer["outgoing_transaction_id"], transfer["incoming_transaction_id"]
    for leg, amount, account in ((outgoing, "-10.00", source), (incoming, "10.00", target)):
        row = client.get(f"/api/v1/transactions/{leg}").json()
        assert row["amount"] == amount and row["account_id"] == account
        assert row["transfer_group_id"] == id and row["category_id"] is None
        assert row["kind"] == "transfer" and row["status"] == "posted" and row["source"] == "web"
        assert row["note"] == "Synthetic note"
        for method, suffix, body in (
            ("patch", "", {"title": "Bad"}),
            ("delete", "", None),
            ("post", "/restore", None),
        ):
            response = client.request(
                method,
                f"/api/v1/transactions/{leg}{suffix}",
                json=body,
                headers=csrf_headers(client),
            )
            assert response.status_code == 409
            assert response.json()["code"] == "transaction_flow_required"
    response = client.patch(
        f"/api/v1/transfers/{id}",
        json={
            "from_amount": "15.00",
            "to_amount": "15.00",
            "note": None,
            "title": "Changed",
            "occurred_at": "2026-10-08T00:00:00-05:00",
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    assert response.json()["note"] is None
    assert response.json()["occurred_at"] == "2026-10-08T05:00:00Z"
    for leg in (outgoing, incoming):
        assert client.get(f"/api/v1/transactions/{leg}").json()["title"] == "Changed"
    deletion = client.delete(f"/api/v1/transfers/{id}", headers=csrf_headers(client))
    assert deletion.json() == {"success": True, "affected_count": 2}
    assert client.get(f"/api/v1/transfers/{id}").status_code == 404
    assert client.get("/api/v1/transfers").json()["items"] == []
    for leg in (outgoing, incoming):
        assert client.get(f"/api/v1/transactions/{leg}?include_deleted=true").json()["deleted_at"]
        response = client.post(f"/api/v1/transactions/{leg}/restore", headers=csrf_headers(client))
        assert response.status_code == 409
    restored = client.post(f"/api/v1/transfers/{id}/restore", headers=csrf_headers(client))
    assert restored.status_code == 200 and restored.json()["deleted_at"] is None
    assert restored.json()["outgoing_transaction_id"] == outgoing
    assert restored.json()["incoming_transaction_id"] == incoming


@pytest.mark.parametrize("reverse", [False, True])
def test_example_c_and_historical_rates(client: TestClient, reverse: bool) -> None:
    login(client)
    pen = create_account(client)
    usd = create_account(client, "Dollars", currency="USD")
    source, target = (usd, pen) if reverse else (pen, usd)
    values = {
        "from_amount": "100.00" if reverse else "380.00",
        "to_amount": "380.00" if reverse else "100.00",
        "from_fx_rate_to_base": "3.800000" if reverse else "1.000000",
        "to_fx_rate_to_base": "1.000000" if reverse else "3.800000",
    }
    id = create_transfer(client, source, target, **values)
    row = client.get(f"/api/v1/transfers/{id}").json()
    assert row["implicit_rate"] == ("3.800000" if reverse else "0.263158")
    assert all(row[k] == v for k, v in values.items())
    assert (
        client.patch(
            f"/api/v1/transfers/{id}", json={"title": "New title"}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    row = client.get(f"/api/v1/transfers/{id}").json()
    assert all(row[k] == v for k, v in values.items())
    for account, change in (
        (pen, "380.00" if reverse else "-380.00"),
        (usd, "-100.00" if reverse else "100.00"),
    ):
        from decimal import Decimal

        assert Decimal(client.get(f"/api/v1/accounts/{account}").json()["balance"]) == (
            Decimal("12.50") + Decimal(change)
        )


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"to_amount": "11.00"}, "transfer_amount_mismatch"),
        ({"from_fx_rate_to_base": "1.100000"}, "invalid_fx_rate"),
        ({"to_fx_rate_to_base": "2.000000"}, "invalid_fx_rate"),
    ],
)
def test_create_validation(client: TestClient, changes: dict[str, object], code: str) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    response = client.post(
        "/api/v1/transfers",
        json=transfer_payload(source, target, **changes),
        headers=csrf_headers(client),
    )
    assert response.status_code == 422 and response.json()["code"] == code
    assert client.get("/api/v1/transactions").json()["items"] == []


@pytest.mark.parametrize(
    "changes",
    [
        {"from_amount": "0.00"},
        {"from_amount": "-1.00"},
        {"to_amount": 10},
        {"occurred_at": "2026-10-07T12:00:00"},
        {"user_id": str(uuid4())},
    ],
)
def test_strict_payload(client: TestClient, changes: dict[str, object]) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    assert (
        client.post(
            "/api/v1/transfers",
            json=transfer_payload(source, target, **changes),
            headers=csrf_headers(client),
        ).status_code
        == 422
    )


def test_equal_missing_and_deleted_accounts(client: TestClient) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    assert (
        client.post(
            "/api/v1/transfers", json=transfer_payload(source, source), headers=csrf_headers(client)
        ).status_code
        == 422
    )
    for account in (str(uuid4()), target):
        if account == target:
            assert (
                client.delete(
                    f"/api/v1/accounts/{target}", headers=csrf_headers(client)
                ).status_code
                == 200
            )
        assert (
            client.post(
                "/api/v1/transfers",
                json=transfer_payload(source, account),
                headers=csrf_headers(client),
            ).status_code
            == 404
        )


def test_patch_revalidation_and_currency_change(client: TestClient) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    usd = create_account(client, "Dollars", currency="USD")
    id = create_transfer(client, source, target)
    before = client.get(f"/api/v1/transfers/{id}").json()
    for body, code in (
        ({"from_amount": "11.00"}, "transfer_amount_mismatch"),
        ({"to_account_id": source}, "transfer_accounts_equal"),
        ({"to_account_id": usd}, "invalid_fx_rate"),
        ({"to_fx_rate_to_base": "2.000000"}, "invalid_fx_rate"),
    ):
        response = client.patch(f"/api/v1/transfers/{id}", json=body, headers=csrf_headers(client))
        assert response.status_code == 422, response.text
        assert response.json()["code"] == code
        assert client.get(f"/api/v1/transfers/{id}").json() == before
    response = client.patch(
        f"/api/v1/transfers/{id}",
        json={
            "to_account_id": usd,
            "to_fx_rate_to_base": "3.800000",
            "to_amount": "2.00",
            "fx_rate_source": "auto",
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    assert response.json()["implicit_rate"] == "0.200000"
    for leg in (before["outgoing_transaction_id"], before["incoming_transaction_id"]):
        assert client.get(f"/api/v1/transactions/{leg}").json()["fx_rate_source"] == "auto"
    # Al volver a PEN también se exige una tasa explícita, exactamente 1.
    assert (
        client.patch(
            f"/api/v1/transfers/{id}", json={"to_account_id": target}, headers=csrf_headers(client)
        ).status_code
        == 422
    )
    response = client.patch(
        f"/api/v1/transfers/{id}",
        json={"to_account_id": target, "to_fx_rate_to_base": "1.000000", "to_amount": "10.00"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200


def test_zero_rounded_implicit_rate(client: TestClient) -> None:
    login(client)
    source = create_account(client)
    target = create_account(client, "Dollars", currency="USD")
    response = client.post(
        "/api/v1/transfers",
        json=transfer_payload(
            source,
            target,
            from_amount="1000000.00",
            to_amount="0.01",
            to_fx_rate_to_base="3.800000",
        ),
        headers=csrf_headers(client),
    )
    assert response.status_code == 422 and response.json()["code"] == "invalid_fx_rate"


def test_restore_conflict(client: TestClient, db_session: Session) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    id = create_transfer(client, source, target)
    client.delete(f"/api/v1/transfers/{id}", headers=csrf_headers(client))
    assert (
        client.delete(f"/api/v1/accounts/{target}", headers=csrf_headers(client)).status_code == 200
    )
    response = client.post(f"/api/v1/transfers/{id}/restore", headers=csrf_headers(client))
    assert response.status_code == 409 and response.json()["code"] == "restore_conflict"
    assert client.get("/api/v1/transactions").json()["items"] == []
    row = db_session.get(Account, UUID(target))
    assert row is not None
    row.deleted_at = None
    db_session.flush()
    assert (
        client.post(f"/api/v1/transfers/{id}/restore", headers=csrf_headers(client)).status_code
        == 200
    )


def test_pagination_one_query_no_gaps(client: TestClient, db_engine: Engine) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    ids = [create_transfer(client, source, target) for _ in range(7)]
    seen: list[str] = []
    cursor = None
    while True:
        with statements(db_engine) as queries:
            response = client.get(
                "/api/v1/transfers", params={"limit": 2, **({"cursor": cursor} if cursor else {})}
            )
        assert response.status_code == 200, response.text
        assert len([q for q in queries if "FROM transactions" in q]) == 1
        assert not any("FOR SHARE" in q or "FOR UPDATE" in q for q in queries)
        seen.extend(row["id"] for row in response.json()["items"])
        cursor = response.json()["next_cursor"]
        if cursor is None:
            break
    assert seen == sorted(ids, reverse=True)
    assert len(set(seen)) == 7
    for limit in (0, 201):
        assert client.get("/api/v1/transfers", params={"limit": limit}).status_code == 422
    assert client.get("/api/v1/transfers", params={"cursor": "tampered"}).status_code == 400
    assert client.get("/api/v1/transfers", params={"limit": 200}).status_code == 200


def test_both_foreign_legs_have_independent_rates(client: TestClient) -> None:
    login(client)
    source = create_account(client, currency="USD")
    target = create_account(client, "Euro", currency="EUR")
    id = create_transfer(
        client,
        source,
        target,
        from_amount="100.00",
        to_amount="90.00",
        from_fx_rate_to_base="3.800000",
        to_fx_rate_to_base="4.200000",
    )
    row = client.get(f"/api/v1/transfers/{id}").json()
    assert row["implicit_rate"] == "0.900000"
    assert row["from_fx_rate_to_base"] == "3.800000"
    assert row["to_fx_rate_to_base"] == "4.200000"
    assert (
        client.patch(
            f"/api/v1/transfers/{id}",
            json={"from_fx_rate_to_base": "3.700000", "to_fx_rate_to_base": "4.100000"},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )
    row = client.get(f"/api/v1/transfers/{id}").json()
    assert row["implicit_rate"] == "0.900000"
    assert row["from_fx_rate_to_base"] == "3.700000"
    assert row["to_fx_rate_to_base"] == "4.100000"


def test_patch_account_reference_errors_leave_both_legs_intact(
    client: TestClient,
    application: FastAPI,
) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    id = create_transfer(client, source, target)
    before = client.get(f"/api/v1/transfers/{id}").json()
    deleted = create_account(client, "Deleted")
    client.delete(f"/api/v1/accounts/{deleted}", headers=csrf_headers(client))
    with TestClient(application, base_url="https://testserver") as other:
        login(other, "second@example.test")
        foreign = create_account(other)
    for direction in ("from", "to"):
        for account in (foreign, deleted, str(uuid4())):
            response = client.patch(
                f"/api/v1/transfers/{id}",
                json={f"{direction}_account_id": account, "title": "Bad"},
                headers=csrf_headers(client),
            )
            assert response.status_code == 404
            assert client.get(f"/api/v1/transfers/{id}").json() == before
