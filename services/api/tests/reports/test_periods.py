from datetime import date

import pytest

from monetae.reports.periods import resolve_range
from monetae.services.auth import AuthError


def test_exactly_400_daily_buckets_are_allowed() -> None:
    _, _, buckets = resolve_range(date(2025, 1, 1), date(2026, 2, 4), "daily", date(2026, 1, 1))
    assert len(buckets) == 400
    with pytest.raises(AuthError) as error:
        resolve_range(date(2025, 1, 1), date(2026, 2, 5), "daily", date(2026, 1, 1))
    assert error.value.code == "range_too_large"


def test_leap_month_and_year_buckets() -> None:
    _, _, months = resolve_range(date(2024, 2, 1), date(2024, 3, 1), "monthly", date(2026, 1, 1))
    assert months[0].end_on == date(2024, 2, 29)
    assert months[1].start_on == months[1].end_on == date(2024, 3, 1)
    _, _, years = resolve_range(date(2023, 6, 1), date(2024, 3, 1), "yearly", date(2026, 1, 1))
    assert years[0].start_on == date(2023, 6, 1) and years[0].end_on == date(2023, 12, 31)
    assert years[1].start_on == date(2024, 1, 1) and years[1].end_on == date(2024, 3, 1)
