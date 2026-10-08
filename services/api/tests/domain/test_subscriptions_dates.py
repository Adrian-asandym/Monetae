from datetime import date, datetime

import pytest

from monetae.domain import PEN, Money
from monetae.domain.subscriptions import (
    Period,
    Subscription,
    SubscriptionValidationError,
    last_paid_on,
    next_after,
    occurrence,
    upcoming,
)


@pytest.mark.parametrize(
    ("anchor", "period", "interval", "n", "expected"),
    [
        (date(2023, 1, 31), Period.MONTHLY, 1, 0, date(2023, 1, 31)),
        (date(2023, 1, 31), Period.MONTHLY, 1, 1, date(2023, 2, 28)),
        (date(2024, 1, 31), Period.MONTHLY, 1, 1, date(2024, 2, 29)),
        (date(2023, 1, 31), Period.MONTHLY, 1, 2, date(2023, 3, 31)),
        (date(2023, 12, 31), Period.MONTHLY, 2, 1, date(2024, 2, 29)),
        (date(2023, 12, 31), Period.MONTHLY, 3, 1, date(2024, 3, 31)),
        (date(2024, 2, 29), Period.YEARLY, 1, 1, date(2025, 2, 28)),
        (date(2024, 2, 29), Period.YEARLY, 1, 4, date(2028, 2, 29)),
        (date(2024, 2, 29), Period.YEARLY, 2, 2, date(2028, 2, 29)),
        (date(2024, 2, 29), Period.YEARLY, 3, 1, date(2027, 2, 28)),
        (date(2024, 2, 29), Period.DAILY, 2, 1, date(2024, 3, 2)),
        (date(2024, 12, 31), Period.WEEKLY, 3, 1, date(2025, 1, 21)),
    ],
)
def test_occurrence(anchor: date, period: Period, interval: int, n: int, expected: date) -> None:
    assert occurrence(anchor, period, interval, n) == expected


@pytest.mark.parametrize("period", list(Period))
@pytest.mark.parametrize("interval", [1, 2, 3, 366])
def test_next_after_and_sixty_dates(period: Period, interval: int) -> None:
    anchor = date(2000, 1, 31)
    sub = Subscription("Calendar", Money(1, PEN), period, interval, anchor, anchor)
    assert next_after(sub, date(1999, 12, 31)) == anchor
    boundary = occurrence(anchor, period, interval, 1)
    assert next_after(sub, boundary) == occurrence(anchor, period, interval, 2)
    # The largest yearly interval exceeds the representable range over 60 dates.
    count = 10 if period == Period.YEARLY and interval == 366 else 60
    dates = upcoming(sub, boundary, count)
    assert len(dates) == count
    assert dates == [occurrence(anchor, period, interval, n) for n in range(2, count + 2)]
    after = date(2000, 2, 1)
    following = next_after(sub, after)
    assert following > after
    if period in (Period.MONTHLY, Period.YEARLY):
        assert following == occurrence(anchor, period, interval, 1)


@pytest.mark.parametrize("period", list(Period))
def test_date_overflow_is_domain_error(period: Period) -> None:
    with pytest.raises(SubscriptionValidationError):
        occurrence(date.max, period, 1, 1)


@pytest.mark.parametrize("count", [0, -1, 61, True])
def test_invalid_upcoming_count(count: int) -> None:
    sub = Subscription(
        "Calendar", Money(1, PEN), Period.MONTHLY, 1, date(2024, 1, 1), date(2024, 1, 1)
    )
    with pytest.raises(SubscriptionValidationError):
        upcoming(sub, date(2024, 1, 1), count)


def test_invalid_occurrence_inputs_and_datetime() -> None:
    with pytest.raises(SubscriptionValidationError):
        occurrence(date(2024, 1, 1), Period.MONTHLY, 1, -1)
    with pytest.raises(SubscriptionValidationError):
        occurrence(datetime(2024, 1, 1), Period.MONTHLY, 1, 0)
    with pytest.raises(SubscriptionValidationError):
        last_paid_on([datetime(2024, 1, 1)])
