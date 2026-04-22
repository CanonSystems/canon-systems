"""Application settings (env-backed)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=None,
        extra="ignore",
        case_sensitive=False,
    )

    state_table_name: str = Field(default="", validation_alias="STATE_TABLE_NAME")
    aws_region: str = Field(default="us-east-1", validation_alias="AWS_REGION")


@lru_cache
def get_settings() -> Settings:
    return Settings()
