"""Authenticated, read-only statistical reports."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from monetae.api.routers.auth import ERROR_RESPONSES
from monetae.api.schemas.auth import Currency
from monetae.api.schemas.reports import CashFlowRowPage, CategoryReportRowPage, Period
from monetae.api.security import Authenticated, Database, clock_for, settings_for
from monetae.reports.service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"], responses=ERROR_RESPONSES)


def report_service(request: Request, db: Database) -> ReportService:
    return ReportService(db, settings_for(request).secret_key, clock_for(request))


Reports = Annotated[ReportService, Depends(report_service)]


@router.get("/cash-flow", response_model=CashFlowRowPage, operation_id="get_reports_cash_flow")
def cash_flow(
    identity: Authenticated,
    service: Reports,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    report_currency: Currency | None = None,
    account_id: UUID | None = None,
    person_id: UUID | None = None,
    period: Period = "monthly",
) -> CashFlowRowPage:
    options = service.options(
        identity.user, date_from, date_to, period, report_currency, account_id, person_id
    )
    return service.cash_flow(identity.user, options, limit, cursor)


@router.get(
    "/categories", response_model=CategoryReportRowPage, operation_id="get_reports_categories"
)
def categories(
    identity: Authenticated,
    service: Reports,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    report_currency: Currency | None = None,
    account_id: UUID | None = None,
    person_id: UUID | None = None,
    period: Period | None = None,
) -> CategoryReportRowPage:
    options = service.options(
        identity.user, date_from, date_to, period, report_currency, account_id, person_id
    )
    return service.categories(identity.user, options, limit, cursor)
