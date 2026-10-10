"""Strict budget boundaries matching the frozen Phase 6 contract."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from monetae.api.schemas.accounts import MoneyAmount
from monetae.api.schemas.auth import Currency, StrictModel
from monetae.api.schemas.categories import JsonUUID
from monetae.api.schemas.common import Page
from monetae.api.schemas.loans import JsonDate, NonNegativeAmount, PositiveAmount
from monetae.api.schemas.reports import ReportTotal
from monetae.domain.budgets import BudgetPeriod, validate_dates

Scope = Literal["all", "selected"]
Name = Annotated[str, Field(min_length=1)]
Color = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class BudgetCategoryLimit(StrictModel):
    category_id: JsonUUID
    limit_amount: NonNegativeAmount


def validate_categories(limits: list[BudgetCategoryLimit]) -> None:
    if len({limit.category_id for limit in limits}) != len(limits):
        raise ValueError("category_limits must contain unique categories.")


class BudgetCreate(StrictModel):
    name: Name
    period: BudgetPeriod
    start_on: JsonDate
    end_on: JsonDate | None = None
    amount: PositiveAmount
    currency: Currency
    scope: Scope
    category_limits: list[BudgetCategoryLimit] = Field(default_factory=list)
    color: Color | None = None

    @model_validator(mode="after")
    def valid_create(self) -> "BudgetCreate":
        validate_dates(self.period, self.start_on, self.end_on)
        validate_categories(self.category_limits)
        return self


class BudgetUpdate(StrictModel):
    model_config = {"strict": True, "extra": "forbid", "json_schema_extra": {"minProperties": 1}}
    name: Name | None = None
    period: BudgetPeriod | None = None
    start_on: JsonDate | None = None
    end_on: JsonDate | None = None
    amount: PositiveAmount | None = None
    currency: Currency | None = None
    scope: Scope | None = None
    category_limits: list[BudgetCategoryLimit] | None = None
    color: Color | None = None

    @model_validator(mode="after")
    def valid_patch(self) -> "BudgetUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one property is required.")
        for field in self.model_fields_set - {"end_on", "color"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        if self.category_limits is not None:
            validate_categories(self.category_limits)
        return self


class Budget(StrictModel):
    name: Name
    period: BudgetPeriod
    start_on: date
    end_on: date | None
    amount: PositiveAmount
    currency: Currency
    scope: Scope
    category_limits: list[BudgetCategoryLimit]
    color: Color | None
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    spent_amount: NonNegativeAmount
    remaining_amount: MoneyAmount
    report_total: ReportTotal


class BudgetPage(Page[Budget]):
    pass


class TransactionAssignment(StrictModel):
    transaction_ids: list[JsonUUID] = Field(max_length=200, json_schema_extra={"uniqueItems": True})

    @model_validator(mode="after")
    def unique_ids(self) -> "TransactionAssignment":
        if len(set(self.transaction_ids)) != len(self.transaction_ids):
            raise ValueError("transaction_ids must be unique.")
        return self
