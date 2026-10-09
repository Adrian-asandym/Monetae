"""Report response models matching the frozen OpenAPI contract."""

from datetime import date
from typing import Literal
from uuid import UUID

from monetae.api.schemas.auth import StrictModel
from monetae.api.schemas.common import Page
from monetae.api.schemas.subscriptions import CurrencyTotal, Period, ReportTotal

ReportKind = Literal["income", "expense"]


class CashFlowRow(StrictModel):
    start_on: date
    end_on: date
    income: ReportTotal
    expense: ReportTotal
    net: ReportTotal
    cumulative_net: ReportTotal


class CategoryReportRow(StrictModel):
    category_id: UUID | None
    kind: ReportKind
    start_on: date
    end_on: date
    total: ReportTotal


class CashFlowRowPage(Page[CashFlowRow]):
    pass


class CategoryReportRowPage(Page[CategoryReportRow]):
    pass


__all__ = [
    "CashFlowRow",
    "CashFlowRowPage",
    "CategoryReportRow",
    "CategoryReportRowPage",
    "CurrencyTotal",
    "Period",
    "ReportKind",
    "ReportTotal",
]
