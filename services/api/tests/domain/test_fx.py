import random
from dataclasses import FrozenInstanceError
from decimal import ROUND_DOWN, Decimal, Inexact, localcontext
from typing import cast

import pytest

from monetae.domain import (
    PEN,
    USD,
    CurrencyMismatchError,
    ExchangeRate,
    InvalidExchangeRateError,
    Money,
    apply_rate_to_base,
    convert,
    convert_back,
    implied_rate,
)


@pytest.mark.parametrize(
    "value,expected", [("3.8", "3.800000"), ("1.2345675", "1.234568"), ("0.0000005", "0.000001")]
)
def test_rate_rounding(value: str, expected: str) -> None:
    assert str(ExchangeRate(USD, PEN, Decimal(value)).rate) == expected


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        Decimal("0.0000004"),
        1.2,
        True,
        "3.8",
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_invalid_rates(value: object) -> None:
    with pytest.raises(InvalidExchangeRateError) as caught:
        ExchangeRate(USD, PEN, cast(Decimal, value))
    assert caught.value.from_currency == USD
    assert caught.value.to_currency == PEN
    assert "USD->PEN" in str(caught.value)


def test_same_currency_rejected() -> None:
    with pytest.raises(InvalidExchangeRateError, match="differ"):
        ExchangeRate(PEN, PEN, 1)


def test_rate_value_semantics() -> None:
    rate = ExchangeRate(USD, PEN, Decimal("3.8"))
    equal = ExchangeRate(USD, PEN, Decimal("3.800000"))
    assert rate == equal and hash(rate) == hash(equal)
    assert len({rate, equal}) == 1
    assert {rate: 1}[equal] == 1
    attribute = "rate"
    with pytest.raises(FrozenInstanceError):
        setattr(rate, attribute, Decimal(4))


def test_spec_example_c() -> None:
    rate = ExchangeRate(USD, PEN, Decimal("3.800000"))
    assert convert(Money(100, USD), rate) == Money(380, PEN)
    assert convert_back(Money(380, PEN), rate) == Money(100, USD)
    assert rate.inverse() == ExchangeRate(PEN, USD, Decimal("0.263158"))
    assert implied_rate(Money(-100, USD), Money(380, PEN)) == rate


def test_conversion_rounds_once_in_both_directions() -> None:
    rate = ExchangeRate(USD, PEN, Decimal("1.5"))
    assert convert(Money.parse("0.01", USD), rate) == Money.parse("0.02", PEN)
    assert convert(Money.parse("-0.01", USD), rate) == Money.parse("-0.02", PEN)
    rate = ExchangeRate(USD, PEN, 2)
    assert convert_back(Money.parse("0.01", PEN), rate) == Money.parse("0.01", USD)
    assert convert_back(Money.parse("-0.01", PEN), rate) == Money.parse("-0.01", USD)


def test_conversion_currency_mismatch() -> None:
    rate = ExchangeRate(USD, PEN, 4)
    with pytest.raises(CurrencyMismatchError):
        convert(Money(1, PEN), rate)
    with pytest.raises(CurrencyMismatchError):
        convert_back(Money(1, USD), rate)


@pytest.mark.parametrize("source,target", [(0, 10), (10, 0), (0, 0)])
def test_zero_implied_rate(source: int, target: int) -> None:
    with pytest.raises(InvalidExchangeRateError, match="nonzero"):
        implied_rate(Money(source, USD), Money(target, PEN))


def test_implied_rate_rounding_and_signs() -> None:
    assert implied_rate(Money(3, USD), Money(-10, PEN)).rate == Decimal("3.333333")
    with pytest.raises(InvalidExchangeRateError):
        implied_rate(Money(1, PEN), Money(2, PEN))


def test_apply_rate_to_base() -> None:
    assert apply_rate_to_base(Money(100, USD), Decimal("3.8")) == Money(380, PEN)
    money = Money(100, PEN)
    assert apply_rate_to_base(money, 1) is money
    assert apply_rate_to_base(Money(100, USD), 1, USD) == Money(100, USD)
    with pytest.raises(InvalidExchangeRateError, match="rate 1"):
        apply_rate_to_base(money, Decimal("1.0000001"))
    with pytest.raises(InvalidExchangeRateError):
        apply_rate_to_base(money, 0)


def test_global_context_does_not_affect_rates() -> None:
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        rate = ExchangeRate(USD, PEN, Decimal("3.8000004"))
        assert rate.rate == Decimal("3.800000")
        assert rate.inverse().rate == Decimal("0.263158")
        assert implied_rate(Money(3, USD), Money(10, PEN)).rate == Decimal("3.333333")
        assert convert_back(convert(Money(100, USD), rate), rate) == Money(100, USD)


def test_thousand_conversion_samples() -> None:
    generator = random.Random(202)
    for _ in range(1000):
        money = Money(Decimal(generator.randrange(-10000000, 10000000)) / 100, USD)
        rate = ExchangeRate(USD, PEN, Decimal(generator.randrange(1000000, 10000000)) / 1000000)
        round_trip = convert_back(convert(money, rate), rate)
        assert abs(round_trip - money) <= Money.parse("0.01", USD)
