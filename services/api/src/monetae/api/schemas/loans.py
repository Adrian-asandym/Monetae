"""Bordes estrictos del contrato de préstamos, con dinero decimal en cadenas."""

import re
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field, model_validator

from monetae.api.schemas.accounts import MoneyAmount
from monetae.api.schemas.auth import Currency, StrictModel
from monetae.api.schemas.categories import JsonUUID
from monetae.api.schemas.common import Page
from monetae.api.schemas.transactions import ExchangeRate, RateSource, Timestamp

PositiveAmount = Annotated[
    str, Field(pattern=re.compile(r"^(?:0\.(?:0[1-9]|[1-9][0-9])|[1-9][0-9]{0,15}\.[0-9]{2})$"))
]
NonNegativeAmount = Annotated[str, Field(pattern=re.compile(r"^(?:0|[1-9][0-9]{0,15})\.[0-9]{2}$"))]
Percentage = Annotated[str, Field(pattern=re.compile(r"^(?:0|[1-9][0-9]*)\.[0-9]{6}$"))]
Direction = Literal["lent", "borrowed"]
LoanStatus = Literal["open", "settled"]


def parse_date(value: object) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError("An ISO date is required.")


JsonDate = Annotated[date, BeforeValidator(parse_date)]


class MovementRequest(StrictModel):
    amount_in_loan_currency: PositiveAmount
    occurred_at: Timestamp
    note: str | None = None


class CashRequest(MovementRequest):
    account_id: JsonUUID
    account_amount: PositiveAmount
    account_currency: Currency
    fx_rate_to_base: ExchangeRate
    fx_rate_source: RateSource
    fx_rate_applied: ExchangeRate | None = None


class DisbursementRequest(CashRequest):
    kind: Literal["disbursement"]


class PaymentRequest(CashRequest):
    kind: Literal["payment"]
    interest_part: NonNegativeAmount | None = None
    principal_part: NonNegativeAmount | None = None
    excess_handling: Literal["adjustment", "income_expense"] | None = None

    @model_validator(mode="after")
    def paired_split(self) -> "PaymentRequest":
        if (self.interest_part is None) != (self.principal_part is None):
            raise ValueError("Both split parts must be provided together.")
        for field in ("interest_part", "principal_part", "excess_handling"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class InterestRequest(MovementRequest):
    kind: Literal["interest"]


class AdjustmentRequest(MovementRequest):
    kind: Literal["adjustment"]
    amount_in_loan_currency: MoneyAmount


class WriteOffRequest(MovementRequest):
    kind: Literal["write_off"]
    interest_part: NonNegativeAmount
    principal_part: NonNegativeAmount


MovementCreate = Annotated[
    DisbursementRequest | PaymentRequest | InterestRequest | AdjustmentRequest | WriteOffRequest,
    Field(discriminator="kind"),
]


class LoanCreate(StrictModel):
    person_id: JsonUUID
    direction: Direction
    currency: Currency
    principal: PositiveAmount
    opened_on: JsonDate
    due_on: JsonDate | None = None
    note: str | None = None
    disbursement: DisbursementRequest


class LoanUpdate(StrictModel):
    person_id: JsonUUID | None = None
    opened_on: JsonDate | None = None
    due_on: JsonDate | None = None
    note: str | None = None

    @model_validator(mode="after")
    def required_metadata(self) -> "LoanUpdate":
        for name in {"person_id", "opened_on"} & self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null.")
        return self


class Loan(StrictModel):
    person_id: UUID
    direction: Direction
    currency: Currency
    principal: PositiveAmount
    opened_on: date
    due_on: date | None
    note: str | None
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    status: LoanStatus
    outstanding: NonNegativeAmount


class LoanSideEffect(StrictModel):
    kind: Literal["adjustment", "income", "expense"]
    transaction_id: UUID | None
    account_id: UUID | None
    amount: PositiveAmount
    currency: Currency
    adjustment_id: UUID | None


class LoanMovement(StrictModel):
    kind: Literal["disbursement", "payment", "interest", "adjustment", "write_off"]
    amount_in_loan_currency: MoneyAmount
    occurred_at: datetime
    note: str | None
    account_id: UUID | None
    account_amount: PositiveAmount | None
    account_currency: Currency | None
    fx_rate_to_base: ExchangeRate | None
    fx_rate_source: RateSource | None
    fx_rate_applied: ExchangeRate | None
    interest_part: NonNegativeAmount | None
    principal_part: NonNegativeAmount | None
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    loan_id: UUID
    transaction_id: UUID | None
    running_balance: NonNegativeAmount
    side_effects: list[LoanSideEffect]


class LoanBalance(StrictModel):
    loan_id: UUID
    currency: Currency
    principal: PositiveAmount
    interest_total: NonNegativeAmount
    adjustment_total: MoneyAmount
    payment_total: NonNegativeAmount
    write_off_total: NonNegativeAmount
    outstanding: NonNegativeAmount
    status: LoanStatus


class PaymentProposalRequest(StrictModel):
    amount_in_loan_currency: PositiveAmount


class PaymentProposal(StrictModel):
    amount_in_loan_currency: PositiveAmount
    interest_part: NonNegativeAmount
    principal_part: NonNegativeAmount
    outstanding: NonNegativeAmount


class InterestProposalRequest(StrictModel):
    percentage: Percentage


class InterestProposal(StrictModel):
    percentage: Percentage
    outstanding: NonNegativeAmount
    amount_in_loan_currency: NonNegativeAmount
    currency: Currency


class LoanSummary(StrictModel):
    person_id: UUID
    currency: Currency
    lent_outstanding: NonNegativeAmount
    borrowed_outstanding: NonNegativeAmount
    open_count: int = Field(ge=0)
    settled_count: int = Field(ge=0)


class LoanPage(Page[Loan]):
    pass


class LoanMovementPage(Page[LoanMovement]):
    pass


class LoanSummaryPage(Page[LoanSummary]):
    pass
