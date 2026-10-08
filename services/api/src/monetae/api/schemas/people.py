from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from monetae.api.schemas.auth import StrictModel
from monetae.api.schemas.common import Page


class PersonFields(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    note: str | None = None

    @field_validator("aliases")
    @classmethod
    def normalize_aliases(cls, aliases: list[str]) -> list[str]:
        cleaned = [alias.strip() for alias in aliases]
        if any(not 1 <= len(alias) <= 60 for alias in cleaned):
            raise ValueError("Aliases must contain 1 to 60 non-space characters.")
        if len({alias.casefold() for alias in cleaned}) != len(cleaned):
            raise ValueError("Aliases must be unique ignoring case.")
        return cleaned


class PersonCreate(PersonFields):
    pass


class PersonUpdate(StrictModel):
    model_config = {"strict": True, "extra": "forbid", "json_schema_extra": {"minProperties": 1}}
    name: str | None = Field(default=None, min_length=1, max_length=120)
    aliases: list[str] | None = Field(default=None, max_length=20)
    note: str | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "PersonUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one property is required.")
        for field in ("name", "aliases"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self

    @field_validator("aliases")
    @classmethod
    def normalize_aliases(cls, aliases: list[str] | None) -> list[str] | None:
        if aliases is None:
            return None
        return PersonFields.normalize_aliases(aliases)


class Person(StrictModel):
    name: str
    aliases: list[str]
    note: str | None
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class PersonPage(Page[Person]):
    pass
