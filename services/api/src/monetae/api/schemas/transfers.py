import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field, model_validator

from monetae.api.schemas.auth import StrictModel
from monetae.api.schemas.categories import JsonUUID
from monetae.api.schemas.common import Page
from monetae.api.schemas.transactions import ExchangeRate, RateSource, Timestamp

PositiveAmount = Annotated[
    str, Field(pattern=re.compile(r"^(?:0\.(?!00)[0-9]{2}|[1-9][0-9]{0,15}\.[0-9]{2})$"))
]


class TransferCreate(StrictModel):
    from_account_id: JsonUUID
    to_account_id: JsonUUID
    from_amount: PositiveAmount
    to_amount: PositiveAmount
    from_fx_rate_to_base: ExchangeRate
    to_fx_rate_to_base: ExchangeRate
    fx_rate_source: RateSource
    occurred_at: Timestamp
    title: str
    note: str | None = None


class TransferUpdate(StrictModel):
    model_config = {"strict": True, "extra": "forbid", "json_schema_extra": {"minProperties": 1}}
    from_account_id: JsonUUID | None = None
    to_account_id: JsonUUID | None = None
    from_amount: PositiveAmount | None = None
    to_amount: PositiveAmount | None = None
    from_fx_rate_to_base: ExchangeRate | None = None
    to_fx_rate_to_base: ExchangeRate | None = None
    fx_rate_source: RateSource | None = None
    occurred_at: Timestamp | None = None
    title: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "TransferUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one property is required.")
        for field in self.model_fields_set - {"note"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class Transfer(StrictModel):
    from_account_id: UUID
    to_account_id: UUID
    from_amount: PositiveAmount
    to_amount: PositiveAmount
    from_fx_rate_to_base: ExchangeRate
    to_fx_rate_to_base: ExchangeRate
    fx_rate_source: RateSource
    occurred_at: datetime
    title: str
    note: str | None
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    outgoing_transaction_id: UUID
    incoming_transaction_id: UUID
    implicit_rate: ExchangeRate


class TransferPage(Page[Transfer]):
    pass
