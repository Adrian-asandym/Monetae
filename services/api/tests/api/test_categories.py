from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.conftest import create_category, csrf_headers, login


def test_duplicate_category_names_are_allowed_under_same_and_different_parents(
    client: TestClient,
) -> None:
    login(client)
    food_id = create_category(client, "Food")
    transport_id = create_category(client, "Transport")

    first = create_category(client, "Other", parent_id=food_id)
    same_parent = create_category(client, "Other", parent_id=food_id)
    other_parent = create_category(client, "Other", parent_id=transport_id)
    assert len({first, same_parent, other_parent}) == 3

    renamed = client.patch(
        f"/api/v1/categories/{food_id}",
        json={"name": "Other"},
        headers=csrf_headers(client),
    )
    assert renamed.status_code == 200


def test_category_with_children_cannot_be_deleted_or_change_kind(client: TestClient) -> None:
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
    assert blocked_kind.json()["code"] == "category_has_children"

    assert (
        client.delete(f"/api/v1/categories/{child_id}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/categories",
            json={"name": "Groceries", "kind": "expense"},
            headers=csrf_headers(client),
        ).status_code
        == 201
    )


def test_system_categories_cannot_be_edited_or_deleted(client: TestClient) -> None:
    login(client)
    system = next(
        item for item in client.get("/api/v1/categories").json()["items"] if item["is_system"]
    )
    update = client.patch(
        f"/api/v1/categories/{system['id']}",
        json={"name": "Changed"},
        headers=csrf_headers(client),
    )
    assert update.status_code == 409
    assert update.json()["code"] == "system_category_immutable"
    deleted = client.delete(f"/api/v1/categories/{system['id']}", headers=csrf_headers(client))
    assert deleted.status_code == 409
    assert deleted.json()["code"] == "system_category_immutable"


def test_category_patch_cannot_set_system_fields(client: TestClient) -> None:
    login(client)
    category_id = create_category(client, "Normal")
    for field, value in (("is_system", True), ("system_key", "interest_income")):
        response = client.patch(
            f"/api/v1/categories/{category_id}",
            json={field: value},
            headers=csrf_headers(client),
        )
        assert response.status_code == 422


def test_subcategory_requires_root_parent_of_same_kind(client: TestClient) -> None:
    login(client)
    income_parent = create_category(client, "Income", kind="income")
    wrong_kind = client.post(
        "/api/v1/categories",
        json={"name": "Wrong kind", "kind": "expense", "parent_id": income_parent},
        headers=csrf_headers(client),
    )
    assert wrong_kind.status_code == 422
    assert wrong_kind.json()["code"] == "invalid_category_hierarchy"

    expense_parent = create_category(client, "Expense root")
    child_id = create_category(client, "Child", parent_id=expense_parent)
    grandchild = client.post(
        "/api/v1/categories",
        json={"name": "Grandchild", "kind": "expense", "parent_id": child_id},
        headers=csrf_headers(client),
    )
    assert grandchild.status_code == 422
    assert grandchild.json()["code"] == "invalid_category_hierarchy"


def test_category_cannot_be_moved_under_itself(client: TestClient) -> None:
    login(client)
    category_id = create_category(client, "Root")
    response = client.patch(
        f"/api/v1/categories/{category_id}",
        json={"parent_id": category_id},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_category_hierarchy"


def test_category_with_children_cannot_become_a_child(client: TestClient) -> None:
    login(client)
    parent_id = create_category(client, "Parent")
    create_category(client, "Existing child", parent_id=parent_id)
    other_parent_id = create_category(client, "Other parent")

    response = client.patch(
        f"/api/v1/categories/{parent_id}",
        json={"parent_id": other_parent_id},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_category_hierarchy"


def test_category_kind_must_match_its_parent_on_patch(client: TestClient) -> None:
    login(client)
    parent_id = create_category(client, "Expense parent")
    child_id = create_category(client, "Child", parent_id=parent_id)
    response = client.patch(
        f"/api/v1/categories/{child_id}",
        json={"kind": "income"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_category_hierarchy"


def test_foreign_user_category_parent_is_hidden_on_create_and_patch(
    client: TestClient, application: FastAPI
) -> None:
    login(client)
    other_user = TestClient(application, base_url="https://testserver")
    other_user.get("/api/v1/health")
    login(other_user, "second@example.test")
    foreign_parent_id = create_category(other_user, "Foreign parent")

    create_response = client.post(
        "/api/v1/categories",
        json={"name": "Child", "kind": "expense", "parent_id": foreign_parent_id},
        headers=csrf_headers(client),
    )
    assert create_response.status_code == 404

    owned_id = create_category(client, "Owned root")
    patch_response = client.patch(
        f"/api/v1/categories/{owned_id}",
        json={"parent_id": foreign_parent_id},
        headers=csrf_headers(client),
    )
    assert patch_response.status_code == 404
