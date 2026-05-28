"""PUT /state/checkpoint — conditional write, conflicts, event emission."""

from __future__ import annotations

import json
import logging
import time

import boto3
from fastapi.testclient import TestClient

from state_api.config import Settings, get_settings
from state_api.events import get_event_emitter
from state_api.leases import get_state_store
from state_api.main import app
from state_api.storage import StateStore

SCOPE = {
    "company_id": "MJC",
    "repository_id": "marrow",
    "plan_id": "p1",
    "task_id": "E2-T2",
    "workstream_id": "ws1",
}


def _acquire(client) -> dict:
    r = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "run-a",
            "owner_actor_id": "act-a",
            "ttl_seconds": 600,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _put_body(token: str, state_version: int, **kwargs) -> dict:
    return {
        **SCOPE,
        "handoff_id": "h1",
        "phase": "implementer",
        "phase_status": "pass",
        "state_version": state_version,
        "lease_token": token,
        **kwargs,
    }


def test_put_success_increments_version_header_and_event(client, captured_events) -> None:
    a = _acquire(client)
    token = a["lease_token"]

    r = client.put("/state/checkpoint", json=_put_body(token, 0))
    assert r.status_code == 200
    body = r.json()
    assert body["state_version"] == 1
    assert "X-Canon-Event-Id" in r.headers
    eid = r.headers["X-Canon-Event-Id"]
    assert body["last_event_id"] == eid
    assert len(captured_events) == 1
    ev = captured_events[0]
    assert ev.event_type == "checkpoint_write"
    assert ev.schema_version == 1
    assert ev.agent_name == "state-api"
    assert ev.state_version == 1
    assert ev.parent_event_id == ""
    assert ev.payload == {
        "phase": "implementer",
        "phase_status": "pass",
        "updated_at": body["updated_at"],
    }


def test_put_state_version_conflict(client, dynamodb_table) -> None:
    a = _acquire(client)
    token = a["lease_token"]
    client.put("/state/checkpoint", json=_put_body(token, 0))
    r = client.put("/state/checkpoint", json=_put_body(token, 0))
    assert r.status_code == 409
    d = r.json()["detail"]
    assert d["error"] == "state_version_conflict"
    assert d["expected"] == 0
    assert d["actual"] == 1


def test_put_lease_token_mismatch(client, dynamodb_table) -> None:
    a = _acquire(client)
    token = a["lease_token"]
    r = client.put(
        "/state/checkpoint",
        json=_put_body(token + "-wrong", 0),
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "lease_token_mismatch"


def test_put_lease_expired(client, dynamodb_table) -> None:
    a = _acquire(client)
    token = a["lease_token"]
    pk, sk = "MJC#marrow", "p1#E2-T2#ws1"
    tbl = boto3.resource("dynamodb", region_name="us-east-1").Table(dynamodb_table)
    past = int(time.time()) - 60
    tbl.update_item(
        Key={"pk": pk, "sk": sk},
        UpdateExpression="SET lease_expires_at = :p",
        ExpressionAttributeValues={":p": past},
    )
    r = client.put("/state/checkpoint", json=_put_body(token, 0))
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "lease_expired"


def test_put_lease_required(client, dynamodb_table) -> None:
    pk, sk = "MJC#marrow", "p1#E2-T2#ws1"
    tbl = boto3.resource("dynamodb", region_name="us-east-1").Table(dynamodb_table)
    now = int(time.time())
    tbl.put_item(
        Item={
            "pk": pk,
            "sk": sk,
            "schema_version": 1,
            **SCOPE,
            "handoff_id": "h1",
            "phase": "scoper",
            "phase_status": "in_progress",
            "state_version": 2,
            "updated_at": "2026-04-22T00:00:00Z",
            "last_event_id": "",
        }
    )
    r = client.put(
        "/state/checkpoint",
        json=_put_body("any-token", 2),
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "lease_required"


def test_put_not_found(client, dynamodb_table) -> None:
    """No item: conditional write fails; probe returns not_found."""
    settings = Settings(state_table_name=dynamodb_table, aws_region="us-east-1")
    store = StateStore(dynamodb_table, "us-east-1")

    def ov_settings() -> Settings:
        return settings

    def ov_store() -> StateStore:
        return store

    app.dependency_overrides[get_settings] = ov_settings
    app.dependency_overrides[get_state_store] = ov_store
    try:
        with TestClient(app) as bare:
            r = bare.put(
                "/state/checkpoint",
                json={
                    "company_id": "X",
                    "repository_id": "Y",
                    "plan_id": "z",
                    "task_id": "t",
                    "workstream_id": "w",
                    "handoff_id": "h",
                    "phase": "a",
                    "phase_status": "b",
                    "state_version": 0,
                    "lease_token": "t",
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 404


def test_put_failed_emits_zero_events(client, captured_events) -> None:
    a = _acquire(client)
    client.put("/state/checkpoint", json=_put_body(a["lease_token"], 0))
    captured_events.clear()
    r = client.put("/state/checkpoint", json=_put_body(a["lease_token"], 0))
    assert r.status_code == 409
    assert captured_events == []


def test_default_emitter_logs_json_line(caplog, dynamodb_table) -> None:
    """Without overriding get_event_emitter, events go to state_api.events logger."""
    settings = Settings(state_table_name=dynamodb_table, aws_region="us-east-1")
    store = StateStore(dynamodb_table, "us-east-1")

    def ov_settings() -> Settings:
        return settings

    def ov_store() -> StateStore:
        return store

    app.dependency_overrides[get_settings] = ov_settings
    app.dependency_overrides[get_state_store] = ov_store
    try:
        with caplog.at_level(logging.INFO, logger="state_api.events"):
            with TestClient(app) as tc:
                ar = tc.post(
                    "/state/lease/acquire",
                    json={
                        **SCOPE,
                        "owner_agent_run_id": "run-log",
                        "owner_actor_id": "act-log",
                        "ttl_seconds": 120,
                    },
                )
                assert ar.status_code == 200
                tok = ar.json()["lease_token"]
                pr = tc.put("/state/checkpoint", json=_put_body(tok, 0))
                assert pr.status_code == 200
    finally:
        app.dependency_overrides.clear()

    assert any(
        rec.name == "state_api.events" and "checkpoint_write" in rec.message
        for rec in caplog.records
    )
    # Message should be valid JSON line
    log_line = next(
        rec.message
        for rec in caplog.records
        if rec.name == "state_api.events" and "checkpoint_write" in rec.message
    )
    payload = json.loads(log_line)
    assert payload["event_type"] == "checkpoint_write"
