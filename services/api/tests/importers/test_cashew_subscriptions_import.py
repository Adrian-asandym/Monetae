"""Calendarios, historia y aislamiento sobre PostgreSQL y datos sintéticos."""

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae.api.main import create_app
from monetae.api.security import database
from monetae.config import Settings
from monetae.db.models import RecurringRule, Subscription, Transaction, TransactionTag, User
from monetae.importers.cashew import subscriptions
from monetae.importers.cashew.mapping import ImportOptions, external_id
from monetae.importers.cashew.reader import Snapshot
from monetae.importers.cashew.runner import ImportExecutionError, run_import
from monetae.services.auth import AuthService

from .test_runner import ROW_MAP, financial_rows


class ImportClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


@pytest.fixture
def import_clock(monkeypatch: pytest.MonkeyPatch) -> ImportClock:
    clock = ImportClock(datetime(2026, 10, 8, 12, tzinfo=UTC))
    monkeypatch.setattr(subscriptions, "SystemClock", lambda: clock)
    return clock


def all_rows(session: Session, user: User) -> dict[str, list[dict[str, object]]]:
    result = financial_rows(session, user)
    for model in (Subscription, RecurringRule):
        result[model.__tablename__] = [
            {c.name: getattr(row, c.name) for c in model.__table__.columns}
            for row in session.scalars(
                select(model).where(model.user_id == user.id).order_by(model.id)
            )
        ]
    return result


def test_fixture_g_history_schedule_tags_and_idempotence(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    import_clock: ImportClock,
) -> None:
    report = run_import(db_session, import_user.id, snapshot, options)
    assert report.warnings.count("recurrence_anchor_assumed:2") == 1
    rules = list(
        db_session.scalars(select(RecurringRule).where(RecurringRule.user_id == import_user.id))
    )
    assert len(rules) == 2
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == import_user.id))
    assert sub is not None and sub.status == "active" and sub.amount == Decimal("44.90")
    for case, kind, amount in (
        ("G_subscription", "expense", Decimal("-44.90")),
        ("G_repetitive", "income", Decimal("2500.00")),
    ):
        rule = next(r for r in rules if r.import_external_id == external_id(ROW_MAP[case]))
        assert rule.kind == kind and rule.amount == amount and rule.fx_rate_to_base == Decimal(1)
        assert (rule.subscription_id == sub.id) == (case == "G_subscription")
        history = db_session.scalar(
            select(Transaction).where(
                Transaction.user_id == import_user.id,
                Transaction.import_external_id == external_id(ROW_MAP[case]),
            )
        )
        assert history is not None and history.status == "posted" and history.amount == amount
        assert history.recurring_rule_id == rule.id
        source = next(r for r in snapshot.transactions if r.pk == ROW_MAP[case])
        assert history.occurred_at == source.occurred_at and history.note == source.note
        scheduled = list(
            db_session.scalars(
                select(Transaction).where(
                    Transaction.user_id == import_user.id,
                    Transaction.recurring_rule_id == rule.id,
                    Transaction.status == "scheduled",
                    Transaction.deleted_at.is_(None),
                )
            )
        )
        assert len(scheduled) == 1 and scheduled[0].occurred_at.hour == 5
        assert scheduled[0].amount == amount and scheduled[0].fx_rate_source == "manual"
        assert scheduled[0].occurred_at.date() >= import_clock.value.date()
        tags = set(
            db_session.scalars(
                select(TransactionTag.tag_id).where(
                    TransactionTag.user_id == import_user.id,
                    TransactionTag.transaction_id == history.id,
                )
            )
        )
        assert len(tags) == (1 if case == "G_subscription" else 2)
    sub.title = "Synthetic manual edit"
    rules[0].note = "Synthetic edited rule"
    db_session.flush()
    before = all_rows(db_session, import_user)
    import_clock.value = datetime(2027, 12, 1, tzinfo=UTC)
    second = run_import(db_session, import_user.id, snapshot, options)
    assert all(c.created == 0 for c in second.counts.values())
    assert second.steps["subscriptions"]["already_imported"] == 2
    assert all_rows(db_session, import_user) == before


