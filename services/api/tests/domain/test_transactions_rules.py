from decimal import Decimal

import pytest

from monetae.domain.currency import PEN, USD
from monetae.domain.errors import CurrencyMismatchError, InvalidExchangeRateError
from monetae.domain.money import Money
from monetae.domain.transactions import (
    InvalidTransactionError,
    equivalent_in_base,
    normalize_transaction,
    validate_amount,
)


@pytest.mark.parametrize(
    "kind,amount",
    [
        ("income", "0"),
        ("income", "-1"),
        ("expense", "0"),
        ("expense", "1"),
        ("loan", "1"),
        ("transfer", "-1"),
    ],
)
def test_invalid_direct_kind_or_sign(kind: str, amount: str) -> None:
    with pytest.raises(InvalidTransactionError):
        validate_amount(kind, Money(Decimal(amount), PEN))


@pytest.mark.parametrize("kind,amount", [("income", "1"), ("expense", "-1")])
def test_valid_sign(kind: str, amount: str) -> None:
    validate_amount(kind, Money(Decimal(amount), PEN))


def test_transaction_currency_must_match_account() -> None:
    with pytest.raises(CurrencyMismatchError):
        normalize_transaction("income", Decimal(1), USD, PEN, PEN, Decimal(1))


def test_base_rate_must_be_exactly_one_before_rounding() -> None:
    with pytest.raises(InvalidExchangeRateError):
        normalize_transaction("income", Decimal(1), PEN, PEN, PEN, Decimal("1.0000001"))


def test_foreign_rate_and_money_use_half_up_and_historical_equivalent() -> None:
    money, rate = normalize_transaction(
        "expense", Decimal("-1.005"), USD, USD, PEN, Decimal("3.8000005")
    )
    assert money.amount == Decimal("-1.01")
    assert rate == Decimal("3.800001")
    assert equivalent_in_base(money, rate, PEN).amount == Decimal("-3.84")


@pytest.mark.parametrize("rate", ["0", "-1", "0.0000001"])
def test_rate_must_remain_positive_after_rounding(rate: str) -> None:
    with pytest.raises(InvalidExchangeRateError):
        normalize_transaction("income", Decimal(1), USD, USD, PEN, Decimal(rate))
