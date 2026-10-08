from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import cast

import pytest

from monetae.domain import PEN, USD, CurrencyMismatchError, DomainError, Money
from monetae.domain.loans import (
    DisbursementMismatchError,
    DuplicateDisbursementError,
    InvalidAdjustmentError,
    InvalidMovementError,
    InvalidSplitError,
    LedgerCurrencyMismatchError,
    LedgerError,
    LedgerMovementError,
    MissingDisbursementError,
    Movement,
    MovementKind,
    replay,
)

START = datetime(2026, 1, 1, tzinfo=UTC)


def disbursement() -> Movement:
    return Movement(MovementKind.DISBURSEMENT, Money(100, PEN), START, 0)


@pytest.mark.parametrize(
    "ledger", [[], [Movement(MovementKind.INTEREST, Money(10, PEN), START, 0)]]
)
def test_missing_disbursement(ledger: list[Movement]) -> None:
    with pytest.raises(MissingDisbursementError) as caught:
        replay(Money(100, PEN), ledger)
    assert caught.value.index == len(ledger)
    assert isinstance(caught.value, LedgerError)


def test_duplicate_and_mismatching_disbursement() -> None:
    with pytest.raises(DuplicateDisbursementError) as caught:
        replay(Money(100, PEN), [disbursement(), replace(disbursement(), sequence=1)])
    assert caught.value.index == 1
    with pytest.raises(DisbursementMismatchError) as mismatch:
        replay(Money(100, PEN), [replace(disbursement(), amount=Money(99, PEN))])
    assert mismatch.value.index == 0


@pytest.mark.parametrize("principal", [0, -1])
def test_principal_must_be_positive(principal: int) -> None:
    with pytest.raises(InvalidMovementError):
        replay(Money(principal, PEN), [])


@pytest.mark.parametrize("kind", list(MovementKind))
def test_currency_mismatch_carries_replay_index_and_currency_error(kind: MovementKind) -> None:
    interest = Money(0, USD) if kind in {MovementKind.PAYMENT, MovementKind.WRITE_OFF} else None
    principal = Money(1, USD) if interest is not None else None
    invalid = Movement(kind, Money(1, USD), START, 1, interest, principal)
    with pytest.raises(LedgerCurrencyMismatchError) as caught:
        replay(Money(100, PEN), [disbursement(), invalid])
    assert caught.value.index == 1
    assert caught.value.expected == PEN and caught.value.actual == USD
    assert isinstance(caught.value, CurrencyMismatchError)
    assert isinstance(caught.value, LedgerError)
    assert isinstance(caught.value.__cause__, CurrencyMismatchError)


@pytest.mark.parametrize("kind", [MovementKind.PAYMENT, MovementKind.WRITE_OFF])
@pytest.mark.parametrize("amount,interest,principal", [(11, 11, 0), (101, 0, 101)])
def test_saved_split_exceeding_a_component_fails_even_with_sufficient_total_balance(
    kind: MovementKind, amount: int, interest: int, principal: int
) -> None:
    ledger = [
        disbursement(),
        Movement(MovementKind.INTEREST, Money(10, PEN), START, 1),
        Movement(kind, Money(amount, PEN), START, 2, Money(interest, PEN), Money(principal, PEN)),
    ]
    with pytest.raises(LedgerMovementError) as caught:
        replay(Money(100, PEN), ledger)
    assert caught.value.index == 2
    assert isinstance(caught.value.__cause__, InvalidSplitError)


def test_negative_adjustment_cannot_spend_pending_interest() -> None:
    ledger = [
        disbursement(),
        Movement(MovementKind.INTEREST, Money(10, PEN), START, 1),
        Movement(MovementKind.ADJUSTMENT, Money(-101, PEN), START, 2),
    ]
    with pytest.raises(LedgerMovementError) as caught:
        replay(Money(100, PEN), ledger)
    assert caught.value.index == 2
    assert isinstance(caught.value.__cause__, InvalidAdjustmentError)


def test_replay_stops_at_first_violation_before_duplicate_disbursement() -> None:
    ledger = [
        disbursement(),
        Movement(MovementKind.ADJUSTMENT, Money(-101, PEN), START, 1),
        replace(disbursement(), sequence=2),
    ]
    with pytest.raises(LedgerMovementError) as caught:
        replay(Money(100, PEN), ledger)
    assert caught.value.index == 1


