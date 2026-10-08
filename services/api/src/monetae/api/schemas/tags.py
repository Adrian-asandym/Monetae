from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from monetae.api.schemas.auth import StrictModel
from monetae.api.schemas.common import Page


class TagCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    color: str | None = None
    icon: str | None = None
    emoji: str | None = None
    sort_order: int = 0


class TagUpdate(StrictModel):
    model_config = {"strict": True, "extra": "forbid", "json_schema_extra": {"minProperties": 1}}
    name: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = None
    icon: str | None = None
    emoji: str | None = None
    sort_order: int | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "TagUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one property is required.")
        for field in ("name", "sort_order"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class Tag(StrictModel):
    name: str
    color: str | None
    icon: str | None
    emoji: str | None
    sort_order: int
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    archived_at: datetime | None


class TagPage(Page[Tag]):
    pass
