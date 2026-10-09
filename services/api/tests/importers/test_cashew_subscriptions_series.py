"""Series Cashew reales en estructura, con filas exclusivamente sintéticas."""

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae.db.models import RecurringRule, Subscription, Transaction, User
from monetae.importers.cashew import subscriptions
from monetae.importers.cashew.mapping import ImportOptions, external_id
from monetae.importers.cashew.reader import read_snapshot
from monetae.importers.cashew.runner import run_import
from monetae.services.subscriptions import SubscriptionService

from .test_cashew_subscriptions_import import ImportClock, all_rows
from .test_runner import ROW_MAP

ROOT = ROW_MAP["G_subscription"]


@pytest.fixture
def import_clock(monkeypatch: pytest.MonkeyPatch) -> ImportClock:
    clock = ImportClock(datetime(2026, 10, 8, 12, tzinfo=UTC))
    monkeypatch.setattr(subscriptions, "SystemClock", lambda: clock)
    return clock


def write_series(
    path: Path,
    *,
    root: str = ROOT,
    paid: tuple[bool, ...] = (True, True, True, False),
    amounts: tuple[str, ...] = ("-10", "-20", "-30", "-40"),
    changes: Mapping[str, object] | None = None,
) -> list[str]:
    identities = []
    with sqlite3.connect(path) as db:
        columns = [str(c[1]) for c in db.execute("PRAGMA table_info(transactions)")]
        original = db.execute(
            "SELECT * FROM transactions WHERE transaction_pk = ?", (ROOT,)
        ).fetchone()
        assert original is not None
        # SQLite es el borde dinámico de este generador sintético; sus valores quedan como object.
        template = dict(zip(columns, cast(tuple[object, ...], original), strict=True))
        for index, (is_paid, amount) in enumerate(zip(paid, amounts, strict=True)):
            pk = root if index == 0 else f"{root}::predict::{index}"
            identities.append(pk)
            values = {
                **template,
                "transaction_pk": pk,
                "amount": amount,
                "income": int(Decimal(amount) > 0),
                "paid": int(is_paid),
                "date_created": int(datetime(2026, index + 1, 8, 15, tzinfo=UTC).timestamp()),
                **(changes or {}),
            }
            if root == ROOT and index == 0:
                db.execute("DELETE FROM transactions WHERE transaction_pk = ?", (ROOT,))
            names = ",".join(f'"{column}"' for column in columns)
            placeholders = ",".join("?" for _ in columns)
            db.execute(
                f"INSERT INTO transactions ({names}) VALUES ({placeholders})",
                tuple(values[c] for c in columns),
            )
    return identities


def series_rows(session: Session, user: User, identities: list[str]) -> list[Transaction]:
    return list(
        session.scalars(
            select(Transaction)
            .where(
                Transaction.user_id == user.id,
                Transaction.import_external_id.in_([external_id(pk) for pk in identities]),
            )
            .order_by(Transaction.occurred_at)
        )
    )


def test_four_occurrences_preserve_history_and_use_pending_template(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    source_path: Path,
    import_clock: ImportClock,
) -> None:
    identities = write_series(source_path)
    snapshot = read_snapshot(source_path)
    report = run_import(db_session, import_user.id, snapshot, options)
    assert report.exit_code == 0 and all(b.unexplained == Decimal("0.00") for b in report.balances)
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == import_user.id))
    assert sub is not None and sub.import_external_id == external_id(ROOT)
    assert sub.amount == Decimal("40") and sub.anchor_on.isoformat() == "2026-01-08"
    assert sub.next_due_on.isoformat() == "2026-04-08"  # pendiente vencida, no saltar hasta hoy
    rule = db_session.get(RecurringRule, sub.recurring_rule_id)
    assert rule is not None and rule.amount == Decimal("-40")
    assert rule.next_run_on == sub.next_due_on and rule.import_external_id == external_id(ROOT)
    rows = series_rows(db_session, import_user, identities)
    assert [r.amount for r in rows] == [
        Decimal("-10"),
        Decimal("-20"),
        Decimal("-30"),
        Decimal("-40"),
    ]
    assert [r.status for r in rows] == ["posted", "posted", "posted", "scheduled"]
    assert all(r.recurring_rule_id == rule.id for r in rows)
    assert rows[-1].occurred_at == datetime(2026, 4, 8, 5, tzinfo=UTC)
    representation = SubscriptionService(db_session, "synthetic", import_clock).representation(sub)
    assert representation.last_paid_on is not None
    assert (
        representation.historical_paid == "60.00"
        and representation.last_paid_on.isoformat() == "2026-03-08"
    )
    assert report.steps["subscriptions"]["series"] == 2
    assert report.steps["subscriptions"]["rows_total"] == 5
    assert report.steps["subscriptions"]["historical_posted"] == 4
    assert report.steps["subscriptions"]["pending_scheduled"] == 2
    assert report.warnings.count("recurrence_anchor_assumed:2") == 1
    before = all_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, snapshot, options)
    assert all(c.created == 0 for c in second.counts.values())
    assert all_rows(db_session, import_user) == before


