"""Literal anchored cycle examples, including clamping without anchor drift."""

from datetime import date

import pytest

from monetae.domain.budgets import BudgetPeriod, current_cycle


@pytest.mark.parametrize(
    "period,start,end,today,first,last",
    [
        ("daily", "2026-10-01", None, "2026-10-07", "2026-10-07", "2026-10-07"),
        ("weekly", "2026-10-01", None, "2026-10-07", "2026-10-01", "2026-10-07"),
        ("weekly", "2026-10-01", None, "2026-10-08", "2026-10-08", "2026-10-14"),
        ("weekly", "2026-12-30", None, "2027-01-01", "2026-12-30", "2027-01-05"),
        ("monthly", "2026-01-31", None, "2026-02-27", "2026-01-31", "2026-02-27"),
        ("monthly", "2026-01-31", None, "2026-02-28", "2026-02-28", "2026-03-30"),
        ("monthly", "2026-01-31", None, "2026-03-31", "2026-03-31", "2026-04-29"),
        ("monthly", "2024-01-31", None, "2024-02-29", "2024-02-29", "2024-03-30"),
        ("monthly", "2024-02-29", None, "2025-02-28", "2025-02-28", "2025-03-28"),
        ("monthly", "2024-02-29", None, "2025-03-29", "2025-03-29", "2025-04-28"),
        ("monthly", "2026-12-31", None, "2027-01-30", "2026-12-31", "2027-01-30"),
        ("monthly", "2026-12-31", None, "2027-01-31", "2027-01-31", "2027-02-27"),
        ("monthly", "2026-04-30", None, "2026-05-30", "2026-05-30", "2026-06-29"),
        ("monthly", "2026-01-15", "2026-02-20", "2026-03-01", "2026-02-15", "2026-02-20"),
        ("weekly", "2026-10-01", "2026-10-10", "2026-10-20", "2026-10-08", "2026-10-10"),
        ("daily", "2026-10-01", "2026-10-10", "2026-10-20", "2026-10-10", "2026-10-10"),
        ("weekly", "2026-10-01", "2026-10-07", "2026-10-08", "2026-10-01", "2026-10-07"),
        ("monthly", "2026-01-31", "2026-02-28", "2026-03-31", "2026-02-28", "2026-02-28"),
        ("daily", "2026-10-01", None, "2026-09-01", "2026-10-01", "2026-10-01"),
        ("weekly", "2026-10-01", None, "2026-09-01", "2026-10-01", "2026-10-07"),
        ("monthly", "2026-10-31", None, "2026-09-01", "2026-10-31", "2026-11-29"),
        ("custom", "2026-10-01", "2026-10-10", "2026-09-01", "2026-10-01", "2026-10-10"),
        ("custom", "2026-10-01", "2026-10-10", "2026-10-07", "2026-10-01", "2026-10-10"),
        ("custom", "2026-10-01", "2026-10-10", "2026-11-01", "2026-10-01", "2026-10-10"),
    ],
)
def test_current_cycle(
    period: BudgetPeriod, start: str, end: str | None, today: str, first: str, last: str
) -> None:
    cycle = current_cycle(
        period,
        date.fromisoformat(start),
        date.fromisoformat(end) if end else None,
        date.fromisoformat(today),
    )
    assert cycle.start == date.fromisoformat(first)
    assert cycle.end == date.fromisoformat(last)


@pytest.mark.parametrize(
    "period,end",
    [
        ("custom", None),
        ("daily", "2026-09-01"),
        ("weekly", "2026-09-01"),
        ("monthly", "2026-09-01"),
        ("custom", "2026-09-01"),
    ],
)
def test_invalid_dates(period: BudgetPeriod, end: str | None) -> None:
    with pytest.raises(ValueError):
        current_cycle(
            period, date(2026, 10, 1), date.fromisoformat(end) if end else None, date(2026, 10, 7)
        )
