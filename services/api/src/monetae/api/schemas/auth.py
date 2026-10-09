from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
Email = Annotated[str, Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=320)]


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class PasswordLogin(StrictModel):
    method: Literal["password"]
    email: Email
    password: SecretStr = Field(min_length=1)


class GoogleLogin(StrictModel):
    method: Literal["google"]


LoginRequest = Annotated[PasswordLogin | GoogleLogin, Field(discriminator="method")]


class TransactionCardPreferences(StrictModel):
    show_date: bool = True
    show_time: bool = False
    show_note: bool = True
    show_tags: bool = True
    show_account: bool = False
    show_actions: bool = False

    @model_validator(mode="after")
    def include_defaults(self) -> "TransactionCardPreferences":
        # Profile responses and PATCH serialization exclude unset fields.
        self.model_fields_set.update(type(self).model_fields)
        return self


class UserPreferences(StrictModel):
    default_account_id: UUID | None = None
    theme: Literal["light", "dark", "system"] = "system"
    accent_color: str | None = None
    home_widgets: list[str] = Field(default_factory=list, json_schema_extra={"uniqueItems": True})
    transaction_card: TransactionCardPreferences = Field(default_factory=TransactionCardPreferences)

    @field_validator("default_account_id", mode="before")
    @classmethod
    def parse_default_account_id(cls, value: object) -> UUID | None:
        # FastAPI parses JSON before strict validation; accept only UUID strings.
        if value is None or isinstance(value, UUID):
            return value
        if isinstance(value, str):
            return UUID(value)
        raise ValueError("A UUID string is required.")

    @model_validator(mode="after")
    def validate_preferences(self) -> "UserPreferences":
        if len(set(self.home_widgets)) != len(self.home_widgets):
            raise ValueError("home_widgets must be unique.")
        # Materialize RF-47 for legacy jsonb without changing other optional fields.
        self.model_fields_set.update({"transaction_card", "default_account_id"})
        return self


class CurrentUser(StrictModel):
    id: UUID
    email: Email
    preferences: UserPreferences
    pin_configured: bool
    locked: bool
    webauthn_enabled: bool
    timezone: str
    base_currency: Currency = Field(json_schema_extra={"readOnly": True})
    locale: Literal["es", "en"]
    lock_after_minutes: int | None = Field(ge=1)
    report_currency: Currency


class UserUpdate(StrictModel):
    model_config = ConfigDict(strict=True, extra="forbid", json_schema_extra={"minProperties": 1})

    timezone: str = "America/Lima"
    base_currency: Currency = Field(default="PEN", json_schema_extra={"readOnly": True})
    locale: Literal["es", "en"] = "es"
    lock_after_minutes: int | None = Field(default=None, ge=1)
    report_currency: Currency = "PEN"
    preferences: UserPreferences = Field(default_factory=UserPreferences)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ValueError("Unknown timezone.") from exc
        return value

    @model_validator(mode="after")
    def nonempty_patch(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one property is required.")
        for name in self.model_fields_set - {"lock_after_minutes"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null.")
        return self


class AuthenticatedSession(StrictModel):
    user: CurrentUser
    csrf_token: str
    expires_at: datetime


class GoogleAuthorization(StrictModel):
    authorization_url: str


LoginResult = AuthenticatedSession | GoogleAuthorization


class Session(StrictModel):
    id: UUID
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    user_agent: str
    ip: str
    is_current: bool


class SessionPage(StrictModel):
    items: list[Session]
    next_cursor: str | None


class ActionResult(StrictModel):
    success: bool
    affected_count: int = Field(ge=0)
