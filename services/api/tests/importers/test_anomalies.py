"""Regresiones de T-401b sobre copias SQLite, sin modificar el fixture original."""

import hashlib
import sqlite3
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae.db.models import ImportReviewItem, ImportRun, Transaction, User
from monetae.importers.cashew.mapping import ImportOptions, external_id
from monetae.importers.cashew.reader import read_snapshot
from monetae.importers.cashew.runner import run_import

from .test_runner import ROW_MAP, financial_rows


@pytest.fixture(params=["zero_null", "zero_0", "orphan", "unsupported", "polarity"])
def anomalous_source(source_path: Path, request: pytest.FixtureRequest) -> tuple[Path, str]:
    anomaly = str(request.param)
    pk = ROW_MAP["I_food"]
    with sqlite3.connect(source_path) as connection:
        if anomaly == "zero_null":
            connection.execute(
                "UPDATE transactions SET amount = 0, type = NULL WHERE transaction_pk = ?", (pk,)
            )
        elif anomaly == "zero_0":
            connection.execute(
                "UPDATE transactions SET amount = 0, type = 0 WHERE transaction_pk = ?", (pk,)
            )
        elif anomaly == "orphan":
            connection.execute(
                "UPDATE transactions SET wallet_fk = '0' WHERE transaction_pk = ?", (pk,)
            )
        elif anomaly == "unsupported":
            connection.execute("UPDATE transactions SET type = 9 WHERE transaction_pk = ?", (pk,))
        else:
            connection.execute("UPDATE transactions SET income = 1 WHERE transaction_pk = ?", (pk,))
    return source_path, anomaly


def test_anomaly_keeps_other_rows_and_reimport_is_insertion_only(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    anomalous_source: tuple[Path, str],
) -> None:
    path, anomaly = anomalous_source
    snapshot = read_snapshot(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    report = run_import(db_session, import_user.id, snapshot, options)
    pk = ROW_MAP["I_food"]
    skipped = anomaly != "polarity"
    assert report.outcome == "succeeded"
    assert report.counts["transactions"].created == (25 if skipped else 26)
    assert report.counts["transactions"].skipped == int(skipped)
    assert report.counts["transactions"].deferred == 0
    assert report.steps["loans"]["deferred"] == 0
    assert report.steps["loans"]["processed_transactions"] == 17
    assert report.counts["deferred_recurring"].deferred == 2
    reviews = [item for item in report.review_items if item.payload.get("transaction_pk") == pk]
    assert len(reviews) == 1
    review = reviews[0]
    kinds = {
        "zero_null": "zero_amount_transaction",
        "zero_0": "zero_amount_transaction",
        "orphan": "orphan_transaction",
        "unsupported": "unsupported_transaction_type",
        "polarity": "polarity_mismatch",
    }
    assert review.kind == kinds[anomaly]
    payloads: dict[str, dict[str, object]] = {
        "zero_null": {"transaction_pk": pk},
        "zero_0": {"transaction_pk": pk},
        "orphan": {"transaction_pk": pk, "wallet_pk": "0"},
        "unsupported": {"transaction_pk": pk, "type": 9},
        "polarity": {"transaction_pk": pk, "amount": "-25.50", "income": True},
    }
    assert review.payload == payloads[anomaly]
    records = {
        row.import_external_id: row
        for row in db_session.scalars(
            select(Transaction).where(Transaction.user_id == import_user.id)
        )
    }
    remaining = {
        ROW_MAP[name] for name in ("A_interest", "H_out", "H_in", "K_future", "K_archived_wallet")
    }
    assert {external_id(source_pk) for source_pk in remaining} <= records.keys()
    if skipped:
        assert external_id(pk) not in records
    else:
        assert records[external_id(pk)].kind == "expense"
        assert records[external_id(pk)].amount == Decimal("-25.50")
    wallet_pk = next(row.wallet_pk for row in snapshot.transactions if row.pk == pk)
    for balance in report.balances:
        expected = (
            Decimal("-25.50")
            if anomaly == "unsupported" and balance.source_wallet_pk == wallet_pk
            else Decimal("0.00")
        )
        assert balance.unexplained == expected
    # Reporte y auditoría explican la anomalía con códigos/PK, sin textos de la fila.
    persisted = db_session.scalar(
        select(ImportReviewItem).where(ImportReviewItem.user_id == import_user.id)
    )
    assert (
        persisted is not None
        and persisted.kind == review.kind
        and persisted.payload == review.payload
    )
    for source_row in snapshot.transactions:
        assert source_row.name not in review.model_dump_json()
        if source_row.note:
            assert source_row.note not in review.model_dump_json()
    before = financial_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, snapshot, options)
    assert all(count.created == 0 for count in second.counts.values())
    assert second.counts["transactions"].skipped == int(skipped)
    assert second.counts["transactions"].already_imported == (5 if skipped else 6)
    assert financial_rows(db_session, import_user) == before
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_dry_run_with_anomaly_keeps_only_audit(
    db_session: Session,
    import_user: User,
    options: ImportOptions,
    anomalous_source: tuple[Path, str],
) -> None:
    path, anomaly = anomalous_source
    snapshot = read_snapshot(path)
    before = financial_rows(db_session, import_user)
    report = run_import(db_session, import_user.id, snapshot, replace(options, dry_run=True))
    assert report.outcome == "succeeded"
    assert report.counts["transactions"].created == (26 if anomaly == "polarity" else 25)
    assert report.counts["transactions"].skipped == int(anomaly != "polarity")
    assert financial_rows(db_session, import_user) == before
    audit = db_session.scalar(select(ImportRun).where(ImportRun.user_id == import_user.id))
    assert audit is not None and audit.mode == "dry_run" and audit.report["outcome"] == "succeeded"
    review = db_session.scalar(
        select(ImportReviewItem).where(ImportReviewItem.user_id == import_user.id)
    )
    assert review is not None and review.payload["transaction_pk"] == ROW_MAP["I_food"]
    assert len(report.balances) == 4
    assert sum(balance.unexplained != 0 for balance in report.balances) == int(
        anomaly == "unsupported"
    )


