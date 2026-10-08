from time import perf_counter

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from api.conftest import create_account, create_tag, create_transaction, login
from api.test_account_balance import statements


def test_first_page_20000_transactions_under_300ms_and_uses_index(
    client: TestClient, db_session: Session, db_engine: Engine
) -> None:
    login(client)
    account = create_account(client)
    tag = create_tag(client)
    entity_id = create_transaction(client, account, tag_ids=[tag])
    owner = client.get("/api/v1/users/me").json()["id"]
    db_session.execute(
        text("""
        INSERT INTO transactions (user_id, account_id, currency, kind, amount, occurred_at,
            status, title, fx_rate_to_base, fx_rate_source, source)
        SELECT :user_id, :account_id, 'PEN', 'expense', -1.00,
            '2026-01-01T00:00:00Z'::timestamptz + n * interval '1 minute',
            'posted', 'Synthetic ' || n, 1.000000, 'manual', 'web'
        FROM generate_series(1, 19999) n
    """),
        {"user_id": owner, "account_id": account},
    )
    db_session.execute(text("ANALYZE transactions"))
    with statements(db_engine) as queries:
        start = perf_counter()
        response = client.get("/api/v1/transactions")
        elapsed = perf_counter() - start
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 50
    assert response.json()["items"][0]["id"] == entity_id
    assert response.json()["items"][0]["tag_ids"] == [tag]
    assert elapsed < 0.300, f"First page took {elapsed * 1000:.1f} ms"
    assert len([q for q in queries if "FROM transaction_tags JOIN tags" in q]) == 1
    assert len(queries) <= 5, queries
    assert not any("FOR UPDATE" in q.upper() or "FOR SHARE" in q.upper() for q in queries)
    plan = "\n".join(
        db_session.scalars(
            text("""
        EXPLAIN (ANALYZE, BUFFERS)
        SELECT * FROM transactions WHERE user_id=:user_id AND deleted_at IS NULL
        ORDER BY occurred_at DESC, id DESC LIMIT 51
    """),
            {"user_id": owner},
        )
    )
    assert "ix_transactions_user_occurred" in plan, plan
    print(f"20000 rows: first page {elapsed * 1000:.1f} ms\n{plan}")
