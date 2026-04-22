"""POST /state/lease/renew."""

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

SCOPE_IDS = {k: SCOPE[k] for k in SCOPE}


def _acquire(client) -> dict:
    r = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "r1",
            "owner_actor_id": "a1",
            "ttl_seconds": 400,
        },
    )
    assert r.status_code == 200
    return r.json()


def test_renew_success(client) -> None:
    a = _acquire(client)
    before = int(time.time())
    r = client.post(
        "/state/lease/renew",
        json={
            "scope_ids": SCOPE_IDS,
            "lease_token": a["lease_token"],
            "ttl_seconds": 500,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["lease_token"] == a["lease_token"]
    assert body["expires_at"] >= before + 500


def test_renew_token_mismatch(client) -> None:
    a = _acquire(client)
    r = client.post(
        "/state/lease/renew",
        json={
            "scope_ids": SCOPE_IDS,
            "lease_token": a["lease_token"] + "-nope",
            "ttl_seconds": 100,
        },
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "lease_token_mismatch"


def test_renew_lease_expired(client, dynamodb_table) -> None:
    a = _acquire(client)
    tbl = boto3.resource("dynamodb", region_name="us-east-1").Table(dynamodb_table)
    past = int(time.time()) - 30
    tbl.update_item(
        Key={"pk": "IMC#innermost", "sk": "p1#E2-T2#ws1"},
        UpdateExpression="SET lease_expires_at = :p",
        ExpressionAttributeValues={":p": past},
    )
    r = client.post(
        "/state/lease/renew",
        json={
            "scope_ids": SCOPE_IDS,
            "lease_token": a["lease_token"],
            "ttl_seconds": 100,
        },
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "lease_expired"
