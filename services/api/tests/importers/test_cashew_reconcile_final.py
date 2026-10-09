"""Cuadre estricto, excepción explícita y auditoría durable."""

import json
import sqlite3
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae import cli
from monetae.config import Settings
from monetae.db.models import ImportRun, RecurringRule, Transaction, User
from monetae.importers.cashew.mapping import ImportOptions
from monetae.importers.cashew.reader import Snapshot
from monetae.importers.cashew.runner import run_import

from .test_cashew_subscriptions_import import all_rows
from .test_runner import ROW_MAP


def test_full_reconciliation_with_integrated_loans(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
) -> None:
    report = run_import(db_session, import_user.id, snapshot, options)
    assert report.exit_code == 0 and not report.balance_mismatch
    assert len(report.balances) == 4
    assert all(b.deferred_amount == Decimal("0.00") for b in report.balances)
    for balance in report.balances:
        assert balance.unexplained == Decimal("0.00")
        assert balance.cashew_balance == balance.monetae_balance + balance.deferred_amount
    assert report.pending_phase_6 == {
        "budgets": 1,
        "category_budget_limits": 1,
        "associated_titles": 1,
        "scanner_templates": 1,
        "goals": 0,
    }


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("allow", [False, True])
def test_mismatch_rollback_and_exception(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    dry_run: bool,
    allow: bool,
) -> None:
    source = next(r for r in snapshot.transactions if r.pk == ROW_MAP["I_food"])
    changed = replace(
        snapshot,
        transactions=tuple(
            replace(r, type=9) if r.pk == source.pk else r for r in snapshot.transactions
        ),
    )
    before = all_rows(db_session, import_user)
    report = run_import(
        db_session,
        import_user.id,
        changed,
        replace(options, dry_run=dry_run),
        allow_balance_diff=allow,
    )
    assert report.exit_code == (0 if allow else 5)
    assert report.balance_mismatch and report.allow_balance_diff == allow
    assert report.financial_rolled_back == (dry_run or not allow)
    assert "balance_mismatch" in report.warnings
    assert (
        next(b for b in report.balances if b.source_wallet_pk == source.wallet_pk).unexplained
        == source.amount
    )
    if dry_run or not allow:
        assert all_rows(db_session, import_user) == before
    else:
        assert all_rows(db_session, import_user) != before
    audit = db_session.scalar(select(ImportRun).where(ImportRun.user_id == import_user.id))
    assert audit is not None and audit.report["balance_mismatch"] is True
    expected = (
        "dry_run_with_balance_diff"
        if allow and dry_run
        else "applied_with_balance_diff"
        if allow
        else "balance_mismatch"
    )
    assert report.outcome == audit.report["outcome"] == expected
    assert len(report.balances) == 4


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("allow", [False, True])
def test_cli_balance_exit_and_privacy(
    db_session: Session,
    import_user: User,
    source_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    dry_run: bool,
    allow: bool,
) -> None:
    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "UPDATE transactions SET type = 9 WHERE transaction_pk = ?", (ROW_MAP["I_food"],)
        )
    db_connection = db_session.connection()

    def factory(settings: Settings) -> type[Session]:
        # CLI confirma sus savepoints; la transacción de la fixture sigue aislando el test.
        class TestSession(Session):
            def __init__(self) -> None:
                super().__init__(bind=db_connection, join_transaction_mode="create_savepoint")

        return TestSession

    monkeypatch.setattr(cli, "create_session_factory", factory)
    report_path = tmp_path / "report.json"
    args = [
        "import-cashew",
        "--file",
        str(source_path),
        "--user-email",
        import_user.email,
        "--fx-rate",
        "USD=3.800000",
        "--report-file",
        str(report_path),
    ]
    if dry_run:
        args.append("--dry-run")
    if allow:
        args.append("--allow-balance-diff")
    assert cli.main(args) == (0 if allow else 5)
    captured = capsys.readouterr()
    assert ("no se importó nada" in captured.err) == (not allow)
    summary = cast(dict[str, object], json.loads(captured.out))
    assert summary["balance_mismatch"] is True and summary["allow_balance_diff"] == allow
    assert summary["exit_code"] == (0 if allow else 5)
    assert all(
        word not in captured.out
        for word in ("Servicio", "Cuenta", "Salario", '"title"', '"note"', '"payload"')
    )
    report = cast(dict[str, object], json.loads(report_path.read_text()))
    assert report["balance_mismatch"] is True and report["allow_balance_diff"] == allow
    balances = cast(list[dict[str, str]], report["balances"])
    assert any(Decimal(b["unexplained"]) == Decimal("-25.50") for b in balances)
    db_session.expire_all()
    assert bool(
        list(
            db_session.scalars(select(RecurringRule).where(RecurringRule.user_id == import_user.id))
        )
    ) == (allow and not dry_run)
    assert (
        db_session.scalar(select(ImportRun).where(ImportRun.user_id == import_user.id)) is not None
    )


def test_manual_balance_change_rejected_without_overwriting(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
) -> None:
    run_import(db_session, import_user.id, snapshot, options)
    history = db_session.scalar(
        select(Transaction).where(
            Transaction.user_id == import_user.id,
            Transaction.status == "posted",
        )
    )
    assert history is not None
    history.amount += Decimal("1.00")
    db_session.flush()
    before = all_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, snapshot, options)
    assert second.exit_code == 5
    assert all_rows(db_session, import_user) == before
    assert all(c.created == 0 for c in second.counts.values())


def test_pending_goals_count_without_importing_them(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
) -> None:
    changed = replace(snapshot, objectives=tuple(replace(o, type=0) for o in snapshot.objectives))
    report = run_import(db_session, import_user.id, changed, options)
    assert report.pending_phase_6["goals"] == len(snapshot.objectives)
    assert report.counts["goals"].deferred == len(snapshot.objectives)
    assert report.steps["phase_6"]["goals"] == len(snapshot.objectives)
