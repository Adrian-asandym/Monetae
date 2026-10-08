"""Reglas puras de suscripciones; las transacciones pertenecen al libro mayor."""

from __future__ import annotations

import calendar
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from enum import StrEnum
from math import lcm
from typing import Literal

from .currency import Currency
from .errors import DomainError
from .money import Money


class SubscriptionValidationError(DomainError):
    """Datos inválidos para una suscripción o su calendario."""


class SubscriptionStateError(DomainError):
    """La transición solicitada no parte del estado requerido."""


class Period(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


def _integer(value: int, minimum: int, maximum: int | None = None) -> None:
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise SubscriptionValidationError("Integer outside allowed range")


def _date(value: date) -> None:
    if type(value) is not date:
        raise SubscriptionValidationError("Expected a date, without a time component")


def _schedule(period: Period, interval_count: int) -> None:
    if not isinstance(period, Period):
        raise SubscriptionValidationError("Expected a Period")
    _integer(interval_count, 1, 366)


@dataclass(frozen=True, slots=True)
class Subscription:
    title: str
    amount: Money
    period: Period
    interval_count: int
    next_due_on: date
    anchor_on: date
    status: Literal["active", "archived"] = "active"
    archived_at: datetime | None = None
    archive_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise SubscriptionValidationError("Title must not be empty")
        if not isinstance(self.amount, Money) or self.amount.amount <= 0:
            raise SubscriptionValidationError("Subscription amount must be positive Money")
        _schedule(self.period, self.interval_count)
        _date(self.next_due_on)
        _date(self.anchor_on)
        if self.status not in ("active", "archived"):
            raise SubscriptionValidationError("Invalid subscription status")
        if self.archive_reason is not None and (
            not isinstance(self.archive_reason, str) or len(self.archive_reason) > 500
        ):
            raise SubscriptionValidationError("Archive reason must have at most 500 characters")
        if self.archived_at is not None and (
            not isinstance(self.archived_at, datetime) or self.archived_at.utcoffset() is None
        ):
            raise SubscriptionValidationError("Archive timestamp must be timezone aware")
        if self.status == "active" and (
            self.archived_at is not None or self.archive_reason is not None
        ):
            raise SubscriptionValidationError("Active subscriptions cannot have archive metadata")
        if self.status == "archived" and self.archived_at is None:
            raise SubscriptionValidationError("Archived subscriptions require a timestamp")


def _monthly_ratio(sub: Subscription) -> tuple[Decimal, int]:
    # Keep division until the final result: repeating decimals could otherwise
    # move an exact half-cent below the ROUND_HALF_UP boundary when aggregated.
    if sub.period == Period.YEARLY:
        return sub.amount.amount, sub.interval_count * 12
    factor = {
        Period.DAILY: Decimal("30.4375"),
        Period.WEEKLY: Decimal("4.348125"),
        Period.MONTHLY: Decimal(1),
    }[sub.period]
    return sub.amount.amount * factor, sub.interval_count


def monthly_equivalent(sub: Subscription) -> Money:
    with localcontext(Context(prec=256, rounding=ROUND_HALF_UP)):
        numerator, denominator = _monthly_ratio(sub)
        return Money(numerator / Decimal(denominator), sub.amount.currency)


def yearly_equivalent(sub: Subscription) -> Money:
    with localcontext(Context(prec=256, rounding=ROUND_HALF_UP)):
        numerator, denominator = _monthly_ratio(sub)
        return Money(numerator * Decimal(12) / Decimal(denominator), sub.amount.currency)


def totals(subscriptions: Iterable[Subscription]) -> dict[Currency, tuple[Money, Money, int]]:
    """Suma equivalentes exactos; redondea una vez por total y moneda."""
    raw: dict[Currency, tuple[Decimal, int, int]] = {}
    # Denominators divide lcm(1..366)*12 (< 170 digits). 256 digits cover
    # the common denominator, NUMERIC(18,2), factors and practical counts.
    with localcontext(Context(prec=256, rounding=ROUND_HALF_UP)):
        for sub in subscriptions:
            if sub.status != "active":
                continue
            currency = sub.amount.currency
            numerator, denominator = _monthly_ratio(sub)
            previous, previous_denominator, count = raw.get(currency, (Decimal(0), 1, 0))
            common = lcm(denominator, previous_denominator)
            total = previous * Decimal(common // previous_denominator) + numerator * Decimal(
                common // denominator
            )
            raw[currency] = (total, common, count + 1)
        return {
            currency: (
                Money(numerator / Decimal(denominator), currency),
                Money(numerator * Decimal(12) / Decimal(denominator), currency),
                count,
            )
            for currency, (numerator, denominator, count) in raw.items()
        }


def archive(sub: Subscription, at: datetime, reason: str | None = None) -> Subscription:
    if sub.status != "active":
        raise SubscriptionStateError("Subscription is already archived")
    if not isinstance(at, datetime) or at.utcoffset() is None:
        raise SubscriptionValidationError("Archive timestamp must be timezone aware")
    return replace(sub, status="archived", archived_at=at, archive_reason=reason)


def reactivate(sub: Subscription, next_due_on: date) -> Subscription:
    if sub.status != "archived":
        raise SubscriptionStateError("Subscription is already active")
    return replace(
        sub, status="active", next_due_on=next_due_on, archived_at=None, archive_reason=None
    )


def occurrence(anchor_on: date, period: Period, interval_count: int, n: int) -> date:
    """Ocurrencia de índice cero: n=0 es el ancla, sin deriva por meses cortos."""
    _date(anchor_on)
    _schedule(period, interval_count)
    _integer(n, 0)
    try:
        if period in (Period.DAILY, Period.WEEKLY):
            days = interval_count * n * (7 if period == Period.WEEKLY else 1)
            return anchor_on + timedelta(days=days)
        months = interval_count * n * (12 if period == Period.YEARLY else 1)
        year, month_index = divmod(anchor_on.year * 12 + anchor_on.month - 1 + months, 12)
        month = month_index + 1
        day = min(anchor_on.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    except (OverflowError, ValueError) as error:
        raise SubscriptionValidationError("Occurrence exceeds supported date range") from error


def _next_index(sub: Subscription, after: date) -> int:
    _date(after)
    if after < sub.anchor_on:
        return 0
    if sub.period in (Period.DAILY, Period.WEEKLY):
        step = sub.interval_count * (7 if sub.period == Period.WEEKLY else 1)
        return (after - sub.anchor_on).days // step + 1
    months = (after.year - sub.anchor_on.year) * 12 + after.month - sub.anchor_on.month
    step = sub.interval_count * (12 if sub.period == Period.YEARLY else 1)
    index = months // step
    if occurrence(sub.anchor_on, sub.period, sub.interval_count, index) <= after:
        index += 1
    return index


def next_after(sub: Subscription, after: date) -> date:
    """Primera fecha del calendario anclado > after, independiente del estado.

    La capa de servicios solo programa cobros para suscripciones activas.
    """
    return occurrence(sub.anchor_on, sub.period, sub.interval_count, _next_index(sub, after))


def upcoming(sub: Subscription, after: date, count: int) -> list[date]:
    """Siguientes fechas matemáticas del calendario; no crea cobros programados."""
    _integer(count, 1, 60)
    first = _next_index(sub, after)
    return [
        occurrence(sub.anchor_on, sub.period, sub.interval_count, n)
        for n in range(first, first + count)
    ]


def normalize_title(title: str) -> str:
    if not isinstance(title, str):
        raise SubscriptionValidationError("Title must be a string")
    normalized = unicodedata.normalize("NFD", title.casefold())
    return " ".join("".join(c for c in normalized if not unicodedata.combining(c)).split())


def matching_archived(title: str, archived: Iterable[Subscription]) -> list[Subscription]:
    normalized = normalize_title(title)
    if not normalized:
        return []
    return [
        sub
        for sub in archived
        if sub.status == "archived" and normalize_title(sub.title) == normalized
    ]


def historical_paid(payments: Iterable[Money], currency: Currency) -> Money:
    return Money.sum(payments, currency)


def last_paid_on(dates: Iterable[date]) -> date | None:
    latest: date | None = None
    for paid_on in dates:
        _date(paid_on)
        if latest is None or paid_on > latest:
            latest = paid_on
    return latest
