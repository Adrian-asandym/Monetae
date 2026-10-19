"""Batch signed goal progress using the report historical conversion rules."""

from datetime import date
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import Uuid, text
from sqlalchemy.orm import Session

from monetae.db.models import User
from monetae.reports.queries import Aggregate

# Corrections are income/expense legs: retain their signed contribution,
# exactly as transfers (Cashew watchTotalTowardsObjective includes category 0).
GOAL_TRANSACTION_PREDICATE_SQL = """
    gt.user_id = :user_id AND gt.deleted_at IS NULL
    AND t.user_id = :user_id AND t.deleted_at IS NULL AND t.status = 'posted'
    AND t.kind IN ('income', 'expense', 'transfer')
"""

GOAL_TRANSACTION_IDS_SQL = text(
    """
SELECT t.id AS transaction_id
FROM goal_transactions gt JOIN transactions t ON t.id = gt.transaction_id
WHERE gt.goal_id = :goal_id AND """
    + GOAL_TRANSACTION_PREDICATE_SQL
).columns(transaction_id=Uuid())

GOAL_SQL = text(
    """
WITH daily AS (
    SELECT g.id AS goal_id, g.currency AS report_currency,
           (t.occurred_at AT TIME ZONE :timezone)::date AS day, t.currency,
           sum(t.amount * CASE WHEN g.kind = 'spend' THEN -1 ELSE 1 END) AS amount,
           sum(t.amount * t.fx_rate_to_base *
               CASE WHEN g.kind = 'spend' THEN -1 ELSE 1 END) AS base_amount,
           count(*) AS entry_count
    FROM goals g
    JOIN goal_transactions gt ON gt.goal_id = g.id
    JOIN transactions t ON t.id = gt.transaction_id
    WHERE g.user_id = :user_id AND g.deleted_at IS NULL AND g.id = ANY(:goal_ids)
      AND """
    + GOAL_TRANSACTION_PREDICATE_SQL
    + """
    GROUP BY g.id, g.currency, g.kind, day, t.currency
)
SELECT daily.goal_id, daily.currency, sum(daily.amount) AS amount,
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
GROUP BY daily.goal_id, daily.currency
"""
)


def goal_progress(db: Session, user: User, ids: list[UUID]) -> dict[UUID, list[Aggregate]]:
    if not ids:
        return {}
    rows = db.execute(
        GOAL_SQL,
        {
            "user_id": user.id,
            "timezone": user.timezone,
            "base_currency": user.base_currency,
            "goal_ids": ids,
        },
    )
    result: dict[UUID, list[Aggregate]] = {}
    # Raw SQL is a DB boundary; casts reflect the fixed SELECT column types.
    for row in rows:
        goal_id = cast(UUID, row.goal_id)
        result.setdefault(goal_id, []).append(
            Aggregate(
                bucket=date.min,
                category_id=None,
                kind="income",
                currency=cast(str, row.currency),
                amount=cast(Decimal, row.amount),
                report_amount=cast(Decimal, row.report_amount),
                unconverted_count=int(row.unconverted_count),
            )
        )
    return result
