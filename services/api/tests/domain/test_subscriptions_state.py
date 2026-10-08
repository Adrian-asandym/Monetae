from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime
from typing import Literal, cast

import pytest

from monetae.domain import PEN, DomainError, Money
from monetae.domain.subscriptions import (
    Period,
    Subscription,
    SubscriptionStateError,
    SubscriptionValidationError,
    archive,
    historical_paid,
    matching_archived,
    reactivate,
    totals,
)


def netflix() -> Subscription:
    return Subscription(
        "Netflix",
        Money.parse("44.90", PEN),
        Period.MONTHLY,
        1,
        date(2024, 4, 30),
        date(2024, 1, 31),
    )


def test_spec_archive_preserves_history_and_reactivation_restores_totals() -> None:
    sub = netflix()
    payments = (Money.parse("44.90", PEN),) * 3
    at = datetime(2024, 4, 1, tzinfo=UTC)
    archived = archive(sub, at, "Paused")
    assert archived.status == "archived"
    assert archived.archived_at == at
    assert archived.archive_reason == "Paused"
    assert archived.anchor_on == sub.anchor_on
    assert archived.next_due_on == sub.next_due_on
    assert sub.status == "active"
    assert sub.archived_at is None
    assert totals([archived]) == {}
    assert historical_paid(payments, PEN) == Money.parse("134.70", PEN)
    assert len(payments) == 3
    assert matching_archived("Netflix", [archived]) == [archived]
    active = reactivate(archived, date(2024, 5, 31))
    assert active.status == "active"
    assert active.archived_at is None and active.archive_reason is None
    assert active.anchor_on == sub.anchor_on
    assert active.next_due_on == date(2024, 5, 31)
    assert archived.status == "archived"
    assert totals([active]) == totals([sub])
    assert historical_paid(payments, PEN) == Money.parse("134.70", PEN)
    attribute = "title"
    with pytest.raises(FrozenInstanceError):
        setattr(sub, attribute, "Changed")
    with pytest.raises(SubscriptionStateError):
        archive(archived, at)
    with pytest.raises(SubscriptionStateError):
        reactivate(active, date(2024, 6, 30))


@pytest.mark.parametrize("interval", [0, -1, 367, True])
def test_invalid_intervals(interval: int) -> None:
    with pytest.raises(SubscriptionValidationError):
        replace(netflix(), interval_count=interval)


@pytest.mark.parametrize("title", ["", "   ", "\n\t"])
def test_invalid_title(title: str) -> None:
    with pytest.raises(SubscriptionValidationError):
        replace(netflix(), title=title)


@pytest.mark.parametrize("amount", [0, -1])
def test_invalid_amount(amount: int) -> None:
    with pytest.raises(SubscriptionValidationError):
        replace(netflix(), amount=Money(amount, PEN))


def test_archive_metadata_validation() -> None:
    sub = netflix()
    at = datetime(2024, 1, 1, tzinfo=UTC)
    with pytest.raises(DomainError):
        archive(sub, datetime(2024, 1, 1))
    with pytest.raises(DomainError):
        archive(sub, at, "x" * 501)
    assert archive(sub, at, "x" * 500).archive_reason == "x" * 500
    with pytest.raises(DomainError):
        replace(sub, archived_at=at)
    with pytest.raises(DomainError):
        replace(sub, archive_reason="Reason")
    with pytest.raises(DomainError):
        replace(sub, status="archived")
    with pytest.raises(DomainError):
        replace(sub, archived_at=datetime(2024, 1, 1))
    with pytest.raises(DomainError):
        replace(sub, status=cast(Literal["active", "archived"], "invalid"))
    with pytest.raises(DomainError):
        replace(sub, period=cast(Period, "monthly"))
    with pytest.raises(DomainError):
        replace(sub, next_due_on=datetime(2024, 1, 1))
    assert replace(sub, interval_count=366).interval_count == 366
