"""Calendar buckets in the user's timezone, with bounded inclusive ranges."""

from dataclasses import dataclass
from datetime import date, timedelta

from monetae.api.schemas.reports import Period
from monetae.services.auth import AuthError


@dataclass(frozen=True)
class Bucket:
    start_on: date
    end_on: date


def period_start(day: date, period: Period) -> date:
    match period:
        case "daily":
            return day
        case "weekly":
            return day - timedelta(days=day.weekday())
        case "monthly":
            return day.replace(day=1)
        case "yearly":
            return day.replace(month=1, day=1)


def shift_period(start: date, period: Period, count: int) -> date:
    match period:
        case "daily":
            return start + timedelta(days=count)
        case "weekly":
            return start + timedelta(weeks=count)
        case "monthly":
            index = start.year * 12 + start.month - 1 + count
            year, month = divmod(index, 12)
            return date(year, month + 1, 1)
        case "yearly":
            return date(start.year + count, 1, 1)


def resolve_range(
    date_from: date | None, date_to: date | None, period: Period | None, today: date
) -> tuple[date, date, list[Bucket]]:
    end = date_to or today
    reference = period or "monthly"
    try:
        start = date_from or shift_period(period_start(end, reference), reference, -11)
        if start > end:
            raise AuthError(422, "invalid_date_range", "date_from must not exceed date_to.")
        # Inclusive query bounds require an exclusive next day representable by datetime.
        if end == date.max:
            raise ValueError
        if period is None:
            return start, end, [Bucket(start, end)]
        buckets: list[Bucket] = []
        current = period_start(start, period)
        while current <= end:
            if len(buckets) == 400:
                raise AuthError(422, "range_too_large", "The range exceeds 400 periods.")
            following = shift_period(current, period, 1)
            buckets.append(Bucket(max(start, current), min(end, following - timedelta(days=1))))
            current = following
        return start, end, buckets
    except (ValueError, OverflowError) as exc:
        raise AuthError(422, "invalid_date_range", "The date range is not representable.") from exc
