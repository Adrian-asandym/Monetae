from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.conftest import (
    create_account,
    create_category,
    create_tag,
    create_transaction,
    csrf_headers,
    login,
    transaction_payload,
)


def test_each_transaction_operation_and_filters_are_user_scoped(
    client: TestClient, application: FastAPI
) -> None:
    login(client)
    account, category, tag = create_account(client), create_category(client), create_tag(client)
    entity_id = create_transaction(client, account, category_id=category, tag_ids=[tag])
    deleted_id = create_transaction(client, account)
    client.delete(f"/api/v1/transactions/{deleted_id}", headers=csrf_headers(client))
    with TestClient(application, base_url="https://testserver") as other:
        login(other, "second@example.test")
        url = f"/api/v1/transactions/{entity_id}"
        assert other.get(url).status_code == 404
        assert other.get(url + "?include_deleted=true").status_code == 404
        assert (
            other.patch(url, json={"title": "attack"}, headers=csrf_headers(other)).status_code
            == 404
        )
        assert other.delete(url, headers=csrf_headers(other)).status_code == 404
        assert other.post(url + "/restore", headers=csrf_headers(other)).status_code == 404
        assert (
            other.post(
                f"/api/v1/transactions/{deleted_id}/restore", headers=csrf_headers(other)
            ).status_code
            == 404
        )
        assert (
            other.put(url + "/tags", json={"tag_ids": []}, headers=csrf_headers(other)).status_code
            == 404
        )
        for filters in (
            {},
            {"account_id": account},
            {"category_id": category},
            {"tag_ids": tag},
            {"include_deleted": "true"},
            {"q": "Synthetic"},
        ):
            assert other.get("/api/v1/transactions", params=filters).json()["items"] == []
        own = create_account(other)
        for changes in (
            {"account_id": account},
            {"account_id": own, "category_id": category},
            {"account_id": own, "tag_ids": [tag]},
        ):
            response = other.post(
                "/api/v1/transactions",
                json={**transaction_payload(own), **changes},
                headers=csrf_headers(other),
            )
            assert response.status_code == 404, response.text
        own_transaction = create_transaction(other, own)
        for patch_changes in (
            {"account_id": account},
            {"category_id": category},
            {"tag_ids": [tag]},
        ):
            assert (
                other.patch(
                    f"/api/v1/transactions/{own_transaction}",
                    json=patch_changes,
                    headers=csrf_headers(other),
                ).status_code
                == 404
            )
        assert (
            other.put(
                f"/api/v1/transactions/{own_transaction}/tags",
                json={"tag_ids": [tag]},
                headers=csrf_headers(other),
            ).status_code
            == 404
        )
        foreign_cursor = client.get("/api/v1/transactions?limit=1").json()["next_cursor"]
        # Crea una segunda fila propia del primer usuario para obtener cursor.
        if foreign_cursor is None:
            create_transaction(client, account)
            foreign_cursor = client.get("/api/v1/transactions?limit=1").json()["next_cursor"]
        assert (
            other.get("/api/v1/transactions", params={"cursor": foreign_cursor}).status_code == 400
        )
    assert client.get(url).json()["title"] == "Synthetic purchase"
