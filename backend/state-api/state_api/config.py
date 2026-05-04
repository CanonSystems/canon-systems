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
        populate_by_name=True,
    )

    state_table_name: str = Field(default="", validation_alias="STATE_TABLE_NAME")
    state_run_ledger_table_name: str = Field(
        default="",
        validation_alias="STATE_RUN_LEDGER_TABLE_NAME",
    )
    aws_region: str = Field(default="us-east-1", validation_alias="AWS_REGION")
    state_artifact_bucket: str = Field(default="", validation_alias="STATE_ARTIFACT_BUCKET")
    state_archive_key_prefix: str = Field(
        default="canon/packets",
        validation_alias="STATE_ARCHIVE_KEY_PREFIX",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
