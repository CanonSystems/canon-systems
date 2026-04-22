"""S3-compatible object storage helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import boto3
from botocore.config import Config

from app.config import get_settings


class ObjectStore(Protocol):
    def put_text(self, *, bucket: str, key: str, text: str, content_type: str) -> None: ...
    def get_text(self, *, bucket: str, key: str) -> tuple[str, str]: ...


class S3ObjectStore:
    def __init__(self) -> None:
        settings = get_settings()
        client_kwargs: dict[str, object] = {
            "region_name": settings.s3_region,
            "config": Config(s3={"addressing_style": "path" if settings.s3_force_path_style else "auto"}),
        }
        if settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = settings.s3_endpoint_url
        # Use static credentials only when explicitly configured.
        # Otherwise boto3 falls back to AWS default provider chain (e.g., ECS task role).
        if settings.s3_access_key and settings.s3_secret_key:
            client_kwargs["aws_access_key_id"] = settings.s3_access_key
            client_kwargs["aws_secret_access_key"] = settings.s3_secret_key
        self._client = boto3.client("s3", **client_kwargs)

    def put_text(self, *, bucket: str, key: str, text: str, content_type: str) -> None:
        self._client.put_object(
            Bucket=bucket,
            Key=key,
            Body=text.encode("utf-8"),
            ContentType=content_type,
        )

    def get_text(self, *, bucket: str, key: str) -> tuple[str, str]:
        response = self._client.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read().decode("utf-8")
        content_type = response.get("ContentType") or "text/plain"
        return body, content_type


@lru_cache(maxsize=1)
def get_object_store() -> S3ObjectStore:
    return S3ObjectStore()
