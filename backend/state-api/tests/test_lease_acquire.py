"""POST /state/lease/acquire."""

from __future__ import annotations

import time
from uuid import UUID

import boto3

SCOPE = {
    "company_id": "IMC",
    "repository_id": "innermost",
    "plan_id": "p1",
    "task_id": "E2-T2",
    "workstream_id": "ws1",
}


def test_acquire_ttl_bounds_422(client) -> None:
    r = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "r1",
            "owner_actor_id": "a1",
            "ttl_seconds": 0,
        },
    )
    assert r.status_code == 422
    r2 = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "r1",
            "owner_actor_id": "a1",
            "ttl_seconds": 3601,
        },
    )
    assert r2.status_code == 422


def test_acquire_mints_uuidv4_and_creates_item(client, dynamodb_table) -> None:
    before = int(time.time())
    r = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "r1",
            "owner_actor_id": "a1",
            "ttl_seconds": 60,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert UUID(body["lease_token"]).version == 4
    assert body["expires_at"] >= before + 60
    assert body["acquired_at"] >= before

    tbl = boto3.resource("dynamodb", region_name="us-east-1").Table(dynamodb_table)
    item = tbl.get_item(Key={"pk": "IMC#innermost", "sk": "p1#E2-T2#ws1"})["Item"]
    assert int(item["state_version"]) == 0
    assert item["lease_token"] == body["lease_token"]


def test_acquire_foreign_lease_409_no_token_leak(client) -> None:
    r1 = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "owner-a",
            "owner_actor_id": "act-a",
            "ttl_seconds": 120,
        },
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "owner-b",
            "owner_actor_id": "act-b",
            "ttl_seconds": 120,
        },
    )
    assert r2.status_code == 409
    d = r2.json()["detail"]
    assert d["error"] == "lease_held"
    assert d["owner_agent_run_id"] == "owner-a"
    assert "lease_token" not in d
    body_txt = r2.text
    assert r1.json()["lease_token"] not in body_txt


def test_acquire_same_owner_idempotent_reuses_token(client) -> None:
    r1 = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "same",
            "owner_actor_id": "act",
            "ttl_seconds": 100,
        },
    )
    assert r1.status_code == 200
    tok1 = r1.json()["lease_token"]
    exp1 = r1.json()["expires_at"]

    time.sleep(0.01)
    r2 = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "same",
            "owner_actor_id": "act",
            "ttl_seconds": 200,
        },
    )
    assert r2.status_code == 200
    assert r2.json()["lease_token"] == tok1
    assert r2.json()["expires_at"] >= exp1
    assert r2.json()["acquired_at"] == r1.json()["acquired_at"]
