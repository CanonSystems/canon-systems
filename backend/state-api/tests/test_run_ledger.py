"""Run ledger REST + DynamoDB: moto-backed AC2/AC3/AC4/AC5/AC8 slices for state-api."""

from __future__ import annotations

import uuid
from typing import Any

import boto3
from fastapi.testclient import TestClient

from canon_backend_shared.packet_archive import sha256_hex_digest
from canon_backend_shared.run_ledger import build_run_ledger_pk, build_run_ledger_sk

from state_api.config import Settings, get_settings
from state_api.events import get_event_emitter
from state_api.leases import get_state_store
from state_api.main import app
from state_api.run_ledger import get_run_ledger_store
from state_api.storage import StateStore

from .conftest import ARTIFACT_BUCKET, LEDGER_TABLE, TABLE


def _ledger_payload(*, ledger_run_id: str, **extra: Any) -> dict[str, Any]:
    return {
        "ledger_run_id": ledger_run_id,
        "company_id": "IMC",
        "repository_id": "innermost",
        "plan_id": "p-readiness",
        "task_id": "run-ledger",
        "workstream_id": "run-ledger",
        "handoff_id": "canon-readiness-gates",
        "phase": "qa-gate",
        "phase_status": "completed",
        "created_at": "2026-05-04T12:00:00Z",
        **extra,
    }


def test_put_get_round_trip(client: TestClient) -> None:
    run_id = str(uuid.uuid4())
    body = _ledger_payload(ledger_run_id=run_id)
    r1 = client.put("/state/run-ledger", json=body)
    assert r1.status_code == 200, r1.text
    rec = r1.json()
    assert rec["ledger_run_id"] == run_id
    assert rec["phase"] == "qa-gate"
    assert "body" not in rec and "body_base64" not in rec

    r2 = client.get(
        "/state/run-ledger",
        params={
            "company_id": "IMC",
            "repository_id": "innermost",
            "plan_id": "p-readiness",
            "task_id": "run-ledger",
            "workstream_id": "run-ledger",
            "ledger_run_id": run_id,
        },
    )
    assert r2.status_code == 200, r2.text
    got = r2.json()["record"]
    assert got["ledger_run_id"] == run_id


def test_ledger_row_not_in_checkpoint_table(client: TestClient) -> None:
    run_id = str(uuid.uuid4())
    body = _ledger_payload(ledger_run_id=run_id)
    lpk = build_run_ledger_pk(company_id=body["company_id"], repository_id=body["repository_id"])
    lsk = build_run_ledger_sk(
        plan_id=body["plan_id"],
        task_id=body["task_id"],
        workstream_id=body["workstream_id"],
        ledger_run_id=run_id,
    )
    cp_pk = f'{body["company_id"]}#{body["repository_id"]}'
    assert lpk != cp_pk
    assert lpk.endswith("#run_ledger")

    assert client.put("/state/run-ledger", json=body).status_code == 200

    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    missing = ddb.Table(TABLE).get_item(Key={"pk": lpk, "sk": lsk}).get("Item")
    assert missing is None
    present = ddb.Table(LEDGER_TABLE).get_item(Key={"pk": lpk, "sk": lsk}).get("Item")
    assert present is not None


def test_idempotent_put_same_payload(client: TestClient) -> None:
    run_id = str(uuid.uuid4())
    body = _ledger_payload(
        ledger_run_id=run_id,
        validation_outcomes={
            "qa_validate": {"status": "pass", "verdict": "PASS", "exit_code": 0},
        },
    )
    r1 = client.put("/state/run-ledger", json=body)
    r2 = client.put("/state/run-ledger", json=body)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json()


def test_put_conflict_same_run_id_different_payload(client: TestClient) -> None:
    run_id = str(uuid.uuid4())
    a = _ledger_payload(ledger_run_id=run_id, phase_status="running")
    b = _ledger_payload(ledger_run_id=run_id, phase_status="failed")
    ra = client.put("/state/run-ledger", json=a)
    assert ra.status_code == 200
    rb = client.put("/state/run-ledger", json=b)
    assert rb.status_code == 409
    assert rb.json()["detail"]["error"] == "run_ledger_id_conflict"


