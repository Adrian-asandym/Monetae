from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import localcontext

import pytest

from monetae.domain import PEN, USD, CurrencyMismatchError, Money
from monetae.domain.subscriptions import (
    Period,
    Subscription,
    archive,
    historical_paid,
    last_paid_on,
    monthly_equivalent,
    totals,
    yearly_equivalent,
)


def subscription(amount: str, period: Period, interval: int = 1) -> Subscription:
    return Subscription(
        "Netflix", Money.parse(amount, PEN), period, interval, date(2024, 1, 1), date(2024, 1, 1)
    )


@pytest.mark.parametrize(
    ("period", "amount", "interval", "monthly", "yearly"),
    [
        (Period.DAILY, "1", 1, "30.44", "365.25"),
        (Period.DAILY, "1", 2, "15.22", "182.63"),
        (Period.DAILY, "1", 3, "10.15", "121.75"),
        (Period.WEEKLY, "12", 1, "52.18", "626.13"),
        (Period.WEEKLY, "12", 2, "26.09", "313.07"),
        (Period.WEEKLY, "12", 3, "17.39", "208.71"),
        (Period.MONTHLY, "44.90", 1, "44.90", "538.80"),
        (Period.MONTHLY, "44.90", 2, "22.45", "269.40"),
        (Period.MONTHLY, "44.90", 3, "14.97", "179.60"),
        (Period.YEARLY, "100", 1, "8.33", "100.00"),
        (Period.YEARLY, "100", 2, "4.17", "50.00"),
        (Period.YEARLY, "100", 3, "2.78", "33.33"),
        (Period.DAILY, "1", 7, "4.35", "52.18"),
    ],
)
def test_equivalents(period: Period, amount: str, interval: int, monthly: str, yearly: str) -> None:
    sub = subscription(amount, period, interval)
    with localcontext() as context:
        context.prec = 2
        assert monthly_equivalent(sub) == Money.parse(monthly, PEN)
        assert yearly_equivalent(sub) == Money.parse(yearly, PEN)


def test_yearly_equivalent_uses_unrounded_monthly() -> None:
    sub = subscription("100", Period.YEARLY)
    assert yearly_equivalent(sub) == Money(100, PEN)
    assert monthly_equivalent(sub) * 12 == Money.parse("99.96", PEN)


def test_totals_round_only_at_end_and_separate_currencies() -> None:
    pen = subscription("100", Period.YEARLY)
    usd = replace(pen, amount=Money.parse("44.90", USD), period=Period.MONTHLY)
    archived = archive(pen, datetime(2024, 1, 1, tzinfo=UTC))
    assert totals(iter([pen, pen, usd, archived])) == {
        PEN: (Money.parse("16.67", PEN), Money(200, PEN), 2),
        USD: (Money.parse("44.90", USD), Money.parse("538.80", USD), 1),
    }
    assert totals([]) == {}
    assert totals([archived]) == {}


def test_historical_payments_and_last_date() -> None:
    payments = [Money.parse("44.90", PEN)] * 3
    assert historical_paid(iter(payments), PEN) == Money.parse("134.70", PEN)
    assert historical_paid([], USD) == Money(0, USD)
    with pytest.raises(CurrencyMismatchError):
        historical_paid([Money(1, USD)], PEN)
    assert last_paid_on([]) is None
    assert last_paid_on(iter([date(2024, 3, 1), date(2024, 1, 1), date(2024, 4, 1)])) == date(
        2024, 4, 1
    )


def test_totals_preserve_exact_half_cent_with_repeating_equivalents() -> None:
    annual = subscription("0.01", Period.YEARLY)
    assert totals([annual] * 6)[PEN] == (Money.parse("0.01", PEN), Money.parse("0.06", PEN), 6)
    every_two_years = subscription("0.01", Period.YEARLY, 2)
    assert totals([every_two_years] * 3)[PEN][1] == Money.parse("0.02", PEN)
