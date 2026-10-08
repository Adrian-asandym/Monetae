from fastapi.testclient import TestClient

from .conftest import create_account, create_subscription, csrf_headers, login, transaction_payload


def test_spec_archived_payment_suggests_but_never_reactivates(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    entity = create_subscription(client, account, title="  NétFlix  Premium ")
    assert (
        client.post(
            f"/api/v1/subscriptions/{entity}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    response = client.post(
        "/api/v1/transactions",
        json=transaction_payload(account, title="NETFLIX   PREMIUM"),
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    assert response.json()["reactivation_suggestions"] == [entity]
    assert client.get("/api/v1/subscriptions").json()["items"] == []
    assert client.get(f"/api/v1/subscriptions/{entity}").json()["status"] == "archived"
    result = client.post(f"/api/v1/subscriptions/{entity}/reactivate", headers=csrf_headers(client))
    assert result.status_code == 200
    assert len(client.get("/api/v1/subscriptions").json()["items"]) == 1


def test_suggestions_on_post_and_multiple_matches(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    entities = [
        create_subscription(client, account, title=title) for title in ["Netflix", "NÉTFLIX"]
    ]
    active = create_subscription(client, account)
    deleted = create_subscription(client, account)
    for entity in entities + [deleted]:
        assert (
            client.post(
                f"/api/v1/subscriptions/{entity}/archive", json={}, headers=csrf_headers(client)
            ).status_code
            == 200
        )
    assert (
        client.delete(f"/api/v1/subscriptions/{deleted}", headers=csrf_headers(client)).status_code
        == 200
    )
    response = client.post(
        "/api/v1/transactions",
        json=transaction_payload(account, title="Unrelated", status="scheduled"),
        headers=csrf_headers(client),
    )
    assert response.json()["reactivation_suggestions"] == []
    posted = client.post(
        f"/api/v1/transactions/{response.json()['id']}/post",
        json={"title": "netflix"},
        headers=csrf_headers(client),
    )
    assert posted.status_code == 200, posted.text
    assert set(posted.json()["reactivation_suggestions"]) == set(entities)
    assert client.get(f"/api/v1/subscriptions/{active}").json()["status"] == "active"
    income = client.post(
        "/api/v1/transactions",
        json=transaction_payload(account, title="Netflix", kind="income", amount="10.00"),
        headers=csrf_headers(client),
    )
    assert income.status_code == 201 and income.json()["reactivation_suggestions"] == []
