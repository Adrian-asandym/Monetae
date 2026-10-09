"""Importación por inserción de calendarios Cashew e historial de sus cobros."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from pydantic import JsonValue
from sqlalchemy import select

from monetae.db.models import RecurringRule, Subscription, Transaction, User
from monetae.domain.currency import Currency
from monetae.domain.errors import DomainError
from monetae.domain.money import Money
from monetae.domain.subscriptions import Period, archive, next_after
from monetae.domain.subscriptions import Subscription as Calendar
from monetae.importers.cashew.mapping import external_id, map_transaction
from monetae.importers.cashew.report import ReviewItem
from monetae.services.auth import Clock, SystemClock

if TYPE_CHECKING:
    from monetae.importers.cashew.runner import ImportContext

LIMA = ZoneInfo("America/Lima")
PERIODS = {1: Period.DAILY, 2: Period.WEEKLY, 3: Period.MONTHLY, 4: Period.YEARLY}


def _insert_subscription(context: ImportContext, calendar: Calendar, rule: RecurringRule) -> None:
    subscription = Subscription(
        user_id=context.user_id,
        import_external_id=rule.import_external_id,
        title=calendar.title,
        amount=calendar.amount.amount,
        currency=rule.currency,
        account_id=rule.account_id,
        category_id=rule.category_id,
        period=rule.period,
        interval_count=calendar.interval_count,
        anchor_on=calendar.anchor_on,
        next_due_on=calendar.next_due_on,
        status=calendar.status,
        archived_at=calendar.archived_at,
        archive_reason=calendar.archive_reason,
        recurring_rule_id=rule.id,
    )
    context.session.add(subscription)
    context.session.flush()
    rule.subscription_id = subscription.id
    context.report.entity("subscriptions").created += 1


def _materialize(context: ImportContext, rule: RecurringRule) -> bool:
    if rule.active and (rule.end_on is None or rule.next_run_on <= rule.end_on):
        scheduled = Transaction(
            user_id=context.user_id,
            account_id=rule.account_id,
            category_id=rule.category_id,
            kind=rule.kind,
            amount=rule.amount,
            currency=rule.currency,
            occurred_at=datetime.combine(rule.next_run_on, time.min, LIMA).astimezone(UTC),
            status="scheduled",
            title=rule.title,
            note=rule.note,
            fx_rate_to_base=rule.fx_rate_to_base,
            fx_rate_source="manual",
            source="import",
            categorization_source="manual" if rule.category_id else None,
            recurring_rule_id=rule.id,
            import_external_id=rule.import_external_id + ":scheduled"
            if rule.import_external_id
            else None,
        )
        context.session.add(scheduled)
        context.report.entity("transactions").created += 1
        return True
    return False


def run(context: ImportContext, *, clock: Clock | None = None) -> dict[str, JsonValue]:
    today = (clock or SystemClock()).now().astimezone(LIMA).date()
    base = context.session.scalar(select(User.base_currency).where(User.id == context.user_id))
    assert base is not None
    accounts = {account.source.pk: account for account in context.plan.accounts}
    result: dict[str, JsonValue] = {
        "subscriptions_created": 0,
        "recurring_rules_created": 0,
        "already_imported": 0,
        "archived": 0,
        "skipped": 0,
        "unsupported_recurrence": 0,
        "scheduled_created": 0,
    }
    totals = {name: 0 for name in result}
    assumed = 0
    context.report.entity("subscriptions")
    context.report.entity("recurring_rules")
    for source in context.plan.deferred_recurring:
        account = accounts[source.wallet_pk]
        period = PERIODS.get(source.reoccurrence or 0)
        interval = source.period_length
        try:
            mapped = map_transaction(source, account, base)
            if not source.name.strip() or (source.type == 1 and source.amount > 0):
                raise ValueError("Invalid recurring template")
        except (DomainError, ValueError):
            context.report.entity("transactions").skipped += 1
            totals["skipped"] += 1
            context.report.review_items.append(
                ReviewItem(
                    kind="invalid_recurring_transaction", payload={"transaction_pk": source.pk}
                )
            )
            continue
        if period is None or interval is None or not 1 <= interval <= 366:
            context.insert_transaction(mapped)
            totals["unsupported_recurrence"] += 1
            totals["skipped"] += 1
            context.report.review_items.append(
                ReviewItem(kind="unsupported_recurrence", payload={"transaction_pk": source.pk})
            )
            continue
        anchor = source.occurred_at.astimezone(LIMA).date()
        try:
            calendar = Calendar(
                source.name,
                Money(abs(mapped.amount), Currency(mapped.currency)),
                period,
                interval,
                anchor,
                anchor,
            )
            due = next_after(calendar, today - timedelta(days=1))
        except DomainError:
            context.report.entity("transactions").skipped += 1
            totals["skipped"] += 1
            context.report.review_items.append(
                ReviewItem(
                    kind="invalid_recurring_transaction", payload={"transaction_pk": source.pk}
                )
            )
            continue
        assumed += 1
        rule = context.session.scalar(
            select(RecurringRule).where(
                RecurringRule.user_id == context.user_id,
                RecurringRule.import_external_id == external_id(source.pk),
            )
        )
        if rule is not None:
            context.report.entity("recurring_rules").already_imported += 1
            if rule.subscription_id is not None:
                context.report.entity("subscriptions").already_imported += 1
            context.insert_transaction(replace(mapped, status="posted"))
            totals["already_imported"] += 1
            continue
        # Una identidad histórica previa nunca se edita ni se vincula retroactivamente.
        historical = context.session.scalar(
            select(Transaction).where(
                Transaction.user_id == context.user_id,
                Transaction.import_external_id == external_id(source.pk),
            )
        )
        if historical is not None:
            context.insert_transaction(mapped)
            totals["skipped"] += 1
            context.report.review_items.append(
                ReviewItem(
                    kind="recurrence_already_imported", payload={"transaction_pk": source.pk}
                )
            )
            continue
        category = context.categories.get(mapped.category_pk or "")
        end_on = source.end_date.astimezone(LIMA).date() if source.end_date else None
        ended = end_on is not None and end_on < today
        rule = RecurringRule(
            user_id=context.user_id,
            import_external_id=external_id(source.pk),
            account_id=context.accounts[source.wallet_pk].id,
            kind=mapped.kind,
            amount=mapped.amount,
            currency=mapped.currency,
            category_id=category.id if category else None,
            title=source.name,
            note=source.note,
            period=period.value,
            interval_count=interval,
            anchor_on=anchor,
            next_run_on=due,
            end_on=end_on,
            active=not ended,
            fx_rate_to_base=mapped.fx_rate_to_base,
        )
        context.session.add(rule)
        context.session.flush()
        context.report.entity("recurring_rules").created += 1
        totals["recurring_rules_created"] += 1
        if ended:
            totals["archived"] += 1
        if source.type == 1:
            calendar = replace(calendar, next_due_on=due)
            if ended:
                assert source.end_date is not None
                calendar = archive(calendar, source.end_date, "Terminada en Cashew")
            _insert_subscription(context, calendar, rule)
            totals["subscriptions_created"] += 1
        historical = context.insert_transaction(replace(mapped, status="posted"))
        historical.recurring_rule_id = rule.id
        if _materialize(context, rule):
            totals["scheduled_created"] += 1
        context.session.flush()
    if assumed:
        context.report.warnings.append(f"recurrence_anchor_assumed:{assumed}")
    return {name: total for name, total in totals.items()}
