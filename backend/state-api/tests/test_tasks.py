"""Task plane REST + DynamoDB (moto-backed): POST events + GET stream for state-api."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from state_api.config import Settings, get_settings
from state_api.main import app


def _event(
    *,
    event_id: str,
    event_type: str = "task_created",
    task_ref: str = "fmo-001",
    company_id: str = "FMO",
    actor_id: str = "romi",
    timestamp: str = "2026-06-02T12:00:00Z",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": event_type,
        "task_ref": task_ref,
        "company_id": company_id,
        "actor_id": actor_id,
        "timestamp": timestamp,
        **extra,
    }


def test_post_then_get_round_trip(client: TestClient) -> None:
    body = _event(
        event_id="evt_1",
        fields={"title": "Wire FMO deploy", "assignee": "edward", "status": "open"},
        repository_id="familyone-api",
    )
    r1 = client.post("/state/tasks/events", json=body)
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "created"
    assert r1.json()["event"]["event_id"] == "evt_1"

    r2 = client.get("/state/tasks", params={"company_id": "FMO"})
    assert r2.status_code == 200, r2.text
    payload = r2.json()
    assert payload["count"] == 1
    assert payload["events"][0]["task_ref"] == "fmo-001"
    assert payload["events"][0]["fields"]["assignee"] == "edward"


def test_post_is_idempotent_on_event_id(client: TestClient) -> None:
    body = _event(event_id="evt_dup", fields={"title": "x"})
    r1 = client.post("/state/tasks/events", json=body)
    assert r1.status_code == 200, r1.text
    r2 = client.post("/state/tasks/events", json=body)
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "idempotent"

    r3 = client.get("/state/tasks", params={"company_id": "FMO"})
    assert r3.json()["count"] == 1


def test_post_conflict_on_same_id_different_body(client: TestClient) -> None:
    client.post("/state/tasks/events", json=_event(event_id="evt_c", fields={"title": "a"}))
    r = client.post(
        "/state/tasks/events",
        json=_event(event_id="evt_c", fields={"title": "DIFFERENT"}),
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["error"] == "task_event_id_conflict"


def test_get_filtered_by_task_ref(client: TestClient) -> None:
    client.post("/state/tasks/events", json=_event(event_id="e1", task_ref="fmo-001"))
    client.post("/state/tasks/events", json=_event(event_id="e2", task_ref="fmo-002"))
    client.post(
        "/state/tasks/events",
        json=_event(event_id="e3", event_type="task_updated", task_ref="fmo-001"),
    )

    r = client.get("/state/tasks", params={"company_id": "FMO", "task_ref": "fmo-001"})
    assert r.status_code == 200, r.text
    refs = {e["event_id"] for e in r.json()["events"]}
    assert refs == {"e1", "e3"}


def test_validation_rejects_bad_event_type(client: TestClient) -> None:
    r = client.post(
        "/state/tasks/events",
        json=_event(event_id="bad", event_type="nope"),
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["error"] == "task_validation_error"


def test_validation_rejects_key_unsafe_segment(client: TestClient) -> None:
    r = client.post(
        "/state/tasks/events",
        json=_event(event_id="e#bad", task_ref="fmo-001"),
    )
    assert r.status_code == 400, r.text


def test_tasks_table_unset_returns_503() -> None:
    def ov() -> Settings:
        return Settings(state_table_name="x", state_tasks_table_name="")

    app.dependency_overrides[get_settings] = ov
    try:
        with TestClient(app) as tc:
            r = tc.get("/state/tasks", params={"company_id": "FMO"})
            assert r.status_code == 503, r.text
            assert r.json()["detail"]["error"] == "tasks_table_unset"
    finally:
        app.dependency_overrides.clear()
