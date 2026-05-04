"""POST /state/archive — S3 packet archive writes and canonical events."""

from __future__ import annotations

import base64

import boto3
from fastapi.testclient import TestClient

from canon_backend_shared.packet_archive import sha256_hex_digest

from state_api.config import Settings, get_settings
from state_api.events import get_event_emitter
from state_api.leases import get_state_store
from state_api.main import app
from state_api.storage import StateStore

ARTIFACT_BUCKET = "test-canon-artifacts"
SCOPE = {
    "company_id": "IMC",
    "repository_id": "innermost",
    "plan_id": "p-arch",
    "task_id": "E9-T1",
    "workstream_id": "ws-arch",
    "handoff_id": "h-arch",
}


def _archive_json(body: bytes, **extra: str) -> dict:
    digest = sha256_hex_digest(body)
    payload = {
        **SCOPE,
        "phase": "scoper",
        "artifact_kind": "packet_scoper",
        "source_label": ".cursor/handoffs/demo/scoper.md",
        "content_type": "text/markdown",
        "body_base64": base64.standard_b64encode(body).decode("ascii"),
        "content_sha256": digest,
        **extra,
    }
    return payload


def test_archive_success_writes_s3_and_emits_event(client: TestClient, captured_events: list) -> None:
    content = b"# scoper packet\nhello\n"
    r = client.post("/state/archive", json=_archive_json(content))
    assert r.status_code == 200, r.text
    rec = r.json()
    assert rec["byte_length"] == len(content)
    assert rec["content_sha256"] == sha256_hex_digest(content)
    assert rec["s3_bucket"] == ARTIFACT_BUCKET
    assert rec["artifact_kind"] == "packet_scoper"
    assert "s3_key" in rec and rec["content_sha256"] in rec["s3_key"]
    assert "X-Canon-Event-Id" in r.headers
    assert len(captured_events) == 1
    ev = captured_events[0]
    assert ev.event_type == "packet_archived"
    assert ev.schema_version == 1
    assert ev.state_version == 0
    assert "body_base64" not in ev.payload
    assert ev.payload["content_sha256"] == rec["content_sha256"]
    assert ev.payload["byte_length"] == rec["byte_length"]
    assert ev.payload["s3_key"] == rec["s3_key"]

    s3 = boto3.client("s3", region_name="us-east-1")
    obj = s3.get_object(Bucket=ARTIFACT_BUCKET, Key=rec["s3_key"])
    assert obj["Body"].read() == content


def test_archive_sha256_mismatch(client: TestClient) -> None:
    content = b"x"
    bad = _archive_json(content)
    bad["content_sha256"] = "a" * 64
    r = client.post("/state/archive", json=bad)
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "archive_sha256_mismatch"


def test_archive_invalid_base64_rejected_before_s3_write(client: TestClient, captured_events: list) -> None:
    bad = _archive_json(b"x")
    bad["body_base64"] = "!!!!"
    r = client.post("/state/archive", json=bad)
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "archive_body_decode_failed"
    assert captured_events == []


def test_archive_idempotent_same_body_same_key(client: TestClient, captured_events: list) -> None:
    content = b"same-bytes\n"
    r1 = client.post("/state/archive", json=_archive_json(content))
    r2 = client.post("/state/archive", json=_archive_json(content))
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["s3_key"] == r2.json()["s3_key"]
    assert len(captured_events) == 2


def test_archive_different_body_different_keys(client: TestClient) -> None:
    r1 = client.post("/state/archive", json=_archive_json(b"a"))
    r2 = client.post("/state/archive", json=_archive_json(b"b"))
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["s3_key"] != r2.json()["s3_key"]


def test_archive_bucket_unset_returns_503(dynamodb_table: str, captured_events: list) -> None:
    settings = Settings(
        state_table_name=dynamodb_table,
        aws_region="us-east-1",
        state_artifact_bucket="",
        state_archive_key_prefix="canon/packets",
    )
    store = StateStore(dynamodb_table, "us-east-1")

    def ov_settings() -> Settings:
        return settings

    def ov_store() -> StateStore:
        return store

    app.dependency_overrides[get_settings] = ov_settings
    app.dependency_overrides[get_state_store] = ov_store

    def ov_emitter():
        def _emit(ev) -> None:
            captured_events.append(ev)

        return _emit

    app.dependency_overrides[get_event_emitter] = ov_emitter
    try:
        with TestClient(app) as tc:
            r = tc.post("/state/archive", json=_archive_json(b"n"))
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "artifact_bucket_unset"
    assert captured_events == []


def test_archive_path_traversal_rejected(client: TestClient) -> None:
    content = b"x"
    payload = _archive_json(content)
    payload["company_id"] = "../evil"
    r = client.post("/state/archive", json=payload)
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "archive_validation_error"


def test_implementer_shard_requires_subtype(client: TestClient) -> None:
    content = b"shard handoff"
    payload = _archive_json(content, artifact_kind="packet_implementer_shard", phase="implementer")
    r = client.post("/state/archive", json=payload)
    assert r.status_code == 400

    payload["evidence_subtype"] = "shard-a"
    r2 = client.post("/state/archive", json=payload)
    assert r2.status_code == 200
