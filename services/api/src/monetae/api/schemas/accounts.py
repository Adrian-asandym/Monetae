from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from monetae.api.schemas.auth import Currency, StrictModel
from monetae.api.schemas.common import Page

MoneyAmount = Annotated[str, Field(pattern=r"^-?(0|[1-9][0-9]{0,15})\.[0-9]{2}$")]
AccountType = Literal["cash", "bank", "wallet", "card", "other"]


class AccountCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    type: AccountType
    currency: Currency
    initial_balance: MoneyAmount
    color: str | None = None
    icon: str | None = None
    sort_order: int = 0


class AccountUpdate(StrictModel):
    model_config = {"strict": True, "extra": "forbid", "json_schema_extra": {"minProperties": 1}}
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: AccountType | None = None
    currency: Currency | None = None
    initial_balance: MoneyAmount | None = None
    color: str | None = None
    icon: str | None = None
    sort_order: int | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "AccountUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one property is required.")
        for field in ("name", "type", "currency", "initial_balance", "sort_order"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class Account(StrictModel):
    name: str
    type: AccountType
    currency: Currency
    initial_balance: MoneyAmount
    color: str | None
    icon: str | None
    sort_order: int
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    balance: MoneyAmount
    archived_at: datetime | None


class AccountPage(Page[Account]):
    pass
