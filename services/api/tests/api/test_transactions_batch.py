from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from monetae.db.models import Transaction

from .conftest import (
    create_account,
    create_category,
    create_tag,
    create_transaction,
    create_transfer,
    csrf_headers,
    login,
)


def batch(client: TestClient, ids: list[str], action: str, **values: object) -> Response:
    response = client.post(
        "/api/v1/transactions/batch",
        json={"transaction_ids": ids, "action": action, **values},
        headers=csrf_headers(client),
    )
    assert isinstance(response, Response)
    return response


def test_delete_restore_and_edit(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    ids = [create_transaction(client, account, status="scheduled") for _ in range(2)]
    category = create_category(client)
    changes = {
        "category_id": category,
        "title": "Batch title",
        "note": "Batch note",
        "status": "posted",
        "occurred_at": "2026-10-08T12:00:00-05:00",
    }
    response = batch(client, ids, "edit", changes=changes)
    assert response.json() == {"success": True, "affected_count": 2}, response.text
    for id in ids:
        row = client.get(f"/api/v1/transactions/{id}").json()
        assert row["category_id"] == category and row["title"] == "Batch title"
        assert row["status"] == "posted" and row["occurred_at"] == "2026-10-08T17:00:00Z"
    assert (
        batch(client, ids, "edit", changes={"category_id": None, "note": None}).status_code == 200
    )
    assert batch(client, ids, "delete").json()["affected_count"] == 2
    assert client.get("/api/v1/transactions").json()["items"] == []
    assert batch(client, ids, "restore").json()["affected_count"] == 2
    assert len(client.get("/api/v1/transactions").json()["items"]) == 2


def test_tag_actions_and_archived_rules(client: TestClient) -> None:
    login(client)
    account, tag = create_account(client), create_tag(client)
    ids = [create_transaction(client, account) for _ in range(2)]
    assert batch(client, ids, "add_tags", tag_ids=[tag]).status_code == 200
    for id in ids:
        assert client.get(f"/api/v1/transactions/{id}").json()["tag_ids"] == [tag]
    assert (
        client.post(
            f"/api/v1/tags/{tag}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert batch(client, ids, "add_tags", tag_ids=[tag]).status_code == 200
    assert batch(client, ids, "remove_tags", tag_ids=[tag]).status_code == 200
    for id in ids:
        assert client.get(f"/api/v1/transactions/{id}").json()["tag_ids"] == []
    response = batch(client, ids, "add_tags", tag_ids=[tag])
    assert response.status_code == 422 and response.json()["code"] == "tag_archived"
    assert (
        client.post(f"/api/v1/tags/{tag}/reactivate", headers=csrf_headers(client)).status_code
        == 200
    )
    assert batch(client, ids, "add_tags", tag_ids=[tag]).status_code == 200
    assert batch(client, ids, "remove_tags", tag_ids=[str(uuid4())]).status_code == 404
    assert client.delete(f"/api/v1/tags/{tag}", headers=csrf_headers(client)).status_code == 200
    assert batch(client, ids, "remove_tags", tag_ids=[tag]).status_code == 404


@pytest.mark.parametrize(
    "action,values",
    [
        ("delete", {}),
        ("restore", {}),
        ("edit", {"changes": {"title": "Forbidden"}}),
        ("add_tags", {"tag_ids": []}),
        ("remove_tags", {"tag_ids": []}),
    ],
)
def test_missing_or_foreign_id_is_atomic(
    client: TestClient, application: FastAPI, action: str, values: dict[str, object]
) -> None:
    login(client)
    account = create_account(client)
    own = create_transaction(client, account)
    if action in {"add_tags", "remove_tags"}:
        values = {"tag_ids": [create_tag(client)]}
    if action == "restore":
        client.delete(f"/api/v1/transactions/{own}", headers=csrf_headers(client))
    before = client.get(f"/api/v1/transactions/{own}?include_deleted=true").json()
    with TestClient(application, base_url="https://testserver") as other:
        login(other, "second@example.test")
        other_account = create_account(other)
        foreign = create_transaction(other, other_account, fx_rate_to_base="1.000000")
    for id in (str(uuid4()), foreign):
        response = batch(client, [own, id], action, **values)
        assert response.status_code == 404, response.text
        assert client.get(f"/api/v1/transactions/{own}?include_deleted=true").json() == before


@pytest.mark.parametrize("action", ["edit", "delete", "restore", "add_tags", "remove_tags"])
def test_transfer_legs_rejected_atomically(client: TestClient, action: str) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    direct = create_transaction(client, source)
    id = create_transfer(client, source, target)
    leg = client.get(f"/api/v1/transfers/{id}").json()["incoming_transaction_id"]
    values: dict[str, object] = {}
    if action == "edit":
        values["changes"] = {"title": "Forbidden"}
    if action in {"add_tags", "remove_tags"}:
        values["tag_ids"] = [create_tag(client)]
    before = client.get(f"/api/v1/transactions/{direct}").json()
    response = batch(client, [direct, leg], action, **values)
    assert response.status_code == 409 and response.json()["code"] == "transaction_flow_required"
    assert client.get(f"/api/v1/transactions/{direct}").json() == before


@pytest.mark.parametrize(
    "values",
    [
        {"action": "edit"},
        {"action": "edit", "tag_ids": [], "changes": {"title": "X"}},
        {"action": "delete", "changes": {"title": "X"}},
        {"action": "restore", "tag_ids": []},
        {"action": "delete", "changes": None},
        {"action": "delete", "tag_ids": None},
        {"action": "add_tags"},
        {"action": "add_tags", "tag_ids": []},
        {"action": "remove_tags", "tag_ids": []},
        {"action": "remove_tags", "tag_ids": [str(uuid4())], "changes": {"title": "X"}},
    ],
)
def test_action_shape(client: TestClient, values: dict[str, object]) -> None:
    login(client)
    id = create_transaction(client, create_account(client))
    response = client.post(
        "/api/v1/transactions/batch",
        json={"transaction_ids": [id], **values},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", "-2.00"),
        ("kind", "expense"),
        ("account_id", str(uuid4())),
        ("fx_rate_to_base", "1.000000"),
        ("fx_rate_source", "auto"),
        ("tag_ids", []),
    ],
)
def test_disallowed_edit_fields(client: TestClient, field: str, value: object) -> None:
    login(client)
    id = create_transaction(client, create_account(client))
    response = batch(client, [id], "edit", changes={field: value})
    assert response.status_code == 422 and response.json()["code"] == "batch_field_not_allowed"


def test_limits_unique_and_deleted_ids(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    ids = [create_transaction(client, account) for _ in range(200)]
    for invalid in ([], [ids[0], ids[0]], [*ids, str(uuid4())]):
        assert batch(client, invalid, "delete").status_code == 422
    assert batch(client, ids, "delete").json() == {"success": True, "affected_count": 200}
    assert batch(client, ids, "edit", changes={"title": "Bad"}).status_code == 404
    assert batch(client, ids, "restore").json() == {"success": True, "affected_count": 200}


@pytest.mark.parametrize("resource", ["accounts", "categories"])
def test_restore_conflict_is_atomic(client: TestClient, resource: str) -> None:
    login(client)
    account = create_account(client)
    category = create_category(client)
    other = create_account(client, "Bank")
    ids = [
        create_transaction(client, other),
        create_transaction(client, account, category_id=category),
    ]
    assert batch(client, ids, "delete").status_code == 200
    reference = account if resource == "accounts" else category
    assert (
        client.delete(f"/api/v1/{resource}/{reference}", headers=csrf_headers(client)).status_code
        == 200
    )
    response = batch(client, ids, "restore")
    assert response.status_code == 409 and response.json()["code"] == "restore_conflict"
    assert client.get("/api/v1/transactions").json()["items"] == []


def test_tag_errors_and_late_validation_rollback(client: TestClient, application: FastAPI) -> None:
    login(client)
    account, tag = create_account(client), create_tag(client)
    ids = [create_transaction(client, account) for _ in range(2)]
    with TestClient(application, base_url="https://testserver") as other:
        login(other, "second@example.test")
        foreign = create_tag(other)
        category = create_category(other)
    for action in ("add_tags", "remove_tags"):
        assert batch(client, ids, action, tag_ids=[foreign]).status_code == 404
        assert batch(client, ids, action, tag_ids=[str(uuid4())]).status_code == 404
    assert batch(client, ids, "edit", changes={"category_id": category}).status_code == 404
    # La primera fila tiene la etiqueta archivada; la segunda no: ninguna se modifica.
    client.put(
        f"/api/v1/transactions/{ids[0]}/tags", json={"tag_ids": [tag]}, headers=csrf_headers(client)
    )
    client.post(f"/api/v1/tags/{tag}/archive", json={}, headers=csrf_headers(client))
    assert batch(client, ids, "add_tags", tag_ids=[tag]).status_code == 422
    assert client.get(f"/api/v1/transactions/{ids[1]}").json()["tag_ids"] == []


def test_loan_rows_require_loan_flow(client: TestClient, db_session: Session) -> None:
    login(client)
    account = create_account(client)
    direct = create_transaction(client, account)
    id = create_transaction(client, account)
    row = db_session.get(Transaction, UUID(id))
    assert row is not None
    row.kind = "loan"
    db_session.commit()
    for action in ("delete", "restore", "edit", "add_tags", "remove_tags"):
        values: dict[str, object] = {}
        if action == "edit":
            values["changes"] = {"title": "Bad"}
        elif action in {"add_tags", "remove_tags"}:
            values["tag_ids"] = [create_tag(client, action)]
        response = batch(client, [direct, id], action, **values)
        assert (
            response.status_code == 409 and response.json()["code"] == "transaction_flow_required"
        )
    assert client.get(f"/api/v1/transactions/{direct}").json()["deleted_at"] is None
