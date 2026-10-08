from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MONETAE_", strict=True, extra="forbid")

    database_url: str | None = None
    environment: Literal["local", "test", "prod"] = "local"
    cors_origins: list[str] = Field(default_factory=list)

    secret_key: str = Field(default="fake-local-key-change-before-production-0000", min_length=32)
    cookie_secure: bool = True
    session_idle_minutes: int = Field(default=20160, ge=1)
    session_absolute_days: int = Field(default=30, ge=1)

    @model_validator(mode="after")
    def require_production_security(self) -> "Settings":
        if self.environment == "prod" and (
            self.secret_key.startswith("fake-") or not self.cookie_secure
        ):
            raise ValueError("Production requires a real secret key and Secure cookies.")
        return self
