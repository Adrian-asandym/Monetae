from datetime import UTC, datetime
from typing import cast

import pytest

from monetae.domain import PEN, USD, CurrencyMismatchError, Money
from monetae.domain.loans import (
    Adjustment,
    Direction,
    ExcessCash,
    InvalidAdjustmentError,
    InvalidDirectionError,
    InvalidExcessHandlingError,
    InvalidMovementError,
    InvalidSplitError,
    LoanBalance,
    Movement,
    MovementKind,
    OverpaymentError,
    Payment,
    PaymentSplit,
    cash_sign,
    plan_excess,
    recognized_interest,
    replay,
    split_payment,
    split_write_off,
    validate_adjustment,
    validate_split,
)

START = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def state() -> LoanBalance:
    return replay(
        Money(100, PEN),
        [
            Movement(MovementKind.DISBURSEMENT, Money(100, PEN), START, 0),
            Movement(MovementKind.INTEREST, Money(10, PEN), START, 1),
        ],
    )


@pytest.mark.parametrize(
    "amount,interest,principal", [(5, 5, 0), (10, 10, 0), (30, 10, 20), (110, 10, 100)]
)
def test_payment_and_write_off_interest_first(
    state: LoanBalance, amount: int, interest: int, principal: int
) -> None:
    expected = PaymentSplit(Money(interest, PEN), Money(principal, PEN))
    assert split_payment(Money(amount, PEN), state) == expected
    assert split_write_off(Money(amount, PEN), state) == expected


def test_edited_split_may_pay_principal_before_interest(state: LoanBalance) -> None:
    assert validate_split(Money(30, PEN), Money(0, PEN), Money(30, PEN), state) == PaymentSplit(
        Money(0, PEN), Money(30, PEN)
    )


@pytest.mark.parametrize(
    "amount,interest,principal",
    [(30, -1, 31), (30, 31, -1), (30, 5, 20), (30, 11, 19), (101, 0, 101)],
)
def test_invalid_edited_splits(
    state: LoanBalance, amount: int, interest: int, principal: int
) -> None:
    with pytest.raises(InvalidSplitError):
        validate_split(Money(amount, PEN), Money(interest, PEN), Money(principal, PEN), state)


def test_overpayment_has_useful_amounts(state: LoanBalance) -> None:
    with pytest.raises(OverpaymentError) as caught:
        split_payment(Money(120, PEN), state)
    assert caught.value.excess == Money(10, PEN)
    assert caught.value.outstanding == Money(110, PEN)
    assert "110.00" in str(caught.value) and "10.00" in str(caught.value)
    with pytest.raises(OverpaymentError):
        split_write_off(Money(120, PEN), state)


@pytest.mark.parametrize("amount", [0, -1])
def test_payment_rejects_nonpositive_amounts(state: LoanBalance, amount: int) -> None:
    with pytest.raises(InvalidMovementError):
        split_payment(Money(amount, PEN), state)
    with pytest.raises(InvalidMovementError):
        validate_split(Money(amount, PEN), Money(0, PEN), Money(amount, PEN), state)


def test_payment_split_and_adjustment_currency_validation(state: LoanBalance) -> None:
    with pytest.raises(CurrencyMismatchError):
        split_payment(Money(5, USD), state)
    with pytest.raises(CurrencyMismatchError):
        validate_split(Money(5, PEN), Money(5, USD), Money(0, PEN), state)
    with pytest.raises(CurrencyMismatchError):
        validate_split(Money(5, PEN), Money(5, PEN), Money(0, USD), state)
    with pytest.raises(CurrencyMismatchError):
        validate_adjustment(Money(1, USD), state)


def test_adjustment_can_reduce_capital_to_zero_but_cannot_reduce_interest(
    state: LoanBalance,
) -> None:
    validate_adjustment(Money(-100, PEN), state)
    validate_adjustment(Money(1, PEN), state)
    with pytest.raises(InvalidAdjustmentError):
        validate_adjustment(Money(0, PEN), state)
    with pytest.raises(InvalidAdjustmentError, match="principal"):
        validate_adjustment(Money(-101, PEN), state)


