from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from canon_backend_shared.events import CanonicalEvent
from synthesis.main import app, get_event_source
from synthesis.sources import InMemoryEventSource


def _e(**kw) -> CanonicalEvent:
    d = {
        "schema_version": 1,
        "event_id": "01JAPI1",
        "parent_event_id": "01J0000",
        "event_type": "retrieval_breakdown",
        "company_id": "IMC",
        "repository_id": "innermost",
        "plan_id": "plan-b",
        "task_id": "E5-T2",
        "handoff_id": "h1",
        "agent_name": "implementer",
        "agent_run_id": "run-1",
        "actor_id": "actor-1",
        "model": "m1",
        "timestamp": "2026-04-23T10:00:00Z",
        "state_version": 1,
        "payload": {"phase": "implementer", "agent": "a", "sources": {}},
    }
    d.update(kw)
    return CanonicalEvent.from_dict(d)


def test_synth_vault_changes_returns_deterministic_change_list() -> None:
    ev0 = _e(
        event_id="01J0001",
        timestamp="2026-04-23T11:00:00Z",
    )
    ev1 = _e(
        event_id="01J0002",
        timestamp="2026-04-23T10:00:00Z",
    )
    app.dependency_overrides[get_event_source] = (
        lambda: InMemoryEventSource([ev0, ev1])
    )
    try:
        with TestClient(app) as c:
            r = c.get(
                "/synth/vault/changes",
                params={"since": "2026-04-23T09:00:00Z"},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["schema_version"] == 1
    assert j["count"] == 2
    assert j["changes"] == [
        {
            "vault_key": "events/retrieval-breakdown/plan-b/E5-T2.md",
            "event_id": "01J0002",
            "timestamp": "2026-04-23T10:00:00Z",
        },
        {
            "vault_key": "events/retrieval-breakdown/plan-b/E5-T2.md",
            "event_id": "01J0001",
            "timestamp": "2026-04-23T11:00:00Z",
        },
    ]
    with TestClient(app) as c:
        bad = c.get("/synth/vault/changes", params={"since": "not a date"})
    assert bad.status_code == 422


def test_synth_show_returns_json_envelope_and_markdown_alt_format() -> None:
    ev = _e(
        event_id="01J0003",
    )
    app.dependency_overrides[get_event_source] = (
        lambda: InMemoryEventSource([ev])
    )
    try:
        with TestClient(app) as c:
            rj = c.get(
                "/synth/show",
                params={"plan_id": "plan-b", "task_id": "E5-T2"},
            )
    finally:
        app.dependency_overrides.clear()
    assert rj.status_code == 200, rj.text
    b = rj.json()
    assert b["schema_version"] == 1
    assert b["vault_key"] == "plans/plan-b/tasks/E5-T2/index.md"
    assert "[[event:01J0003" in b["markdown"] or "[[event:01J0003]]" in b["markdown"] or b["markdown"].count("[[event:") >= 1

    app.dependency_overrides[get_event_source] = (
        lambda: InMemoryEventSource([ev])
    )
    try:
        with TestClient(app) as c:
            rm = c.get(
                "/synth/show",
                params={
                    "plan_id": "plan-b",
                    "task_id": "E5-T2",
                    "format": "markdown",
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert rm.status_code == 200
    assert "text/markdown" in (rm.headers.get("content-type") or "")
    assert b["markdown"] == rm.text

    app.dependency_overrides[get_event_source] = (
        lambda: InMemoryEventSource([])
    )
    try:
        with TestClient(app) as c:
            n404 = c.get(
                "/synth/show",
                params={"plan_id": "nope", "task_id": "nope"},
            )
    finally:
        app.dependency_overrides.clear()
    assert n404.status_code == 404
