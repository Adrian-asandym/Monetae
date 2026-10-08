from fastapi.testclient import TestClient

from api.conftest import create_account, create_tag, login


def test_keyset_pagination_order_and_insert_between_pages(client: TestClient) -> None:
    login(client)
    create_account(client, "Alpha")
    create_account(client, "Charlie")
    first = client.get("/api/v1/accounts?limit=1")
    assert first.status_code == 200
    first_items = first.json()["items"]
    cursor = first.json()["next_cursor"]
    assert first_items[0]["name"] == "Alpha"

    create_account(client, "Bravo")
    second = client.get(f"/api/v1/accounts?limit=1&cursor={cursor}")
    assert second.status_code == 200
    combined = first_items + second.json()["items"]
    assert len({item["id"] for item in combined}) == 2
    assert second.json()["items"][0]["name"] in {"Bravo", "Charlie"}

    all_rows = client.get("/api/v1/accounts?limit=200")
    assert all_rows.status_code == 200
    names = [item["name"] for item in all_rows.json()["items"]]
    assert names == sorted(names, key=str.lower)
    assert client.get("/api/v1/accounts?limit=0").status_code == 422


def test_invalid_and_cross_resource_cursors(client: TestClient) -> None:
    login(client)
    create_account(client, "A")
    create_account(client, "B")
    create_tag(client, "One")
    create_tag(client, "Two")
    cursor = client.get("/api/v1/accounts?limit=1").json()["next_cursor"]
    assert client.get("/api/v1/accounts?limit=1&cursor=!!!").json()["code"] == "invalid_cursor"
    altered_cursor = f"{'A' if cursor[0] != 'A' else 'B'}{cursor[1:]}"
    assert (
        client.get(f"/api/v1/accounts?limit=1&cursor={altered_cursor}").json()["code"]
        == "invalid_cursor"
    )
    cross_resource = client.get(f"/api/v1/tags?limit=1&cursor={cursor}")
    assert cross_resource.status_code == 400
    assert cross_resource.json()["code"] == "invalid_cursor"
    filter_mismatch = client.get(f"/api/v1/accounts?limit=1&include_archived=true&cursor={cursor}")
    assert filter_mismatch.status_code == 400


def test_mutating_catalog_request_requires_origin_and_csrf(client: TestClient) -> None:
    login(client)
    response = client.post(
        "/api/v1/tags",
        json={"name": "blocked"},
        headers={"X-CSRF-Token": client.cookies["monetae_csrf"]},
    )
    assert response.status_code == 403
