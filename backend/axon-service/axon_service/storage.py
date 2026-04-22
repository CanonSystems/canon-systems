from __future__ import annotations
import gzip
import json
from datetime import datetime, timezone
from typing import Any, Optional
import boto3
from botocore.exceptions import ClientError


def _pk(company_id: str, repository_id: str) -> str:
    return f"{company_id}#{repository_id}"


def _snapshot_key(company_id: str, repository_id: str, commit_sha: str) -> str:
    return f"{company_id}/{repository_id}/{commit_sha}.json.gz"


class AxonStore:
    def __init__(self, *, s3_bucket: str, meta_table_name: str, region: str) -> None:
        self._s3_bucket = s3_bucket
        self._s3 = boto3.client("s3", region_name=region)
        self._table = boto3.resource("dynamodb", region_name=region).Table(meta_table_name)

    @property
    def bucket_name(self) -> str:
        return self._s3_bucket

    def put_snapshot(
        self,
        *,
        company_id: str,
        repository_id: str,
        commit_sha: str,
        nodes: list,
        edges: list,
        metadata: dict,
    ) -> dict:
        key = _snapshot_key(company_id, repository_id, commit_sha)
        payload = json.dumps(
            {"nodes": nodes, "edges": edges, "metadata": metadata},
            ensure_ascii=True,
        ).encode("utf-8")
        gz = gzip.compress(payload)
        self._s3.put_object(
            Bucket=self._s3_bucket,
            Key=key,
            Body=gz,
            ContentType="application/json",
            ContentEncoding="gzip",
        )
        uploaded_at = datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()
        node_count = len(nodes)
        edge_count = len(edges)
        size_bytes = len(gz)
        self._table.put_item(
            Item={
                "pk": _pk(company_id, repository_id),
                "sk": commit_sha,
                "uploaded_at": uploaded_at,
                "size_bytes": size_bytes,
                "node_count": node_count,
                "edge_count": edge_count,
                "snapshot_key": key,
            }
        )
        return {
            "snapshot_key": key,
            "uploaded_at": uploaded_at,
            "node_count": node_count,
            "edge_count": edge_count,
            "size_bytes": size_bytes,
        }

    def get_snapshot_meta(
        self, *, company_id: str, repository_id: str, commit_sha: str
    ) -> Optional[dict]:
        resp = self._table.get_item(Key={"pk": _pk(company_id, repository_id), "sk": commit_sha})
        return resp.get("Item")

    def get_snapshot_payload(self, key: str) -> Optional[dict]:
        try:
            obj = self._s3.get_object(Bucket=self._s3_bucket, Key=key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return None
            raise
        body = obj["Body"].read()
        decompressed = gzip.decompress(body)
        return json.loads(decompressed.decode("utf-8"))

    def list_snapshots_count(self) -> int:
        try:
            resp = self._table.scan(Select="COUNT")
            return int(resp.get("Count", 0))
        except ClientError:
            return 0
