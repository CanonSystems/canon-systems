"""In-memory S3 for unit tests (mirrors real boto3 client surface we use)."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Mapping

from botocore.exceptions import ClientError


class _ListPaginator:
    def __init__(self, parent: "DictS3Client", name: str) -> None:
        _ = name
        self._parent = parent

    def paginate(self, **kwargs: Any) -> Iterator[dict[str, Any]]:
        bucket = kwargs.get("Bucket", "")
        prefix = kwargs.get("Prefix") or ""
        _ = bucket
        keys: list[str] = []
        for k in self._parent.objects:
            if not prefix or k.startswith(prefix):
                keys.append(k)
        cont = [{"Key": k, "Size": 0} for k in sorted(keys)]
        if not cont:
            yield {"Contents": []}
        else:
            yield {"Contents": cont}


class DictS3Client:
    """In-memory S3: put_object, head_object, list_objects_v2 (paginate)."""

    def __init__(self) -> None:
        # key -> {Body, Metadata, ContentType}
        self.objects: dict[str, dict[str, Any]] = {}

    def put_object(
        self,
        *,
        Bucket: str,  # noqa: N803
        Key: str,  # noqa: N803
        Body: bytes,  # noqa: N803
        ContentType: str | None = None,  # noqa: N803
        Metadata: Mapping[str, str] | None = None,  # noqa: N803
    ) -> dict[str, Any]:
        _ = Bucket
        self.objects[Key] = {
            "Body": Body,
            "ContentType": ContentType or "binary/octet-stream",
            "Metadata": dict(Metadata) if Metadata else {},
        }
        return {"ETag": '"moto-dict"'}

    def head_object(
        self,
        *,
        Bucket: str,  # noqa: N803
        Key: str,  # noqa: N803
    ) -> dict[str, Any]:
        _ = Bucket
        if Key not in self.objects:
            raise ClientError(
                {
                    "Error": {"Code": "404", "Message": "Not Found"},
                    "ResponseMetadata": {
                        "HTTPStatusCode": 404,
                    },
                },
                "HeadObject",
            )
        o = self.objects[Key]
        return {
            "ContentType": o.get("ContentType"),
            "Metadata": o.get("Metadata", {}),
        }

    def get_paginator(self, name: str) -> _ListPaginator:
        return _ListPaginator(self, name)
