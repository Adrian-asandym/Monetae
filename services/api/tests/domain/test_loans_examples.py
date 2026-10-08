"""Ejemplos literales A–E de SPEC §7, efectos en cuentas y P1/P2/P3."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from monetae.domain import PEN, USD, ExchangeRate, Money
from monetae.domain.loans import (
    Adjustment,
    Direction,
    ExcessCash,
    Movement,
    MovementKind,
    OverpaymentError,
    Payment,
    account_amount_from_loan,
    cash_sign,
    loan_amount_from_account,
    plan_excess,
    propose_interest,
    recognized_interest,
    replay,
    split_payment,
)

START = datetime(2026, 1, 1, tzinfo=UTC)


def payment(principal: Money, ledger: list[Movement], amount: Money) -> Movement:
    split = split_payment(amount, replay(principal, ledger))
    return Movement(
        MovementKind.PAYMENT,
        amount,
        START + timedelta(days=len(ledger)),
        len(ledger),
        split.interest_part,
        split.principal_part,
    )


def test_a_borrowed_200_interest_5_percent_pay_100_then_110() -> None:
    principal = Money(200, PEN)
    ledger = [Movement(MovementKind.DISBURSEMENT, principal, START, 0)]
    cash: dict[str, Money] = {"Efectivo": Money(200, PEN), "BCP": Money(0, PEN)}
    interest = propose_interest(Decimal(5), replay(principal, ledger).outstanding)
    assert interest == Money(10, PEN)
    ledger.append(Movement(MovementKind.INTEREST, interest, START + timedelta(days=1), 1))
    assert replay(principal, ledger).outstanding == Money(210, PEN)
    assert recognized_interest(Direction.BORROWED, ledger) == ()
    for account, amount, expected_interest, expected_principal, expected_balance in [
        ("BCP", 100, 10, 90, 110),
        ("Efectivo", 110, 0, 110, 0),
    ]:
        movement = payment(principal, ledger, Money(amount, PEN))
        assert movement.interest_part == Money(expected_interest, PEN)
        assert movement.principal_part == Money(expected_principal, PEN)
        cash[account] += movement.amount * cash_sign(Direction.BORROWED, movement.kind)
        ledger.append(movement)
        assert replay(principal, ledger).outstanding == Money(expected_balance, PEN)
    result = replay(principal, ledger)
    assert result.status == "settled"
    assert cash == {"Efectivo": Money(90, PEN), "BCP": Money(-100, PEN)}
    recognized = recognized_interest(Direction.BORROWED, ledger)
    assert len(recognized) == 1
    assert recognized[0].amount == Money(10, PEN)
    assert recognized[0].side == "expense"
    assert recognized[0].occurred_at == ledger[2].occurred_at
    # P1: se conservan cuatro movimientos de libro y tres transacciones con dinero.
    assert len(ledger) == 4 and len(result.running) == 4
    assert sum(cash_sign(Direction.BORROWED, m.kind) != 0 for m in ledger) == 3


def test_b_lent_500_from_yape_collected_300_cash_and_200_bcp() -> None:
    principal = Money(500, PEN)
    ledger = [Movement(MovementKind.DISBURSEMENT, principal, START, 0)]
    cash = {"Yape": Money(-500, PEN), "Efectivo": Money(0, PEN), "BCP": Money(0, PEN)}
    for account, amount in [("Efectivo", 300), ("BCP", 200)]:
        movement = payment(principal, ledger, Money(amount, PEN))
        cash[account] += movement.amount * cash_sign(Direction.LENT, movement.kind)
        ledger.append(movement)
    assert cash == {"Yape": Money(-500, PEN), "Efectivo": Money(300, PEN), "BCP": Money(200, PEN)}
    result = replay(principal, ledger)
    assert result.running == (principal, Money(200, PEN), Money(0, PEN))
    assert result.status == "settled"
    assert len(ledger) == 3 and recognized_interest(Direction.LENT, ledger) == ()


def test_c_lent_usd_100_collected_pen_380_at_3_800000() -> None:
    principal = Money(100, USD)
    rate = ExchangeRate(USD, PEN, Decimal("3.800000"))
    account_amount = Money(380, PEN)
    loan_amount = loan_amount_from_account(account_amount, rate)
    assert loan_amount == principal
    assert account_amount_from_loan(loan_amount, rate) == account_amount
    ledger = [Movement(MovementKind.DISBURSEMENT, principal, START, 0)]
    ledger.append(payment(principal, ledger, loan_amount))
    result = replay(principal, ledger)
    assert result.outstanding - principal == Money(-100, USD)
    assert result.status == "settled"
    assert rate.rate == Decimal("3.800000")
    assert account_amount * cash_sign(Direction.LENT, MovementKind.PAYMENT) == Money(380, PEN)


@pytest.mark.parametrize("handling", ["adjustment", "income_expense"])
def test_d_usd_balance_50_payment_60_requires_explicit_excess_plan(handling: str) -> None:
    principal = Money(50, USD)
    ledger = [Movement(MovementKind.DISBURSEMENT, principal, START, 0)]
    state = replay(principal, ledger)
    with pytest.raises(OverpaymentError) as caught:
        split_payment(Money(60, USD), state)
    assert caught.value.excess == Money(10, USD)
    assert caught.value.outstanding == principal
    plan = plan_excess(handling, Money(60, USD), state)
    excess_cash = Money(0, USD)
    for operation in plan:
        if isinstance(operation, Adjustment):
            ledger.append(Movement(MovementKind.ADJUSTMENT, operation.amount, START, len(ledger)))
        elif isinstance(operation, Payment):
            ledger.append(
                Movement(
                    MovementKind.PAYMENT,
                    operation.amount,
                    START,
                    len(ledger),
                    operation.split.interest_part,
                    operation.split.principal_part,
                )
            )
        else:
            assert isinstance(operation, ExcessCash)
            excess_cash += operation.amount
    result = replay(principal, ledger)
    assert result.outstanding == Money(0, USD) and result.status == "settled"
    if handling == "adjustment":
        assert result.adjustment_total == Money(10, USD)
        assert result.payment_total == Money(60, USD) and excess_cash.is_zero()
    else:
        assert result.adjustment_total.is_zero()
        assert result.payment_total == Money(50, USD) and excess_cash == Money(10, USD)
    assert result.payment_total + excess_cash == Money(60, USD)


def test_e_lent_1000_variable_payments_50_120_30_800_on_different_dates() -> None:
    principal = Money(1000, PEN)
    ledger = [Movement(MovementKind.DISBURSEMENT, principal, START, 0)]
    for amount, expected in [(50, 950), (120, 830), (30, 800), (800, 0)]:
        ledger.append(payment(principal, ledger, Money(amount, PEN)))
        state = replay(principal, ledger)
        assert state.outstanding == Money(expected, PEN)
        assert state.status == ("settled" if expected == 0 else "open")
    assert replay(principal, ledger).running == tuple(
        Money(value, PEN) for value in (1000, 950, 830, 800, 0)
    )
    assert len(ledger) == 5


def test_p3_mixed_payment_accounts_and_currencies_compose_without_original_account() -> None:
    principal = Money(100, USD)
    ledger = [Movement(MovementKind.DISBURSEMENT, principal, START, 0)]
    cash = {
        "USD original": Money(-100, USD),
        "PEN payment": Money(0, PEN),
        "USD payment": Money(0, USD),
    }
    for account, physical, rate in [
        ("PEN payment", Money(190, PEN), ExchangeRate(USD, PEN, Decimal("3.800000"))),
        ("USD payment", Money(50, USD), None),
    ]:
        cash[account] += physical * cash_sign(Direction.LENT, MovementKind.PAYMENT)
        ledger.append(payment(principal, ledger, loan_amount_from_account(physical, rate)))
    assert replay(principal, ledger).status == "settled"
    assert cash == {
        "USD original": Money(-100, USD),
        "PEN payment": Money(190, PEN),
        "USD payment": Money(50, USD),
    }