def test_archive_refs_by_reference_only(client: TestClient) -> None:
    run_id = str(uuid.uuid4())
    digest = sha256_hex_digest(b"ledger-meta")
    body = _ledger_payload(
        ledger_run_id=run_id,
        archive_refs=[
            {
                "content_sha256": digest,
                "artifact_kind": "packet_qa_gate",
                "s3_uri": "s3://bucket/key",
                "archive_event_id": "evt-123",
            },
        ],
    )
    r = client.put("/state/run-ledger", json=body)
    assert r.status_code == 200, r.text
    ar0 = r.json()["archive_refs"][0]
    assert ar0["content_sha256"] == digest
    assert ar0.get("body_base64") is None
    lpk = build_run_ledger_pk(company_id="IMC", repository_id="innermost")
    lsk = build_run_ledger_sk(
        plan_id="p-readiness",
        task_id="run-ledger",
        workstream_id="run-ledger",
        ledger_run_id=run_id,
    )
    raw = boto3.resource("dynamodb", region_name="us-east-1").Table(LEDGER_TABLE).get_item(
        Key={"pk": lpk, "sk": lsk},
    ).get("Item", {})
    assert raw
    assert "body" not in raw and "body_base64" not in raw


def test_reject_body_field_on_ledger(client: TestClient) -> None:
    body = _ledger_payload(ledger_run_id=str(uuid.uuid4()), body_base64="eA==")
    r = client.put("/state/run-ledger", json=body)
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "run_ledger_validation_error"


def test_query_by_scope_and_handoff_filter(client: TestClient) -> None:
    rid_a = str(uuid.uuid4())
    rid_b = str(uuid.uuid4())
    a = _ledger_payload(ledger_run_id=rid_a, handoff_id="canon-readiness-gates")
    b = _ledger_payload(ledger_run_id=rid_b, handoff_id="other-handoff")
    assert client.put("/state/run-ledger", json=a).status_code == 200
    assert client.put("/state/run-ledger", json=b).status_code == 200
    r = client.get(
        "/state/run-ledger",
        params={
            "company_id": "IMC",
            "repository_id": "innermost",
            "plan_id": "p-readiness",
            "task_id": "run-ledger",
            "workstream_id": "run-ledger",
            "handoff_id": "canon-readiness-gates",
            "limit": 20,
        },
    )
    assert r.status_code == 200
    items = r.json()["items"]
    ids = {x["ledger_run_id"] for x in items}
    assert rid_a in ids
    assert rid_b not in ids


