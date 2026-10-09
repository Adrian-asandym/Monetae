"""Alta privada de usuarios; las contraseñas nunca se reciben como argumentos."""

import argparse
import getpass
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, DecimalException
from pathlib import Path
from typing import Never, cast

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from monetae.api.schemas.auth import Currency, Email
from monetae.config import Settings
from monetae.db.models import User
from monetae.db.session import create_session_factory
from monetae.importers.cashew.mapping import ImportFailure, ImportOptions
from monetae.importers.cashew.reader import (
    ForbiddenSourceError,
    InvalidSourceError,
    read_snapshot,
    validate_source_path,
)
from monetae.importers.cashew.report import ImportReport
from monetae.importers.cashew.runner import ImportExecutionError, run_import
from monetae.services.auth import AuthService, SystemClock


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        # Unknown argument values may be passwords mistakenly supplied on the command line.
        self.exit(2, "Invalid command arguments. Use --help; passwords require stdin or getpass.\n")


class ImportArgumentParser(SafeArgumentParser):
    def error(self, message: str) -> Never:
        self.exit(2, "Argumentos de importación inválidos; consulte --help.\n")


def _parse_import_rate(raw: str) -> Decimal:
    value = Decimal(raw)
    if not value.is_finite() or value <= 0:
        raise ValueError("Tasa inválida.")
    rounded = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    if rounded <= 0 or rounded >= Decimal("1000000000000"):
        raise ValueError("Tasa fuera de rango.")
    return rounded


def _import_options(args: argparse.Namespace) -> ImportOptions:
    overrides: dict[str, Decimal] = {}
    for item in args.fx_rate:
        currency, raw = item.split("=", 1)
        currency = TypeAdapter(Currency).validate_python(currency.upper(), strict=True)
        overrides[currency] = _parse_import_rate(raw)
    loan_rates: dict[str, Decimal] = {}
    if args.loan_fx_rates:
        path = validate_source_path(Path(args.loan_fx_rates))
        value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Se requiere un objeto JSON de tasas.")
        for pk, raw in cast(dict[object, object], value).items():
            if not isinstance(pk, str) or not isinstance(raw, str):
                raise ValueError("Las claves y tasas del JSON deben ser cadenas.")
            loan_rates[pk] = _parse_import_rate(raw)
    source = validate_source_path(Path(args.file))
    if args.report_file:
        report_path = validate_source_path(Path(args.report_file))
        if report_path == source or (
            args.loan_fx_rates and report_path == Path(args.loan_fx_rates).resolve()
        ):
            raise ValueError("El reporte no puede sobrescribir un archivo de entrada.")
    return ImportOptions(args.dry_run, overrides, loan_rates, source)


def _write_import_report(report: ImportReport, report_file: str | None) -> None:
    if report_file:
        Path(report_file).write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _import_cashew(args: argparse.Namespace) -> int:
    try:
        email = TypeAdapter(Email).validate_python(args.user_email, strict=True)
        options = _import_options(args)
    except (ValueError, DecimalException, OSError):
        print(
            "Opciones inválidas o ruta prohibida; use una copia fuera de reference/backups.",
            file=sys.stderr,
        )
        return 2
    try:
        assert options.source_path is not None
        snapshot = read_snapshot(options.source_path)
    except ForbiddenSourceError:
        print("Ruta prohibida: utilice una copia fuera de reference/backups.", file=sys.stderr)
        return 2
    except InvalidSourceError:
        print("Archivo Cashew inválido o no accesible.", file=sys.stderr)
        return 3
    try:
        with create_session_factory(Settings())() as db:
            user_id = db.scalar(
                select(User.id).where(
                    func.lower(User.email) == email.lower(), User.deleted_at.is_(None)
                )
            )
            if user_id is None:
                print("El usuario no existe; créelo con create-user.", file=sys.stderr)
                return 2
            try:
                report = run_import(db, user_id, snapshot, options)
            except ImportExecutionError as exc:
                db.commit()  # Auditoría del fallo; el savepoint financiero ya se revirtió.
                _write_import_report(exc.report, args.report_file)
                print(str(exc), file=sys.stderr)
                return 4
            db.commit()
        _write_import_report(report, args.report_file)
    except (ImportFailure, SQLAlchemyError, OSError, ValueError):
        print("Error de importación; consulte el reporte disponible.", file=sys.stderr)
        return 4
    # Lista blanca de salida: conteos, códigos y saldos. Sin nombres/títulos/notas ni payloads.
    summary = {
        "code": "dry_run" if options.dry_run else "applied",
        "counts": {name: counts.model_dump() for name, counts in report.counts.items()},
        "provisional_fx": report.provisional_fx,
        "review_items": len(report.review_items),
        "balances": [
            {
                "code": b.source_wallet_pk,
                "currency": b.currency,
                "cashew_balance": str(b.cashew_balance),
                "monetae_balance": str(b.monetae_balance),
                "deferred_amount": str(b.deferred_amount),
                "unexplained": str(b.unexplained),
            }
            for b in report.balances
        ],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = SafeArgumentParser(prog="monetae", allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user", allow_abbrev=False)
    create.add_argument("--email", required=True)
    create.add_argument("--base-currency", default="PEN")
    create.add_argument("--locale", choices=["es", "en"], default="es")
    create.add_argument("--password-stdin", action="store_true")
    importer = ImportArgumentParser(prog="monetae import-cashew", allow_abbrev=False)
    importer.add_argument("--file", required=True)
    importer.add_argument("--user-email", required=True)
    importer.add_argument("--dry-run", action="store_true")
    importer.add_argument("--report-file")
    importer.add_argument("--fx-rate", action="append", default=[])
    importer.add_argument("--loan-fx-rates")
    commands.add_parser("import-cashew", parents=[importer], add_help=False, allow_abbrev=False)
    args = parser.parse_args(argv)
    if args.command == "import-cashew":
        return _import_cashew(args)
    try:
        email = TypeAdapter(Email).validate_python(args.email, strict=True)
        currency = TypeAdapter(Currency).validate_python(args.base_currency, strict=True)
        if args.password_stdin:
            password = sys.stdin.readline(1024).rstrip("\r\n")
        else:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Confirm password: "):
                raise ValueError("Passwords do not match.")
        config = Settings()
        with create_session_factory(config)() as db:
            AuthService(db, config, SystemClock()).create_user(
                email, password, currency, args.locale
            )
            db.commit()
    except ValidationError:
        print("Invalid user configuration.", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("User created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
