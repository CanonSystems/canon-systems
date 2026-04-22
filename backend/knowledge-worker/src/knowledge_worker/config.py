"""Runtime configuration for knowledge-worker."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    canon_env: str = Field(default="local", alias="CANON_ENV")
    knowledge_api_base_url: str = Field(
        default="http://localhost:8080",
        alias="KNOWLEDGE_API_BASE_URL",
    )
    memory_adapter_base_url: str = Field(
        default="http://localhost:8090",
        alias="MEMORY_ADAPTER_BASE_URL",
    )
    worker_default_bucket: str = Field(default="knowledge-dev", alias="S3_BUCKET")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