@pytest.mark.parametrize("type_value", [None, 0, 1, 2, 3, 4])
def test_orphan_is_skipped_before_deferred_steps_and_tag_links(
    db_session: Session,
    import_user: User,
    source_path: Path,
    options: ImportOptions,
    type_value: int | None,
) -> None:
    pk = ROW_MAP["G_subscription"]
    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "UPDATE transactions SET wallet_fk = '0', type = ? WHERE transaction_pk = ?",
            (type_value, pk),
        )
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.counts["transactions"].skipped == 1
    assert report.counts["transactions"].created == 26
    assert report.counts["deferred_recurring"].deferred == 1
    assert report.steps["loans"]["deferred"] == 0
    assert report.steps["loans"]["processed_transactions"] == 17
    assert report.counts["transaction_tags"].skipped == 1
    assert report.counts["transaction_tags"].deferred == 2
    assert report.review_items[0].payload == {"transaction_pk": pk, "wallet_pk": "0"}
    assert all(balance.unexplained == 0 for balance in report.balances)


def test_unsupported_type_with_loan_fk_is_not_deferred(
    db_session: Session,
    import_user: User,
    source_path: Path,
    options: ImportOptions,
) -> None:
    pk = ROW_MAP["C_disbursement"]
    with sqlite3.connect(source_path) as connection:
        connection.execute("UPDATE transactions SET type = 9 WHERE transaction_pk = ?", (pk,))
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.counts["transactions"].skipped == 1
    assert report.steps["loans"]["deferred"] == 0
    assert report.steps["loans"]["processed_transactions"] == 16
    assert report.review_items[0].kind == "unsupported_transaction_type"
    usd_balance = next(balance for balance in report.balances if balance.currency == "USD")
    assert usd_balance.unexplained == Decimal("-100.00")
    assert all(balance.unexplained == 0 for balance in report.balances if balance.currency != "USD")


def test_transfer_with_contradictory_income_keeps_both_signs(
    db_session: Session,
    import_user: User,
    source_path: Path,
    options: ImportOptions,
) -> None:
    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "UPDATE transactions SET income = 1 - income WHERE transaction_pk IN (?, ?)",
            (ROW_MAP["H_out"], ROW_MAP["H_in"]),
        )
    report = run_import(db_session, import_user.id, read_snapshot(source_path), options)
    assert report.counts["transfers"].created == 1
    reviews = [
        item
        for item in report.review_items
        if item.payload.get("transaction_pk") in (ROW_MAP["H_out"], ROW_MAP["H_in"])
    ]
    assert len(reviews) == 2
    assert all(review.kind == "polarity_mismatch" for review in reviews)
    assert all(balance.unexplained == 0 for balance in report.balances)
