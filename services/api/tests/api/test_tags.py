from fastapi.testclient import TestClient

from api.conftest import create_tag, csrf_headers, login


def test_tag_crud_archive_duplicate_reactivation(client: TestClient) -> None:
    login(client)
    tag_id = create_tag(client, "Travel")
    duplicate = client.post("/api/v1/tags", json={"name": "travel"}, headers=csrf_headers(client))
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate_name"

    assert (
        client.post(
            f"/api/v1/tags/{tag_id}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    replacement = create_tag(client, "Travel")
    conflict = client.post(f"/api/v1/tags/{tag_id}/reactivate", headers=csrf_headers(client))
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "duplicate_name"
    assert client.get("/api/v1/tags").json()["items"][0]["id"] == replacement

    assert (
        client.delete(f"/api/v1/tags/{replacement}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert create_tag(client, "Travel")
