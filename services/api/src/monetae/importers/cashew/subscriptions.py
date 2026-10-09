"""Importación por inserción de calendarios Cashew e historial de sus cobros."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
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
from monetae.importers.cashew.mapping import TransactionPlan, external_id, map_transaction
from monetae.importers.cashew.reader import TransactionRow
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


def _materialize(context: ImportContext, rule: RecurringRule, rate_source: str) -> bool:
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
            fx_rate_source=rate_source,
            source="import",
            categorization_source="manual" if rule.category_id else None,
            recurring_rule_id=rule.id,
            import_external_id=rule.import_external_id + ":scheduled"
            if rule.import_external_id
            else None,
        )
        context.session.add(scheduled)
        context.report.entity("transactions").created += 1
        if rate_source != "manual":
            context.report.provisional_fx += 1
        return True
    return False


def _fallback(
    context: ImportContext,
    series_id: str,
    rows: list[TransactionRow],
    mapped: dict[str, TransactionPlan],
    kind: str,
) -> int:
    context.report.review_items.append(
        ReviewItem(kind=kind, payload={"series_id": series_id, "rows": len(rows)})
    )
    for transaction in mapped.values():
        context.insert_transaction(transaction)
    return len(mapped)


def _insert_rule(
    context: ImportContext,
    series_id: str,
    template: TransactionPlan,
    calendar: Calendar,
    end_on: date | None,
    ended: bool,
) -> RecurringRule:
    category = context.categories.get(template.category_pk or "")
    rule = RecurringRule(
        user_id=context.user_id,
        import_external_id=external_id(series_id),
        account_id=context.accounts[template.source.wallet_pk].id,
        kind=template.kind,
        amount=template.amount,
        currency=template.currency,
        category_id=category.id if category else None,
        title=template.source.name,
        note=template.source.note,
        period=calendar.period.value,
        interval_count=calendar.interval_count,
        anchor_on=calendar.anchor_on,
        next_run_on=calendar.next_due_on,
        end_on=end_on,
        active=not ended,
        fx_rate_to_base=template.fx_rate_to_base,
    )
    context.session.add(rule)
    context.session.flush()
    context.report.entity("recurring_rules").created += 1
    return rule


def _insert_occurrences(
    context: ImportContext,
    rule: RecurringRule,
    rows: list[TransactionRow],
    mapped: dict[str, TransactionPlan],
    pending: TransactionRow | None,
    ended: bool,
    series_id: str,
) -> tuple[int, int, int]:
    historical, scheduled, created = 0, 0, 0
    for source in rows:
        plan = mapped.get(source.pk)
        if plan is None:
            continue
        if not source.paid and ended:
            context.skipped_pks.add(source.pk)
            context.report.entity("transactions").skipped += 1
            context.report.review_items.append(
                ReviewItem(
                    kind="ended_series_pending_occurrence",
                    payload={
                        "series_id": series_id,
                        "transaction_pk": source.pk,
                        "due_on": source.occurred_at.astimezone(LIMA).date().isoformat(),
                    },
                )
            )
            continue
        linked = source.paid or (pending is not None and source.pk == pending.pk and rule.active)
        if not source.paid and pending is not None and source.pk == pending.pk:
            due_at = datetime.combine(source.occurred_at.astimezone(LIMA).date(), time.min, LIMA)
            plan = replace(plan, source=replace(source, occurred_at=due_at.astimezone(UTC)))
        existing = context.session.scalar(
            select(Transaction.id).where(
                Transaction.user_id == context.user_id,
                Transaction.import_external_id == external_id(source.pk),
            )
        )
        transaction = context.insert_transaction(plan)
        if existing is None and linked:
            transaction.recurring_rule_id = rule.id
        historical += int(source.paid)
        scheduled += int(not source.paid)
        created += int(not source.paid and existing is None)
    context.session.flush()
    return historical, scheduled, created


def run(context: ImportContext, *, clock: Clock | None = None) -> dict[str, JsonValue]:
    today = (clock or SystemClock()).now().astimezone(LIMA).date()
    base = context.session.scalar(select(User.base_currency).where(User.id == context.user_id))
    assert base is not None
    accounts = {account.source.pk: account for account in context.plan.accounts}
    totals = dict.fromkeys(
        (
            "subscriptions_created",
            "recurring_rules_created",
            "already_imported",
            "archived",
            "skipped",
            "unsupported_recurrence",
            "scheduled_created",
            "series",
            "rows_total",
            "historical_posted",
            "pending_scheduled",
            "ordinary_fallback",
        ),
        0,
    )
    series: dict[str, list[TransactionRow]] = {}
    for row in context.plan.deferred_recurring:
        series.setdefault(row.pk.split("::predict::")[0], []).append(row)
    totals["series"] = len(series)
    totals["rows_total"] = len(context.plan.deferred_recurring)
    assumed = 0
    context.report.entity("subscriptions")
    context.report.entity("recurring_rules")
    for series_id, rows in series.items():
        rows.sort(key=lambda row: (row.occurred_at, row.pk))
        source = rows[-1]
        mapped: dict[str, TransactionPlan] = {}
        for row in rows:
            if row.amount == 0:
                context.report.entity("transactions").skipped += 1
                context.skipped_pks.add(row.pk)
                totals["skipped"] += 1
                context.report.review_items.append(
                    ReviewItem(
                        kind="zero_amount_transaction",
                        payload={"transaction_pk": row.pk},
                    )
                )
            else:
                mapped[row.pk] = map_transaction(row, accounts[row.wallet_pk], base)
        if not mapped:
            continue
        period = PERIODS.get(source.reoccurrence or 0)
        interval = source.period_length
        if period is None or interval is None or not 1 <= interval <= 366:
            totals["ordinary_fallback"] += _fallback(
                context, series_id, rows, mapped, "unsupported_recurrence"
            )
            totals["unsupported_recurrence"] += 1
            totals["skipped"] += 1
            continue
        template = mapped.get(source.pk)
        if template is None or not source.name.strip() or (source.type == 1 and source.amount > 0):
            totals["ordinary_fallback"] += _fallback(
                context, series_id, rows, mapped, "invalid_recurring_transaction"
            )
            totals["skipped"] += 1
            continue
        pending_rows = [r for r in rows if not r.paid and r.pk in mapped]
        pending = pending_rows[0] if pending_rows else None
        anchor = rows[0].occurred_at.astimezone(LIMA).date()
        try:
            calendar = Calendar(
                source.name,
                Money(abs(template.amount), Currency(template.currency)),
                period,
                interval,
                anchor,
                anchor,
            )
            due = (
                pending.occurred_at.astimezone(LIMA).date()
                if pending
                else next_after(calendar, today - timedelta(days=1))
            )
            calendar = replace(calendar, next_due_on=due)
        except DomainError:
            totals["ordinary_fallback"] += _fallback(
                context, series_id, rows, mapped, "invalid_recurring_transaction"
            )
            totals["skipped"] += 1
            continue
        assumed += 1
        if len(pending_rows) > 1:
            context.report.review_items.append(
                ReviewItem(
                    kind="multiple_pending_occurrences",
                    payload={"series_id": series_id, "count": len(pending_rows)},
                )
            )
        rule = context.session.scalar(
            select(RecurringRule).where(
                RecurringRule.user_id == context.user_id,
                RecurringRule.import_external_id == external_id(series_id),
            )
        )
        end_on = source.end_date.astimezone(LIMA).date() if source.end_date else None
        ended = end_on is not None and end_on < today
        new_rule = rule is None
        if rule is None:
            # No modificar una transacción que ya se importó como ordinaria.
            prior = context.session.scalar(
                select(Transaction.id).where(
                    Transaction.user_id == context.user_id,
                    Transaction.import_external_id.in_([external_id(pk) for pk in mapped]),
                )
            )
            if prior is not None:
                totals["ordinary_fallback"] += _fallback(
                    context, series_id, rows, mapped, "recurrence_already_imported"
                )
                totals["skipped"] += 1
                continue
            rule = _insert_rule(context, series_id, template, calendar, end_on, ended)
            totals["recurring_rules_created"] += 1
            totals["archived"] += int(ended)
            if source.type == 1:
                if ended:
                    assert source.end_date is not None
                    calendar = archive(calendar, source.end_date, "Terminada en Cashew")
                _insert_subscription(context, calendar, rule)
                totals["subscriptions_created"] += 1
        else:
            context.report.entity("recurring_rules").already_imported += 1
            if rule.subscription_id is not None:
                context.report.entity("subscriptions").already_imported += 1
            totals["already_imported"] += 1
        historical, scheduled, created = _insert_occurrences(
            context, rule, rows, mapped, pending, ended, series_id
        )
        totals["skipped"] += len(pending_rows) if ended else 0
        totals["scheduled_created"] += created
        totals["historical_posted"] += historical
        totals["pending_scheduled"] += scheduled
        if pending is None and new_rule and _materialize(context, rule, template.fx_rate_source):
            totals["scheduled_created"] += 1
            totals["pending_scheduled"] += 1
        context.session.flush()
    if assumed:
        context.report.warnings.append(f"recurrence_anchor_assumed:{assumed}")
    return {name: total for name, total in totals.items()}
