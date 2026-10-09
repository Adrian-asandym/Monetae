"""Measure complete report requests and verify bounded read-only SQL access."""

from time import perf_counter

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from api.conftest import create_account, login
from api.test_account_balance import statements
from api.test_reports_statistics import ENDPOINTS, rate


def test_reports_20000_transactions_under_one_second_without_n_plus_one_or_locks(
    client: TestClient,
    db_session: Session,
    db_engine: Engine,
) -> None:
    login(client)
    account = create_account(client)
    owner = client.get("/api/v1/users/me").json()["id"]
    db_session.execute(
        text("""
        INSERT INTO transactions (user_id, account_id, currency, kind, amount, occurred_at,
            status, title, fx_rate_to_base, fx_rate_source, source)
        SELECT :user_id, :account_id, 'PEN',
            CASE WHEN n % 2 = 0 THEN 'income' ELSE 'expense' END,
            CASE WHEN n % 2 = 0 THEN 2.00 ELSE -1.00 END,
            '2026-01-01T12:00:00Z'::timestamptz + n * interval '1 minute',
            'posted', 'Synthetic report benchmark ' || n, 1.000000, 'manual', 'web'
        FROM generate_series(1, 20000) n
    """),
        {"user_id": owner, "account_id": account},
    )
    rate(db_session, "2026-01-01", "0.250000")
    db_session.execute(text("ANALYZE transactions"))
    for endpoint in ENDPOINTS:
        with statements(db_engine) as queries:
            start = perf_counter()
            response = client.get(
                f"/api/v1/reports/{endpoint}",
                params={
                    "date_from": "2026-01-01",
                    "date_to": "2026-03-31",
                    "report_currency": "USD",
                    "period": "monthly",
                },
            )
            elapsed = perf_counter() - start
        assert response.status_code == 200, response.text
        assert elapsed < 1.0, f"{endpoint}: {elapsed:.3f}s"
        assert len(queries) <= 5, queries
        assert sum("WITH entries AS" in q for q in queries) == 1
        assert not any("FOR UPDATE" in q.upper() or "FOR SHARE" in q.upper() for q in queries)
        rows = response.json()["items"]
        if endpoint == "cash-flow":
            assert len(rows) == 3
            assert rows[0]["income"]["report_amount"] == "5000.00"
            assert rows[0]["expense"]["report_amount"] == "2500.00"
            assert rows[1]["net"]["report_amount"] == rows[2]["net"]["report_amount"] == "0.00"
        else:
            assert len(rows) == 2
            assert [r["total"]["report_amount"] for r in rows] == ["5000.00", "2500.00"]
        print(
            f"20000 transactions: {endpoint} {elapsed * 1000:.1f} ms, {len(queries)} SQL statements"
        )