@pytest.mark.parametrize("ended", [False, True])
def test_paid_history_without_pending(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    source_path: Path,
    import_clock: ImportClock,
    ended: bool,
) -> None:
    changes = {"end_date": int(datetime(2026, 5, 1, 5, tzinfo=UTC).timestamp())} if ended else {}
    identities = write_series(
        source_path, paid=(True, True, True), amounts=("-10", "-20", "-30"), changes=changes
    )
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.exit_code == 0
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == import_user.id))
    assert sub is not None and sub.status == ("archived" if ended else "active")
    rows = list(
        db_session.scalars(
            select(Transaction).where(
                Transaction.user_id == import_user.id,
                Transaction.recurring_rule_id == sub.recurring_rule_id,
            )
        )
    )
    assert sum(r.status == "posted" for r in rows) == len(identities)
    scheduled = [r for r in rows if r.status == "scheduled"]
    assert len(scheduled) == int(not ended)
    if scheduled:
        assert scheduled[0].import_external_id == external_id(ROOT) + ":scheduled"
        assert scheduled[0].occurred_at == datetime(2026, 10, 8, 5, tzinfo=UTC)
    else:
        assert sub.archive_reason == "Terminada en Cashew"


@pytest.mark.parametrize("source_type", [1, 2])
def test_pending_only_is_valid(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    source_path: Path,
    import_clock: ImportClock,
    source_type: int,
) -> None:
    identities = write_series(
        source_path,
        paid=(False,),
        amounts=("-10" if source_type == 1 else "2500",),
        changes={"type": source_type},
    )
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.exit_code == 0
    rows = series_rows(db_session, import_user, identities)
    assert (
        len(rows) == 1 and rows[0].status == "scheduled" and rows[0].recurring_rule_id is not None
    )
    assert rows[0].occurred_at == datetime(2026, 1, 8, 5, tzinfo=UTC)
    assert report.counts["subscriptions"].created == int(source_type == 1)
    assert report.counts["recurring_rules"].created == 2


@pytest.mark.parametrize("source_type", [1, 2])
def test_history_and_distinct_series_with_same_title(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    source_path: Path,
    import_clock: ImportClock,
    source_type: int,
) -> None:
    sign = "-" if source_type == 1 else ""
    first = write_series(
        source_path,
        paid=(True, False),
        amounts=(sign + "100", sign + "200"),
        changes={"type": source_type},
    )
    second = write_series(
        source_path,
        root="synthetic-other-series",
        paid=(True, False),
        amounts=(sign + "300", sign + "400"),
        changes={"type": source_type},
    )
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.exit_code == 0 and report.counts["subscriptions"].created == (
        2 if source_type == 1 else 0
    )
    rules = list(
        db_session.scalars(
            select(RecurringRule).where(
                RecurringRule.user_id == import_user.id,
                RecurringRule.import_external_id.in_(
                    [external_id(ROOT), external_id("synthetic-other-series")]
                ),
            )
        )
    )
    assert len(rules) == 2 and rules[0].title == rules[1].title
    assert {r.amount for r in rules} == {Decimal(sign + "200"), Decimal(sign + "400")}
    kind = "expense" if source_type == 1 else "income"
    assert all(r.kind == kind for r in rules)
    assert all(
        r.status == "posted" and r.kind == kind
        for r in (
            series_rows(db_session, import_user, first)[0],
            series_rows(db_session, import_user, second)[0],
        )
    )


