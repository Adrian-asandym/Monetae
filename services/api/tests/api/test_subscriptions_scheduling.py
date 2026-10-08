from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from monetae.db.models import RecurringRule

from .conftest import (
    FakeClock,
    create_account,
    create_subscription,
    csrf_headers,
    login,
    scheduled_for,
)


@pytest.mark.parametrize(
    ("anchor", "period", "expected"),
    [
        ("2027-01-31", "monthly", ["2027-02-28", "2027-03-31"]),
        ("2024-02-29", "yearly", ["2025-02-28", "2026-02-28"]),
        ("2026-11-01", "daily", ["2026-11-02", "2026-11-03"]),
        ("2026-11-01", "weekly", ["2026-11-08", "2026-11-15"]),
    ],
)
def test_post_advances_calendar(
    client: TestClient, anchor: str, period: str, expected: list[str]
) -> None:
    login(client)
    entity = create_subscription(client, create_account(client), next_due_on=anchor, period=period)
    for due in expected:
        old = scheduled_for(client, entity)
        assert len(old) == 1
        response = client.post(
            f"/api/v1/transactions/{old[0]['id']}/post", headers=csrf_headers(client)
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "posted"
        current = client.get(f"/api/v1/subscriptions/{entity}").json()
        assert current["next_due_on"] == due
        following = scheduled_for(client, entity)
        assert len(following) == 1
        occurred_at = following[0]["occurred_at"]
        assert isinstance(occurred_at, str) and occurred_at.startswith(due)
        assert (
            client.post(
                f"/api/v1/transactions/{old[0]['id']}/post", headers=csrf_headers(client)
            ).status_code
            == 409
        )


@pytest.mark.parametrize(
    ("now", "due"),
    [("2026-11-01T04:30:00+00:00", "2026-10-31"), ("2026-11-01T05:30:00+00:00", "2026-11-30")],
)
def test_reactivation_uses_lima_injected_clock(
    client: TestClient, clock: FakeClock, now: str, due: str
) -> None:
    login(client)
    entity = create_subscription(client, create_account(client), next_due_on="2026-08-31")
    assert (
        client.post(
            f"/api/v1/subscriptions/{entity}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    clock.value = datetime.fromisoformat(now)
    login(client)
    response = client.post(
        f"/api/v1/subscriptions/{entity}/reactivate", headers=csrf_headers(client)
    )
    assert response.status_code == 200, response.text
    assert response.json()["next_due_on"] == due


def test_post_confirms_rate_without_overwriting_template(
    client: TestClient, db_session: Session
) -> None:
    login(client)
    entity = create_subscription(
        client, create_account(client, currency="USD"), currency="USD", fx_rate_to_base="3.800000"
    )
    old = scheduled_for(client, entity)[0]
    response = client.post(
        f"/api/v1/transactions/{old['id']}/post",
        json={
            "fx_rate_to_base": "3.900000",
            "amount": "-33.00",
            "occurred_at": "2026-11-05T12:00:00Z",
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    assert response.json()["fx_rate_to_base"] == "3.900000"
    following = scheduled_for(client, entity)[0]
    assert following["fx_rate_to_base"] == "3.800000" and following["amount"] == "-30.00"
    subscription = client.get(f"/api/v1/subscriptions/{entity}").json()
    assert subscription["next_due_on"] == "2026-12-01"
    assert (
        subscription["historical_paid"] == "33.00" and subscription["last_paid_on"] == "2026-11-05"
    )
    rule = db_session.get(RecurringRule, UUID(subscription["recurring_rule_id"]))
    assert rule is not None and str(rule.fx_rate_to_base) == "3.800000"


def test_delete_and_archived_edits_preserve_posted(client: TestClient) -> None:
    login(client)
    entity = create_subscription(client, create_account(client))
    first = scheduled_for(client, entity)[0]
    assert (
        client.post(
            f"/api/v1/transactions/{first['id']}/post", headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/subscriptions/{entity}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/subscriptions/{entity}",
            json={"amount": "99.00"},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )
    assert scheduled_for(client, entity) == []
    assert (
        client.delete(f"/api/v1/subscriptions/{entity}", headers=csrf_headers(client)).status_code
        == 200
    )
    assert client.get(f"/api/v1/transactions/{first['id']}").json()["amount"] == "-30.00"


def test_failed_post_rolls_back_and_interval_edit(client: TestClient) -> None:
    login(client)
    entity = create_subscription(client, create_account(client), next_due_on="2027-01-31")
    initial = scheduled_for(client, entity)[0]
    response = client.post(
        f"/api/v1/transactions/{initial['id']}/post",
        json={"amount": "30.00"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422
    assert scheduled_for(client, entity)[0]["id"] == initial["id"]
    assert (
        client.patch(
            f"/api/v1/subscriptions/{entity}",
            json={"interval_count": 2},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )
    new = scheduled_for(client, entity)[0]
    assert (
        client.post(
            f"/api/v1/transactions/{new['id']}/post", headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/subscriptions/{entity}").json()["next_due_on"] == "2027-03-31"


def test_posting_preserved_old_schedule_does_not_regress_calendar(client: TestClient) -> None:
    login(client)
    entity = create_subscription(client, create_account(client), next_due_on="2026-09-01")
    past = scheduled_for(client, entity)[0]
    assert (
        client.post(
            f"/api/v1/subscriptions/{entity}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/subscriptions/{entity}/reactivate", headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/subscriptions/{entity}").json()["next_due_on"] == "2026-11-01"
    assert (
        client.post(
            f"/api/v1/transactions/{past['id']}/post", headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/subscriptions/{entity}").json()["next_due_on"] == "2026-11-01"
    assert len(scheduled_for(client, entity)) == 1


def test_reactivate_today_does_not_duplicate_preserved_schedule(
    client: TestClient, clock: FakeClock
) -> None:
    clock.value = datetime(2026, 10, 7, 12, tzinfo=UTC)
    login(client)
    entity = create_subscription(client, create_account(client), next_due_on="2026-10-07")
    initial = scheduled_for(client, entity)[0]
    assert (
        client.post(
            f"/api/v1/subscriptions/{entity}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/subscriptions/{entity}/reactivate", headers=csrf_headers(client)
        ).status_code
        == 200
    )
    scheduled = scheduled_for(client, entity)
    assert len(scheduled) == 1 and scheduled[0]["id"] == initial["id"]


def test_calendar_overflow_rolls_back_post(client: TestClient) -> None:
    login(client)
    entity = create_subscription(client, create_account(client), next_due_on="9999-12-31")
    initial = scheduled_for(client, entity)[0]
    response = client.post(
        f"/api/v1/transactions/{initial['id']}/post", headers=csrf_headers(client)
    )
    assert response.status_code == 422 and response.json()["code"] == "invalid_schedule"
    assert scheduled_for(client, entity)[0]["id"] == initial["id"]
    assert client.get(f"/api/v1/subscriptions/{entity}").json()["historical_paid"] == "0.00"
