"""Pares explícitos sobre copias temporales del SQLite sintético."""

import sqlite3
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from monetae.cli import main
from monetae.db.models import Account, ImportReviewItem, ImportRun, Transaction, User
from monetae.importers.cashew.mapping import ImportOptions, build_plan, external_id
from monetae.importers.cashew.reader import Snapshot, read_snapshot
from monetae.importers.cashew.report import ImportReport
from monetae.importers.cashew.runner import run_import

from .test_runner import ROW_MAP, financial_rows


def transfer_snapshot(source_path: Path, *, direction: str = "reciprocal") -> Snapshot:
    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "DELETE FROM transactions WHERE transaction_pk NOT IN (?, ?)",
            (ROW_MAP["H_out"], ROW_MAP["H_in"]),
        )
        connection.execute("DELETE FROM transaction_to_tag_links")
        if direction != "reciprocal":
            connection.execute(
                "UPDATE transactions SET paired_transaction_fk = NULL WHERE transaction_pk = ?",
                (ROW_MAP[direction],),
            )
    return read_snapshot(source_path)


def reasons(snapshot: Snapshot, options: ImportOptions) -> dict[str, str]:
    plan = build_plan(snapshot, "PEN", options)
    return {
        str(item.payload["transaction_pk"]): str(item.payload["reason"])
        for item in plan.review_items
        if item.kind == "unpaired_transfer"
    }


@pytest.mark.parametrize("direction", ["reciprocal", "H_in", "H_out"])
def test_explicit_pair_import_idempotence_and_isolation(
    db_session: Session,
    import_user: User,
    source_path: Path,
    options: ImportOptions,
    direction: str,
) -> None:
    snapshot = transfer_snapshot(source_path, direction=direction)
    first = run_import(db_session, import_user.id, snapshot, options)
    assert first.counts["transfers"].created == 1
    assert first.counts["transactions"].created == 2
    assert first.steps["transfers"] == {"unpaired_by_reason": {}}
    assert all(b.unexplained == Decimal("0.00") for b in first.balances)
    legs = list(
        db_session.scalars(select(Transaction).where(Transaction.user_id == import_user.id))
    )
    assert len(legs) == 2
    assert all(t.kind == "transfer" and t.category_id is None for t in legs)
    assert legs[0].transfer_group_id == legs[1].transfer_group_id is not None
    before = financial_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, snapshot, options)
    assert all(c.created == 0 for c in second.counts.values())
    assert financial_rows(db_session, import_user) == before
    other = User(email="transfer-other@example.test", base_currency="PEN", report_currency="PEN")
    db_session.add(other)
    db_session.flush()
    isolated = run_import(db_session, other.id, snapshot, options)
    assert isolated.counts["transfers"].created == 1
    assert {b.account_id for b in first.balances}.isdisjoint(
        b.account_id for b in isolated.balances
    )
    assert financial_rows(db_session, import_user) == before


