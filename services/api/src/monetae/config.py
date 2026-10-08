from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MONETAE_", strict=True, extra="forbid")

    database_url: str | None = None
    environment: Literal["local", "test", "prod"] = "local"
    cors_origins: list[str] = Field(default_factory=list)
