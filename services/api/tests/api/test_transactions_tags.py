from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.conftest import create_account, create_tag, create_transaction, csrf_headers, login
from monetae.db.models import TransactionTag


def test_replace_tags_soft_deletes_and_reuses_links(
    client: TestClient, db_session: Session
) -> None:
    login(client)
    a, b = create_tag(client, "A"), create_tag(client, "B")
    entity_id = create_transaction(client, create_account(client), tag_ids=[a])
    url = f"/api/v1/transactions/{entity_id}/tags"
    first = db_session.scalar(
        select(TransactionTag).where(TransactionTag.transaction_id == UUID(entity_id))
    )
    assert first is not None
    link_id = first.id
    replaced = client.put(url, json={"tag_ids": [b]}, headers=csrf_headers(client))
    assert replaced.status_code == 200 and replaced.json()["tag_ids"] == [b]
    db_session.expire_all()
    removed = db_session.get(TransactionTag, link_id)
    assert removed is not None and removed.deleted_at is not None
    again = client.put(url, json={"tag_ids": [a, b]}, headers=csrf_headers(client))
    assert again.status_code == 200 and set(again.json()["tag_ids"]) == {a, b}
    db_session.expire_all()
    restored = db_session.get(TransactionTag, link_id)
    assert restored is not None and restored.deleted_at is None
    assert (
        len(
            list(
                db_session.scalars(
                    select(TransactionTag).where(TransactionTag.transaction_id == UUID(entity_id))
                )
            )
        )
        == 2
    )
    assert (
        client.put(url, json={"tag_ids": []}, headers=csrf_headers(client)).json()["tag_ids"] == []
    )


def test_archived_tag_can_stay_but_cannot_be_added_again(client: TestClient) -> None:
    login(client)
    tag = create_tag(client)
    account = create_account(client)
    entity_id = create_transaction(client, account, tag_ids=[tag])
    client.post(f"/api/v1/tags/{tag}/archive", json={}, headers=csrf_headers(client))
    assert client.get(f"/api/v1/transactions/{entity_id}").json()["tag_ids"] == [tag]
    url = f"/api/v1/transactions/{entity_id}/tags"
    assert client.put(url, json={"tag_ids": [tag]}, headers=csrf_headers(client)).status_code == 200
    client.put(url, json={"tag_ids": []}, headers=csrf_headers(client))
    rejected = client.put(url, json={"tag_ids": [tag]}, headers=csrf_headers(client))
    assert rejected.status_code == 422 and rejected.json()["code"] == "tag_archived"
    other = create_transaction(client, account)
    assert (
        client.patch(
            f"/api/v1/transactions/{other}", json={"tag_ids": [tag]}, headers=csrf_headers(client)
        ).status_code
        == 422
    )


def test_deleted_tag_disappears_and_cannot_be_linked(client: TestClient) -> None:
    login(client)
    tag = create_tag(client)
    entity_id = create_transaction(client, create_account(client), tag_ids=[tag])
    client.delete(f"/api/v1/tags/{tag}", headers=csrf_headers(client))
    assert client.get(f"/api/v1/transactions/{entity_id}").json()["tag_ids"] == []
    assert client.get("/api/v1/transactions").json()["items"][0]["tag_ids"] == []
    assert client.get("/api/v1/transactions", params={"tag_ids": tag}).json()["items"] == []
    assert (
        client.put(
            f"/api/v1/transactions/{entity_id}/tags",
            json={"tag_ids": [tag]},
            headers=csrf_headers(client),
        ).status_code
        == 404
    )


@pytest.mark.parametrize("method", ["post", "patch"])
def test_duplicate_tag_ids_rejected(client: TestClient, method: str) -> None:
    login(client)
    tag = create_tag(client)
    account = create_account(client)
    if method == "post":
        from api.conftest import transaction_payload

        response = client.post(
            "/api/v1/transactions",
            json=transaction_payload(account, tag_ids=[tag, tag]),
            headers=csrf_headers(client),
        )
    else:
        entity_id = create_transaction(client, account)
        response = client.patch(
            f"/api/v1/transactions/{entity_id}",
            json={"tag_ids": [tag, tag]},
            headers=csrf_headers(client),
        )
    assert response.status_code == 422


def test_create_with_archived_or_deleted_tag_is_rejected_atomically(client: TestClient) -> None:
    from api.conftest import transaction_payload

    login(client)
    account = create_account(client)
    tag = create_tag(client)
    client.post(f"/api/v1/tags/{tag}/archive", json={}, headers=csrf_headers(client))
    archived = client.post(
        "/api/v1/transactions",
        json=transaction_payload(account, tag_ids=[tag]),
        headers=csrf_headers(client),
    )
    assert archived.status_code == 422 and archived.json()["code"] == "tag_archived"
    client.delete(f"/api/v1/tags/{tag}", headers=csrf_headers(client))
    deleted = client.post(
        "/api/v1/transactions",
        json=transaction_payload(account, tag_ids=[tag]),
        headers=csrf_headers(client),
    )
    assert deleted.status_code == 404
    assert client.get("/api/v1/transactions").json()["items"] == []