@pytest.mark.parametrize("direction", ["H_in", "H_out"])
def test_one_way_dry_run(
    db_session: Session,
    import_user: User,
    source_path: Path,
    options: ImportOptions,
    direction: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    snapshot = transfer_snapshot(source_path, direction=direction)
    before = financial_rows(db_session, import_user)
    report = run_import(db_session, import_user.id, snapshot, replace(options, dry_run=True))
    assert report.counts["transfers"].created == 1
    assert report.counts["transactions"].created == 2
    assert all(b.unexplained == Decimal("0.00") for b in report.balances)
    assert report.financial_rolled_back
    assert financial_rows(db_session, import_user) == before
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("missing", "counterpart_missing"),
        ("loan", "counterpart_not_ordinary"),
        ("objective", "counterpart_not_ordinary"),
        ("recurring", "counterpart_not_ordinary"),
        ("unsupported", "counterpart_not_ordinary"),
        ("omitted", "counterpart_not_ordinary"),
        ("same_wallet", "same_wallet"),
        ("currency", "currency_mismatch"),
        ("amount", "amount_mismatch"),
        ("unpaid", "unpaid"),
        ("ambiguous", "ambiguous_counterpart"),
    ],
)
def test_unpaired_reason_and_money_preserved(
    db_session: Session,
    import_user: User,
    source_path: Path,
    options: ImportOptions,
    change: str,
    reason: str,
) -> None:
    snapshot = transfer_snapshot(source_path, direction="H_in")
    outgoing = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_out"])
    incoming = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_in"])
    with sqlite3.connect(source_path) as connection:
        updates: dict[str, tuple[str, object]] = {
            "missing": ("paired_transaction_fk", "absent-counterpart"),
            "loan": ("type", 3),
            "objective": ("objective_loan_fk", "absent-objective"),
            "recurring": ("type", 1),
            "unsupported": ("type", 99),
            "omitted": ("amount", 0),
            "same_wallet": ("wallet_fk", outgoing.wallet_pk),
            "currency": ("wallet_fk", next(w.pk for w in snapshot.wallets if w.currency == "USD")),
            "amount": ("amount", "199.00"),
            "unpaid": ("paid", 0),
        }
        if change == "ambiguous":
            # Una tercera fila ordinaria del fixture apunta a la misma pata positiva.
            columns = [r[1] for r in connection.execute("PRAGMA table_info(transactions)")]
            values = list(
                connection.execute(
                    "SELECT * FROM transactions WHERE transaction_pk = ?", (outgoing.pk,)
                ).fetchone()
            )
            values[columns.index("transaction_pk")] = "third-transfer-leg"
            connection.execute(
                "INSERT INTO transactions VALUES (" + ",".join("?" for _ in columns) + ")",
                values,
            )
        else:
            column, value = updates[change]
            # Identificador de columna interno y cerrado; valores parametrizados.
            connection.execute(
                f"UPDATE transactions SET {column} = ? WHERE transaction_pk = ?",
                (value, outgoing.pk if change == "missing" else incoming.pk),
            )
    altered = read_snapshot(source_path)
    plan = build_plan(altered, "PEN", options)
    assert not plan.transfers
    found = reasons(altered, options)
    assert found[outgoing.pk] == reason
    if change in {"same_wallet", "currency", "amount", "unpaid", "ambiguous"}:
        assert set(found.values()) == {reason}
        assert len(found) == (3 if change == "ambiguous" else 2)
    report = run_import(db_session, import_user.id, altered, options, allow_balance_diff=True)
    assert report.counts["transfers"].created == 0
    assert report.steps["transfers"]["unpaired_by_reason"] == {reason: len(found)}
    imported = db_session.scalar(
        select(Transaction).where(
            Transaction.user_id == import_user.id,
            Transaction.import_external_id == external_id(outgoing.pk),
        )
    )
    assert imported is not None and imported.amount == outgoing.amount
    assert imported.kind == "expense"
    if change in {"same_wallet", "currency", "amount", "unpaid", "ambiguous", "missing"}:
        assert all(b.unexplained == Decimal("0.00") for b in report.balances)


def test_chain_and_order_never_pair(snapshot: Snapshot, options: ImportOptions) -> None:
    outgoing = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_out"])
    incoming = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_in"])
    third = replace(outgoing, pk="third", paired_pk=None)
    incoming = replace(incoming, paired_pk=third.pk)
    rows = (outgoing, incoming, third)
    for ordered in (rows, tuple(reversed(rows))):
        altered = replace(snapshot, transactions=ordered)
        assert not build_plan(altered, "PEN", options).transfers
        assert set(reasons(altered, options).values()) == {"ambiguous_counterpart"}


def test_reason_precedence(snapshot: Snapshot, options: ImportOptions) -> None:
    outgoing = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_out"])
    incoming = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_in"])
    incoming = replace(incoming, wallet_pk=outgoing.wallet_pk, amount=Decimal("199"), paid=False)
    altered = replace(snapshot, transactions=(outgoing, incoming))
    assert set(reasons(altered, options).values()) == {"same_wallet"}


