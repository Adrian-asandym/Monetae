import json
from decimal import Decimal
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from pydantic import JsonValue
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from monetae.cli import main
from monetae.db.models import Account, Category, ImportReviewItem, ImportRun, Tag, Transaction, User
from monetae.importers.cashew import loans
from monetae.importers.cashew.runner import ImportContext


def test_cli_invalid_file_and_forbidden_path(
    source_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_path.write_bytes(b"not SQLite")
    assert (
        main(
            ["import-cashew", "--file", str(source_path), "--user-email", "synthetic@example.test"]
        )
        == 3
    )
    output = capsys.readouterr()
    assert not output.out and "inválido" in output.err and "Traceback" not in output.err
    path = tmp_path / "reference" / "backups" / "do-not-open.sqlite"
    assert (
        main(["import-cashew", "--file", str(path), "--user-email", "synthetic@example.test"]) == 2
    )
    assert "prohibida" in capsys.readouterr().err


@pytest.mark.parametrize(
    "args",
    [
        ["--fx-rate", "USD=NaN"],
        ["--fx-rate", "USD=0"],
        ["--fx-rate", "USD=bad"],
        ["--fx-rate", "usd=-1"],
        ["--fx-rate", "unknown=1"],
        ["--fx-rate", "USD=0.0000001"],
    ],
)
def test_cli_invalid_rates(
    source_path: Path, args: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "import-cashew",
                "--file",
                str(source_path),
                "--user-email",
                "synthetic@example.test",
                *args,
            ]
        )
        == 2
    )
    assert not capsys.readouterr().out


def test_cli_dry_run_and_loan_rate_plumbing(
    database_url: str,
    db_engine: Engine,
    source_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MONETAE_DATABASE_URL", database_url)
    email = f"cli-{uuid4().hex}@example.test"
    with Session(db_engine) as session:
        user = User(email=email, base_currency="PEN", report_currency="PEN")
        session.add(user)
        session.commit()
        user_id = user.id
    rates_file = tmp_path / "rates.json"
    rates_file.write_text('{"synthetic-pk": "3.800000"}', encoding="utf-8")
    report_path = tmp_path / "report.json"
    original_run = loans.run
    called: list[Decimal] = []

    def capture(context: ImportContext) -> dict[str, JsonValue]:
        called.append(context.options.loan_fx_rates["synthetic-pk"])
        return original_run(context)

    monkeypatch.setattr(loans, "run", capture)
    try:
        assert (
            main(
                [
                    "import-cashew",
                    "--file",
                    str(source_path),
                    "--user-email",
                    email,
                    "--dry-run",
                    "--report-file",
                    str(report_path),
                    "--fx-rate",
                    "usd=3.800000",
                    "--loan-fx-rates",
                    str(rates_file),
                ]
            )
            == 0
        )
        output = capsys.readouterr()
        assert not output.err
        assert called == [Decimal("3.800000")]
        summary = cast(dict[str, object], json.loads(output.out))
        assert summary["code"] == "dry_run"
        assert (
            "Ejemplo" not in output.out and "Cuenta" not in output.out and "Nota" not in output.out
        )
        assert (
            '"name":' not in output.out
            and '"title":' not in output.out
            and '"note":' not in output.out
        )
        with Session(db_engine) as session:
            for model in (Account, Category, Tag, Transaction):
                assert (
                    session.scalar(
                        select(func.count()).select_from(model).where(model.user_id == user_id)
                    )
                    == 0
                )
            audit = session.scalar(select(ImportRun).where(ImportRun.user_id == user_id))
            assert audit is not None and audit.mode == "dry_run"
        report = cast(dict[str, object], json.loads(report_path.read_text(encoding="utf-8")))
        assert report["outcome"] == "succeeded"
    finally:
        with Session(db_engine) as session:
            for audit_model in (ImportReviewItem, ImportRun):
                session.execute(delete(audit_model).where(audit_model.user_id == user_id))
            session.execute(delete(User).where(User.id == user_id))
            session.commit()


def test_cli_missing_user_and_missing_fx(
    database_url: str,
    db_engine: Engine,
    source_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MONETAE_DATABASE_URL", database_url)
    email = f"missing-{uuid4().hex}@example.test"
    args = ["import-cashew", "--file", str(source_path), "--user-email", email]
    assert main(args) == 2
    assert "create-user" in capsys.readouterr().err
    with Session(db_engine) as session:
        user = User(email=email, base_currency="PEN", report_currency="PEN")
        session.add(user)
        session.commit()
        user_id = user.id
    try:
        report_file = tmp_path / "failure-report.json"
        assert main([*args, "--report-file", str(report_file)]) == 4
        output = capsys.readouterr()
        assert not output.out and "Falta tasa" in output.err and "Traceback" not in output.err
        assert report_file.exists()
        with Session(db_engine) as session:
            assert (
                session.scalar(
                    select(func.count()).select_from(Account).where(Account.user_id == user_id)
                )
                == 0
            )
            audit = session.scalar(select(ImportRun).where(ImportRun.user_id == user_id))
            assert audit is not None and audit.report["outcome"] == "failed"
    finally:
        with Session(db_engine) as session:
            session.execute(delete(ImportRun).where(ImportRun.user_id == user_id))
            session.execute(delete(User).where(User.id == user_id))
            session.commit()


def test_report_cannot_overwrite_input(
    source_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = source_path.read_bytes()
    assert (
        main(
            [
                "import-cashew",
                "--file",
                str(source_path),
                "--user-email",
                "synthetic@example.test",
                "--report-file",
                str(source_path),
            ]
        )
        == 2
    )
    assert not capsys.readouterr().out
    assert before == source_path.read_bytes()


def test_cli_usage_errors_in_spanish(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["import-cashew", "--unknown", "PRIVATE_SENTINEL"])
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert "Argumentos de importación inválidos" in output.err
    assert "PRIVATE_SENTINEL" not in output.err and not output.out
