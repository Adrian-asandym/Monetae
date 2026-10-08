from fastapi.testclient import TestClient

from api.conftest import csrf_headers, login


def test_person_alias_normalization_limits_search_and_crud(client: TestClient) -> None:
    login(client)
    created = client.post(
        "/api/v1/people",
        json={"name": "Morgan Lee", "aliases": [" Mo ", "Morg", " Ace "], "note": "synthetic"},
        headers=csrf_headers(client),
    )
    assert created.status_code == 201
    person_id = created.json()["id"]
    assert created.json()["aliases"] == ["Mo", "Morg", "Ace"]

    assert len(client.get("/api/v1/people?q=mOr").json()["items"]) == 1
    assert len(client.get("/api/v1/people?q=aCe").json()["items"]) == 1
    assert client.get("/api/v1/people?q=org").json()["items"] == []

    duplicate_name = client.post(
        "/api/v1/people", json={"name": "morgan lee"}, headers=csrf_headers(client)
    )
    assert duplicate_name.status_code == 409
    assert duplicate_name.json()["code"] == "duplicate_name"

    duplicate_alias = client.post(
        "/api/v1/people",
        json={"name": "Another", "aliases": ["Same", " same "]},
        headers=csrf_headers(client),
    )
    assert duplicate_alias.status_code == 422
    too_many = client.post(
        "/api/v1/people",
        json={"name": "Another", "aliases": [f"alias-{n}" for n in range(21)]},
        headers=csrf_headers(client),
    )
    assert too_many.status_code == 422
    too_long = client.post(
        "/api/v1/people",
        json={"name": "Another", "aliases": ["x" * 61]},
        headers=csrf_headers(client),
    )
    assert too_long.status_code == 422

    changed = client.patch(
        f"/api/v1/people/{person_id}", json={"name": "Morgan B"}, headers=csrf_headers(client)
    )
    assert changed.status_code == 200
    assert (
        client.delete(f"/api/v1/people/{person_id}", headers=csrf_headers(client)).status_code
        == 200
    )
