import hashlib
import json
import shutil
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from pydantic import JsonValue, TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from monetae.db.models import (
    Account,
    Category,
    ImportReviewItem,
    ImportRun,
    Tag,
    Transaction,
    TransactionTag,
    User,
)
from monetae.importers.cashew import subscriptions
from monetae.importers.cashew.mapping import ImportOptions, external_id, transaction_tag_map
from monetae.importers.cashew.reader import Snapshot, read_snapshot
from monetae.importers.cashew.runner import ImportContext, ImportExecutionError, run_import

from .conftest import FIXTURES

EXPECTED = TypeAdapter(dict[str, JsonValue]).validate_json(
    (FIXTURES / "expected.json").read_bytes()
)
ROW_MAP = cast(dict[str, str], EXPECTED["row_map"])


def financial_rows(session: Session, user: User) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    for model in (Account, Category, Tag, Transaction, TransactionTag):
        rows = session.scalars(select(model).where(model.user_id == user.id).order_by(model.id))
        result[model.__tablename__] = [
            {column.name: getattr(row, column.name) for column in model.__table__.columns}
            for row in rows
        ]
    return result


def test_v48_expected_core(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    source_path: Path,
) -> None:
    before = hashlib.sha256(source_path.read_bytes()).hexdigest()
    report = run_import(db_session, import_user.id, snapshot, options)
    assert report.tables == EXPECTED["table_counts_v48"]
    assert report.counts["accounts"].created == 4
    assert report.counts["categories"].created == 7
    assert report.counts["tags"].created == 3
    assert report.counts["transactions"].created == 30
    assert report.counts["transfers"].created == 1
    assert report.steps["loans"]["deferred"] == 0
    assert report.steps["loans"]["processed_transactions"] == 17
    assert report.steps["loans"]["created"] == 7
    assert report.counts["recurring_rules"].created == 2
    assert report.counts["subscriptions"].created == 1
    assert report.counts["transaction_tags"].deferred == 0
    assert report.counts["transaction_tags"].created == 3
    assert report.steps["subscriptions"]["scheduled_created"] == 2
    accounts = {
        a.import_external_id: a
        for a in db_session.scalars(select(Account).where(Account.user_id == import_user.id))
    }
    wallets = cast(list[dict[str, JsonValue]], EXPECTED["wallets"])
    for expected in wallets:
        pk = cast(str, expected["wallet_pk"])
        account = accounts[external_id(pk)]
        assert account.currency == expected["currency"]
        assert account.initial_balance == Decimal("0.00")
        assert account.type == "other"
        assert (account.archived_at is not None) == bool(expected["archived_v48"])
        balance = next(b for b in report.balances if b.source_wallet_pk == pk)
        assert balance.cashew_balance == Decimal(cast(str, expected["balance"]))
        assert balance.unexplained == Decimal("0.00")
    categories = {
        c.import_external_id: c
        for c in db_session.scalars(select(Category).where(Category.user_id == import_user.id))
    }
    for source in snapshot.categories:
        row = categories[external_id(source.pk)]
        assert row.parent_id == (
            categories[external_id(source.parent_pk)].id if source.parent_pk else None
        )
        assert not row.is_system
    transactions = {
        t.import_external_id: t
        for t in db_session.scalars(
            select(Transaction).where(Transaction.user_id == import_user.id)
        )
    }
    future = transactions[external_id(ROW_MAP["K_future"])]
    assert future.status == "scheduled"
    assert not future.is_initial_data
    food = transactions[external_id(ROW_MAP["I_food"])]
    source_food = next(row for row in snapshot.transactions if row.pk == ROW_MAP["I_food"])
    assert food.category_id == categories[external_id(cast(str, source_food.subcategory_pk))].id
    for transaction in transactions.values():
        assert transaction.source == "import" and transaction.categorization_source == "manual"
    outgoing, incoming = (transactions[external_id(ROW_MAP[name])] for name in ("H_out", "H_in"))
    assert outgoing.kind == incoming.kind == "transfer"
    assert outgoing.transfer_group_id == incoming.transfer_group_id
    assert outgoing.transfer_group_id is not None
    assert outgoing.amount + incoming.amount == Decimal("0.00")
    assert outgoing.category_id is incoming.category_id is None
    tags = list(db_session.scalars(select(Tag).where(Tag.user_id == import_user.id)))
    assert sum(tag.archived_at is not None for tag in tags) == 1
    for source_tag in snapshot.tags:
        tag = next(tag for tag in tags if tag.import_external_id == external_id(source_tag.pk))
        assert (tag.color, tag.icon, tag.emoji, tag.sort_order) == (
            source_tag.color,
            source_tag.icon,
            source_tag.emoji,
            source_tag.sort_order,
        )
    assert sum(len(tags) for tags in transaction_tag_map(snapshot).values()) == 3
    assert db_session.scalar(select(func.count()).select_from(TransactionTag)) == 3
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == before


