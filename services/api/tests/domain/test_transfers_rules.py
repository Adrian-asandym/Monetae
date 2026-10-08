from decimal import Decimal

import pytest

from monetae.domain.currency import PEN, USD
from monetae.domain.errors import InvalidExchangeRateError
from monetae.domain.money import Money
from monetae.domain.transfers import (
    InvalidTransferAmountError,
    TransferAmountMismatchError,
    validate_transfer_amounts,
)


@pytest.mark.parametrize(
    ("outgoing", "incoming", "rate"),
    [
        (Money(100, PEN), Money(100, PEN), "1.000000"),
        (Money(380, PEN), Money(100, USD), "0.263158"),
        (Money(100, USD), Money(380, PEN), "3.800000"),
        (Money(128, PEN), Money(1, USD), "0.007813"),
    ],
)
def test_implicit_rate(outgoing: Money, incoming: Money, rate: str) -> None:
    assert validate_transfer_amounts(outgoing, incoming) == Decimal(rate)


@pytest.mark.parametrize("amount", [0, -1])
def test_positive_amounts(amount: int) -> None:
    for outgoing, incoming in (
        (Money(amount, PEN), Money(1, USD)),
        (Money(1, PEN), Money(amount, USD)),
    ):
        with pytest.raises(InvalidTransferAmountError):
            validate_transfer_amounts(outgoing, incoming)


def test_same_currency_mismatch() -> None:
    with pytest.raises(TransferAmountMismatchError):
        validate_transfer_amounts(Money(1, PEN), Money(2, PEN))


def test_rate_rounding_to_zero() -> None:
    with pytest.raises(InvalidExchangeRateError):
        validate_transfer_amounts(Money(1000000, PEN), Money(Decimal("0.01"), USD))
