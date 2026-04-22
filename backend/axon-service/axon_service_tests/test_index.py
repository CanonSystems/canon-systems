from __future__ import annotations
import gzip
import json
import boto3
from fastapi.testclient import TestClient

HDR = {"Authorization": "Bearer test-token"}


def test_post_index_persists_s3_and_dynamo(client: TestClient) -> None:
    r = client.post(
        "/axon/acme/rel/index",
        json={
            "commit_sha": "abc123",
            "nodes": [{"id": "n1"}],
            "edges": [{"s": "a", "t": "b"}],
            "metadata": {"k": "v"},
        },
        headers=HDR,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["commit_sha"] == "abc123"
    assert data["company_id"] == "acme"
    assert data["repository_id"] == "rel"
    key = f"acme/rel/abc123.json.gz"
    assert data["snapshot_key"] == key

    s3 = boto3.client("s3", region_name="us-east-1")
    obj = s3.get_object(Bucket="axon-test-bucket", Key=key)
    raw = obj["Body"].read()
    payload = json.loads(gzip.decompress(raw).decode("utf-8"))
    assert payload["nodes"] == [{"id": "n1"}]
    assert len(payload["edges"]) == 1

    ddb = boto3.resource("dynamodb", region_name="us-east-1").Table("axon-test-meta")
    item = ddb.get_item(Key={"pk": "acme#rel", "sk": "abc123"})["Item"]
    assert int(item["node_count"]) == 1
    assert int(item["edge_count"]) == 1
    assert "uploaded_at" in item
    assert int(item["size_bytes"]) > 0
    assert item["snapshot_key"] == key


def test_path_tenant_authoritative(client: TestClient) -> None:
    client.post(
        "/axon/tenantA/repoX/index",
        json={"commit_sha": "s1", "nodes": [], "metadata": {"note": "ignored-for-keys"}},
        headers=HDR,
    )
    s3 = boto3.client("s3", region_name="us-east-1")
    keys = s3.list_objects_v2(Bucket="axon-test-bucket").get("Contents", [])
    assert any(o["Key"] == "tenantA/repoX/s1.json.gz" for o in keys)


def test_index_400_on_missing_commit_sha(client: TestClient) -> None:
    r = client.post(
        "/axon/c/r/index",
        json={},
        headers=HDR,
    )
    # FastAPI/Pydantic validation
    assert r.status_code == 422
