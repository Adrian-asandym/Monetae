"""Validate references, aggregate statistics, format totals and paginate."""

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, localcontext
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae.api.pagination import decode_cursor, encode_cursor
from monetae.api.schemas.reports import (
    CashFlowRow,
    CashFlowRowPage,
    CategoryReportRow,
    CategoryReportRowPage,
    CurrencyTotal,
    Period,
    ReportKind,
    ReportTotal,
)
from monetae.db.models import Account, Person, User
from monetae.reports.periods import Bucket, period_start, resolve_range
from monetae.reports.queries import Aggregate, aggregate
from monetae.services.auth import AuthError, Clock


def money_text(amount: Decimal) -> str:
    with localcontext() as context:
        context.prec = 60
        rounded = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{abs(rounded) if rounded == 0 else rounded:.2f}"


@dataclass
class Totals:
    by_currency: dict[str, Decimal] = field(default_factory=dict)
    report_amount: Decimal = Decimal(0)
    unconverted_count: int = 0

    def add(self, row: Aggregate, sign: int = 1) -> None:
        # SQL NUMERIC sums can exceed Decimal's default 28-digit context.
        with localcontext() as context:
            context.prec = 60
            self.by_currency[row.currency] = (
                self.by_currency.get(row.currency, Decimal(0)) + row.amount * sign
            )
            self.report_amount += row.report_amount * sign
        self.unconverted_count += row.unconverted_count

    def representation(self, currency: str) -> ReportTotal:
        return ReportTotal(
            by_currency=[
                CurrencyTotal(currency=key, amount=money_text(value))
                for key, value in sorted(self.by_currency.items())
            ],
            report_currency=currency,
            report_amount=money_text(self.report_amount),
            unconverted_count=self.unconverted_count,
        )


@dataclass(frozen=True)
class Options:
    start: date
    end: date
    buckets: list[Bucket]
    period: Period | None
    currency: str
    account_id: UUID | None
    person_id: UUID | None
    filters: str


class ReportService:
    def __init__(self, db: Session, secret: str, clock: Clock) -> None:
        self.db, self.secret, self.clock = db, secret, clock

    def options(
        self,
        user: User,
        date_from: date | None,
        date_to: date | None,
        period: Period | None,
        report_currency: str | None,
        account_id: UUID | None,
        person_id: UUID | None,
    ) -> Options:
        for model, entity_id in ((Account, account_id), (Person, person_id)):
            if (
                entity_id is not None
                and self.db.scalar(
                    select(model.id).where(
                        model.id == entity_id,
                        model.user_id == user.id,
                        model.deleted_at.is_(None),
                    )
                )
                is None
            ):
                raise AuthError(404, "not_found", "The report filter was not found.")
        today = self.clock.now().astimezone(ZoneInfo(user.timezone)).date()
        start, end, buckets = resolve_range(date_from, date_to, period, today)
        currency = report_currency or user.report_currency
        filters = json.dumps(
            [
                str(user.id),
                start.isoformat(),
                end.isoformat(),
                period,
                currency,
                str(account_id),
                str(person_id),
                user.timezone,
                user.base_currency,
            ],
            separators=(",", ":"),
        )
        return Options(start, end, buckets, period, currency, account_id, person_id, filters)

    def rows(self, user: User, options: Options, *, categories: bool) -> list[Aggregate]:
        return aggregate(
            self.db,
            user,
            options.start,
            options.end,
            options.period,
            options.currency,
            options.account_id,
            options.person_id,
            categories=categories,
        )

    def cash_flow(
        self,
        user: User,
        options: Options,
        limit: int,
        cursor: str | None,
    ) -> CashFlowRowPage:
        resource = "reports/cash-flow"
        key = decode_cursor(cursor, resource, options.filters, self.secret)
        after: date | None = None
        if key is not None:
            try:
                if len(key) != 1:
                    raise ValueError
                after = date.fromisoformat(key[0])
            except ValueError as exc:
                raise AuthError(400, "invalid_cursor", "The pagination cursor is invalid.") from exc
        grouped: dict[date, dict[str, Totals]] = {}
        for row in self.rows(user, options, categories=False):
            totals = grouped.setdefault(
                row.bucket, {"income": Totals(), "expense": Totals(), "net": Totals()}
            )
            totals[row.kind].add(row)
            totals["net"].add(row, 1 if row.kind == "income" else -1)
        items: list[CashFlowRow] = []
        for bucket in options.buckets:
            if after is not None and bucket.start_on <= after:
                continue
            natural_start = period_start(bucket.start_on, options.period or "monthly")
            totals = grouped.get(natural_start, {})
            items.append(
                CashFlowRow(
                    start_on=bucket.start_on,
                    end_on=bucket.end_on,
                    income=totals.get("income", Totals()).representation(options.currency),
                    expense=totals.get("expense", Totals()).representation(options.currency),
                    net=totals.get("net", Totals()).representation(options.currency),
                )
            )
            if len(items) > limit:
                break
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            next_cursor = encode_cursor(
                resource, options.filters, [items[-1].start_on.isoformat()], self.secret
            )
        return CashFlowRowPage(items=items, next_cursor=next_cursor)

    def categories(
        self,
        user: User,
        options: Options,
        limit: int,
        cursor: str | None,
    ) -> CategoryReportRowPage:
        resource = "reports/categories"
        key = decode_cursor(cursor, resource, options.filters, self.secret)
        after: tuple[date, Decimal, str, str] | None = None
        if key is not None:
            try:
                if len(key) != 4 or key[2] not in {"income", "expense"}:
                    raise ValueError
                amount = Decimal(key[1])
                if not amount.is_finite():
                    raise ValueError
                if key[3]:
                    UUID(key[3])
                after = (date.fromisoformat(key[0]), amount, key[2], key[3])
            except (ValueError, ArithmeticError) as exc:
                raise AuthError(400, "invalid_cursor", "The pagination cursor is invalid.") from exc
        grouped: dict[tuple[date, UUID | None, ReportKind], Totals] = {}
        for row in self.rows(user, options, categories=True):
            grouped.setdefault((row.bucket, row.category_id, row.kind), Totals()).add(row)
        buckets = {
            (period_start(b.start_on, options.period) if options.period else b.start_on): b
            for b in options.buckets
        }
        entries: list[tuple[tuple[date, Decimal, str, str], CategoryReportRow]] = []
        sort_key: tuple[date, Decimal, str, str]
        for (start, category_id, kind), totals in grouped.items():
            bucket = buckets[start]
            total = totals.representation(options.currency)
            sort_key = (
                bucket.start_on,
                -Decimal(total.report_amount),
                kind,
                str(category_id) if category_id else "",
            )
            if after is None or sort_key > after:
                entries.append(
                    (
                        sort_key,
                        CategoryReportRow(
                            category_id=category_id,
                            kind=kind,
                            start_on=bucket.start_on,
                            end_on=bucket.end_on,
                            total=total,
                        ),
                    )
                )
        entries.sort(key=lambda entry: entry[0])
        next_cursor = None
        if len(entries) > limit:
            entries = entries[:limit]
            sort_key = entries[-1][0]
            next_cursor = encode_cursor(
                resource, options.filters, [str(part) for part in sort_key], self.secret
            )
        return CategoryReportRowPage(items=[item for _, item in entries], next_cursor=next_cursor)
