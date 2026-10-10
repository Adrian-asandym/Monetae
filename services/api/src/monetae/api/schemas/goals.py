"""Strict goal boundaries matching the frozen Phase 6 contract."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from monetae.api.schemas.accounts import MoneyAmount
from monetae.api.schemas.auth import Currency, StrictModel
from monetae.api.schemas.budgets import Color, Name
from monetae.api.schemas.budgets import TransactionAssignment as TransactionAssignment
from monetae.api.schemas.common import Page
from monetae.api.schemas.loans import JsonDate, PositiveAmount
from monetae.api.schemas.reports import ReportTotal

Kind = Literal["spend", "save"]
Icon = Annotated[str, Field(min_length=1, max_length=64)]


class GoalCreate(StrictModel):
    name: Name
    kind: Kind
    target_amount: PositiveAmount
    currency: Currency
    due_on: JsonDate | None = None
    color: Color | None = None
    icon: Icon | None = None


class GoalUpdate(StrictModel):
    model_config = {"strict": True, "extra": "forbid", "json_schema_extra": {"minProperties": 1}}
    name: Name | None = None
    kind: Kind | None = None
    target_amount: PositiveAmount | None = None
    currency: Currency | None = None
    due_on: JsonDate | None = None
    color: Color | None = None
    icon: Icon | None = None

    @model_validator(mode="after")
    def valid_patch(self) -> "GoalUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one property is required.")
        for field in self.model_fields_set - {"due_on", "color", "icon"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class Goal(StrictModel):
    name: Name
    kind: Kind
    target_amount: PositiveAmount
    currency: Currency
    due_on: date | None
    color: Color | None
    icon: Icon | None
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    progress_amount: MoneyAmount
    report_total: ReportTotal


class GoalPage(Page[Goal]):
    pass