def test_excess_plans_use_interest_first_after_adjustment(state: LoanBalance) -> None:
    assert plan_excess("adjustment", Money(120, PEN), state) == (
        Adjustment(Money(10, PEN)),
        Payment(Money(120, PEN), PaymentSplit(Money(10, PEN), Money(110, PEN))),
    )
    assert plan_excess("income_expense", Money(120, PEN), state) == (
        Payment(Money(110, PEN), PaymentSplit(Money(10, PEN), Money(100, PEN))),
        ExcessCash(Money(10, PEN)),
    )
    assert state.outstanding == Money(110, PEN) and state.adjustment_total.is_zero()


@pytest.mark.parametrize(
    "handling,amount",
    [("invalid", 120), ("settle", 120), ("adjustment", 110), ("income_expense", 50)],
)
def test_excess_plan_rejects_unknown_handling_and_missing_excess(
    state: LoanBalance, handling: str, amount: int
) -> None:
    with pytest.raises(InvalidExcessHandlingError):
        plan_excess(handling, Money(amount, PEN), state)


def test_excess_plan_rejects_currency_and_amount(state: LoanBalance) -> None:
    with pytest.raises(CurrencyMismatchError):
        plan_excess("adjustment", Money(120, USD), state)
    with pytest.raises(InvalidMovementError):
        plan_excess("adjustment", Money(0, PEN), state)


def test_cash_entirely_excess_on_settled_loan_never_creates_zero_payment() -> None:
    principal = Money(100, PEN)
    settled = replay(
        principal,
        [
            Movement(MovementKind.DISBURSEMENT, principal, START, 0),
            Movement(MovementKind.PAYMENT, principal, START, 1, Money(0, PEN), principal),
        ],
    )
    assert plan_excess("income_expense", Money(10, PEN), settled) == (ExcessCash(Money(10, PEN)),)
    assert plan_excess("adjustment", Money(10, PEN), settled) == (
        Adjustment(Money(10, PEN)),
        Payment(Money(10, PEN), PaymentSplit(Money(0, PEN), Money(10, PEN))),
    )


@pytest.mark.parametrize("direction", list(Direction))
@pytest.mark.parametrize("kind", list(MovementKind))
def test_cash_sign_for_all_directions_and_kinds(direction: Direction, kind: MovementKind) -> None:
    expected = 0
    if kind == MovementKind.DISBURSEMENT:
        expected = -1 if direction == Direction.LENT else 1
    elif kind == MovementKind.PAYMENT:
        expected = 1 if direction == Direction.LENT else -1
    assert cash_sign(direction, kind) == expected


def test_cash_and_recognition_reject_invalid_direction_and_kind() -> None:
    with pytest.raises(InvalidDirectionError):
        cash_sign(cast(Direction, "lent"), MovementKind.PAYMENT)
    with pytest.raises(InvalidDirectionError):
        recognized_interest(cast(Direction, "invalid"), [])
    with pytest.raises(InvalidMovementError):
        cash_sign(Direction.LENT, cast(MovementKind, "payment"))


def test_write_off_never_recognizes_interest_even_when_it_settles_loan() -> None:
    principal = Money(100, PEN)
    ledger = [
        Movement(MovementKind.DISBURSEMENT, principal, START, 0),
        Movement(MovementKind.INTEREST, Money(10, PEN), START, 1),
    ]
    split = split_write_off(Money(110, PEN), replay(principal, ledger))
    ledger.append(
        Movement(
            MovementKind.WRITE_OFF,
            Money(110, PEN),
            START,
            2,
            split.interest_part,
            split.principal_part,
        )
    )
    result = replay(principal, ledger)
    assert result.status == "settled" and result.write_off_total == Money(110, PEN)
    assert result.payment_total.is_zero()
    for direction in Direction:
        assert recognized_interest(direction, ledger) == ()
        assert cash_sign(direction, MovementKind.WRITE_OFF) == 0