def test_run_ledger_table_unset_returns_503(dynamodb_table: str, captured_events: list) -> None:
    settings = Settings(
        state_table_name=dynamodb_table,
        state_run_ledger_table_name="",
        aws_region="us-east-1",
        state_artifact_bucket=ARTIFACT_BUCKET,
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
            resp = tc.put("/state/run-ledger", json=_ledger_payload(ledger_run_id=str(uuid.uuid4())))
            assert resp.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_ac7_get_run_ledger_preserves_ledger_row_in_dynamodb(client: TestClient) -> None:
    """Readiness-style GETs must not mutate run-ledger rows (moto / no live AWS)."""
    run_id = str(uuid.uuid4())
    missing_id = str(uuid.uuid4())
    body = _ledger_payload(ledger_run_id=run_id)
    assert client.put("/state/run-ledger", json=body).status_code == 200
    lpk = build_run_ledger_pk(company_id="IMC", repository_id="innermost")
    lsk = build_run_ledger_sk(
        plan_id="p-readiness",
        task_id="run-ledger",
        workstream_id="run-ledger",
        ledger_run_id=run_id,
    )
    ddb = boto3.resource("dynamodb", region_name="us-east-1").Table(LEDGER_TABLE)
    snap = ddb.get_item(Key={"pk": lpk, "sk": lsk}).get("Item")
    assert snap

    base_params = {
        "company_id": "IMC",
        "repository_id": "innermost",
        "plan_id": "p-readiness",
        "task_id": "run-ledger",
        "workstream_id": "run-ledger",
    }
    r_list = client.get("/state/run-ledger", params={**base_params, "limit": 20})
    assert r_list.status_code == 200
    r_one = client.get("/state/run-ledger", params={**base_params, "ledger_run_id": run_id})
    assert r_one.status_code == 200
    r_handoff = client.get(
        "/state/run-ledger",
        params={**base_params, "handoff_id": "canon-readiness-gates", "limit": 10},
    )
    assert r_handoff.status_code == 200
    r_404 = client.get(
        "/state/run-ledger",
        params={**base_params, "ledger_run_id": missing_id},
    )
    assert r_404.status_code == 404

    assert ddb.get_item(Key={"pk": lpk, "sk": lsk}).get("Item") == snap


def test_ac7_get_run_ledger_preserves_checkpoint_table_row(client: TestClient, dynamodb_table: str) -> None:
    """GET /state/run-ledger must not write to the checkpoint DynamoDB table."""
    run_id = str(uuid.uuid4())
    assert client.put("/state/run-ledger", json=_ledger_payload(ledger_run_id=run_id)).status_code == 200

    cp_tbl = boto3.resource("dynamodb", region_name="us-east-1").Table(dynamodb_table)
    cp_pk, cp_sk = "IMC#innermost", "p-readiness#run-ledger#run-ledger"
    cp_tbl.put_item(
        Item={
            "pk": cp_pk,
            "sk": cp_sk,
            "schema_version": 1,
            "company_id": "IMC",
            "repository_id": "innermost",
            "plan_id": "p-readiness",
            "task_id": "run-ledger",
            "workstream_id": "run-ledger",
            "handoff_id": "canon-readiness-gates",
            "phase": "implementer",
            "phase_status": "in_progress",
            "state_version": 1,
            "lease_token": "tok-ws3",
            "lease_owner_agent_run_id": "run-ws3",
            "lease_owner_actor_id": "actor-ws3",
            "lease_acquired_at": 1_700_000_000,
            "lease_expires_at": 1_700_000_900,
            "last_event_id": "evt-ws3",
            "updated_at": "2026-05-04T12:00:00Z",
        },
    )
    snap = cp_tbl.get_item(Key={"pk": cp_pk, "sk": cp_sk}).get("Item")
    assert snap

    base_params = {
        "company_id": "IMC",
        "repository_id": "innermost",
        "plan_id": "p-readiness",
        "task_id": "run-ledger",
        "workstream_id": "run-ledger",
    }
    assert client.get("/state/run-ledger", params={**base_params, "ledger_run_id": run_id}).status_code == 200
    assert client.get("/state/run-ledger", params={**base_params, "limit": 25}).status_code == 200

    assert cp_tbl.get_item(Key={"pk": cp_pk, "sk": cp_sk}).get("Item") == snap


def test_ac7_get_run_ledger_preserves_s3_artifact_bucket(client: TestClient) -> None:
    """GET /state/run-ledger must not touch packet-archive artifact objects (read-only boundary)."""
    run_id = str(uuid.uuid4())
    assert client.put("/state/run-ledger", json=_ledger_payload(ledger_run_id=run_id)).status_code == 200

    s3 = boto3.client("s3", region_name="us-east-1")
    key = "ws3-readonly-boundary/obj.txt"
    s3.put_object(Bucket=ARTIFACT_BUCKET, Key=key, Body=b"ws3")

    base_params = {
        "company_id": "IMC",
        "repository_id": "innermost",
        "plan_id": "p-readiness",
        "task_id": "run-ledger",
        "workstream_id": "run-ledger",
    }
    before = s3.list_objects_v2(Bucket=ARTIFACT_BUCKET, Prefix="ws3-readonly-boundary/")
    assert client.get("/state/run-ledger", params={**base_params, "limit": 5}).status_code == 200
    assert client.get("/state/run-ledger", params={**base_params, "ledger_run_id": run_id}).status_code == 200
    after = s3.list_objects_v2(Bucket=ARTIFACT_BUCKET, Prefix="ws3-readonly-boundary/")

    assert before.get("KeyCount", 0) == after.get("KeyCount", 0)
    assert [o["Key"] for o in before.get("Contents", [])] == [o["Key"] for o in after.get("Contents", [])]
