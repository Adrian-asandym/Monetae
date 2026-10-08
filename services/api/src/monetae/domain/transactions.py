"""Invariantes puras del CRUD directo y de la tasa histórica."""

from decimal import Decimal

from monetae.domain.currency import Currency
from monetae.domain.errors import CurrencyMismatchError, DomainError, InvalidExchangeRateError
from monetae.domain.fx import ExchangeRate, apply_rate_to_base
from monetae.domain.money import Money


class InvalidTransactionError(DomainError):
    pass


def validate_amount(kind: str, money: Money) -> None:
    if kind not in {"income", "expense"}:
        raise InvalidTransactionError("Direct transactions must be income or expense.")
    if money.is_zero() or (kind == "income") != (money.amount > 0):
        raise InvalidTransactionError("Income must be positive and expense negative.")


def normalize_transaction(
    kind: str,
    amount: Decimal,
    currency: Currency,
    account_currency: Currency,
    base_currency: Currency,
    rate: Decimal,
) -> tuple[Money, Decimal]:
    if currency != account_currency:
        raise CurrencyMismatchError(account_currency, currency)
    money = Money(amount, currency)
    validate_amount(kind, money)
    if currency == base_currency:
        if rate != Decimal(1):
            raise InvalidExchangeRateError("Base currency requires rate 1", currency, base_currency)
        normalized = Decimal("1.000000")
    else:
        normalized = ExchangeRate(currency, base_currency, rate).rate
    return money, normalized


def equivalent_in_base(money: Money, rate: Decimal, base_currency: Currency) -> Money:
    return apply_rate_to_base(money, rate, base_currency)
