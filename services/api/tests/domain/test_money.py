import operator
import random
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from decimal import ROUND_DOWN, Decimal, Inexact, localcontext
from typing import cast

import pytest

from monetae.domain import PEN, USD, Currency, CurrencyMismatchError, InvalidMoneyError, Money


@pytest.mark.parametrize(
    "source,expected",
    [
        ("0.005", "0.01"),
        ("-0.005", "-0.01"),
        ("0.004", "0.00"),
        ("-0.004", "0.00"),
        ("1.005", "1.01"),
        ("12.345", "12.35"),
        ("-12.345", "-12.35"),
        ("9999999999999999.994", "9999999999999999.99"),
    ],
)
def test_rounding(source: str, expected: str) -> None:
    assert Money(Decimal(source), PEN).format() == expected
    assert Money.parse(source, PEN).format() == expected


@pytest.mark.parametrize(
    "value",
    [
        1.0,
        True,
        False,
        "1.00",
        None,
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("10000000000000000"),
        Decimal("-10000000000000000"),
        Decimal("9999999999999999.995"),
        Decimal("-9999999999999999.995"),
    ],
)
def test_invalid_money(value: object) -> None:
    with pytest.raises(InvalidMoneyError):
        Money(cast(Decimal, value), PEN)


@pytest.mark.parametrize("value", ["garbage", "", "NaN", "Infinity"])
def test_invalid_parse(value: str) -> None:
    with pytest.raises(InvalidMoneyError):
        Money.parse(value, PEN)


def test_invalid_value_objects() -> None:
    with pytest.raises(InvalidMoneyError):
        Money.parse(cast(str, 12), PEN)
    with pytest.raises(InvalidMoneyError):
        Money(1, cast(Currency, "PEN"))


@pytest.mark.parametrize(
    "operation", [operator.add, operator.sub, operator.lt, operator.le, operator.gt, operator.ge]
)
def test_currency_mismatch(operation: Callable[[Money, Money], object]) -> None:
    with pytest.raises(CurrencyMismatchError) as caught:
        operation(Money(1, PEN), Money(1, USD))
    assert caught.value.expected == PEN
    assert caught.value.actual == USD
    assert "PEN" in str(caught.value) and "USD" in str(caught.value)


def test_equality_hash_and_immutability() -> None:
    first = Money(12, PEN)
    equal = Money.parse("12.000", PEN)
    assert first == equal and hash(first) == hash(equal)
    assert first != Money(12, USD)
    assert first != cast(object, 12)
    assert len({first, equal, Money(12, USD)}) == 2
    assert {first: "value"}[equal] == "value"
    assert repr(first) == "Money(amount=Decimal('12.00'), currency=Currency(code='PEN'))"
    for attribute, value in [("amount", Decimal(13)), ("currency", USD)]:
        with pytest.raises(FrozenInstanceError):
            setattr(first, attribute, value)


def test_arithmetic_and_order() -> None:
    positive, negative, zero = Money(2, PEN), Money(-3, PEN), Money(0, PEN)
    assert positive + negative == Money(-1, PEN)
    assert positive - negative == Money(5, PEN)
    assert -negative == abs(negative) == Money(3, PEN)
    assert abs(positive) == positive
    assert negative < zero < positive
    assert negative <= negative and positive >= positive
    assert positive > negative
    assert negative.is_negative() and not zero.is_negative()
    assert zero.is_zero() and not positive.is_zero()
    assert Money.sum(iter([positive, negative]), PEN) == Money(-1, PEN)
    assert Money.sum([], USD) == Money(0, USD)
    with pytest.raises(CurrencyMismatchError):
        Money.sum([positive, Money(1, USD)], PEN)


def test_scalars_round_only_final_result() -> None:
    assert Money(1, PEN) * Decimal("1.005") == Money.parse("1.01", PEN)
    assert Money(1, PEN) / 8 == Money.parse("0.13", PEN)
    assert Money(-1, PEN) / 8 == Money.parse("-0.13", PEN)
    assert 3 * Money(2, PEN) == Money(6, PEN)
    assert Money(1, PEN) * -2 == Money(-2, PEN)
    assert Money(1, PEN) * 0 == Money(0, PEN)
    assert Money(1, PEN) / Decimal("-2") == Money.parse("-0.50", PEN)
    with pytest.raises(InvalidMoneyError, match="zero"):
        Money(1, PEN) / 0


@pytest.mark.parametrize("scalar", [1.2, True, Decimal("NaN"), Decimal("Infinity"), Money(1, PEN)])
@pytest.mark.parametrize("operation", [operator.mul, operator.truediv])
def test_invalid_scalars(scalar: object, operation: Callable[[object, object], object]) -> None:
    with pytest.raises(InvalidMoneyError):
        operation(Money(1, PEN), scalar)


@pytest.mark.parametrize(
    "operation", [operator.add, operator.sub, operator.lt, operator.le, operator.gt, operator.ge]
)
def test_unrelated_operand(operation: Callable[[object, object], object]) -> None:
    with pytest.raises(TypeError):
        operation(Money(1, PEN), 1)


def test_overflow_after_arithmetic() -> None:
    maximum = Money.parse("9999999999999999.99", PEN)
    with pytest.raises(InvalidMoneyError):
        maximum + Money.parse("0.01", PEN)
    with pytest.raises(InvalidMoneyError):
        maximum * 2


def test_global_context_does_not_affect_money() -> None:
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        amount = Money.parse("1234.005", PEN)
        assert amount.format() == "1234.01"
        assert amount + Money(10, PEN) == Money.parse("1244.01", PEN)
        assert -amount == Money.parse("-1234.01", PEN)
        assert abs(-amount) == amount
        assert amount * Decimal("1.000001") == amount
        assert amount / 3 == Money.parse("411.34", PEN)


def test_thousand_addition_samples() -> None:
    generator = random.Random(202)
    for _ in range(1000):
        a = Money.parse(f"{generator.randrange(-1000000, 1000000)}.12", PEN)
        b = Money.parse(f"{generator.randrange(-1000000, 1000000)}.34", PEN)
        assert (a + b) - b == a


def test_spec_examples_a_b_d_e() -> None:
    # SPEC §7 A: capital + interés − pagos variables.
    assert Money(200, PEN) + Money(10, PEN) - Money(100, PEN) - Money(110, PEN) == Money(0, PEN)
    # B: cobros por cuentas distintas, misma moneda.
    assert Money(500, PEN) - Money(300, PEN) - Money(200, PEN) == Money(0, PEN)
    # D: exceso de 10; resolverlo corresponde al dominio de préstamos.
    assert Money(50, USD) - Money(60, USD) == Money(-10, USD)
    assert abs(Money(50, USD) - Money(60, USD)).format() == "10.00"
    # E: saldos intermedios después de cada pago.
    balance = Money(1000, PEN)
    for payment, expected in [(50, 950), (120, 830), (30, 800), (800, 0)]:
        balance -= Money(payment, PEN)
        assert balance == Money(expected, PEN)
