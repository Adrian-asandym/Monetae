"""Batch budget aggregation sharing the report ledger classification."""

import json
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from monetae.db.models import User
from monetae.domain.budgets import BudgetCycle
from monetae.reports.queries import ENTRY_SQL, Aggregate

BUDGET_SQL = text(
    "WITH entries AS ("
    + ENTRY_SQL
    + """
), periods AS (
    SELECT * FROM jsonb_to_recordset(CAST(:periods AS jsonb))
        AS p(id uuid, start_on date, end_on date)
), daily AS (
    SELECT b.id AS budget_id, b.currency AS report_currency,
           (e.occurred_at AT TIME ZONE :timezone)::date AS day,
           e.currency, sum(e.amount) AS amount,
           sum(e.amount * e.fx_rate_to_base) AS base_amount, count(*) AS entry_count
    FROM entries e
    JOIN periods p ON (e.occurred_at AT TIME ZONE :timezone)::date
        BETWEEN p.start_on AND p.end_on
    JOIN budgets b ON b.id = p.id AND b.user_id = :user_id AND b.deleted_at IS NULL
    WHERE e.kind = 'expense'
      AND (b.scope = 'all' OR EXISTS (
          SELECT 1 FROM budget_transactions bt WHERE bt.user_id = :user_id
          AND bt.budget_id = b.id AND bt.transaction_id = e.transaction_id
          AND bt.deleted_at IS NULL))
      AND (NOT EXISTS (SELECT 1 FROM budget_categories bc
          WHERE bc.user_id = :user_id AND bc.budget_id = b.id AND bc.deleted_at IS NULL)
          OR EXISTS (SELECT 1 FROM budget_categories bc
          WHERE bc.user_id = :user_id AND bc.budget_id = b.id AND bc.deleted_at IS NULL
          AND bc.category_id = e.category_id))
    GROUP BY b.id, b.currency, day, e.currency
)
SELECT daily.budget_id, daily.currency, sum(daily.amount) AS amount,
       coalesce(sum(CASE WHEN :base_currency = daily.report_currency THEN daily.base_amount
                         ELSE daily.base_amount * historical.rate END), 0) AS report_amount,
       sum(CASE WHEN :base_currency <> daily.report_currency AND historical.rate IS NULL
                THEN daily.entry_count ELSE 0 END) AS unconverted_count
FROM daily LEFT JOIN LATERAL (
    SELECT rate FROM exchange_rates
    WHERE from_currency = :base_currency AND to_currency = daily.report_currency
      AND as_of <= daily.day AND :base_currency <> daily.report_currency
    ORDER BY as_of DESC, (source = 'manual') DESC, source ASC, id ASC LIMIT 1
) historical ON true
GROUP BY daily.budget_id, daily.currency
"""
)


def budget_expenses(
    db: Session, user: User, cycles: dict[UUID, BudgetCycle]
) -> dict[UUID, list[Aggregate]]:
    if not cycles:
        return {}
    start = min(c.start for c in cycles.values())
    end = max(c.end for c in cycles.values())
    zone = ZoneInfo(user.timezone)
    rows = db.execute(
        BUDGET_SQL,
        {
            "user_id": user.id,
            "start_at": datetime.combine(start, time.min, zone).astimezone(UTC),
            "end_at": datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(UTC),
            "timezone": user.timezone,
            "base_currency": user.base_currency,
            "categories": True,
            "account_id": None,
            "person_id": None,
            "periods": json.dumps(
                [
                    {
                        "id": str(key),
                        "start_on": cycle.start.isoformat(),
                        "end_on": cycle.end.isoformat(),
                    }
                    for key, cycle in cycles.items()
                ]
            ),
        },
    )
    result: dict[UUID, list[Aggregate]] = {}
    # Raw SQL is a DB boundary; casts reflect the fixed SELECT column types.
    for row in rows:
        budget_id = cast(UUID, row.budget_id)
        result.setdefault(budget_id, []).append(
            Aggregate(
                bucket=start,
                category_id=None,
                kind="expense",
                currency=cast(str, row.currency),
                amount=cast(Decimal, row.amount),
                report_amount=cast(Decimal, row.report_amount),
                unconverted_count=int(row.unconverted_count),
            )
        )
    return result