def test_partially_imported_pair_stays_ordinary(
    db_session: Session,
    import_user: User,
    source_path: Path,
    options: ImportOptions,
) -> None:
    snapshot = transfer_snapshot(source_path, direction="H_in")
    incoming = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_in"])
    run_import(db_session, import_user.id, replace(snapshot, transactions=(incoming,)), options)
    before = db_session.scalar(select(Transaction).where(Transaction.user_id == import_user.id))
    assert before is not None
    original = (before.id, before.amount, before.kind, before.updated_at)
    report = run_import(db_session, import_user.id, snapshot, options)
    assert report.counts["transactions"].created == 1
    assert report.counts["transfers"].skipped == 1
    assert report.steps["transfers"] == {"unpaired_by_reason": {"partially_imported": 1}}
    assert (before.id, before.amount, before.kind, before.updated_at) == original
    assert all(
        t.kind != "transfer"
        for t in db_session.scalars(
            select(Transaction).where(Transaction.user_id == import_user.id)
        )
    )
    second = run_import(db_session, import_user.id, snapshot, options)
    assert all(c.created == 0 for c in second.counts.values())


def test_cli_one_way_dry_run_has_no_private_text(
    database_url: str,
    db_engine: Engine,
    source_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    transfer_snapshot(source_path, direction="H_in")
    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "UPDATE transactions SET name = ?, note = ?",
            ("PRIVATE_TRANSFER_TITLE", "PRIVATE_TRANSFER_NOTE"),
        )
    monkeypatch.setenv("MONETAE_DATABASE_URL", database_url)
    with Session(db_engine) as session:
        user = User(
            email=f"transfer-cli-{uuid4().hex}@example.test",
            base_currency="PEN",
            report_currency="PEN",
        )
        session.add(user)
        session.commit()
        user_id, email = user.id, user.email
    report_path = tmp_path / "transfer-report.json"
    try:
        assert (
            main(
                [
                    "import-cashew",
                    "--file",
                    str(source_path),
                    "--user-email",
                    email,
                    "--fx-rate",
                    "USD=3.800000",
                    "--dry-run",
                    "--report-file",
                    str(report_path),
                ]
            )
            == 0
        )
        output = capsys.readouterr()
        assert not output.err
        assert "PRIVATE_TRANSFER_TITLE" not in output.out
        assert "PRIVATE_TRANSFER_NOTE" not in output.out
        assert all(field not in output.out for field in ('"title"', '"note"', '"payload"'))
        report = ImportReport.model_validate_json(report_path.read_bytes())
        assert report.counts["transfers"].created == 1
        assert report.counts["transactions"].created == 2
        assert all(b.unexplained == Decimal("0.00") for b in report.balances)
        with Session(db_engine) as session:
            for model in (Account, Transaction):
                assert (
                    session.scalar(
                        select(func.count()).select_from(model).where(model.user_id == user_id)
                    )
                    == 0
                )
    finally:
        with Session(db_engine) as session:
            for audit_model in (ImportReviewItem, ImportRun):
                session.execute(delete(audit_model).where(audit_model.user_id == user_id))
            session.execute(delete(User).where(User.id == user_id))
            session.commit()


def test_opposite_amounts_without_references_do_not_pair(
    source_path: Path,
    options: ImportOptions,
) -> None:
    transfer_snapshot(source_path)
    with sqlite3.connect(source_path) as connection:
        connection.execute("UPDATE transactions SET paired_transaction_fk = NULL")
    plan = build_plan(read_snapshot(source_path), "PEN", options)
    assert not plan.transfers
    assert len(plan.normal_transactions) == 2
    assert not plan.review_items


def test_nonordinary_incoming_reference_also_blocks_pair(
    snapshot: Snapshot,
    options: ImportOptions,
) -> None:
    outgoing = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_out"])
    incoming = next(r for r in snapshot.transactions if r.pk == ROW_MAP["H_in"])
    third = replace(outgoing, pk="third-recurring", type=1)
    altered = replace(snapshot, transactions=(incoming, outgoing, third))
    assert not build_plan(altered, "PEN", options).transfers
    assert set(reasons(altered, options).values()) == {"ambiguous_counterpart"}