@pytest.mark.parametrize(
    "anchor,today,period,interval,expected",
    [
        (date(2026, 1, 31), date(2026, 2, 1), 3, 1, date(2026, 2, 28)),
        (date(2026, 1, 31), date(2026, 3, 1), 3, 1, date(2026, 3, 31)),
        (date(2024, 2, 29), date(2025, 2, 1), 4, 1, date(2025, 2, 28)),
        (date(2024, 2, 29), date(2028, 2, 1), 4, 1, date(2028, 2, 29)),
        (date(2026, 1, 31), date(2026, 2, 1), 3, 2, date(2026, 3, 31)),
        (date(2026, 1, 1), date(2026, 1, 6), 1, 2, date(2026, 1, 7)),
        (date(2026, 1, 1), date(2026, 1, 16), 2, 2, date(2026, 1, 29)),
        (date(2024, 2, 29), date(2025, 3, 1), 4, 2, date(2026, 2, 28)),
        (date(2026, 1, 31), date(2026, 3, 31), 3, 1, date(2026, 3, 31)),
        (date(2026, 1, 1), date(2026, 1, 1), 1, 1, date(2026, 1, 1)),
        (date(2026, 1, 20), date(2026, 1, 1), 2, 1, date(2026, 1, 20)),
    ],
)
def test_calendar_injected_clock(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    import_clock: ImportClock,
    anchor: date,
    today: date,
    period: int,
    interval: int,
    expected: date,
) -> None:
    source = next(r for r in snapshot.transactions if r.pk == ROW_MAP["G_subscription"])
    source = replace(
        source,
        occurred_at=datetime(anchor.year, anchor.month, anchor.day, 5, tzinfo=UTC),
        reoccurrence=period,
        period_length=interval,
    )
    # UTC date differs from Lima before 05:00; the injected instant is still 'today' in Lima.
    import_clock.value = datetime(today.year, today.month, today.day, 5, tzinfo=UTC)
    report = run_import(
        db_session, import_user.id, replace(snapshot, transactions=(source,)), options
    )
    assert report.exit_code == 0
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == import_user.id))
    assert sub is not None and sub.anchor_on == anchor and sub.next_due_on == expected
    scheduled = db_session.scalar(
        select(Transaction).where(
            Transaction.user_id == import_user.id,
            Transaction.status == "scheduled",
        )
    )
    assert scheduled is not None and scheduled.occurred_at == datetime.combine(
        expected, datetime.min.time(), subscriptions.LIMA
    ).astimezone(UTC)
    assert expected >= today


@pytest.mark.parametrize("source_type", [1, 2])
@pytest.mark.parametrize("end", ["past", "today", "before_next"])
def test_end_date(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    import_clock: ImportClock,
    source_type: int,
    end: str,
) -> None:
    source = next(r for r in snapshot.transactions if r.pk == ROW_MAP["G_subscription"])
    ended = datetime(2026, 10, 7 if end == "past" else 8, 5, tzinfo=UTC)
    anchor = datetime(2026, 1, 8 if end == "today" else 9, 5, tzinfo=UTC)
    source = replace(source, type=source_type, end_date=ended, occurred_at=anchor)
    run_import(db_session, import_user.id, replace(snapshot, transactions=(source,)), options)
    rule = db_session.scalar(select(RecurringRule).where(RecurringRule.user_id == import_user.id))
    assert rule is not None and rule.active == (end != "past")
    rows = list(
        db_session.scalars(select(Transaction).where(Transaction.user_id == import_user.id))
    )
    assert sum(r.status == "posted" for r in rows) == 1
    assert sum(r.status == "scheduled" for r in rows) == int(end == "today")
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == import_user.id))
    if source_type == 1:
        assert sub is not None and sub.status == ("archived" if end == "past" else "active")
        if end == "past":
            assert sub.archived_at == ended and sub.archive_reason == "Terminada en Cashew"
    else:
        assert sub is None


@pytest.mark.parametrize(
    "period,interval", [(0, 1), (None, 1), (5, 1), (3, 0), (3, 367), (3, None)]
)
def test_unsupported_becomes_ordinary(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    import_clock: ImportClock,
    period: int | None,
    interval: int | None,
) -> None:
    source = next(r for r in snapshot.transactions if r.pk == ROW_MAP["G_subscription"])
    source = replace(source, reoccurrence=period, period_length=interval)
    report = run_import(
        db_session, import_user.id, replace(snapshot, transactions=(source,)), options
    )
    assert report.steps["subscriptions"]["unsupported_recurrence"] == 1
    assert report.review_items[-1].kind == "unsupported_recurrence"
    assert report.exit_code == 0
    assert not list(
        db_session.scalars(select(RecurringRule).where(RecurringRule.user_id == import_user.id))
    )
    history = db_session.scalar(select(Transaction).where(Transaction.user_id == import_user.id))
    assert history is not None and history.status == "posted" and history.recurring_rule_id is None
    assert report.counts["transaction_tags"].created == 1


