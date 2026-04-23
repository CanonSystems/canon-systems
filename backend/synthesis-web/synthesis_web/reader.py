"""Read-only S3 vault reader (GET, HEAD, list only).

Write APIs on the injected client are forbidden — see
synthesis_web_tests/test_reader_source_scan.py.
"""
from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError


class NotFound(Exception):
    """Raised when a requested vault key is missing."""


class S3VaultReader:
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
        for page in paginator.paginate(**kwargs):
            for obj in page.get("Contents", []) or []:
                key = obj.get("Key", "")
                if not key:
                    continue
                out.append(self._strip_prefix(key))
        return sorted(out)

    def read_page(self, rel: str) -> bytes:
        try:
            resp = self._s3.get_object(Bucket=self._bucket, Key=self._full_key(rel))
        except ClientError as e:
            code = (e.response.get("Error", {}) or {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                raise NotFound(rel) from e
            raise
        body = resp.get("Body")
        if hasattr(body, "read"):
            return body.read()
        return bytes(body or b"")

    def read_hash(self, rel: str) -> str:
        try:
            h = self._s3.head_object(Bucket=self._bucket, Key=self._full_key(rel))
        except ClientError as e:
            code = (e.response.get("Error", {}) or {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                return ""
            raise
        return (h.get("Metadata", {}) or {}).get("content-hash", "")

    def list_vaults(self) -> list[tuple[str, str]]:
        seen: set[tuple[str, str]] = set()
        for rel in self.list_pages():
            parts = rel.split("/", 2)
            if len(parts) < 2:
                continue
            c, r = parts[0], parts[1]
            if len(c) == 8 and len(r) == 8 and all(ch in "0123456789abcdef" for ch in c + r):
                seen.add((c, r))
        return sorted(seen)
