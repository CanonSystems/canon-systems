from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AXON_", env_file=None, extra="ignore")
    s3_bucket: str = "axon-snapshots-dev"
    meta_table_name: str = "axon-snapshots-meta-dev"
    service_token: str = "dev-token"
    aws_region: str = "us-east-1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