def test_multiple_pending_occurrences(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    source_path: Path,
    import_clock: ImportClock,
) -> None:
    identities = write_series(source_path, paid=(True, False, False), amounts=("-10", "-20", "-30"))
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    rows = series_rows(db_session, import_user, identities)
    assert report.exit_code == 0
    assert rows[0].recurring_rule_id == rows[1].recurring_rule_id
    assert rows[1].status == rows[2].status == "scheduled" and rows[2].recurring_rule_id is None
    review = next(r for r in report.review_items if r.kind == "multiple_pending_occurrences")
    assert review.payload == {"series_id": ROOT, "count": 2}


@pytest.mark.parametrize(
    "changes,kind",
    [
        ({"reoccurrence": 0}, "unsupported_recurrence"),
        ({"period_length": 400}, "unsupported_recurrence"),
        ({"name": " "}, "invalid_recurring_transaction"),
        ({"amount": "10", "income": 1}, "invalid_recurring_transaction"),
    ],
)
def test_invalid_series_preserves_all_ordinary_money(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    source_path: Path,
    import_clock: ImportClock,
    changes: dict[str, object],
    kind: str,
) -> None:
    identities = write_series(source_path, changes=changes)
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.exit_code == 0 and all(b.unexplained == Decimal("0.00") for b in report.balances)
    rows = series_rows(db_session, import_user, identities)
    assert len(rows) == 4 and all(r.recurring_rule_id is None for r in rows)
    assert [r.status for r in rows] == ["posted", "posted", "posted", "scheduled"]
    reviews = [r for r in report.review_items if r.kind == kind]
    assert len(reviews) == 1 and reviews[0].payload == {"series_id": ROOT, "rows": 4}
    assert report.steps["subscriptions"]["ordinary_fallback"] == 4
    before = all_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert all(c.created == 0 for c in second.counts.values())
    assert all_rows(db_session, import_user) == before


def test_ended_series_pending_is_skipped_without_orphan_schedule(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    source_path: Path,
    import_clock: ImportClock,
) -> None:
    identities = write_series(
        source_path, changes={"end_date": int(datetime(2026, 5, 1, tzinfo=UTC).timestamp())}
    )
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.exit_code == 0
    rows = series_rows(db_session, import_user, identities)
    assert len(rows) == 3 and all(r.status == "posted" for r in rows)
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == import_user.id))
    assert sub is not None and sub.status == "archived"
    review = next(r for r in report.review_items if r.kind == "ended_series_pending_occurrence")
    assert review.payload == {
        "series_id": ROOT,
        "transaction_pk": identities[-1],
        "due_on": "2026-04-08",
    }
    assert report.counts["transactions"].skipped == 1


@pytest.mark.parametrize("pending", [False, True])
def test_provisional_fx_includes_pending_and_generated_schedule(
    db_session: Session,
    import_user: User,
    source_path: Path,
    import_clock: ImportClock,
    pending: bool,
) -> None:
    with sqlite3.connect(source_path) as db:
        usd_pk = db.execute("SELECT wallet_pk FROM wallets WHERE currency = 'USD'").fetchone()[0]
        db.execute(
            "UPDATE app_settings SET settings_j_s_o_n = ?",
            (json.dumps({"customCurrencyAmounts": {"pen": "3.8", "usd": "1"}}),),
        )
    identities = write_series(
        source_path,
        paid=(True, False) if pending else (True,),
        amounts=("-10", "-20") if pending else ("-10",),
        changes={"wallet_fk": usd_pk},
    )
    report = run_import(db_session, import_user.id, read_snapshot(source_path), ImportOptions())
    assert report.exit_code == 0
    assert report.provisional_fx == sum(
        r.fx_rate_source == "auto"
        for r in db_session.scalars(
            select(Transaction).where(Transaction.user_id == import_user.id)
        )
    )
    rule = db_session.scalar(
        select(RecurringRule).where(
            RecurringRule.user_id == import_user.id,
            RecurringRule.import_external_id == external_id(ROOT),
        )
    )
    assert rule is not None
    rows = list(
        db_session.scalars(
            select(Transaction).where(
                Transaction.user_id == import_user.id,
                Transaction.recurring_rule_id == rule.id,
            )
        )
    )
    assert len(rows) == 2 and all(r.fx_rate_source == "auto" for r in rows)
    assert rows[-1].fx_rate_to_base == Decimal("3.800000")
    assert identities


