"""Cashew-style balance corrections with independently editable legs."""

import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field, model_validator

from monetae.api.schemas.accounts import MoneyAmount
from monetae.api.schemas.auth import Currency, StrictModel
from monetae.api.schemas.common import Page
from monetae.api.schemas.transactions import Timestamp, Transaction
from monetae.api.schemas.transfers import TransferCreate


class BalanceCorrectionCreate(TransferCreate):
    title: str = "Transferir saldo"
    to_occurred_at: Timestamp | None = None

    @model_validator(mode="after")
    def arrival_date(self) -> "BalanceCorrectionCreate":
        if self.to_occurred_at is None:
            self.to_occurred_at = self.occurred_at
        if self.to_occurred_at < self.occurred_at:
            raise ValueError("The arrival cannot precede the departure.")
        return self


class BalanceCorrection(StrictModel):
    group_id: UUID
    outgoing: Transaction
    incoming: Transaction


class BalanceCorrectionLeg(StrictModel):
    id: UUID
    account_id: UUID
    currency: Currency
    amount: MoneyAmount
    occurred_at: datetime


# A computed ratio is not a stored FX rate: extreme valid amounts may round
# to zero or exceed the precision of ExchangeRate (up to 18 integer digits).
ComputedRate = Annotated[str, Field(pattern=re.compile(r"^(?:0|[1-9][0-9]{0,17})\.[0-9]{6}$"))]


class BalanceCorrectionSummary(StrictModel):
    group_id: UUID
    outgoing: BalanceCorrectionLeg
    incoming: BalanceCorrectionLeg
    implicit_rate: ComputedRate


class BalanceCorrectionPage(Page[BalanceCorrectionSummary]):
    pass
