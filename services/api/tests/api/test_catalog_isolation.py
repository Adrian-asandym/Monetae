from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.conftest import csrf_headers, login
from monetae.db.models import User


def test_catalog_ids_and_lists_are_scoped_to_authenticated_user(
    client: TestClient, application: FastAPI, auth_users: tuple[User, User]
) -> None:
    login(client)
    second = TestClient(application, base_url="https://testserver")
    second.get("/api/v1/health")
    login(second, "second@example.test")

    headers = csrf_headers(second)
    account = second.post(
        "/api/v1/accounts",
        json={"name": "B account", "type": "cash", "currency": "PEN", "initial_balance": "0.00"},
        headers=headers,
    ).json()["id"]
    category = second.post(
        "/api/v1/categories", json={"name": "B category", "kind": "expense"}, headers=headers
    ).json()["id"]
    person = second.post("/api/v1/people", json={"name": "B person"}, headers=headers).json()["id"]
    tag = second.post("/api/v1/tags", json={"name": "B tag"}, headers=headers).json()["id"]

    resource_ids = {"accounts": account, "categories": category, "people": person, "tags": tag}
    for resource, entity_id in resource_ids.items():
        assert client.get(f"/api/v1/{resource}/{entity_id}").status_code == 404
        assert (
            client.patch(
                f"/api/v1/{resource}/{entity_id}",
                json={"name": "A change"},
                headers=csrf_headers(client),
            ).status_code
            == 404
        )
        assert (
            client.delete(
                f"/api/v1/{resource}/{entity_id}", headers=csrf_headers(client)
            ).status_code
            == 404
        )
        listed = client.get(f"/api/v1/{resource}").json()["items"]
        assert entity_id not in {item["id"] for item in listed}
        if resource in {"accounts", "tags"}:
            for action in ("archive", "reactivate"):
                assert (
                    client.post(
                        f"/api/v1/{resource}/{entity_id}/{action}",
                        json={} if action == "archive" else None,
                        headers=csrf_headers(client),
                    ).status_code
                    == 404
                )

    assert (
        client.post(
            "/api/v1/categories",
            json={"name": "A child", "kind": "expense", "parent_id": category},
            headers=csrf_headers(client),
        ).status_code
        == 404
    )
    owned_category = client.post(
        "/api/v1/categories",
        json={"name": "A category", "kind": "expense"},
        headers=csrf_headers(client),
    ).json()["id"]
    assert (
        client.patch(
            f"/api/v1/categories/{owned_category}",
            json={"parent_id": category},
            headers=csrf_headers(client),
        ).status_code
        == 404
    )

    payloads = {
        "accounts": {
            "name": "Bad",
            "type": "cash",
            "currency": "PEN",
            "initial_balance": "0.00",
            "user_id": str(auth_users[0].id),
        },
        "categories": {"name": "Bad", "kind": "expense", "user_id": str(auth_users[0].id)},
        "people": {"name": "Bad", "user_id": str(auth_users[0].id)},
        "tags": {"name": "Bad", "user_id": str(auth_users[0].id)},
    }
    for resource, payload in payloads.items():
        assert (
            client.post(
                f"/api/v1/{resource}", json=payload, headers=csrf_headers(client)
            ).status_code
            == 422
        )
