import hashlib
import shutil
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from monetae.importers.cashew.mapping import (
    ImportFailure,
    ImportOptions,
    build_plan,
    transaction_tag_map,
)
from monetae.importers.cashew.reader import (
    ForbiddenSourceError,
    InvalidSourceError,
    Snapshot,
    open_readonly,
    read_snapshot,
)

from .conftest import FIXTURES


def test_readonly_and_immutable(source_path: Path) -> None:
    before = hashlib.sha256(source_path.read_bytes()).hexdigest()
    with open_readonly(source_path) as connection:
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("CREATE TABLE forbidden (id INTEGER)")
    result = read_snapshot(source_path)
    assert result.file_sha256 == before == hashlib.sha256(source_path.read_bytes()).hexdigest()
    assert result.schema_version == 48
    assert not result.unknown_tables and not result.unknown_columns


def test_unknown_schema_is_reported(source_path: Path) -> None:
    with sqlite3.connect(source_path) as connection:
        connection.execute('ALTER TABLE wallets ADD COLUMN "future_field" TEXT')
        connection.execute('CREATE TABLE "future_table" (id INTEGER)')
    result = read_snapshot(source_path)
    assert result.unknown_tables == ("future_table",)
    assert dict(result.unknown_columns) == {"wallets": ("future_field",)}


def test_v46_without_tags(source_path: Path, options: ImportOptions) -> None:
    shutil.copyfile(FIXTURES / "synthetic_v46_no_tags.sqlite", source_path)
    result = read_snapshot(source_path)
    assert result.schema_version == 46
    assert not result.tags and not result.tag_links
    assert {"missing_table:tags", "missing_table:transaction_to_tag_links"} <= set(result.warnings)
    assert len(build_plan(result, "PEN", options).normal_transactions) == 4


@pytest.mark.parametrize("content", [b"not SQLite", b""])
def test_invalid_source(source_path: Path, content: bytes) -> None:
    source_path.write_bytes(content)
    with pytest.raises(InvalidSourceError):
        read_snapshot(source_path)


def test_missing_minimum_tables(source_path: Path) -> None:
    source_path.unlink()
    with sqlite3.connect(source_path) as connection:
        connection.execute("CREATE TABLE wallets (wallet_pk TEXT)")
    with pytest.raises(InvalidSourceError, match="mínimas"):
        read_snapshot(source_path)


def test_forbidden_path_and_symlink(tmp_path: Path, source_path: Path) -> None:
    forbidden = tmp_path / "reference" / "backups" / "do-not-open.sqlite"
    forbidden.parent.mkdir(parents=True)
    link = forbidden.parent.parent.parent / "alias.sqlite"
    link.symlink_to(forbidden)
    for path in (forbidden, link):
        with pytest.raises(ForbiddenSourceError):
            read_snapshot(path)
    # También rechazar un alias ubicado dentro del directorio prohibido.
    forbidden.symlink_to(source_path)
    with pytest.raises(ForbiddenSourceError):
        read_snapshot(forbidden)


def test_timestamp_scales_and_decimal_rounding(source_path: Path) -> None:
    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "UPDATE transactions SET amount = -25.505, date_created = 1767268800123 "
            "WHERE amount = -25.5"
        )
    result = read_snapshot(source_path)
    row = next(r for r in result.transactions if r.amount == Decimal("-25.51"))
    assert row.occurred_at == datetime(2026, 1, 1, 12, 0, 0, 123000, tzinfo=UTC)
    assert "timestamp_milliseconds:date_created" in result.warnings


def test_missing_currency_and_tag_helper(snapshot: Snapshot, options: ImportOptions) -> None:
    altered = replace(
        snapshot, wallets=(replace(snapshot.wallets[0], currency=None), *snapshot.wallets[1:])
    )
    plan = build_plan(altered, "PEN", options)
    assert plan.accounts[0].currency == "PEN"
    assert any(w.startswith("wallet_currency_defaulted:") for w in plan.warnings)
    links = transaction_tag_map(snapshot)
    assert sum(len(pks) for pks in links.values()) == 3
    archived = next(tag for tag in snapshot.tags if tag.archived)
    assert any(archived.pk in pks for pks in links.values())


def test_lima_initial_window_and_polarity(snapshot: Snapshot, options: ImportOptions) -> None:
    row = next(
        r
        for r in snapshot.transactions
        if r.type is None and not r.paired_pk and not r.objective_loan_pk
    )
    for timestamp, expected in [
        (datetime(2025, 8, 1, 4, 59, 59, tzinfo=UTC), False),
        (datetime(2025, 8, 1, 5, tzinfo=UTC), True),
        (datetime(2025, 11, 1, 4, 59, 59, tzinfo=UTC), True),
        (datetime(2025, 11, 1, 5, tzinfo=UTC), False),
    ]:
        changed = replace(row, amount=abs(row.amount), income=False, occurred_at=timestamp)
        plan = build_plan(replace(snapshot, transactions=(changed,)), "PEN", options)
        assert plan.normal_transactions[0].is_initial_data == expected
        assert plan.normal_transactions[0].amount == abs(row.amount)
        assert plan.normal_transactions[0].kind == "income"
        assert plan.review_items[0].kind == "polarity_mismatch"


def test_fx_absent_fails(snapshot: Snapshot) -> None:
    with pytest.raises(ImportFailure, match="Falta tasa"):
        build_plan(snapshot, "PEN", ImportOptions())


@pytest.mark.parametrize(
    "settings",
    [
        '{"cachedCurrencyExchange": {"usd": 1, "pen": 3.8}}',
        '{"cachedCurrencyExchange": {"usd": "1", "pen": "3.8"}}',
    ],
)
def test_cached_fx_fallback(snapshot: Snapshot, settings: str) -> None:
    plan = build_plan(replace(snapshot, settings_json=(settings,)), "PEN", ImportOptions())
    account = next(account for account in plan.accounts if account.currency == "USD")
    assert account.rate == Decimal("3.800000") and account.rate_source == "auto"


@pytest.mark.parametrize(
    "settings",
    [
        '{"customCurrencyAmounts": {"usd": 1}}',
        '{"customCurrencyAmounts": {"pen": 3.8}}',
        '{"customCurrencyAmounts": {"usd": 0, "pen": 3.8}}',
        '{"customCurrencyAmounts": {"usd": "NaN", "pen": 3.8}}',
        '{"customCurrencyAmounts": []}',
        "[]",
        "invalid",
    ],
)
def test_global_fx_missing_or_invalid(snapshot: Snapshot, settings: str) -> None:
    with pytest.raises(ImportFailure):
        build_plan(replace(snapshot, settings_json=(settings,)), "PEN", ImportOptions())
