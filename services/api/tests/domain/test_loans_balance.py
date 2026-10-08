import random
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from decimal import ROUND_DOWN, Decimal, Inexact, localcontext
from typing import cast

import pytest

from monetae.domain import PEN, USD, Money
from monetae.domain.loans import (
    Direction,
    InvalidInterestError,
    LoanBalance,
    Movement,
    MovementKind,
    propose_interest,
    recognized_interest,
    replay,
    split_payment,
    split_write_off,
)

START = datetime(2026, 1, 1, tzinfo=UTC)


def test_totals_pending_components_and_saved_user_split() -> None:
    principal = Money(100, PEN)
    ledger = [
        Movement(MovementKind.DISBURSEMENT, principal, START, 0),
        Movement(MovementKind.INTEREST, Money(20, PEN), START, 1),
        Movement(MovementKind.ADJUSTMENT, Money(10, PEN), START, 2),
        Movement(MovementKind.ADJUSTMENT, Money(-5, PEN), START, 3),
        Movement(MovementKind.PAYMENT, Money(30, PEN), START, 4, Money(5, PEN), Money(25, PEN)),
        Movement(MovementKind.WRITE_OFF, Money(25, PEN), START, 5, Money(15, PEN), Money(10, PEN)),
    ]
    state = replay(principal, ledger)
    assert state.principal == principal
    assert state.interest_total == Money(20, PEN)
    assert state.adjustment_total == Money(5, PEN)
    assert state.payment_total == Money(30, PEN)
    assert state.write_off_total == Money(25, PEN)
    assert state.interest_pending == Money(0, PEN)
    assert state.principal_outstanding == state.outstanding == Money(70, PEN)
    assert state.status == "open"
    assert recognized_interest(Direction.LENT, ledger)[0].amount == Money(5, PEN)
    assert recognized_interest(Direction.LENT, ledger)[0].side == "income"
    assert len(recognized_interest(Direction.LENT, ledger)) == 1
    assert state.running == tuple(Money(n, PEN) for n in (100, 120, 130, 125, 95, 70))
    for target, attribute, value in [
        (state, "outstanding", Money(0, PEN)),
        (ledger[0], "amount", Money(1, PEN)),
    ]:
        with pytest.raises(FrozenInstanceError):
            setattr(target, attribute, value)


@pytest.mark.parametrize("kind", [MovementKind.INTEREST, MovementKind.ADJUSTMENT])
def test_p2_settled_loan_reopens_by_computed_balance_without_mutating_history(
    kind: MovementKind,
) -> None:
    principal = Money(100, PEN)
    ledger = [
        Movement(MovementKind.DISBURSEMENT, principal, START, 0),
        Movement(MovementKind.PAYMENT, principal, START, 1, Money(0, PEN), principal),
    ]
    original = tuple(ledger)
    settled = replay(principal, ledger)
    assert settled.status == "settled"
    ledger.append(Movement(kind, Money(10, PEN), START, 2))
    reopened = replay(principal, ledger)
    assert reopened.status == "open" and reopened.outstanding == Money(10, PEN)
    assert settled.status == "settled" and tuple(ledger[:2]) == original
    split = split_payment(Money(10, PEN), reopened)
    ledger.append(
        Movement(
            MovementKind.PAYMENT,
            Money(10, PEN),
            START,
            3,
            split.interest_part,
            split.principal_part,
        )
    )
    assert replay(principal, ledger).status == "settled"


@pytest.mark.parametrize(
    "percentage,amount,expected",
    [
        ("5", "200", "10"),
        ("0.5", "1", "0.01"),
        ("5.1234", "100", "5.12"),
        ("5.123400", "100", "5.12"),
        ("1000", "1", "10"),
        ("0.0001", "0", "0"),
    ],
)
def test_interest_proposals_single_rounding(percentage: str, amount: str, expected: str) -> None:
    assert propose_interest(Decimal(percentage), Money.parse(amount, PEN)) == Money.parse(
        expected, PEN
    )


