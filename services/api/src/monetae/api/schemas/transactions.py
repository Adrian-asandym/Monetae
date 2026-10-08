import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BeforeValidator, Field, field_validator, model_validator

from monetae.api.schemas.accounts import MoneyAmount
from monetae.api.schemas.auth import Currency, StrictModel
from monetae.api.schemas.categories import JsonUUID
from monetae.api.schemas.common import Page

TransactionKind = Literal["income", "expense", "transfer", "loan"]
DirectKind = Literal["income", "expense"]
TransactionStatus = Literal["posted", "scheduled"]
RateSource = Literal["manual", "auto"]
ExchangeRate = Annotated[
    str, Field(pattern=re.compile(r"^(?:0\.(?!000000)[0-9]{6}|[1-9][0-9]{0,11}\.[0-9]{6})$"))
]
TagIds = Annotated[list[JsonUUID], Field(json_schema_extra={"uniqueItems": True})]


def parse_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value)
    else:
        raise ValueError("An ISO timestamp with timezone is required.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("A timezone is required.")
    return parsed.astimezone(UTC)


Timestamp = Annotated[AwareDatetime, BeforeValidator(parse_timestamp)]


class TagAssignment(StrictModel):
    tag_ids: list[JsonUUID]


class TransactionCreate(StrictModel):
    account_id: JsonUUID
    category_id: JsonUUID | None = None
    kind: DirectKind
    amount: MoneyAmount
    currency: Currency
    occurred_at: Timestamp
    status: TransactionStatus
    title: str
    note: str | None = None
    fx_rate_to_base: ExchangeRate
    fx_rate_source: RateSource
    tag_ids: TagIds = Field(default_factory=list)

    @field_validator("occurred_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @field_validator("tag_ids")
    @classmethod
    def unique_tags(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("tag_ids must be unique.")
        return value


class TransactionUpdate(StrictModel):
    model_config = {"strict": True, "extra": "forbid", "json_schema_extra": {"minProperties": 1}}
    account_id: JsonUUID | None = None
    kind: DirectKind | None = None
    category_id: JsonUUID | None = None
    amount: MoneyAmount | None = None
    occurred_at: Timestamp | None = None
    status: TransactionStatus | None = None
    title: str | None = None
    note: str | None = None
    fx_rate_to_base: ExchangeRate | None = None
    fx_rate_source: RateSource | None = None
    tag_ids: TagIds | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "TransactionUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one property is required.")
        for field in self.model_fields_set - {"note", "category_id"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        if self.tag_ids is not None and len(self.tag_ids) != len(set(self.tag_ids)):
            raise ValueError("tag_ids must be unique.")
        return self


class Transaction(StrictModel):
    account_id: JsonUUID
    category_id: JsonUUID | None
    kind: TransactionKind
    amount: MoneyAmount
    currency: Currency
    occurred_at: datetime
    status: TransactionStatus
    title: str
    note: str | None
    fx_rate_to_base: ExchangeRate
    fx_rate_source: RateSource
    tag_ids: TagIds
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    transfer_group_id: UUID | None
    recurring_rule_id: UUID | None
    loan_id: UUID | None
    source: Literal["web", "import", "telegram", "api"]
    categorization_source: Literal["manual", "rule", "model", "llm"] | None
    is_initial_data: bool
    reactivation_suggestions: list[UUID]


class TransactionPage(Page[Transaction]):
    pass
