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
        "/api/v1/people",
        json={"name": "morgan lee", "aliases": ["ML"]},
        headers=csrf_headers(client),
    )
    assert duplicate_name.status_code == 201
    duplicate_id = duplicate_name.json()["id"]

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
        f"/api/v1/people/{duplicate_id}",
        json={"name": "Morgan Lee"},
        headers=csrf_headers(client),
    )
    assert changed.status_code == 200
    assert changed.json()["name"] == "Morgan Lee"
    assert (
        client.delete(f"/api/v1/people/{person_id}", headers=csrf_headers(client)).status_code
        == 200
    )


def test_person_name_prefix_search_escapes_like_wildcards(client: TestClient) -> None:
    login(client)
    for name in ("% monthly", "_private", "ordinary"):
        result = client.post("/api/v1/people", json={"name": name}, headers=csrf_headers(client))
        assert result.status_code == 201, result.text

    percent = client.get("/api/v1/people?q=%25")
    underscore = client.get("/api/v1/people?q=_")
    assert percent.status_code == 200
    assert [item["name"] for item in percent.json()["items"]] == ["% monthly"]
    assert underscore.status_code == 200
    assert [item["name"] for item in underscore.json()["items"]] == ["_private"]
