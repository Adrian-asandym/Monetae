from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, select, text
from sqlalchemy.orm import Session as DbSession

from api.conftest import csrf_headers, login
from monetae.config import Settings
from monetae.db.models import Account, Category, User
from monetae.services.auth import AuthService, SystemClock
from monetae.services.catalog import CatalogService


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


def test_catalog_list_does_not_wait_for_same_users_row_lock(db_engine: Engine) -> None:
    settings = Settings(environment="test")
    with DbSession(db_engine) as setup:
        user = AuthService(setup, settings, SystemClock()).create_user(
            "catalog-lock@example.test", "synthetic-password-123"
        )
        account = CatalogService(setup, settings.secret_key).create_account(
            user.id,
            {
                "name": "Concurrent wallet",
                "type": "cash",
                "currency": "PEN",
                "initial_balance": "0.00",
                "color": None,
                "icon": None,
                "sort_order": 0,
            },
        )
        user_id, account_id = user.id, account.id
        setup.commit()

    try:
        with DbSession(db_engine) as first, DbSession(db_engine) as second:
            first.scalar(select(Account).where(Account.id == account_id).with_for_update())
            second.execute(text("SET LOCAL lock_timeout = '500ms'"))
            rows, _ = CatalogService(second, settings.secret_key).list_accounts(
                user_id, 50, None, False
            )
            assert [row.id for row in rows] == [account_id]
    finally:
        with DbSession(db_engine) as cleanup:
            cleanup.execute(delete(Account).where(Account.id == account_id))
            cleanup.execute(delete(Category).where(Category.user_id == user_id))
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.commit()