@pytest.mark.parametrize("rate_source", ["manual", "settings", "missing"])
def test_foreign_template_rates(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    import_clock: ImportClock,
    rate_source: str,
) -> None:
    source = next(r for r in snapshot.transactions if r.pk == ROW_MAP["G_subscription"])
    usd = next(w for w in snapshot.wallets if w.currency == "USD")
    source = replace(source, wallet_pk=usd.pk)
    snapshot = replace(
        snapshot,
        transactions=(source,),
        settings_json=('{"customCurrencyAmounts": {"pen": "3.8", "usd": "1"}}',)
        if rate_source == "settings"
        else (),
    )
    options = ImportOptions(
        fx_rate_overrides={"USD": Decimal("3.9")} if rate_source == "manual" else {}
    )
    if rate_source == "missing":
        with pytest.raises(ImportExecutionError, match="Falta tasa"):
            run_import(db_session, import_user.id, snapshot, options)
        assert all(not rows for rows in all_rows(db_session, import_user).values())
        return
    report = run_import(db_session, import_user.id, snapshot, options)
    rule = db_session.scalar(select(RecurringRule).where(RecurringRule.user_id == import_user.id))
    assert rule is not None and rule.fx_rate_to_base == Decimal(
        "3.9" if rate_source == "manual" else "3.8"
    )
    rows = list(
        db_session.scalars(select(Transaction).where(Transaction.user_id == import_user.id))
    )
    assert len(rows) == 2 and all(r.fx_rate_to_base == rule.fx_rate_to_base for r in rows)
    assert report.provisional_fx == int(rate_source == "settings")


def test_dry_run_and_two_users(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    import_clock: ImportClock,
) -> None:
    before = all_rows(db_session, import_user)
    dry = run_import(db_session, import_user.id, snapshot, replace(options, dry_run=True))
    assert dry.financial_rolled_back and dry.exit_code == 0
    assert all_rows(db_session, import_user) == before
    other = User(
        email="subscription-other@example.test", base_currency="PEN", report_currency="PEN"
    )
    db_session.add(other)
    db_session.flush()
    first = run_import(db_session, import_user.id, snapshot, options)
    before = all_rows(db_session, import_user)
    second = run_import(db_session, other.id, snapshot, options)
    assert first.counts == second.counts and all_rows(db_session, import_user) == before
    for model in (Subscription, RecurringRule, Transaction):
        first_ids = set(db_session.scalars(select(model.id).where(model.user_id == import_user.id)))
        other_ids = set(db_session.scalars(select(model.id).where(model.user_id == other.id)))
        assert first_ids and other_ids and first_ids.isdisjoint(other_ids)


def test_imported_subscription_archive_reactivate_api(
    db_session: Session,
    snapshot: Snapshot,
    options: ImportOptions,
    import_clock: ImportClock,
) -> None:
    settings = Settings(environment="test", cors_origins=[])
    app = create_app(settings)
    app.state.clock = import_clock
    user = AuthService(db_session, settings, import_clock).create_user(
        "imported-api@example.test",
        "synthetic-password-123",
    )
    run_import(db_session, user.id, snapshot, options)
    db_session.commit()
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == user.id))
    assert sub is not None
    entity_id, rule_id = sub.id, sub.recurring_rule_id

    def override() -> Iterator[Session]:
        yield db_session
        db_session.commit()

    app.dependency_overrides[database] = override
    with TestClient(app, base_url="https://testserver") as client:
        client.get("/api/v1/health")
        headers = {"Origin": "https://testserver", "X-CSRF-Token": client.cookies["monetae_csrf"]}
        response = client.post(
            "/api/v1/auth/login",
            headers=headers,
            json={
                "method": "password",
                "email": user.email,
                "password": "synthetic-password-123",
            },
        )
        assert response.status_code == 200, response.text
        headers["X-CSRF-Token"] = client.cookies["monetae_csrf"]
        path = f"/api/v1/subscriptions/{entity_id}"
        archived = client.post(path + "/archive", json={}, headers=headers)
        assert archived.status_code == 200, archived.text
        assert archived.json()["historical_paid"] == "44.90"
        assert not list(
            db_session.scalars(
                select(Transaction).where(
                    Transaction.recurring_rule_id == rule_id,
                    Transaction.status == "scheduled",
                    Transaction.deleted_at.is_(None),
                )
            )
        )
        assert client.get("/api/v1/subscriptions").json()["items"] == []
        reactivated = client.post(path + "/reactivate", headers=headers)
        assert reactivated.status_code == 200, reactivated.text
        assert reactivated.json()["historical_paid"] == "44.90"
        assert (
            len(
                list(
                    db_session.scalars(
                        select(Transaction).where(
                            Transaction.recurring_rule_id == rule_id,
                            Transaction.status == "scheduled",
                            Transaction.deleted_at.is_(None),
                        )
                    )
                )
            )
            == 1
        )


