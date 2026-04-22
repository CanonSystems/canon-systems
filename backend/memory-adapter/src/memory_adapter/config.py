"""Runtime configuration for memory-adapter."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process settings for the memory adapter service."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    canon_env: str = Field(default="local", alias="CANON_ENV")
    memory_adapter_default_limit: int = Field(
        default=5,
        alias="MEMORY_ADAPTER_DEFAULT_LIMIT",
        ge=1,
        le=100,
    )
    mempalace_enabled: bool = Field(default=True, alias="MEMPALACE_ENABLED")
    mempalace_path: str | None = Field(default=None, alias="MEMPALACE_PATH")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for dependency injection or scripts."""

    return Settings()
