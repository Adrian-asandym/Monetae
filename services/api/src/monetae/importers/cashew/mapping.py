"""Plan de importación puro: tasas, polaridad, calendario y pares."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, DecimalException
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from monetae.domain.currency import Currency
from monetae.domain.fx import ExchangeRate
from monetae.domain.transactions import normalize_transaction
from monetae.importers.cashew.reader import Snapshot, TransactionRow, WalletRow
from monetae.importers.cashew.report import ReviewItem


class ImportFailure(ValueError):
    """Error seguro: nunca incorpora títulos, notas ni nombres de origen."""


@dataclass(frozen=True, slots=True)
class ImportOptions:
    dry_run: bool = False
    fx_rate_overrides: dict[str, Decimal] = field(default_factory=dict)
    loan_fx_rates: dict[str, Decimal] = field(default_factory=dict)
    source_path: Path | None = None


@dataclass(frozen=True, slots=True)
class AccountPlan:
    source: WalletRow
    currency: str
    rate: Decimal
    rate_source: str


@dataclass(frozen=True, slots=True)
class TransactionPlan:
    source: TransactionRow
    amount: Decimal
    kind: str
    status: str
    currency: str
    fx_rate_to_base: Decimal
    fx_rate_source: str
    category_pk: str | None
    is_initial_data: bool


@dataclass(frozen=True, slots=True)
class ImportPlan:
    accounts: tuple[AccountPlan, ...]
    normal_transactions: tuple[TransactionPlan, ...]
    transfers: tuple[tuple[TransactionPlan, TransactionPlan], ...]
    deferred_loans: tuple[TransactionRow, ...]
    deferred_recurring: tuple[TransactionRow, ...]
    skipped_transactions: tuple[TransactionRow, ...]
    warnings: tuple[str, ...]
    review_items: tuple[ReviewItem, ...]


def external_id(pk: str) -> str:
    return f"cashew:sqlite:{pk}"


def transaction_tag_map(snapshot: Snapshot) -> dict[str, tuple[str, ...]]:
    """Mapa completo de PK de etiquetas, incluidas las archivadas y filas diferidas."""
    grouped: dict[str, list[str]] = {}
    for link in snapshot.tag_links:
        tags = grouped.setdefault(link.transaction_pk, [])
        if link.tag_pk not in tags:
            tags.append(link.tag_pk)
    return {pk: tuple(tags) for pk, tags in grouped.items()}


def _settings_rates(snapshot: Snapshot) -> dict[str, Decimal]:
    rates: dict[str, Decimal] = {}
    for raw in snapshot.settings_json:
        try:
            # JSON es un borde dinámico: estrechar a object y validar formas antes de usarlo.
            value: object = json.loads(raw, parse_float=Decimal)
        except ValueError as exc:
            raise ImportFailure("Configuración JSON de Cashew inválida.") from exc
        if not isinstance(value, dict):
            raise ImportFailure("Configuración JSON de Cashew inválida.")
        settings = cast(dict[str, object], value)
        # custom tiene precedencia sobre cached, incluso con claves de distinta capitalización.
        for key in ("cachedCurrencyExchange", "customCurrencyAmounts"):
            entries = settings.get(key, {})
            if not isinstance(entries, dict):
                raise ImportFailure("Mapa de tasas de Cashew inválido.")
            for currency, number in cast(dict[object, object], entries).items():
                if (
                    not isinstance(currency, str)
                    or isinstance(number, bool)
                    or not isinstance(number, Decimal | int | str)
                ):
                    raise ImportFailure("Tasa de Cashew inválida.")
                try:
                    rate = Decimal(str(number))
                    if not rate.is_finite() or rate <= 0:
                        raise ImportFailure("Tasa de Cashew inválida.")
                    rates[currency.upper()] = rate
                except DecimalException as exc:
                    raise ImportFailure("Tasa de Cashew inválida.") from exc
    return rates


def resolve_rate(
    currency: str, base: str, options: ImportOptions, settings_rates: dict[str, Decimal]
) -> tuple[Decimal, str]:
    if currency == base:
        return Decimal("1.000000"), "manual"
    override = options.fx_rate_overrides.get(currency)
    if override is not None:
        return ExchangeRate(Currency(currency), Currency(base), override).rate, "manual"
    if currency not in settings_rates or base not in settings_rates:
        raise ImportFailure(f"Falta tasa {currency}→{base}; indique --fx-rate {currency}=TASA.")
    raw = settings_rates[base] / settings_rates[currency]
    rate = raw.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return ExchangeRate(Currency(currency), Currency(base), rate).rate, "auto"


def map_transaction(
    row: TransactionRow, account: AccountPlan, base_currency: str
) -> TransactionPlan:
    # El saldo de Cashew suma este signo; income solo sirve como diagnóstico.
    amount = row.amount
    kind = "income" if amount > 0 else "expense"
    money, rate = normalize_transaction(
        kind,
        amount,
        Currency(account.currency),
        Currency(account.currency),
        Currency(base_currency),
        account.rate,
    )
    local_date = row.occurred_at.astimezone(ZoneInfo("America/Lima")).date()
    return TransactionPlan(
        row,
        money.amount,
        kind,
        "posted" if row.paid else "scheduled",
        account.currency,
        rate,
        account.rate_source,
        row.subcategory_pk or row.category_pk,
        date(2025, 8, 1) <= local_date <= date(2025, 10, 31),
    )


def build_plan(snapshot: Snapshot, base_currency: str, options: ImportOptions) -> ImportPlan:
    rates = _settings_rates(snapshot)
    warnings: list[str] = []
    accounts: list[AccountPlan] = []
    for wallet in snapshot.wallets:
        currency = wallet.currency.upper() if wallet.currency is not None else base_currency
        Currency(currency)
        if wallet.currency is None:
            warnings.append(f"wallet_currency_defaulted:{wallet.pk}")
        rate, source = resolve_rate(currency, base_currency, options, rates)
        accounts.append(AccountPlan(wallet, currency, rate, source))
    by_wallet = {account.source.pk: account for account in accounts}
    normal: dict[str, TransactionPlan] = {}
    loan_rows: list[TransactionRow] = []
    recurring_rows: list[TransactionRow] = []
    reviews: list[ReviewItem] = []
    skipped: list[TransactionRow] = []
    for row in snapshot.transactions:
        if row.wallet_pk not in by_wallet:
            reviews.append(
                ReviewItem(
                    kind="orphan_transaction",
                    payload={
                        "transaction_pk": row.pk,
                        "wallet_pk": row.wallet_pk,
                    },
                )
            )
            skipped.append(row)
            continue
        if row.type not in (None, 0, 1, 2, 3, 4):
            reviews.append(
                ReviewItem(
                    kind="unsupported_transaction_type",
                    payload={
                        "transaction_pk": row.pk,
                        "type": row.type,
                    },
                )
            )
            skipped.append(row)
            continue
        if row.type in (3, 4) or row.objective_loan_pk is not None:
            loan_rows.append(row)
            continue
        if row.type in (1, 2):
            recurring_rows.append(row)
            continue
        if row.amount == 0:
            reviews.append(
                ReviewItem(kind="zero_amount_transaction", payload={"transaction_pk": row.pk})
            )
            skipped.append(row)
            continue
        if (row.amount > 0) != row.income:
            reviews.append(
                ReviewItem(
                    kind="polarity_mismatch",
                    payload={
                        "transaction_pk": row.pk,
                        "amount": str(row.amount),
                        "income": row.income,
                    },
                )
            )
        normal[row.pk] = map_transaction(row, by_wallet[row.wallet_pk], base_currency)
    transfers: list[tuple[TransactionPlan, TransactionPlan]] = []
    paired: set[str] = set()
    for pk, mapped in normal.items():
        row = mapped.source
        if row.paired_pk is None or pk in paired:
            continue
        other = normal.get(row.paired_pk)
        if (
            other is not None
            and other.source.paired_pk == pk
            and row.pk != other.source.pk
            and row.wallet_pk != other.source.wallet_pk
            and mapped.currency == other.currency
            and mapped.amount == -other.amount
            and row.amount == -other.source.amount
            and row.paid
            and other.source.paid
        ):
            transfers.append((mapped, other))
            paired.update((pk, other.source.pk))
        else:
            reviews.append(
                ReviewItem(
                    kind="unpaired_transfer",
                    payload={"transaction_pk": pk, "paired_pk": row.paired_pk},
                )
            )
    return ImportPlan(
        tuple(accounts),
        tuple(row for pk, row in normal.items() if pk not in paired),
        tuple(transfers),
        tuple(loan_rows),
        tuple(recurring_rows),
        tuple(skipped),
        tuple(warnings),
        tuple(reviews),
    )
