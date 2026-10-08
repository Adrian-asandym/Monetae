"""Suscripciones atómicas, historial agregado y programación anclada."""

import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text, tuple_, update
from sqlalchemy.orm import Session

from monetae import domain
from monetae.api.pagination import decode_cursor, encode_cursor
from monetae.api.schemas import subscriptions as schema
from monetae.api.schemas.transactions import TransactionCreate
from monetae.db.models import RecurringRule, Subscription, Transaction, User
from monetae.db.repository import UserScopedRepository
from monetae.services.auth import AuthError, Clock
from monetae.services.transactions import TransactionService

LIMA = ZoneInfo("America/Lima")


class SubscriptionService:
    def __init__(self, db: Session, cursor_secret: str, clock: Clock) -> None:
        self.db = db
        self.cursor_secret = cursor_secret
        self.clock = clock
        self.transactions = TransactionService(db, cursor_secret)

    def get(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        row = UserScopedRepository(self.db, Subscription, user_id).get(subscription_id)
        if row is None:
            raise AuthError(404, "not_found", "Subscription not found.")
        return row

    def lock(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"subscription:{user_id}:{subscription_id}"},
        )
        self.db.expire_all()
        return self.get(user_id, subscription_id)

    def rule(self, row: Subscription, *, lock: bool = False) -> RecurringRule:
        if lock:
            self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": f"recurring-rule:{row.user_id}:{row.recurring_rule_id}"},
            )
        rule = self.db.scalar(
            select(RecurringRule)
            .where(
                RecurringRule.id == row.recurring_rule_id,
                RecurringRule.user_id == row.user_id,
                RecurringRule.deleted_at.is_(None),
            )
            .execution_options(populate_existing=True)
        )
        if rule is None:
            raise AuthError(409, "recurring_rule_missing", "Subscription rule is unavailable.")
        return rule

    @staticmethod
    def model(row: Subscription) -> domain.Subscription:
        return domain.Subscription(
            title=row.title,
            amount=domain.Money(row.amount, domain.Currency(row.currency)),
            period=domain.Period(row.period),
            interval_count=row.interval_count,
            next_due_on=row.next_due_on,
            anchor_on=row.anchor_on,
            status=cast(schema.SubscriptionStatus, row.status),
            archived_at=row.archived_at,
            archive_reason=row.archive_reason,
        )

    def representations(self, user_id: UUID, rows: list[Subscription]) -> list[schema.Subscription]:
        if not rows:
            return []
        history = self.db.execute(
            select(
                Transaction.recurring_rule_id,
                func.sum(func.abs(Transaction.amount)),
                func.max(func.date(func.timezone("America/Lima", Transaction.occurred_at))),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.recurring_rule_id.in_([r.recurring_rule_id for r in rows]),
                Transaction.status == "posted",
                Transaction.deleted_at.is_(None),
            )
            .group_by(Transaction.recurring_rule_id)
        ).all()
        paid = {rule_id: (amount, last) for rule_id, amount, last in history}
        results = []
        for row in rows:
            amount, last = paid.get(row.recurring_rule_id, (Decimal(0), None))
            values = {
                name: getattr(row, name)
                for name in schema.Subscription.model_fields
                if name not in {"historical_paid", "last_paid_on"}
            }
            values.update(
                amount=f"{row.amount:.2f}", historical_paid=f"{amount:.2f}", last_paid_on=last
            )
            results.append(schema.Subscription.model_validate(values))
        return results

    def representation(self, row: Subscription) -> schema.Subscription:
        return self.representations(row.user_id, [row])[0]

    def list(
        self, user_id: UUID, status: schema.SubscriptionStatus, limit: int, cursor: str | None
    ) -> schema.SubscriptionPage:
        fingerprint = json.dumps([str(user_id), status])
        key = decode_cursor(cursor, "subscriptions", fingerprint, self.cursor_secret)
        query = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == status,
            Subscription.deleted_at.is_(None),
        )
        if key is not None:
            try:
                if len(key) != 2:
                    raise ValueError
                query = query.where(
                    tuple_(Subscription.next_due_on, Subscription.id)
                    > tuple_(date.fromisoformat(key[0]), UUID(key[1]))
                )
            except ValueError as exc:
                raise AuthError(400, "invalid_cursor", "Invalid subscription cursor.") from exc
        rows = list(
            self.db.scalars(
                query.order_by(Subscription.next_due_on, Subscription.id).limit(limit + 1)
            )
        )
        more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = (
            encode_cursor(
                "subscriptions",
                fingerprint,
                [rows[-1].next_due_on.isoformat(), str(rows[-1].id)],
                self.cursor_secret,
            )
            if more
            else None
        )
        return schema.SubscriptionPage(
            items=self.representations(user_id, rows), next_cursor=next_cursor
        )

    def _rate(
        self, user_id: UUID, currency: str, supplied: str | None, stored: Decimal | None = None
    ) -> Decimal:
        base = self.transactions._base_currency(user_id)
        if currency == base:
            if supplied is not None and Decimal(supplied) != Decimal(1):
                raise AuthError(422, "invalid_fx_rate", "Base currency rate must be 1.000000.")
            return Decimal("1.000000")
        if supplied is None and stored is None:
            raise AuthError(
                422, "fx_rate_required", "A provisional manual exchange rate is required."
            )
        return Decimal(supplied) if supplied is not None else cast(Decimal, stored)

    def _references(self, row: Subscription) -> None:
        account = self.transactions._references(row.user_id, row.account_id, row.category_id)
        if account.currency != row.currency:
            raise AuthError(
                422, "currency_mismatch", "Subscription currency must match its account."
            )

    def materialize(self, row: Subscription, rule: RecurringRule) -> Transaction | None:
        if not rule.active or row.status != "active" or row.deleted_at is not None:
            return None
        if rule.end_on is not None and rule.next_run_on > rule.end_on:
            return None
        due_at = datetime.combine(rule.next_run_on, time.min, LIMA).astimezone(UTC)
        existing = self.db.scalar(
            select(Transaction).where(
                Transaction.user_id == row.user_id,
                Transaction.recurring_rule_id == rule.id,
                Transaction.status == "scheduled",
                Transaction.deleted_at.is_(None),
                Transaction.occurred_at == due_at,
            )
        )
        if existing is not None:
            return existing
        payload = TransactionCreate.model_validate(
            {
                "account_id": row.account_id,
                "category_id": row.category_id,
                "kind": "expense",
                "amount": f"{-row.amount:.2f}",
                "currency": row.currency,
                "occurred_at": due_at,
                "status": "scheduled",
                "title": row.title,
                "note": rule.note,
                "fx_rate_to_base": f"{rule.fx_rate_to_base:.6f}",
                "fx_rate_source": "manual",
            }
        )
        transaction = self.transactions.create(row.user_id, payload)
        transaction.recurring_rule_id = rule.id
        self.db.flush()
        return transaction

    def create(self, user_id: UUID, payload: schema.SubscriptionCreate) -> Subscription:
        subscription_id = uuid4()
        # Una alta también usa el bloqueo propio antes de regla y referencias.
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"subscription:{user_id}:{subscription_id}"},
        )
        rate = self._rate(user_id, payload.currency, payload.fx_rate_to_base)
        row = Subscription(
            id=subscription_id,
            user_id=user_id,
            status="active",
            anchor_on=payload.next_due_on,
            **payload.model_dump(exclude={"fx_rate_to_base"}),
        )
        row.amount = Decimal(payload.amount)
        self.model(row)
        self._references(row)
        rule = RecurringRule(
            user_id=user_id,
            account_id=row.account_id,
            kind="expense",
            amount=-row.amount,
            currency=row.currency,
            category_id=row.category_id,
            title=row.title,
            period=row.period,
            interval_count=row.interval_count,
            anchor_on=row.anchor_on,
            next_run_on=row.next_due_on,
            active=True,
            fx_rate_to_base=rate,
        )
        self.db.add(rule)
        self.db.flush()
        row.recurring_rule_id = rule.id
        self.db.add(row)
        self.db.flush()
        rule.subscription_id = row.id
        self.materialize(row, rule)
        self.db.flush()
        return row

    def _cancel_scheduled(self, row: Subscription, *, future_only: bool) -> None:
        query = update(Transaction).where(
            Transaction.user_id == row.user_id,
            Transaction.recurring_rule_id == row.recurring_rule_id,
            Transaction.status == "scheduled",
            Transaction.deleted_at.is_(None),
        )
        if future_only:
            query = query.where(Transaction.occurred_at >= self.clock.now())
        self.db.execute(query.values(deleted_at=self.clock.now()))

    def update(
        self, user_id: UUID, subscription_id: UUID, payload: schema.SubscriptionUpdate
    ) -> Subscription:
        row = self.lock(user_id, subscription_id)
        rule = self.rule(row, lock=True)
        if payload.currency is not None and payload.currency != row.currency:
            raise AuthError(
                422, "currency_mismatch", "Archive and create a subscription in another currency."
            )
        rate = self._rate(user_id, row.currency, payload.fx_rate_to_base, rule.fx_rate_to_base)
        with self.db.no_autoflush:
            for key, value in payload.model_dump(
                exclude_unset=True, exclude={"fx_rate_to_base"}
            ).items():
                setattr(row, key, Decimal(value) if key == "amount" else value)
            if "next_due_on" in payload.model_fields_set:
                row.anchor_on = row.next_due_on
            self.model(row)
            self._references(row)
        self._cancel_scheduled(row, future_only=False)
        for name in (
            "account_id",
            "currency",
            "category_id",
            "title",
            "period",
            "interval_count",
            "anchor_on",
        ):
            setattr(rule, name, getattr(row, name))
        rule.amount = -row.amount
        rule.next_run_on = row.next_due_on
        rule.fx_rate_to_base = rate
        self.materialize(row, rule)
        self.db.flush()
        return row

    def archive(self, user_id: UUID, subscription_id: UUID, reason: str | None) -> Subscription:
        row = self.lock(user_id, subscription_id)
        rule = self.rule(row, lock=True)
        try:
            result = domain.archive(self.model(row), self.clock.now(), reason)
        except domain.SubscriptionStateError as exc:
            raise AuthError(409, "already_archived", str(exc)) from exc
        row.status, row.archived_at, row.archive_reason = (
            result.status,
            result.archived_at,
            result.archive_reason,
        )
        rule.active = False
        self._cancel_scheduled(row, future_only=True)
        self.db.flush()
        return row

    def reactivate(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        row = self.lock(user_id, subscription_id)
        rule = self.rule(row, lock=True)
        today = self.clock.now().astimezone(LIMA).date()
        model = self.model(row)
        try:
            due = self.next_after(row, today - timedelta(days=1))
            result = domain.reactivate(model, due)
        except domain.SubscriptionStateError as exc:
            raise AuthError(409, "already_active", str(exc)) from exc
        row.status, row.archived_at, row.archive_reason = result.status, None, None
        row.next_due_on = rule.next_run_on = due
        rule.active = True
        self.materialize(row, rule)
        self.db.flush()
        return row

    def delete(self, user_id: UUID, subscription_id: UUID) -> None:
        row = self.lock(user_id, subscription_id)
        rule = self.rule(row, lock=True)
        rule.active = False
        row.deleted_at = rule.deleted_at = self.clock.now()
        self._cancel_scheduled(row, future_only=True)
        self.db.flush()

    @staticmethod
    def next_after(row: Subscription, after: date) -> date:
        try:
            return domain.next_after(SubscriptionService.model(row), after)
        except domain.SubscriptionValidationError as exc:
            raise AuthError(422, "invalid_schedule", str(exc)) from exc

    def advance(self, row: Subscription, rule: RecurringRule, scheduled_on: date) -> None:
        if not rule.active or row.status != "active" or row.deleted_at is not None:
            return
        # Publicar un cobro vencido conservado al archivar no retrocede el calendario.
        if scheduled_on < rule.next_run_on:
            return
        row.next_due_on = rule.next_run_on = self.next_after(row, scheduled_on)
        self.materialize(row, rule)
        self.db.flush()

    def totals(
        self, user_id: UUID, report_currency: str | None, limit: int, cursor: str | None
    ) -> schema.SubscriptionTotalPage:
        report = report_currency or self.db.scalar(
            select(User.report_currency).where(User.id == user_id)
        )
        if report is None:
            raise AuthError(404, "not_found", "User not found.")
        rows = list(
            self.db.scalars(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.status == "active",
                    Subscription.deleted_at.is_(None),
                )
            )
        )
        totals = domain.totals(self.model(row) for row in rows)
        reports = []
        for index in (0, 1):
            amounts = {
                currency: (monthly, yearly)[index]
                for currency, (monthly, yearly, _) in totals.items()
            }
            converted = amounts.get(domain.Currency(report))
            reports.append(
                schema.ReportTotal.model_validate(
                    {
                        "by_currency": [
                            {"currency": currency.code, "amount": f"{amount.amount:.2f}"}
                            for currency, amount in sorted(
                                amounts.items(), key=lambda item: item[0].code
                            )
                        ],
                        "report_currency": report,
                        "report_amount": f"{converted.amount:.2f}"
                        if converted is not None
                        else "0.00",
                        "unconverted_count": sum(
                            v[2] for c, v in totals.items() if c.code != report
                        ),
                    }
                )
            )
        fingerprint = json.dumps([str(user_id), report])
        key = decode_cursor(cursor, "subscription-totals", fingerprint, self.cursor_secret)
        if key is not None and (len(key) != 1 or key[0] not in {c.code for c in totals}):
            raise AuthError(400, "invalid_cursor", "Invalid totals cursor.")
        currencies = [
            c for c in sorted(totals, key=lambda c: c.code) if key is None or c.code > key[0]
        ]
        more = len(currencies) > limit
        currencies = currencies[:limit]
        items = [
            schema.SubscriptionTotal.model_validate(
                {
                    "currency": c.code,
                    "monthly_amount": f"{totals[c][0].amount:.2f}",
                    "yearly_amount": f"{totals[c][1].amount:.2f}",
                    "active_count": totals[c][2],
                    "monthly_total": reports[0],
                    "yearly_total": reports[1],
                }
            )
            for c in currencies
        ]
        next_cursor = (
            encode_cursor(
                "subscription-totals", fingerprint, [currencies[-1].code], self.cursor_secret
            )
            if more
            else None
        )
        return schema.SubscriptionTotalPage(items=items, next_cursor=next_cursor)