@pytest.mark.parametrize("ended", [False, True])
def test_skipped_occurrence_tags_are_not_deferred(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    source_path: Path,
    import_clock: ImportClock,
    ended: bool,
) -> None:
    changes: dict[str, object] = (
        {"end_date": int(datetime(2026, 5, 1, tzinfo=UTC).timestamp())} if ended else {}
    )
    identities = write_series(source_path, changes=changes)
    skipped_pk = identities[-1] if ended else identities[0]
    with sqlite3.connect(source_path) as db:
        db.execute(
            "UPDATE transaction_to_tag_links SET transaction_pk = ? WHERE transaction_pk = ?",
            (skipped_pk, ROOT),
        )
        if not ended:
            db.execute("UPDATE transactions SET amount = 0 WHERE transaction_pk = ?", (skipped_pk,))
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.exit_code == 0
    assert report.counts["transaction_tags"].skipped == 1
    assert report.counts["transaction_tags"].deferred == 0
    assert report.counts["transaction_tags"].created == 2
    assert report.counts["transactions"].skipped == 1


def test_latest_template_fields_and_first_anchor(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    source_path: Path,
    import_clock: ImportClock,
) -> None:
    identities = write_series(source_path)
    with sqlite3.connect(source_path) as db:
        wallet = db.execute("SELECT wallet_pk FROM wallets WHERE name = 'Efectivo'").fetchone()[0]
        db.execute(
            "UPDATE transactions SET wallet_fk = ?, name = ?, note = ?, reoccurrence = 2, "
            "period_length = 2, sub_category_fk = NULL WHERE transaction_pk = ?",
            (wallet, "Synthetic changed title", "Synthetic changed note", identities[-1]),
        )
    snapshot = read_snapshot(source_path)
    report = run_import(db_session, import_user.id, snapshot, options)
    assert report.exit_code == 0 and all(b.unexplained == Decimal("0.00") for b in report.balances)
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == import_user.id))
    assert sub is not None and sub.title == "Synthetic changed title"
    assert (
        sub.period == "weekly"
        and sub.interval_count == 2
        and sub.anchor_on.isoformat() == "2026-01-08"
    )
    rule = db_session.get(RecurringRule, sub.recurring_rule_id)
    assert (
        rule is not None
        and rule.note == "Synthetic changed note"
        and rule.account_id == sub.account_id
    )
    rows = series_rows(db_session, import_user, identities)
    assert rows[-1].account_id == rule.account_id and rows[0].account_id != rule.account_id
    assert rows[0].title != rule.title


def test_anchor_and_template_use_dates_instead_of_pk_suffix(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    source_path: Path,
    import_clock: ImportClock,
) -> None:
    identities = write_series(source_path)
    with sqlite3.connect(source_path) as db:
        db.execute(
            "UPDATE transactions SET date_created = ? WHERE transaction_pk = ?",
            (int(datetime(2025, 12, 31, 15, tzinfo=UTC).timestamp()), identities[2]),
        )
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.exit_code == 0
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == import_user.id))
    assert sub is not None and sub.anchor_on.isoformat() == "2025-12-31"
    assert sub.amount == Decimal("40") and sub.next_due_on.isoformat() == "2026-04-08"
