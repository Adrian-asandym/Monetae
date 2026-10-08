from fastapi.testclient import TestClient

from api.conftest import create_category, csrf_headers, login


def test_category_hierarchy_system_immutability_and_soft_delete(client: TestClient) -> None:
    login(client)
    parent_id = create_category(client, "Food")
    child_id = create_category(client, "Groceries", parent_id=parent_id)

    blocked_delete = client.delete(f"/api/v1/categories/{parent_id}", headers=csrf_headers(client))
    assert blocked_delete.status_code == 409
    assert blocked_delete.json()["code"] == "category_has_children"
    blocked_kind = client.patch(
        f"/api/v1/categories/{parent_id}",
        json={"kind": "income"},
        headers=csrf_headers(client),
    )
    assert blocked_kind.status_code == 409

    system = next(
        item for item in client.get("/api/v1/categories").json()["items"] if item["is_system"]
    )
    assert (
        client.patch(
            f"/api/v1/categories/{system['id']}",
            json={"name": "Changed"},
            headers=csrf_headers(client),
        ).json()["code"]
        == "system_category_immutable"
    )
    assert (
        client.delete(f"/api/v1/categories/{system['id']}", headers=csrf_headers(client)).json()[
            "code"
        ]
        == "system_category_immutable"
    )

    assert (
        client.delete(f"/api/v1/categories/{child_id}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/categories/{parent_id}",
            json={"name": "Meals"},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )


def test_category_duplicate_name_and_parent_validation(client: TestClient) -> None:
    login(client)
    create_category(client, "Rent")
    duplicate = client.post(
        "/api/v1/categories", json={"name": "rent", "kind": "expense"}, headers=csrf_headers(client)
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate_name"

    root = create_category(client, "Income", kind="income")
    wrong_kind = client.post(
        "/api/v1/categories",
        json={"name": "Wrong", "kind": "expense", "parent_id": root},
        headers=csrf_headers(client),
    )
    assert wrong_kind.status_code == 422
