from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field, model_validator

from monetae.api.schemas.auth import StrictModel
from monetae.api.schemas.common import Page


def parse_uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise ValueError("A UUID string is required.")


JsonUUID = Annotated[UUID, BeforeValidator(parse_uuid)]


class CategoryCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["income", "expense"]
    parent_id: JsonUUID | None = None
    icon: str | None = None
    color: str | None = None


class CategoryUpdate(StrictModel):
    model_config = {"strict": True, "extra": "forbid", "json_schema_extra": {"minProperties": 1}}
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: Literal["income", "expense"] | None = None
    parent_id: JsonUUID | None = None
    icon: str | None = None
    color: str | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "CategoryUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one property is required.")
        for field in ("name", "kind"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class Category(StrictModel):
    name: str
    kind: Literal["income", "expense"]
    parent_id: UUID | None
    icon: str | None
    color: str | None
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    is_system: bool
    system_key: Literal["interest_income", "interest_expense"] | None


class CategoryPage(Page[Category]):
    pass