def test_idempotence_preserves_manual_edits(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    run_import(db_session, import_user.id, snapshot, options)
    account = db_session.scalar(select(Account).where(Account.user_id == import_user.id))
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.user_id == import_user.id)
    )
    assert account is not None and transaction is not None
    account.name = "Edición sintética"
    transaction.note = "Nota sintética editada"
    transaction.amount += Decimal("1.00")
    db_session.flush()
    before = financial_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, snapshot, options)
    assert all(count.created == 0 for count in second.counts.values())
    assert second.counts["transactions"].already_imported == 8
    assert financial_rows(db_session, import_user) == before
    assert (
        len(list(db_session.scalars(select(ImportRun).where(ImportRun.user_id == import_user.id))))
        == 2
    )


def test_dry_run_keeps_audit_and_reviews(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    row = next(row for row in snapshot.transactions if row.pk == ROW_MAP["I_food"])
    altered = replace(snapshot, transactions=(replace(row, amount=abs(row.amount)),))
    before = financial_rows(db_session, import_user)
    report = run_import(db_session, import_user.id, altered, replace(options, dry_run=True))
    assert report.counts["transactions"].created == 1
    assert financial_rows(db_session, import_user) == before
    run = db_session.scalar(select(ImportRun).where(ImportRun.user_id == import_user.id))
    assert run is not None and run.mode == "dry_run" and run.finished_at is not None
    assert run.report["outcome"] == "succeeded"
    assert (
        len(
            list(
                db_session.scalars(
                    select(ImportReviewItem).where(
                        ImportReviewItem.import_run_id == run.id,
                        ImportReviewItem.kind == "polarity_mismatch",
                    )
                )
            )
        )
        == 1
    )


def test_two_users_are_isolated(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    second_user = User(
        email="other-import@example.test", base_currency="PEN", report_currency="PEN"
    )
    db_session.add(second_user)
    db_session.flush()
    first = run_import(db_session, import_user.id, snapshot, options)
    before = financial_rows(db_session, import_user)
    second = run_import(db_session, second_user.id, snapshot, options)
    assert first.counts == second.counts
    assert set(b.account_id for b in first.balances).isdisjoint(
        b.account_id for b in second.balances
    )
    assert financial_rows(db_session, import_user) == before
    for model in (Account, Category, Tag, Transaction):
        first_ids = set(db_session.scalars(select(model.id).where(model.user_id == import_user.id)))
        second_ids = set(
            db_session.scalars(select(model.id).where(model.user_id == second_user.id))
        )
        assert first_ids and second_ids and first_ids.isdisjoint(second_ids)


def test_midway_failure_is_atomic(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(context: ImportContext) -> dict[str, JsonValue]:
        assert context.report.counts["transactions"].created == 26
        raise RuntimeError("Synthetic failure containing private text")

    monkeypatch.setattr(subscriptions, "run", fail)
    before = financial_rows(db_session, import_user)
    with pytest.raises(ImportExecutionError) as caught:
        run_import(db_session, import_user.id, snapshot, options)
    assert financial_rows(db_session, import_user) == before
    assert "private text" not in caught.value.report.model_dump_json()
    assert caught.value.report.outcome == "failed"
    assert all(count.created == 0 for count in caught.value.report.counts.values())
    assert db_session.scalar(select(func.count()).select_from(ImportRun)) == 1


def test_missing_fx_fails_before_inserts(
    db_session: Session, import_user: User, snapshot: Snapshot
) -> None:
    with pytest.raises(ImportExecutionError, match="Falta tasa"):
        run_import(db_session, import_user.id, snapshot, ImportOptions())
    assert all(not rows for rows in financial_rows(db_session, import_user).values())
    assert db_session.scalar(select(func.count()).select_from(ImportRun)) == 1


def test_v46_import(
    db_session: Session, import_user: User, source_path: Path, options: ImportOptions
) -> None:
    shutil.copyfile(FIXTURES / "synthetic_v46_no_tags.sqlite", source_path)
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.tables == EXPECTED["table_counts_v46"]
    assert report.counts["tags"].created == 0
    assert "missing_table:tags" in report.warnings
    assert all(b.unexplained == Decimal("0.00") for b in report.balances)


@pytest.mark.parametrize("override", [False, True])
def test_global_fx_and_manual_priority(
    db_session: Session, import_user: User, source_path: Path, override: bool
) -> None:
    settings = {
        "customCurrencyAmounts": {"pen": "3.8", "usd": 1},
        "cachedCurrencyExchange": {"pen": 4.5, "usd": 2},
    }
    with sqlite3.connect(source_path) as connection:
        connection.execute("UPDATE wallets SET currency = lower(currency)")
        connection.execute("UPDATE app_settings SET settings_j_s_o_n = ?", (json.dumps(settings),))
        # Necesitamos una fila ordinaria USD para comprobar fx_rate_source y provisional_fx.
        connection.execute(
            "UPDATE transactions SET type = NULL, objective_loan_fk = NULL "
            "WHERE transaction_pk = ?",
            (ROW_MAP["C_disbursement"],),
        )
    options = ImportOptions(fx_rate_overrides={"USD": Decimal("3.9")} if override else {})
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    row = db_session.scalar(
        select(Transaction).where(
            Transaction.user_id == import_user.id,
            Transaction.import_external_id == external_id(ROW_MAP["C_disbursement"]),
        )
    )
    assert row is not None
    assert row.fx_rate_to_base == Decimal("3.900000" if override else "3.800000")
    assert row.fx_rate_source == ("manual" if override else "auto")
    assert report.provisional_fx == (0 if override else 4)
    assert all(b.unexplained == Decimal("0.00") for b in report.balances)


def test_name_collisions_and_system_category(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    db_session.add(
        Account(
            user_id=import_user.id,
            name=snapshot.wallets[0].name.upper(),
            currency="PEN",
            type="cash",
        )
    )
    db_session.add(Tag(user_id=import_user.id, name=snapshot.tags[0].name.upper()))
    db_session.add(
        Category(
            user_id=import_user.id,
            name="Intereses",
            kind="expense",
            is_system=True,
            system_key="interest_expense",
        )
    )
    db_session.flush()
    report = run_import(db_session, import_user.id, snapshot, options)
    assert any(w.startswith("account_name_collision:") for w in report.warnings)
    assert any(w.startswith("tag_name_collision:") for w in report.warnings)
    assert any(w.startswith("interest_category_not_merged:") for w in report.warnings)
    assert (
        len(list(db_session.scalars(select(Category).where(Category.user_id == import_user.id))))
        == 8
    )


@pytest.mark.parametrize("mode", ["nonreciprocal", "different_amount", "same_account", "unpaid"])
def test_invalid_transfer_becomes_ordinary(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions, mode: str
) -> None:
    outgoing = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_out"])
    incoming = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_in"])
    if mode == "nonreciprocal":
        incoming = replace(incoming, paired_pk=None)
    elif mode == "different_amount":
        incoming = replace(incoming, amount=Decimal("199.00"))
    elif mode == "same_account":
        incoming = replace(incoming, wallet_pk=outgoing.wallet_pk)
    else:
        incoming = replace(incoming, paid=False)
    report = run_import(
        db_session, import_user.id, replace(snapshot, transactions=(outgoing, incoming)), options
    )
    assert report.counts["transactions"].created == 2
    assert report.counts["transfers"].created == 0
    assert any(item.kind == "unpaired_transfer" for item in report.review_items)
    assert all(
        row.kind in ("expense", "income")
        for row in db_session.scalars(
            select(Transaction).where(Transaction.user_id == import_user.id)
        )
    )
    assert all(b.unexplained == Decimal("0.00") for b in report.balances)


def test_initial_data_written(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    row = next(r for r in snapshot.transactions if r.pk == ROW_MAP["I_food"])
    row = replace(row, occurred_at=datetime(2025, 9, 1, tzinfo=UTC))
    run_import(db_session, import_user.id, replace(snapshot, transactions=(row,)), options)
    imported = db_session.scalar(select(Transaction).where(Transaction.user_id == import_user.id))
    assert imported is not None and imported.is_initial_data


def test_tag_links_helper_preserves_archived_and_reimport(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    # Convertir solo en memoria las filas G a ordinarias para ejercitar el helper
    # que utilizará T-403, sin cambiar los fixtures ni ampliar el alcance productivo.
    transactions = tuple(
        replace(row, type=None) if row.type in (1, 2) else row for row in snapshot.transactions
    )
    altered = replace(snapshot, transactions=transactions)
    report = run_import(db_session, import_user.id, altered, options)
    assert report.counts["transaction_tags"].created == 3
    archived_tag = db_session.scalar(
        select(Tag).where(Tag.user_id == import_user.id, Tag.archived_at.is_not(None))
    )
    assert archived_tag is not None
    link = db_session.scalar(
        select(TransactionTag).where(
            TransactionTag.user_id == import_user.id, TransactionTag.tag_id == archived_tag.id
        )
    )
    assert link is not None
    link.deleted_at = datetime.now(UTC)
    db_session.flush()
    before = financial_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, altered, options)
    assert second.counts["transaction_tags"].created == 0
    assert financial_rows(db_session, import_user) == before


def test_database_failure_keeps_audit(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid_insert(context: ImportContext) -> dict[str, JsonValue]:
        from uuid import uuid4

        context.session.add(
            TransactionTag(user_id=context.user_id, transaction_id=uuid4(), tag_id=uuid4())
        )
        context.session.flush()
        return {}

    monkeypatch.setattr(subscriptions, "run", invalid_insert)
    with pytest.raises(ImportExecutionError):
        run_import(db_session, import_user.id, snapshot, options)
    assert all(not rows for rows in financial_rows(db_session, import_user).values())
    audit = db_session.scalar(select(ImportRun).where(ImportRun.user_id == import_user.id))
    assert audit is not None and audit.report["outcome"] == "failed"
    assert "INSERT INTO" not in json.dumps(audit.report)


def test_deleted_imported_rows_are_never_recreated(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    run_import(db_session, import_user.id, snapshot, options)
    for model in (Transaction, Account, Category, Tag):
        for row in db_session.scalars(select(model).where(model.user_id == import_user.id)):
            row.deleted_at = datetime.now(UTC)
    db_session.flush()
    before = financial_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, snapshot, options)
    assert all(count.created == 0 for count in second.counts.values())
    assert financial_rows(db_session, import_user) == before


def test_reimport_does_not_replace_provisional_rate(
    db_session: Session, import_user: User, snapshot: Snapshot
) -> None:
    row = next(row for row in snapshot.transactions if row.pk == ROW_MAP["C_disbursement"])
    row = replace(row, objective_loan_pk=None, type=None)
    altered = replace(
        snapshot,
        transactions=(row,),
        settings_json=('{"cachedCurrencyExchange": {"usd": 1, "pen": 3.8}}',),
    )
    first = run_import(db_session, import_user.id, altered, ImportOptions())
    assert first.provisional_fx == 1
    before = financial_rows(db_session, import_user)
    second = run_import(
        db_session,
        import_user.id,
        altered,
        ImportOptions(fx_rate_overrides={"USD": Decimal("4.2")}),
    )
    assert second.counts["transactions"].created == 0
    assert second.provisional_fx == 1
    assert financial_rows(db_session, import_user) == before
