"""Runtime configuration for knowledge-api."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    canon_env: str = Field(default="local", alias="CANON_ENV")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5434, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="canon_systems", alias="POSTGRES_DB")
    postgres_user: str = Field(default="canon", alias="POSTGRES_USER")
    postgres_password: str = Field(default="canon", alias="POSTGRES_PASSWORD")
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_access_key: str | None = Field(default=None, alias="S3_ACCESS_KEY")
    s3_secret_key: str | None = Field(default=None, alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="knowledge-dev", alias="S3_BUCKET")
    s3_force_path_style: bool = Field(default=False, alias="S3_FORCE_PATH_STYLE")
    knowledge_api_host: str = Field(default="0.0.0.0", alias="KNOWLEDGE_API_HOST")
    knowledge_api_port: int = Field(default=8080, alias="KNOWLEDGE_API_PORT")

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
