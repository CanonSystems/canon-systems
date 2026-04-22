"""GET /state/checkpoint — read-any, nested lease, no token echo."""

from __future__ import annotations

import time

import boto3

SCOPE = {
    "company_id": "IMC",
    "repository_id": "innermost",
    "plan_id": "p1",
    "task_id": "E2-T2",
    "workstream_id": "ws1",
}


def test_checkpoint_get_not_found(client, dynamodb_table) -> None:
    r = client.get(
        "/state/checkpoint",
        params=SCOPE,
    )
    assert r.status_code == 404
    d = r.json()["detail"]
    assert d["error"] == "not_found"
    assert d["pk"] == "IMC#innermost"
    assert d["sk"] == "p1#E2-T2#ws1"


def test_checkpoint_get_missing_param_422(client) -> None:
    r = client.get(
        "/state/checkpoint",
        params={k: SCOPE[k] for k in list(SCOPE)[:4]},
    )
    assert r.status_code == 422


def test_checkpoint_get_reshapes_lease_no_token(client, dynamodb_table) -> None:
    now = int(time.time())
    tbl = boto3.resource("dynamodb", region_name="us-east-1").Table(dynamodb_table)
    pk, sk = "IMC#innermost", "p1#E2-T2#ws1"
    tbl.put_item(
        Item={
            "pk": pk,
            "sk": sk,
            "schema_version": 1,
            "company_id": "IMC",
            "repository_id": "innermost",
            "plan_id": "p1",
            "task_id": "E2-T2",
            "workstream_id": "ws1",
            "handoff_id": "h1",
            "phase": "implementer",
            "phase_status": "in_progress",
            "state_version": 3,
            "lease_token": "secret-tok",
            "lease_owner_agent_run_id": "run-1",
            "lease_owner_actor_id": "actor-1",
            "lease_acquired_at": now - 10,
            "lease_expires_at": now + 300,
            "last_event_id": "evt-prev",
            "updated_at": "2026-04-22T00:00:00Z",
        }
    )

    r = client.get("/state/checkpoint", params=SCOPE)
    assert r.status_code == 200
    body = r.json()
    assert body["state_version"] == 3
    assert body["lease"] is not None
    assert body["lease"]["owner_agent_run_id"] == "run-1"
    assert body["lease"]["expires_at"] == now + 300
    assert "lease_token" not in body
    assert "lease_token" not in body.get("lease", {})
