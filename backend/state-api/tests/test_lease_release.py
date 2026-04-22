"""POST /state/lease/release — no canonical event emission."""

from __future__ import annotations

SCOPE = {
    "company_id": "IMC",
    "repository_id": "innermost",
    "plan_id": "p1",
    "task_id": "E2-T2",
    "workstream_id": "ws1",
}

SCOPE_IDS = {k: SCOPE[k] for k in SCOPE}


def test_release_success(client) -> None:
    ar = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "r1",
            "owner_actor_id": "a1",
            "ttl_seconds": 200,
        },
    )
    assert ar.status_code == 200
    tok = ar.json()["lease_token"]
    rr = client.post(
        "/state/lease/release",
        json={"scope_ids": SCOPE_IDS, "lease_token": tok},
    )
    assert rr.status_code == 200
    assert rr.json() == {"released": True}


def test_release_token_mismatch(client) -> None:
    ar = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "r1",
            "owner_actor_id": "a1",
            "ttl_seconds": 200,
        },
    )
    assert ar.status_code == 200
    rr = client.post(
        "/state/lease/release",
        json={"scope_ids": SCOPE_IDS, "lease_token": ar.json()["lease_token"] + "x"},
    )
    assert rr.status_code == 409
    assert rr.json()["detail"]["error"] == "lease_token_mismatch"


def test_release_does_not_emit_canonical_event(client, captured_events) -> None:
    ar = client.post(
        "/state/lease/acquire",
        json={
            **SCOPE,
            "owner_agent_run_id": "r1",
            "owner_actor_id": "a1",
            "ttl_seconds": 200,
        },
    )
    captured_events.clear()
    tok = ar.json()["lease_token"]
    rr = client.post(
        "/state/lease/release",
        json={"scope_ids": SCOPE_IDS, "lease_token": tok},
    )
    assert rr.status_code == 200
    assert captured_events == []
