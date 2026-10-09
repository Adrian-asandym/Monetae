"""Lectura SQLite sin escrituras ni salida de datos privados."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import cast


class InvalidSourceError(ValueError):
    pass


class ForbiddenSourceError(ValueError):
    pass


# Columnas del DDL documentado v48; se seleccionan solo las conocidas.
KNOWN_COLUMNS = {
    "wallets": (
        "wallet_pk name colour icon_name date_created date_time_modified order currency "
        "currency_format decimals home_page_widget_display archived emoji_icon_name"
    ),
    "categories": (
        "category_pk name colour icon_name emoji_icon_name date_created date_time_modified "
        "order income method_added main_category_pk archived"
    ),
    "tags": (
        "tag_pk name colour icon_name emoji_icon_name date_created date_time_modified order "
        "archived"
    ),
    "transaction_to_tag_links": "transaction_pk tag_pk",
    "transactions": (
        "transaction_pk paired_transaction_fk name amount note category_fk sub_category_fk "
        "wallet_fk date_created date_time_modified original_date_due income period_length "
        "reoccurrence end_date upcoming_transaction_notification type paid "
        "created_another_future_transaction skip_paid method_added transaction_owner_email "
        "transaction_original_owner_email shared_key shared_old_key shared_status "
        "shared_date_updated shared_reference_budget_pk objective_fk objective_loan_fk "
        "budget_fks_exclude"
    ),
    "objectives": (
        "objective_pk type name amount order colour date_created end_date date_time_modified "
        "icon_name emoji_icon_name income pinned archived wallet_fk"
    ),
    "budgets": (
        "budget_pk name amount colour start_date end_date wallet_fks category_fks "
        "category_fks_exclude income archived added_transactions_only period_length "
        "reoccurrence date_created date_time_modified pinned order wallet_fk "
        "budget_transaction_filters member_transaction_filters shared_key shared_owner_member "
        "shared_date_updated shared_members shared_all_members_ever is_absolute_spending_limit"
    ),
    "category_budget_limits": (
        "category_limit_pk category_fk budget_fk amount date_time_modified wallet_fk"
    ),
    "associated_titles": (
        "associated_title_pk category_fk title date_created date_time_modified order "
        "is_exact_match archived"
    ),
    "scanner_templates": (
        "scanner_template_pk date_created date_time_modified template_name contains "
        "title_transaction_before title_transaction_after amount_transaction_before "
        "amount_transaction_after default_category_fk wallet_fk ignore default_title"
    ),
    "app_settings": "settings_pk settings_j_s_o_n date_updated",
    "delete_logs": "delete_log_pk entry_pk type date_time_modified",
}


@dataclass(frozen=True, slots=True)
class WalletRow:
    pk: str
    name: str
    currency: str | None
    color: str | None
    icon: str | None
    sort_order: int
    archived: bool
    created_at: datetime
    modified_at: datetime | None


@dataclass(frozen=True, slots=True)
class CategoryRow:
    pk: str
    name: str
    income: bool
    parent_pk: str | None
    color: str | None
    icon: str | None
    emoji: str | None
    archived: bool
    created_at: datetime
    modified_at: datetime | None


@dataclass(frozen=True, slots=True)
class TagRow:
    pk: str
    name: str
    color: str | None
    icon: str | None
    emoji: str | None
    sort_order: int
    archived: bool
    created_at: datetime
    modified_at: datetime | None


@dataclass(frozen=True, slots=True)
class TransactionRow:
    pk: str
    wallet_pk: str
    name: str
    note: str | None
    amount: Decimal
    income: bool
    paid: bool
    type: int | None
    category_pk: str | None
    subcategory_pk: str | None
    paired_pk: str | None
    objective_loan_pk: str | None
    occurred_at: datetime
    modified_at: datetime | None
    original_date_due: datetime | None
    period_length: int | None
    reoccurrence: int | None
    end_date: datetime | None
    created_another_future_transaction: bool
    skip_paid: bool


@dataclass(frozen=True, slots=True)
class ObjectiveRow:
    pk: str
    type: int
    name: str
    amount: Decimal
    income: bool
    wallet_pk: str
    archived: bool
    created_at: datetime
    modified_at: datetime | None
    end_date: datetime | None


@dataclass(frozen=True, slots=True)
class TagLinkRow:
    transaction_pk: str
    tag_pk: str


@dataclass(frozen=True, slots=True)
class Snapshot:
    file_sha256: str
    schema_version: int
    tables: tuple[tuple[str, int], ...]
    unknown_tables: tuple[str, ...]
    unknown_columns: tuple[tuple[str, tuple[str, ...]], ...]
    warnings: tuple[str, ...]
    wallets: tuple[WalletRow, ...]
    categories: tuple[CategoryRow, ...]
    tags: tuple[TagRow, ...]
    transactions: tuple[TransactionRow, ...]
    objectives: tuple[ObjectiveRow, ...]
    tag_links: tuple[TagLinkRow, ...]
    settings_json: tuple[str, ...]


def validate_source_path(path: Path) -> Path:
    resolved = path.resolve()
    for candidate in (path.absolute(), resolved):
        parts = candidate.parts
        if any(parts[i : i + 2] == ("reference", "backups") for i in range(len(parts) - 1)):
            raise ForbiddenSourceError(
                "Ruta prohibida: utilice una copia fuera de reference/backups."
            )
    return resolved


@contextmanager
def open_readonly(path: Path) -> Iterator[sqlite3.Connection]:
    resolved = validate_source_path(path)
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(resolved.as_uri() + "?mode=ro", uri=True)
        connection.execute("PRAGMA query_only=ON")
        yield connection
    except sqlite3.Error as exc:
        raise InvalidSourceError("Archivo SQLite inválido o no accesible.") from exc
    finally:
        if connection is not None:
            connection.close()


def _text(row: dict[str, object], key: str, *, optional: bool = False) -> str | None:
    value = row.get(key)
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise InvalidSourceError(f"Campo de texto inválido: {key}.")
    return value


def _required_text(row: dict[str, object], key: str) -> str:
    value = _text(row, key)
    assert value is not None
    return value


def _int(row: dict[str, object], key: str, default: int | None = None) -> int | None:
    value = row.get(key, default)
    if value is None:
        return None
    if not isinstance(value, int):
        raise InvalidSourceError(f"Campo entero inválido: {key}.")
    return value


def _required_int(row: dict[str, object], key: str, default: int = 0) -> int:
    value = _int(row, key, default)
    if value is None:
        raise InvalidSourceError(f"Campo entero ausente: {key}.")
    return value


def _bool(row: dict[str, object], key: str) -> bool:
    value = _required_int(row, key)
    if value not in (0, 1):
        raise InvalidSourceError(f"Campo booleano inválido: {key}.")
    return value == 1


def _amount(row: dict[str, object]) -> Decimal:
    # SQLite REAL es el único borde float: convertir inmediatamente, sin aritmética float.
    value = row.get("amount")
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise InvalidSourceError("Importe inválido.")
    result = Decimal(str(value))
    if not result.is_finite():
        raise InvalidSourceError("Importe no finito.")
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _date(row: dict[str, object], key: str, warnings: list[str]) -> datetime | None:
    value = _int(row, key)
    if value is None:
        return None
    divisor = 1
    if abs(value) >= 10**14:
        divisor = 10**6
        warnings.append(f"timestamp_microseconds:{key}")
    elif abs(value) > 10**11:
        divisor = 1000
        warnings.append(f"timestamp_milliseconds:{key}")
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=value * (10**6 // divisor))


def _created(row: dict[str, object], warnings: list[str]) -> datetime:
    result = _date(row, "date_created", warnings)
    if result is None:
        raise InvalidSourceError("Fecha de creación ausente.")
    return result


def _quote(identifier: str) -> str:
    # Identificadores descubiertos por PRAGMA: no son valores SQL. Escapar comillas dobles.
    return '"' + identifier.replace('"', '""') + '"'


def read_snapshot(path: Path) -> Snapshot:
    resolved = validate_source_path(path)
    warnings: list[str] = []
    try:
        with open_readonly(resolved) as connection:
            schema_version = cast(int, connection.execute("PRAGMA user_version").fetchone()[0])
            names = tuple(
                sorted(
                    cast(str, r[0])
                    for r in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%'"
                    )
                )
            )
            if not {"wallets", "categories", "transactions"}.issubset(names):
                raise InvalidSourceError("Faltan tablas mínimas de Cashew.")
            unknown = tuple(name for name in names if name not in KNOWN_COLUMNS)
            columns: dict[str, tuple[str, ...]] = {}
            unknown_columns: list[tuple[str, tuple[str, ...]]] = []
            tables: list[tuple[str, int]] = []
            for name in names:
                tables.append(
                    (
                        name,
                        cast(
                            int,
                            connection.execute(f"SELECT count(*) FROM {_quote(name)}").fetchone()[
                                0
                            ],
                        ),
                    )
                )
                discovered = tuple(
                    cast(str, r[1])
                    for r in connection.execute(f"PRAGMA table_info({_quote(name)})")
                )
                if name in KNOWN_COLUMNS:
                    known = set(KNOWN_COLUMNS[name].split())
                    columns[name] = tuple(c for c in discovered if c in known)
                    extra = tuple(c for c in discovered if c not in known)
                    if extra:
                        unknown_columns.append((name, extra))
            for name in KNOWN_COLUMNS:
                if name not in names:
                    warnings.append(f"missing_table:{name}")

            def rows(name: str) -> list[dict[str, object]]:
                if name not in columns:
                    return []
                selected = columns[name]
                # sqlite3 stubs expose Any; narrow to object immediately and validate each field.
                values = connection.execute(
                    f"SELECT {', '.join(_quote(c) for c in selected)} FROM {_quote(name)}"
                ).fetchall()
                return [
                    dict(zip(selected, cast(tuple[object, ...], row), strict=True))
                    for row in values
                ]

            wallets = tuple(
                WalletRow(
                    _required_text(r, "wallet_pk"),
                    _required_text(r, "name"),
                    _text(r, "currency", optional=True),
                    _text(r, "colour", optional=True),
                    _text(r, "icon_name", optional=True),
                    _required_int(r, "order"),
                    _bool(r, "archived"),
                    _created(r, warnings),
                    _date(r, "date_time_modified", warnings),
                )
                for r in rows("wallets")
            )
            categories = tuple(
                CategoryRow(
                    _required_text(r, "category_pk"),
                    _required_text(r, "name"),
                    _bool(r, "income"),
                    _text(r, "main_category_pk", optional=True),
                    _text(r, "colour", optional=True),
                    _text(r, "icon_name", optional=True),
                    _text(r, "emoji_icon_name", optional=True),
                    _bool(r, "archived"),
                    _created(r, warnings),
                    _date(r, "date_time_modified", warnings),
                )
                for r in rows("categories")
            )
            tags = tuple(
                TagRow(
                    _required_text(r, "tag_pk"),
                    _required_text(r, "name"),
                    _text(r, "colour", optional=True),
                    _text(r, "icon_name", optional=True),
                    _text(r, "emoji_icon_name", optional=True),
                    _required_int(r, "order"),
                    _bool(r, "archived"),
                    _created(r, warnings),
                    _date(r, "date_time_modified", warnings),
                )
                for r in rows("tags")
            )
            transactions = tuple(
                TransactionRow(
                    _required_text(r, "transaction_pk"),
                    _required_text(r, "wallet_fk"),
                    _required_text(r, "name"),
                    _text(r, "note", optional=True),
                    _amount(r),
                    _bool(r, "income"),
                    _bool(r, "paid"),
                    _int(r, "type"),
                    _text(r, "category_fk", optional=True),
                    _text(r, "sub_category_fk", optional=True),
                    _text(r, "paired_transaction_fk", optional=True),
                    _text(r, "objective_loan_fk", optional=True),
                    _created(r, warnings),
                    _date(r, "date_time_modified", warnings),
                    _date(r, "original_date_due", warnings),
                    _int(r, "period_length"),
                    _int(r, "reoccurrence"),
                    _date(r, "end_date", warnings),
                    _bool(r, "created_another_future_transaction"),
                    _bool(r, "skip_paid"),
                )
                for r in rows("transactions")
            )
            objectives = tuple(
                ObjectiveRow(
                    _required_text(r, "objective_pk"),
                    _required_int(r, "type"),
                    _required_text(r, "name"),
                    _amount(r),
                    _bool(r, "income"),
                    _required_text(r, "wallet_fk"),
                    _bool(r, "archived"),
                    _created(r, warnings),
                    _date(r, "date_time_modified", warnings),
                    _date(r, "end_date", warnings),
                )
                for r in rows("objectives")
            )
            links = tuple(
                TagLinkRow(_required_text(r, "transaction_pk"), _required_text(r, "tag_pk"))
                for r in rows("transaction_to_tag_links")
            )
            settings = tuple(_required_text(r, "settings_j_s_o_n") for r in rows("app_settings"))
        with resolved.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        return Snapshot(
            digest,
            schema_version,
            tuple(tables),
            unknown,
            tuple(unknown_columns),
            tuple(dict.fromkeys(warnings)),
            wallets,
            categories,
            tags,
            transactions,
            objectives,
            links,
            settings,
        )
    except (OSError, ValueError, OverflowError, ArithmeticError) as exc:
        if isinstance(exc, InvalidSourceError):
            raise
        raise InvalidSourceError("Archivo Cashew inválido o no accesible.") from exc
