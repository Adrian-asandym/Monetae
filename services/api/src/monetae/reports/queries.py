"""One SQL aggregation for each report, without loading individual transactions."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from monetae.api.schemas.reports import Period, ReportKind
from monetae.db.models import User

# All dynamic values (including date_trunc's unit) are bound parameters.
# Daily preaggregation avoids repeating the historical rate lookup per transaction.
AGGREGATE_SQL = text("""
WITH entries AS (
    SELECT t.occurred_at, t.currency, t.kind,
           CASE WHEN :categories THEN t.category_id ELSE NULL::uuid END AS category_id,
           abs(t.amount) AS amount, t.fx_rate_to_base
    FROM transactions t
    WHERE t.user_id = :user_id AND t.deleted_at IS NULL AND t.status = 'posted'
      AND t.kind IN ('income', 'expense') AND CAST(:person_id AS uuid) IS NULL
      AND t.occurred_at >= :start_at AND t.occurred_at < :end_at
      AND (CAST(:account_id AS uuid) IS NULL OR t.account_id = :account_id)
    UNION ALL
    SELECT m.occurred_at, t.currency,
           CASE WHEN l.direction = 'lent' THEN 'income' ELSE 'expense' END,
           CASE WHEN :categories THEN c.id ELSE NULL::uuid END,
           m.interest_part * coalesce(m.fx_rate_applied, 1), t.fx_rate_to_base
    FROM loan_movements m
    JOIN loans l ON l.id = m.loan_id AND l.user_id = :user_id AND l.deleted_at IS NULL
    JOIN transactions t ON t.id = m.transaction_id AND t.user_id = :user_id
       AND t.deleted_at IS NULL AND t.status = 'posted' AND t.kind = 'loan'
    JOIN categories c ON c.user_id = :user_id AND c.deleted_at IS NULL
       AND c.system_key = CASE WHEN l.direction = 'lent' THEN 'interest_income'
                              ELSE 'interest_expense' END
    WHERE m.user_id = :user_id AND m.deleted_at IS NULL AND m.kind = 'payment'
      AND m.interest_part > 0
      AND m.occurred_at >= :start_at AND m.occurred_at < :end_at
      AND (CAST(:account_id AS uuid) IS NULL OR t.account_id = :account_id)
      AND (CAST(:person_id AS uuid) IS NULL OR l.person_id = :person_id)
), daily AS (
    SELECT (occurred_at AT TIME ZONE :timezone)::date AS day,
           category_id, kind, currency, sum(amount) AS amount,
           sum(amount * fx_rate_to_base) AS base_amount, count(*) AS entry_count
    FROM entries GROUP BY day, category_id, kind, currency
), days AS (
    SELECT DISTINCT day FROM daily
), rates AS (
    SELECT days.day, historical.rate
    FROM days LEFT JOIN LATERAL (
        SELECT rate FROM exchange_rates
        WHERE from_currency = :base_currency AND to_currency = :report_currency
          AND as_of <= days.day AND :base_currency <> :report_currency
        ORDER BY as_of DESC, (source = 'manual') DESC, source ASC, id ASC LIMIT 1
    ) historical ON true
)
SELECT CASE WHEN CAST(:unit AS text) IS NULL THEN CAST(:start_on AS date)
            ELSE date_trunc(:unit, daily.day::timestamp)::date END AS bucket,
       category_id, kind, currency, sum(amount) AS amount,
       coalesce(sum(CASE WHEN :base_currency = :report_currency THEN base_amount
                         ELSE base_amount * rates.rate END), 0) AS report_amount,
       sum(CASE WHEN :base_currency <> :report_currency AND rates.rate IS NULL
                THEN entry_count ELSE 0 END) AS unconverted_count
FROM daily JOIN rates ON rates.day = daily.day
GROUP BY bucket, category_id, kind, currency
ORDER BY bucket, category_id, kind, currency
""")


@dataclass(frozen=True)
class Aggregate:
    bucket: date
    category_id: UUID | None
    kind: ReportKind
    currency: str
    amount: Decimal
    report_amount: Decimal
    unconverted_count: int


def aggregate(
    db: Session,
    user: User,
    start: date,
    end: date,
    period: Period | None,
    report_currency: str,
    account_id: UUID | None,
    person_id: UUID | None,
    *,
    categories: bool,
) -> list[Aggregate]:
    zone = ZoneInfo(user.timezone)
    start_at = datetime.combine(start, time.min, zone).astimezone(UTC)
    end_at = datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(UTC)
    unit = {"daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}
    result = db.execute(
        AGGREGATE_SQL,
        {
            "user_id": user.id,
            "start_at": start_at,
            "end_at": end_at,
            "start_on": start,
            "timezone": user.timezone,
            "base_currency": user.base_currency,
            "report_currency": report_currency,
            "account_id": account_id,
            "person_id": person_id,
            "unit": unit[period] if period else None,
            "categories": categories,
        },
    )
    # Raw SQL is a DB boundary; casts reflect the fixed SELECT column types.
    return [
        Aggregate(
            bucket=cast(date, row.bucket),
            category_id=cast(UUID | None, row.category_id),
            kind=cast(ReportKind, row.kind),
            currency=cast(str, row.currency),
            amount=cast(Decimal, row.amount),
            report_amount=cast(Decimal, row.report_amount),
            unconverted_count=int(row.unconverted_count),
        )
        for row in result
    ]
