"""Bordes estrictos de suscripciones y compromisos separados por moneda."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from monetae.api.schemas.accounts import MoneyAmount
from monetae.api.schemas.auth import Currency, StrictModel
from monetae.api.schemas.categories import JsonUUID
from monetae.api.schemas.common import Page
from monetae.api.schemas.loans import JsonDate, NonNegativeAmount, PositiveAmount
from monetae.api.schemas.transactions import ExchangeRate

Period = Literal["daily", "weekly", "monthly", "yearly"]
SubscriptionStatus = Literal["active", "archived"]
Interval = Annotated[int, Field(ge=1, le=366)]
Reminder = Annotated[int, Field(ge=0)]
Title = Annotated[str, Field(min_length=1)]


class SubscriptionCreate(StrictModel):
    title: Title
    amount: PositiveAmount
    currency: Currency
    account_id: JsonUUID
    category_id: JsonUUID | None = None
    period: Period
    interval_count: Interval = 1
    next_due_on: JsonDate
    reminder_days_before: Reminder | None = None
    # Ampliación aditiva autorizada: tasa provisional, confirmada al publicar.
    fx_rate_to_base: ExchangeRate | None = None

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title must not be blank.")
        return value


class SubscriptionUpdate(StrictModel):
    title: Title | None = None
    amount: PositiveAmount | None = None
    currency: Currency | None = None
    account_id: JsonUUID | None = None
    category_id: JsonUUID | None = None
    period: Period | None = None
    interval_count: Interval | None = None
    next_due_on: JsonDate | None = None
    reminder_days_before: Reminder | None = None
    fx_rate_to_base: ExchangeRate | None = None

    @model_validator(mode="after")
    def valid_patch(self) -> "SubscriptionUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one property is required.")
        for field in self.model_fields_set - {"category_id", "reminder_days_before"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        if self.title is not None and not self.title.strip():
            raise ValueError("Title must not be blank.")
        return self


class ArchiveRequest(StrictModel):
    reason: Annotated[str, Field(max_length=500)] | None = None


class Subscription(StrictModel):
    title: Title
    amount: PositiveAmount
    currency: Currency
    account_id: UUID
    category_id: UUID | None
    period: Period
    interval_count: Interval
    next_due_on: date
    reminder_days_before: Reminder | None
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    status: SubscriptionStatus
    archived_at: datetime | None
    archive_reason: str | None
    recurring_rule_id: UUID | None
    historical_paid: NonNegativeAmount
    last_paid_on: date | None


class CurrencyTotal(StrictModel):
    currency: Currency
    amount: MoneyAmount


class ReportTotal(StrictModel):
    by_currency: list[CurrencyTotal]
    report_currency: Currency
    report_amount: MoneyAmount
    unconverted_count: int = Field(ge=0)


class SubscriptionTotal(StrictModel):
    currency: Currency
    monthly_amount: NonNegativeAmount
    yearly_amount: NonNegativeAmount
    active_count: int = Field(ge=0)
    monthly_total: ReportTotal
    yearly_total: ReportTotal


class SubscriptionPage(Page[Subscription]):
    pass


class SubscriptionTotalPage(Page[SubscriptionTotal]):
    pass
