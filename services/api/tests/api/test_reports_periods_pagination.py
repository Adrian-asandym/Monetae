"""Calendar, validation and cursor behavior of both report endpoints."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.conftest import FakeClock, create_account, create_category, create_transaction, login
from api.test_reports_statistics import ENDPOINTS, RANGE
from monetae.db.models import User


def test_week_iso_cross_month_and_daily_local_boundary(client: TestClient) -> None:
    login(client)
    wallet = create_account(client)
    create_transaction(client, wallet, amount="-10.00", occurred_at="2026-09-30T12:00:00Z")
    create_transaction(client, wallet, amount="-20.00", occurred_at="2026-10-05T04:30:00Z")
    create_transaction(client, wallet, amount="-30.00", occurred_at="2026-10-05T05:00:00Z")
    params = {"date_from": "2026-09-28", "date_to": "2026-10-11", "period": "weekly"}
    for endpoint in ENDPOINTS:
        response = client.get(f"/api/v1/reports/{endpoint}", params=params)
        assert response.status_code == 200, response.text
        rows = response.json()["items"]
        assert [(r["start_on"], r["end_on"]) for r in rows] == [
            ("2026-09-28", "2026-10-04"),
            ("2026-10-05", "2026-10-11"),
        ]
        field = "expense" if endpoint == "cash-flow" else "total"
        assert [r[field]["report_amount"] for r in rows] == ["30.00", "30.00"]
    params = {"date_from": "2026-10-04", "date_to": "2026-10-06", "period": "daily"}
    response = client.get("/api/v1/reports/cash-flow", params=params)
    rows = response.json()["items"]
    assert [r["expense"]["report_amount"] for r in rows] == ["20.00", "30.00", "0.00"]
    assert rows[-1]["expense"]["by_currency"] == []
    assert rows[-1]["net"]["unconverted_count"] == 0
    categories = client.get("/api/v1/reports/categories", params=params).json()["items"]
    assert [r["start_on"] for r in categories] == ["2026-10-04", "2026-10-05"]


@pytest.mark.parametrize(
    "period,start",
    [
        ("daily", "2026-09-26"),
        ("weekly", "2026-07-20"),
        ("monthly", "2025-11-01"),
        ("yearly", "2015-01-01"),
    ],
)
def test_default_range_twelve_buckets_including_current_partial(
    client: TestClient,
    period: str,
    start: str,
) -> None:
    login(client)
    response = client.get("/api/v1/reports/cash-flow", params={"period": period})
    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert len(rows) == 12 and rows[0]["start_on"] == start
    assert rows[-1]["end_on"] == "2026-10-07"


def test_defaults_use_user_timezone_and_categories_single_range(
    client: TestClient,
    clock: FakeClock,
    db_session: Session,
    auth_users: tuple[User, User],
) -> None:
    login(client)
    # Oct 7 UTC is still Oct 6 locally; no datetime.now dependency.
    clock.value = datetime(2026, 10, 7, 4, 30, tzinfo=UTC)
    wallet = create_account(client)
    create_transaction(client, wallet, amount="-10.00", occurred_at="2026-10-07T04:00:00Z")
    response = client.get("/api/v1/reports/cash-flow")
    rows = response.json()["items"]
    assert len(rows) == 12 and rows[0]["start_on"] == "2025-11-01"
    assert rows[-1]["end_on"] == "2026-10-06"
    categories = client.get("/api/v1/reports/categories").json()["items"]
    assert len(categories) == 1
    assert categories[0]["start_on"] == "2025-11-01" and categories[0]["end_on"] == "2026-10-06"
    auth_users[0].timezone = "Asia/Tokyo"
    db_session.commit()
    response = client.get("/api/v1/reports/cash-flow", params={"period": "daily"})
    assert response.json()["items"][-1]["end_on"] == "2026-10-07"


@pytest.mark.parametrize("period", ["daily", "weekly", "monthly", "yearly"])
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_partial_bucket_boundaries_are_clipped(
    client: TestClient, endpoint: str, period: str
) -> None:
    login(client)
    wallet = create_account(client)
    create_transaction(client, wallet)
    response = client.get(
        f"/api/v1/reports/{endpoint}",
        params={"date_from": "2026-10-07", "date_to": "2026-10-07", "period": period},
    )
    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert len(rows) == 1 and rows[0]["start_on"] == rows[0]["end_on"] == "2026-10-07"


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize(
    "params,code",
    [
        ({"date_from": "2026-11-01", "date_to": "2026-10-01"}, "invalid_date_range"),
        (
            {"date_from": "2025-01-01", "date_to": "2026-10-01", "period": "daily"},
            "range_too_large",
        ),
        (
            {"date_from": "0001-01-01", "date_to": "2026-10-01", "period": "yearly"},
            "range_too_large",
        ),
        ({"date_to": "9999-12-31"}, "invalid_date_range"),
    ],
)
def test_invalid_ranges(
    client: TestClient, endpoint: str, params: dict[str, str], code: str
) -> None:
    login(client)
    response = client.get(f"/api/v1/reports/{endpoint}", params=params)
    assert response.status_code == 422, response.text
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == code


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize(
    "params",
    [
        {"limit": "0"},
        {"limit": "201"},
        {"limit": "1.5"},
        {"period": "quarterly"},
        {"date_from": "invalid"},
        {"report_currency": "usd"},
        {"account_id": "not-a-uuid"},
    ],
)
def test_invalid_query_parameters(
    client: TestClient, endpoint: str, params: dict[str, str]
) -> None:
    login(client)
    response = client.get(f"/api/v1/reports/{endpoint}", params=params)
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_session_required(client: TestClient, endpoint: str) -> None:
    response = client.get(f"/api/v1/reports/{endpoint}")
    assert response.status_code == 401


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_stable_pagination_no_duplicates_with_ties_and_null_categories(
    client: TestClient,
    endpoint: str,
) -> None:
    login(client)
    wallet = create_account(client)
    categories: list[str | None] = [create_category(client, name) for name in ("A", "B", "C")]
    categories.append(None)
    for day in ("01", "02", "03"):
        for category in categories:
            create_transaction(
                client,
                wallet,
                amount="-10.00",
                category_id=category,
                occurred_at=f"2026-10-{day}T12:00:00Z",
            )
    params: dict[str, str | int] = {
        **RANGE,
        "date_to": "2026-10-04",
        "period": "daily",
        "limit": 200,
    }
    expected = client.get(f"/api/v1/reports/{endpoint}", params=params).json()["items"]
    params["limit"] = 2
    actual: list[dict[str, object]] = []
    first_cursor: str | None = None
    for _ in range(10):
        response = client.get(f"/api/v1/reports/{endpoint}", params=params)
        assert response.status_code == 200, response.text
        page = response.json()
        actual.extend(page["items"])
        if page["next_cursor"] is None:
            break
        first_cursor = first_cursor or page["next_cursor"]
        params["cursor"] = page["next_cursor"]
    else:
        pytest.fail("Pagination did not terminate")
    assert actual == expected
    assert first_cursor is not None
    # Cursor binds effective filters, identity and resource; malformed values are rejected.
    for override in ({"cursor": first_cursor + "x"}, {"cursor": first_cursor, "period": "monthly"}):
        response = client.get(f"/api/v1/reports/{endpoint}", params={**params, **override})
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_cursor"
    login(client, "second@example.test")
    response = client.get(f"/api/v1/reports/{endpoint}", params={**params, "cursor": first_cursor})
    assert response.status_code == 400
