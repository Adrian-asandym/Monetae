"""Anchored budget cycles, independent of storage and presentation timezones."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

BudgetPeriod = Literal["daily", "weekly", "monthly", "custom"]


@dataclass(frozen=True)
class BudgetCycle:
    start: date
    end: date


def validate_dates(period: BudgetPeriod, start: date, end: date | None) -> None:
    if period == "custom" and end is None:
        raise ValueError("Custom budgets require end_on.")
    if end is not None and end < start:
        raise ValueError("end_on must be on or after start_on.")


def month_anchor(start: date, offset: int) -> date:
    year, month = divmod(start.year * 12 + start.month - 1 + offset, 12)
    return date(year, month + 1, min(start.day, monthrange(year, month + 1)[1]))


def current_cycle(period: BudgetPeriod, start: date, end: date | None, today: date) -> BudgetCycle:
    validate_dates(period, start, end)
    if period == "custom":
        assert end is not None
        return BudgetCycle(start, end)
    target = max(start, min(today, end) if end is not None else today)
    if period == "monthly":
        offset = (target.year - start.year) * 12 + target.month - start.month
        if month_anchor(start, offset) > target:
            offset -= 1
        first = month_anchor(start, offset)
        last = month_anchor(start, offset + 1) - timedelta(days=1)
    else:
        days = 1 if period == "daily" else 7
        first = start + timedelta(days=((target - start).days // days) * days)
        last = first + timedelta(days=days - 1)
    return BudgetCycle(first, min(last, end) if end is not None else last)
