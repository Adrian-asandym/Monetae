from decimal import ROUND_HALF_UP, Decimal

import pytest
from fastapi.testclient import TestClient

from .conftest import create_account, create_subscription, csrf_headers, login


@pytest.mark.parametrize(
    ("period", "amount", "interval", "monthly", "yearly"),
    [
        ("daily", "10.00", 2, "152.19", "1826.25"),
        ("weekly", "10.00", 3, "14.49", "173.93"),
        ("monthly", "10.00", 3, "3.33", "40.00"),
        ("yearly", "10.00", 2, "0.42", "5.00"),
        ("weekly", "10.00", 1, "43.48", "521.78"),
    ],
)
def test_period_totals(
    client: TestClient, period: str, amount: str, interval: int, monthly: str, yearly: str
) -> None:
    login(client)
    create_subscription(
        client, create_account(client), period=period, amount=amount, interval_count=interval
    )
    response = client.get("/api/v1/subscriptions/totals")
    assert response.status_code == 200, response.text
    total = response.json()["items"][0]
    assert total["monthly_amount"] == monthly and total["yearly_amount"] == yearly
    assert total["monthly_total"]["report_amount"] == monthly
    assert total["yearly_total"]["report_amount"] == yearly
    assert total["active_count"] == 1


def test_separate_currencies_unconverted_and_archived(client: TestClient) -> None:
    login(client)
    pen = create_account(client)
    usd = create_account(client, "Dollar", currency="USD")
    create_subscription(client, pen, amount="20.00")
    create_subscription(client, usd, amount="10.00", currency="USD", fx_rate_to_base="3.800000")
    archived = create_subscription(
        client, usd, amount="99.00", currency="USD", fx_rate_to_base="3.800000"
    )
    assert (
        client.post(
            f"/api/v1/subscriptions/{archived}/archive", json={}, headers=csrf_headers(client)
        ).status_code
        == 200
    )
    for report, expected in [("PEN", "20.00"), ("USD", "10.00"), ("EUR", "0.00")]:
        response = client.get("/api/v1/subscriptions/totals", params={"report_currency": report})
        assert response.status_code == 200, response.text
        totals = response.json()["items"]
        assert [
            (item["currency"], item["monthly_amount"], item["active_count"]) for item in totals
        ] == [("PEN", "20.00", 1), ("USD", "10.00", 1)]
        for item in totals:
            monthly = item["monthly_total"]
            assert monthly["report_amount"] == expected
            assert monthly["unconverted_count"] == (2 if report == "EUR" else 1)
            assert monthly["by_currency"] == [
                {"currency": "PEN", "amount": "20.00"},
                {"currency": "USD", "amount": "10.00"},
            ]
    page = client.get("/api/v1/subscriptions/totals?limit=1").json()
    assert len(page["items"]) == 1 and page["next_cursor"]
    next_page = client.get(
        "/api/v1/subscriptions/totals", params={"limit": 1, "cursor": page["next_cursor"]}
    ).json()
    assert next_page["items"][0]["currency"] == "USD" and next_page["next_cursor"] is None
    assert (
        client.get(
            "/api/v1/subscriptions/totals",
            params={"cursor": page["next_cursor"], "report_currency": "USD"},
        ).status_code
        == 400
    )


def test_aggregate_rounds_only_once(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    for _ in range(3):
        create_subscription(client, account, amount="0.01", interval_count=3)
    item = client.get("/api/v1/subscriptions/totals").json()["items"][0]
    assert item["monthly_amount"] == "0.01" and item["yearly_amount"] == "0.12"
    assert Decimal(item["monthly_amount"]).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ) == Decimal("0.01")