def test_replay_orders_by_timestamp_then_caller_sequence() -> None:
    interest = Movement(MovementKind.INTEREST, Money(10, PEN), START, 1)
    payment = Movement(
        MovementKind.PAYMENT, Money(110, PEN), START, 2, Money(10, PEN), Money(100, PEN)
    )
    assert replay(Money(100, PEN), [payment, interest, disbursement()]).status == "settled"
    with pytest.raises(LedgerMovementError) as caught:
        replay(
            Money(100, PEN),
            [replace(payment, sequence=1), replace(interest, sequence=2), disbursement()],
        )
    assert caught.value.index == 1
    # Instantes equivalentes en distintas zonas se desempatan por sequence.
    local_interest = replace(interest, occurred_at=START.astimezone(timezone(timedelta(hours=-5))))
    assert replay(Money(100, PEN), [payment, local_interest, disbursement()]).status == "settled"


def test_edit_delete_and_retroactive_movement_reject_invalid_saved_splits() -> None:
    interest = Movement(MovementKind.INTEREST, Money(10, PEN), START + timedelta(days=1), 1)
    payment = Movement(
        MovementKind.PAYMENT,
        Money(20, PEN),
        START + timedelta(days=2),
        2,
        Money(10, PEN),
        Money(10, PEN),
    )
    assert replay(Money(100, PEN), [disbursement(), interest, payment]).outstanding == Money(
        90, PEN
    )
    for changed in [
        [disbursement(), replace(interest, amount=Money(5, PEN)), payment],
        [disbursement(), payment],
        [disbursement(), replace(interest, occurred_at=START + timedelta(days=3)), payment],
    ]:
        with pytest.raises(LedgerMovementError):
            replay(Money(100, PEN), changed)
    capital_payment = replace(
        payment, amount=Money(100, PEN), interest_part=Money(0, PEN), principal_part=Money(100, PEN)
    )
    with pytest.raises(LedgerMovementError):
        replay(
            Money(100, PEN),
            [
                disbursement(),
                capital_payment,
                Movement(MovementKind.ADJUSTMENT, Money(-1, PEN), START + timedelta(days=1), 1),
            ],
        )


@pytest.mark.parametrize("kind", [k for k in MovementKind if k != MovementKind.ADJUSTMENT])
@pytest.mark.parametrize("amount", [0, -1])
def test_movement_amounts_must_be_positive(kind: MovementKind, amount: int) -> None:
    with pytest.raises(InvalidMovementError):
        Movement(kind, Money(amount, PEN), START, 0)


def test_zero_adjustment_rejected() -> None:
    with pytest.raises(InvalidAdjustmentError):
        Movement(MovementKind.ADJUSTMENT, Money(0, PEN), START, 0)


@pytest.mark.parametrize("kind", [MovementKind.PAYMENT, MovementKind.WRITE_OFF])
@pytest.mark.parametrize(
    "interest,principal",
    [
        (None, None),
        (Money(0, PEN), None),
        (None, Money(1, PEN)),
        (Money(-1, PEN), Money(2, PEN)),
        (Money(0, PEN), Money(2, PEN)),
    ],
)
def test_movement_requires_valid_split(
    kind: MovementKind, interest: Money | None, principal: Money | None
) -> None:
    with pytest.raises(InvalidSplitError):
        Movement(kind, Money(1, PEN), START, 0, interest, principal)


@pytest.mark.parametrize(
    "kind", [MovementKind.DISBURSEMENT, MovementKind.INTEREST, MovementKind.ADJUSTMENT]
)
def test_nonpayment_movement_cannot_have_parts(kind: MovementKind) -> None:
    with pytest.raises(InvalidSplitError):
        Movement(kind, Money(1, PEN), START, 0, Money(0, PEN), None)
    with pytest.raises(InvalidSplitError):
        Movement(kind, Money(1, PEN), START, 0, None, Money(1, PEN))


def test_split_parts_cannot_mix_currencies() -> None:
    with pytest.raises(CurrencyMismatchError):
        Movement(MovementKind.PAYMENT, Money(1, PEN), START, 0, Money(0, USD), Money(1, PEN))


@pytest.mark.parametrize("sequence", [-1, True, Decimal(1), "1"])
def test_invalid_sequence(sequence: object) -> None:
    with pytest.raises(InvalidMovementError):
        replace(disbursement(), sequence=cast(int, sequence))


def test_invalid_kind_and_naive_timestamp() -> None:
    with pytest.raises(InvalidMovementError):
        replace(disbursement(), kind=cast(MovementKind, "disbursement"))
    with pytest.raises(InvalidMovementError):
        replace(disbursement(), occurred_at=START.replace(tzinfo=None))
    assert issubclass(LedgerError, DomainError)