def test_failure_after_subscriptions_is_atomic(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    import_clock: ImportClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import JsonValue

    from monetae.importers.cashew.runner import ImportContext

    original = subscriptions.run

    def fail(context: ImportContext) -> dict[str, JsonValue]:
        original(context, clock=import_clock)
        assert context.report.counts["subscriptions"].created == 1
        assert context.report.counts["recurring_rules"].created == 2
        assert context.report.counts["transactions"].created == 10
        raise RuntimeError("SYNTHETIC_PRIVATE_DETAIL")

    monkeypatch.setattr(subscriptions, "run", fail)
    before = all_rows(db_session, import_user)
    with pytest.raises(ImportExecutionError) as caught:
        run_import(db_session, import_user.id, snapshot, options)
    assert all_rows(db_session, import_user) == before
    assert caught.value.report.outcome == "failed"
    assert "SYNTHETIC_PRIVATE_DETAIL" not in caught.value.report.model_dump_json()
    assert all(c.created == 0 for c in caught.value.report.counts.values())


@pytest.mark.parametrize("anomaly", ["zero", "empty_title", "positive_subscription"])
def test_invalid_recurring_row_does_not_abort_other_templates(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    import_clock: ImportClock,
    anomaly: str,
) -> None:
    sub = next(r for r in snapshot.transactions if r.pk == ROW_MAP["G_subscription"])
    other = next(r for r in snapshot.transactions if r.pk == ROW_MAP["G_repetitive"])
    if anomaly == "zero":
        sub = replace(sub, amount=Decimal("0.00"))
    elif anomaly == "empty_title":
        sub = replace(sub, name=" ")
    else:
        sub = replace(sub, amount=abs(sub.amount), income=True)
    report = run_import(
        db_session,
        import_user.id,
        replace(snapshot, transactions=(sub, other)),
        options,
        allow_balance_diff=True,
    )
    assert report.review_items[-1].kind == "invalid_recurring_transaction"
    assert report.steps["subscriptions"]["skipped"] == 1
    assert report.counts["transactions"].skipped == 1
    assert report.counts["recurring_rules"].created == 1
    assert report.counts["subscriptions"].created == 0
    assert (
        len(
            list(
                db_session.scalars(
                    select(RecurringRule).where(
                        RecurringRule.user_id == import_user.id,
                    )
                )
            )
        )
        == 1
    )


def test_clock_uses_lima_date_before_utc_midnight_boundary(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    import_clock: ImportClock,
) -> None:
    source = next(r for r in snapshot.transactions if r.pk == ROW_MAP["G_subscription"])
    source = replace(source, occurred_at=datetime(2026, 1, 8, 5, tzinfo=UTC))
    import_clock.value = datetime(2026, 10, 9, 2, tzinfo=UTC)  # Lima sigue en 8 de octubre.
    run_import(db_session, import_user.id, replace(snapshot, transactions=(source,)), options)
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == import_user.id))
    assert sub is not None and sub.next_due_on == date(2026, 10, 8)


def test_deleted_rules_and_subscriptions_are_never_recreated(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    import_clock: ImportClock,
) -> None:
    run_import(db_session, import_user.id, snapshot, options)
    for model in (Subscription, RecurringRule, Transaction):
        for row in db_session.scalars(select(model).where(model.user_id == import_user.id)):
            row.deleted_at = import_clock.now()
    db_session.flush()
    before = all_rows(db_session, import_user)
    report = run_import(db_session, import_user.id, snapshot, options, allow_balance_diff=True)
    assert all(c.created == 0 for c in report.counts.values())
    assert all_rows(db_session, import_user) == before
