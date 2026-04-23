"""Read-only S3 shim for `canon synth show` (HEAD, GET, list only)."""

from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError


class NotFound(Exception):
    """Missing vault key."""


class AccessDenied(Exception):
    """S3 access denied (HTTP 403)."""

    def __init__(self, op: str) -> None:
        self.op = op
        super().__init__(f"access denied: {op}")


def _is_not_found(e: ClientError) -> bool:
    code = (e.response.get("Error", {}) or {}).get("Code", "")
    return code in ("404", "NoSuchKey", "NotFound")


def _is_access_denied(e: ClientError) -> bool:
    if e.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 403:
        return True
    code = (e.response.get("Error", {}) or {}).get("Code", "")
    return code in ("403", "AccessDenied")


class SynthShowReader:
    """HEAD + GET + list_objects_v2 paginator; no writes."""

    def __init__(self, *, bucket: str, prefix: str, s3_client: Any) -> None:
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        self._s3 = s3_client

    def _full_key(self, rel: str) -> str:
        r = rel.lstrip("/")
        if not self._prefix:
            return r
        return f"{self._prefix}/{r}"

    def _strip_prefix(self, full_key: str) -> str:
        if not self._prefix:
            return full_key
        p = f"{self._prefix}/"
        return full_key[len(p) :] if full_key.startswith(p) else full_key

    def list_pages(self) -> list[str]:
        paginator = self._s3.get_paginator("list_objects_v2")
        kwargs: dict[str, Any] = {"Bucket": self._bucket}
        if self._prefix:
            kwargs["Prefix"] = f"{self._prefix}/"
        out: list[str] = []
        try:
            for page in paginator.paginate(**kwargs):
                for obj in page.get("Contents", []) or []:
                    key = obj.get("Key", "")
                    if not key:
                        continue
                    out.append(self._strip_prefix(key))
        except ClientError as e:
            if _is_access_denied(e):
                raise AccessDenied("list_objects_v2") from e
            raise
        return sorted(out)

    def read_page(self, rel: str) -> bytes:
        try:
            resp = self._s3.get_object(Bucket=self._bucket, Key=self._full_key(rel))
        except ClientError as e:
            if _is_not_found(e):
                raise NotFound(rel) from e
            if _is_access_denied(e):
                raise AccessDenied("get_object") from e
            raise
        body = resp.get("Body")
        if hasattr(body, "read"):
            return body.read()
        return bytes(body or b"")

    def head_hash(self, rel: str) -> str:
        try:
            h = self._s3.head_object(Bucket=self._bucket, Key=self._full_key(rel))
        except ClientError as e:
            if _is_not_found(e):
                return ""
            if _is_access_denied(e):
                raise AccessDenied("head_object") from e
            raise
        return (h.get("Metadata", {}) or {}).get("content-hash", "")
