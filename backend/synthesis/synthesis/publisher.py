"""S3 publisher with SHA-256 content-hash sidecar diff-only writes."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Iterable, Set

from botocore.exceptions import ClientError

from synthesis.generator import VaultBundle


@dataclass(frozen=True)
class PublishResult:
    written: int
    skipped: int
    keys_written: list[str] = field(default_factory=list)


def _is_json_attach(relative: str) -> bool:
    if relative.startswith("attachments/") and relative.endswith(".json"):
        return True
    if relative.startswith(".obsidian/") and relative.endswith(".json"):
        return True
    return False


class SynthesisPublisher:
    def __init__(self, *, bucket: str, s3_client: Any, prefix: str) -> None:
        self._bucket = bucket
        self._s3 = s3_client
        self._prefix = prefix.rstrip("/")

    @staticmethod
    def _content_hash(body: bytes) -> str:
        return hashlib.sha256(body).hexdigest()

    def _full_key(self, rel: str) -> str:
        r = rel.lstrip("/")
        if not self._prefix:
            return r
        return f"{self._prefix}/{r}"

    def put_page(self, key: str, body: bytes) -> None:
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType="text/markdown; charset=utf-8",
            Metadata={"content-hash": self._content_hash(body)},
        )

    def put_attachment(self, key: str, body_bytes: bytes) -> None:
        h = self._content_hash(body_bytes)
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body_bytes,
            ContentType="application/json",
            Metadata={"content-hash": h},
        )

    def _put_for_rel(self, rel: str, body: bytes) -> None:
        fk = self._full_key(rel)
        if _is_json_attach(rel):
            self.put_attachment(fk, body)
        else:
            self.put_page(fk, body)

    def list_remote_hashes(self, sub_prefix: str = "") -> dict[str, str]:
        paginator = self._s3.get_paginator("list_objects_v2")
        out: dict[str, str] = {}
        if sub_prefix:
            pfx = f"{self._prefix}/{sub_prefix.strip('/')}/" if self._prefix else f"{sub_prefix.strip('/')}/"
        else:
            pfx = f"{self._prefix}/" if self._prefix else ""
        kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
        }
        if pfx:
            kwargs["Prefix"] = pfx
        for page in paginator.paginate(**kwargs):
            for obj in page.get("Contents", []):
                key = obj.get("Key", "")
                if not key:
                    continue
                try:
                    h = self._s3.head_object(
                        Bucket=self._bucket, Key=key
                    )
                except ClientError as e:
                    if e.response.get("Error", {}).get("Code", "") in (
                        "404",
                        "NoSuchKey",
                    ):
                        continue
                    raise
                rel = self._key_to_relative(key)
                meta = h.get("Metadata", {}) or {}
                ch = meta.get("content-hash", "")
                if ch:
                    out[rel] = ch
        return out

    def _key_to_relative(self, key: str) -> str:
        p = f"{self._prefix}/" if self._prefix else ""
        if p and key.startswith(p):
            return key[len(p) :]
        return key

    def publish(
        self,
        bundle: VaultBundle,
        *,
        write_once: Iterable[str] = (),
    ) -> PublishResult:
        w_once: Set[str] = set(write_once) | set(bundle.write_once_keys)
        written = 0
        skipped = 0
        keys_out: list[str] = []
        for rel, body in sorted(bundle.pages.items()):
            fk = self._full_key(rel)
            if rel in w_once and self._object_exists(fk):
                skipped += 1
                continue
            hnew = self._content_hash(body)
            if rel not in w_once and self._remote_hash(fk) == hnew:
                skipped += 1
                continue
            self._put_for_rel(rel, body)
            written += 1
            keys_out.append(rel)
        return PublishResult(
            written=written, skipped=skipped, keys_written=keys_out
        )

    def _object_exists(self, full_key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self._bucket, Key=full_key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code", "") in (
                "404",
                "NoSuchKey",
            ):
                return False
            raise

    def _remote_hash(self, full_key: str) -> str:
        try:
            h = self._s3.head_object(Bucket=self._bucket, Key=full_key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code", "") in (
                "404",
                "NoSuchKey",
            ):
                return ""
            raise
        return (h.get("Metadata", {}) or {}).get("content-hash", "")
