from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from monetae.db.models import Transaction

from .conftest import (
    FakeClock,
    create_account,
    create_subscription,
    csrf_headers,
    login,
    scheduled_for,
)


def test_spec_netflix_three_payments_archive_and_reactivate(
    client: TestClient, clock: FakeClock
) -> None:
    login(client)
    entity = create_subscription(client, create_account(client), next_due_on="2026-07-01")
    payments = []
    for month in (7, 8, 9):
        scheduled = scheduled_for(client, entity)
        assert len(scheduled) == 1
        response = client.post(
            f"/api/v1/transactions/{scheduled[0]['id']}/post",
            json={"occurred_at": f"2026-{month:02d}-01T15:00:00Z"},
            headers=csrf_headers(client),
        )
        assert response.status_code == 200, response.text
        payments.append(response.json()["id"])
    before = client.get(f"/api/v1/subscriptions/{entity}").json()
    assert before["historical_paid"] == "90.00" and before["last_paid_on"] == "2026-09-01"
    # El próximo cobro es futuro respecto al reloj inyectado.
    clock.value = datetime(2026, 9, 15, 12, tzinfo=UTC)
    archived = client.post(
        f"/api/v1/subscriptions/{entity}/archive",
        json={"reason": "Cancelled"},
        headers=csrf_headers(client),
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["archive_reason"] == "Cancelled"
    assert archived.json()["historical_paid"] == "90.00"
    assert client.get("/api/v1/subscriptions").json()["items"] == []
    assert client.get("/api/v1/subscriptions/totals").json()["items"] == []
    assert scheduled_for(client, entity) == []
    assert client.get("/api/v1/subscriptions?status=archived").json()["items"][0]["id"] == entity
    for payment in payments:
        assert client.get(f"/api/v1/transactions/{payment}").json()["status"] == "posted"
    assert (
        client.post(
            f"/api/v1/subscriptions/{entity}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 409
    )
    response = client.post(
        f"/api/v1/subscriptions/{entity}/reactivate", headers=csrf_headers(client)
    )
    assert response.status_code == 200, response.text
    assert response.json()["next_due_on"] == "2026-10-01"
    assert (
        response.json()["historical_paid"] == "90.00"
        and response.json()["last_paid_on"] == "2026-09-01"
    )
    assert response.json()["archived_at"] is None and response.json()["archive_reason"] is None
    assert len(scheduled_for(client, entity)) == 1
    assert len(client.get("/api/v1/subscriptions").json()["items"]) == 1
    assert (
        client.get("/api/v1/subscriptions/totals").json()["items"][0]["monthly_amount"] == "30.00"
    )
    assert (
        client.post(
            f"/api/v1/subscriptions/{entity}/reactivate", headers=csrf_headers(client)
        ).status_code
        == 409
    )


def test_archive_preserves_past_scheduled_and_ignores_deleted_payments(
    client: TestClient, db_session: Session
) -> None:
    login(client)
    entity = create_subscription(client, create_account(client), next_due_on="2026-09-01")
    past = scheduled_for(client, entity)[0]
    response = client.post(f"/api/v1/transactions/{past['id']}/post", headers=csrf_headers(client))
    assert response.status_code == 200
    payment_id = UUID(str(past["id"]))
    assert (
        client.delete(
            f"/api/v1/transactions/{payment_id}", headers=csrf_headers(client)
        ).status_code
        == 200
    )
    next_past = scheduled_for(client, entity)[0]
    assert (
        client.post(
            f"/api/v1/subscriptions/{entity}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/transactions/{next_past['id']}").status_code == 200
    historical = client.get(f"/api/v1/subscriptions/{entity}").json()
    assert historical["historical_paid"] == "0.00" and historical["last_paid_on"] is None
    row = db_session.get(Transaction, payment_id)
    assert row is not None and row.deleted_at is not None


def test_reason_limit(client: TestClient) -> None:
    login(client)
    entity = create_subscription(client, create_account(client))
    response = client.post(
        f"/api/v1/subscriptions/{entity}/archive",
        json={"reason": "x" * 501},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422
    assert client.get(f"/api/v1/subscriptions/{entity}").json()["status"] == "active"
