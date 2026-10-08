from decimal import ROUND_DOWN, Decimal, Inexact, localcontext

import pytest

from monetae.domain import PEN, USD, CurrencyMismatchError, ExchangeRate, Money
from monetae.domain.loans import account_amount_from_loan, loan_amount_from_account


@pytest.mark.parametrize("sign", [-1, 1])
def test_fx_converts_magnitudes_with_account_units_per_loan_unit(sign: int) -> None:
    rate = ExchangeRate(USD, PEN, Decimal("3.800000"))
    assert loan_amount_from_account(Money(380 * sign, PEN), rate) == Money(100, USD)
    assert account_amount_from_loan(Money(100 * sign, USD), rate) == Money(380, PEN)


def test_no_fx_means_same_currency_and_no_conversion() -> None:
    assert loan_amount_from_account(Money(-100, USD), None) == Money(100, USD)
    assert account_amount_from_loan(Money(-100, PEN), None) == Money(100, PEN)


def test_fx_rejects_wrong_side_of_rate() -> None:
    rate = ExchangeRate(USD, PEN, Decimal("3.800000"))
    with pytest.raises(CurrencyMismatchError) as caught:
        loan_amount_from_account(Money(100, USD), rate)
    assert caught.value.expected == PEN and caught.value.actual == USD
    with pytest.raises(CurrencyMismatchError) as caught:
        account_amount_from_loan(Money(380, PEN), rate)
    assert caught.value.expected == USD and caught.value.actual == PEN


def test_fx_direct_division_avoids_rounded_inverse_and_rounds_once() -> None:
    rate = ExchangeRate(USD, PEN, Decimal(3))
    # El recíproco redondeado 0.333333 daría 99999.90, perdiendo 0.10 USD.
    assert loan_amount_from_account(Money(300000, PEN), rate) == Money(100000, USD)
    assert loan_amount_from_account(
        Money.parse("0.01", PEN), ExchangeRate(USD, PEN, Decimal(2))
    ) == Money.parse("0.01", USD)
    assert account_amount_from_loan(
        Money.parse("0.01", USD), ExchangeRate(USD, PEN, Decimal("0.5"))
    ) == Money.parse("0.01", PEN)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        assert loan_amount_from_account(Money(300000, PEN), rate) == Money(100000, USD)