@pytest.mark.parametrize(
    "value",
    [
        Decimal(0),
        Decimal(-1),
        Decimal("1000.0001"),
        Decimal("5.123456"),
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        True,
        5,
        "5",
    ],
)
def test_invalid_interest_percentage(value: object) -> None:
    with pytest.raises(InvalidInterestError):
        propose_interest(cast(Decimal, value), Money(100, PEN))


def test_interest_negative_balance_and_hostile_decimal_context() -> None:
    with pytest.raises(InvalidInterestError, match="nonnegative"):
        propose_interest(Decimal(5), Money(-1, PEN))
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        assert propose_interest(Decimal("5.123400"), Money(200, USD)) == Money.parse("10.25", USD)
        assert Money.parse("0.005", USD) == Money.parse("0.01", USD)


def assert_identity(state: LoanBalance) -> None:
    assert state.outstanding == (
        state.principal
        + state.interest_total
        + state.adjustment_total
        - state.payment_total
        - state.write_off_total
    )
    assert state.outstanding == state.interest_pending + state.principal_outstanding
    assert state.interest_pending.amount >= 0 and state.principal_outstanding.amount >= 0
    assert state.status == ("settled" if state.outstanding.is_zero() else "open")


def test_balance_identity_has_no_artificial_money_overflow_after_earlier_payments() -> None:
    principal = Money(9000000000000000, PEN)
    paid = Money(8000000000000000, PEN)
    ledger = [
        Movement(MovementKind.DISBURSEMENT, principal, START, 0),
        Movement(MovementKind.PAYMENT, paid, START, 1, Money(0, PEN), paid),
        Movement(MovementKind.INTEREST, Money(2000000000000000, PEN), START, 2),
    ]
    assert replay(principal, ledger).outstanding == Money(3000000000000000, PEN)


def test_two_thousand_deterministic_valid_ledgers_incremental_equals_full_replay() -> None:
    generator = random.Random(301)
    for _ in range(2000):
        currency = generator.choice([PEN, USD])
        principal = Money(Decimal(generator.randrange(1, 100001)) / 100, currency)
        ledger = [Movement(MovementKind.DISBURSEMENT, principal, START, 0)]
        prefixes = [replay(principal, ledger)]
        incremental_interest = Money(0, currency)
        incremental_principal = principal
        for sequence in range(1, 9):
            state = prefixes[-1]
            kind = generator.choice(
                [
                    MovementKind.INTEREST,
                    MovementKind.ADJUSTMENT,
                    MovementKind.PAYMENT,
                    MovementKind.WRITE_OFF,
                ]
            )
            amount = Money(Decimal(generator.randrange(1, 10001)) / 100, currency)
            interest_part: Money | None = None
            principal_part: Money | None = None
            if kind == MovementKind.INTEREST:
                incremental_interest += amount
            elif kind == MovementKind.ADJUSTMENT:
                if generator.choice([True, False]) and not incremental_principal.is_zero():
                    amount = -min(amount, incremental_principal)
                incremental_principal += amount
            elif state.outstanding.is_zero():
                kind = MovementKind.INTEREST
                incremental_interest += amount
            else:
                amount = min(amount, state.outstanding)
                split = (split_payment if kind == MovementKind.PAYMENT else split_write_off)(
                    amount, state
                )
                interest_part, principal_part = split.interest_part, split.principal_part
                incremental_interest -= interest_part
                incremental_principal -= principal_part
            ledger.append(
                Movement(
                    kind,
                    amount,
                    START + timedelta(days=sequence),
                    sequence,
                    interest_part,
                    principal_part,
                )
            )
            incremental = replay(principal, ledger)
            assert_identity(incremental)
            assert incremental.interest_pending == incremental_interest
            assert incremental.principal_outstanding == incremental_principal
            assert incremental.outstanding == incremental_interest + incremental_principal
            assert incremental.running[:-1] == prefixes[-1].running
            prefixes.append(incremental)
        generator.shuffle(ledger)
        full = replay(principal, iter(ledger))
        assert full == prefixes[-1]
        for prefix in prefixes:
            assert full.running[: len(prefix.running)] == prefix.running
