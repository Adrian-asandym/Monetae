from fastapi import FastAPI
from fastapi.testclient import TestClient

from .conftest import create_account, create_transfer, csrf_headers, login, transfer_payload


def test_all_transfer_operations_are_scoped(client: TestClient, application: FastAPI) -> None:
    login(client)
    source, target = create_account(client), create_account(client, "Bank")
    id = create_transfer(client, source, target)
    cursor = client.get("/api/v1/transfers", params={"limit": 1}).json()["next_cursor"]
    create_transfer(client, source, target)
    cursor = client.get("/api/v1/transfers", params={"limit": 1}).json()["next_cursor"]
    with TestClient(application, base_url="https://testserver") as other:
        login(other, "second@example.test")
        assert other.get("/api/v1/transfers").json()["items"] == []
        assert other.get("/api/v1/transfers", params={"cursor": cursor}).status_code == 400
        own = create_account(other)
        for method, suffix, body in (
            ("get", "", None),
            ("patch", "", {"title": "Bad"}),
            ("delete", "", None),
            ("post", "/restore", None),
        ):
            response = other.request(
                method, f"/api/v1/transfers/{id}{suffix}", json=body, headers=csrf_headers(other)
            )
            assert response.status_code == 404, response.text
        for source_id, target_id in ((source, own), (own, target)):
            response = other.post(
                "/api/v1/transfers",
                json=transfer_payload(source_id, target_id),
                headers=csrf_headers(other),
            )
            assert response.status_code == 404
        assert other.get("/api/v1/transfers").json()["items"] == []
    assert client.get(f"/api/v1/transfers/{id}").status_code == 200
