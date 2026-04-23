"""Tests for E6-T1 metrics aggregator."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from canon_systems import metrics_rollup


def _mk_event(
    event_type: str,
    *,
    task_id: str = "E1-T1",
    agent_name: str = "scoper",
    agent_run_id: str = "run-a",
    timestamp: str = "2026-04-23T10:00:00Z",
    company_id: str = "acme",
    repository_id: str = "canon-systems",
    plan_id: str = "plan-alpha",
    payload: dict[str, Any] | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event_id": event_id or f"ev-{hash((event_type, task_id, agent_run_id, timestamp)) & 0xffffff}",
        "parent_event_id": "",
        "event_type": event_type,
        "company_id": company_id,
        "repository_id": repository_id,
        "plan_id": plan_id,
        "task_id": task_id,
        "handoff_id": "canon-memory-v1",
        "agent_name": agent_name,
        "agent_run_id": agent_run_id,
        "actor_id": "tester",
        "model": "inherit",
        "timestamp": timestamp,
        "state_version": 1,
        "payload": payload or {},
    }


def test_ac1_empty_stream_returns_zero_filled_rollup() -> None:
    result = metrics_rollup.aggregate([])
    assert result["schema_version"] == metrics_rollup.SCHEMA_VERSION
    assert result["totals"]["events"] == 0
    assert result["totals"]["tasks_seen"] == 0
    assert result["lead_time_by_task"] == {}
    assert result["retries_by_task_phase"] == {}
    assert result["dor_causes"] == {}
    assert result["stalls"] == {"total": 0, "by_task": {}}
    for phase in ("scoper", "cursor-pilot", "implementer", "qa-gate", "release-orchestrator"):
        assert result["cycle_time_by_phase"][phase] == {
            "task_count": 0,
            "total_seconds": 0,
            "avg_seconds": 0,
        }
    assert result["synth_publish"] == {"ok": 0, "failed": 0, "notifier_ok": 0}


def test_ac2_scope_filters_drop_non_matching() -> None:
    events = [
        _mk_event("scoper", company_id="acme", plan_id="plan-alpha", task_id="T1"),
        _mk_event("scoper", company_id="other-co", plan_id="plan-alpha", task_id="T2"),
        _mk_event("scoper", company_id="acme", plan_id="plan-beta", task_id="T3"),
    ]
    result = metrics_rollup.aggregate(events, scope={"company_id": "acme", "plan_id": "plan-alpha"})
    assert result["totals"]["events"] == 1
    assert list(result["lead_time_by_task"].keys()) == ["T1"]


def test_ac2_window_filters_timestamps() -> None:
    events = [
        _mk_event("scoper", task_id="A", timestamp="2026-04-20T00:00:00Z"),
        _mk_event("scoper", task_id="B", timestamp="2026-04-23T12:00:00Z"),
        _mk_event("scoper", task_id="C", timestamp="2026-04-30T00:00:00Z"),
    ]
    result = metrics_rollup.aggregate(
        events,
        window={"since": "2026-04-22T00:00:00Z", "until": "2026-04-24T00:00:00Z"},
    )
    assert set(result["lead_time_by_task"].keys()) == {"B"}


def test_ac3_lead_time_single_event_is_zero_seconds() -> None:
    ev = _mk_event("scoper", task_id="solo", timestamp="2026-04-23T10:00:00Z")
    result = metrics_rollup.aggregate([ev])
    lt = result["lead_time_by_task"]["solo"]
    assert lt["seconds"] == 0
    assert lt["first_ts"] == "2026-04-23T10:00:00Z"
    assert lt["last_ts"] == "2026-04-23T10:00:00Z"


def test_ac3_lead_time_spans_phases() -> None:
    events = [
        _mk_event("scoper", task_id="T", agent_name="scoper", timestamp="2026-04-23T10:00:00Z"),
        _mk_event("release_status", task_id="T", agent_name="release-orchestrator", timestamp="2026-04-23T10:15:30Z"),
    ]
    result = metrics_rollup.aggregate(events)
    lt = result["lead_time_by_task"]["T"]
    assert lt["seconds"] == 930
    assert lt["first_ts"].startswith("2026-04-23T10:00")
    assert lt["last_ts"].startswith("2026-04-23T10:15")


def test_ac4_cycle_time_avg_is_integer_per_phase() -> None:
    events = [
        _mk_event("x", task_id="T1", agent_name="scoper", agent_run_id="r1", timestamp="2026-04-23T10:00:00Z"),
        _mk_event("x", task_id="T1", agent_name="scoper", agent_run_id="r1", timestamp="2026-04-23T10:00:30Z"),
        _mk_event("x", task_id="T2", agent_name="scoper", agent_run_id="r2", timestamp="2026-04-23T11:00:00Z"),
        _mk_event("x", task_id="T2", agent_name="scoper", agent_run_id="r2", timestamp="2026-04-23T11:01:30Z"),
    ]
    result = metrics_rollup.aggregate(events)
    sc = result["cycle_time_by_phase"]["scoper"]
    assert sc["task_count"] == 2
    assert sc["total_seconds"] == 30 + 90
    assert sc["avg_seconds"] == 60
    assert isinstance(sc["avg_seconds"], int)


def test_ac5_retries_counted_by_distinct_agent_run_id() -> None:
    events = [
        _mk_event("x", task_id="T", agent_name="implementer", agent_run_id="a", event_id="e1"),
        _mk_event("x", task_id="T", agent_name="implementer", agent_run_id="a", event_id="e2"),
        _mk_event("x", task_id="T", agent_name="implementer", agent_run_id="b", event_id="e3"),
        _mk_event("x", task_id="T", agent_name="implementer", agent_run_id="c", event_id="e4"),
        _mk_event("x", task_id="T", agent_name="qa-gate", agent_run_id="x", event_id="e5"),
    ]
    result = metrics_rollup.aggregate(events)
    retries = result["retries_by_task_phase"]
    assert retries == {"T": {"implementer": 2}}
    assert result["totals"]["retries"] == 2


def test_ac6_dor_causes_aggregated_by_stage() -> None:
    events = [
        _mk_event("dor_failure", payload={"stage": "scoper"}),
        _mk_event("dor_failure", payload={"stage": "scoper"}),
        _mk_event("dor_failure", payload={"stage": "cursor-pilot"}),
        _mk_event("dor_failure", payload={}),
    ]
    result = metrics_rollup.aggregate(events)
    assert result["dor_causes"] == {"scoper": 2, "cursor-pilot": 1, "unknown": 1}
    assert result["totals"]["dor_failures"] == 4


def test_ac7_stalls_total_and_by_task() -> None:
    events = [
        _mk_event("lease_stall_detected", task_id="T1"),
        _mk_event("lease_stall_detected", task_id="T1"),
        _mk_event("lease_stall_detected", task_id="T2"),
    ]
    result = metrics_rollup.aggregate(events)
    assert result["stalls"]["total"] == 3
    assert result["stalls"]["by_task"] == {"T1": 2, "T2": 1}


def test_ac8_token_cost_rollups_split_correctly() -> None:
    events = [
        _mk_event(
            "retrieval_breakdown",
            agent_name="scoper",
            payload={
                "totals": {"tokens_in": 100, "tokens_out": 40},
                "sources": {
                    "graph": {"tokens_in": 60, "tokens_out": 20},
                    "state": {"tokens_in": 30, "tokens_out": 15},
                    "canonical": {"tokens_in": 10, "tokens_out": 5},
                    "file": {"tokens_in": 0, "tokens_out": 0},
                },
            },
        ),
        _mk_event(
            "retrieval_breakdown",
            agent_name="implementer",
            payload={
                "totals": {"tokens_in": 200, "tokens_out": 80},
                "sources": {
                    "graph": {"tokens_in": 150, "tokens_out": 50},
                    "file": {"tokens_in": 50, "tokens_out": 30},
                },
            },
        ),
    ]
    result = metrics_rollup.aggregate(events)
    tc = result["token_cost"]
    assert tc["by_agent"]["scoper"] == {"tokens_in": 100, "tokens_out": 40}
    assert tc["by_agent"]["implementer"] == {"tokens_in": 200, "tokens_out": 80}
    assert tc["by_phase"]["scoper"]["tokens_in"] == 100
    assert tc["by_phase"]["implementer"]["tokens_out"] == 80
    assert tc["by_source"]["graph"] == {"tokens_in": 210, "tokens_out": 70}
    assert tc["by_source"]["file"] == {"tokens_in": 50, "tokens_out": 30}
    assert result["totals"]["tokens_in"] == 300
    assert result["totals"]["tokens_out"] == 120


def test_ac9_synth_publish_counts_ok_failed_and_notifier() -> None:
    events = [
        _mk_event("synth_publish", payload={"status": "ok"}),
        _mk_event("synth_publish", payload={"status": "ok"}),
        _mk_event("synth_publish", payload={"status": "failed"}),
        _mk_event("vault_sync_notified", payload={"http_status": 200}),
    ]
    result = metrics_rollup.aggregate(events)
    assert result["synth_publish"] == {"ok": 2, "failed": 1, "notifier_ok": 1}


def test_ac10_totals_consistent_with_sub_rollups() -> None:
    events = [
        _mk_event("scoper", task_id="T1", agent_name="scoper", timestamp="2026-04-23T10:00:00Z"),
        _mk_event("release_status", task_id="T1", agent_name="release-orchestrator", timestamp="2026-04-23T11:00:00Z"),
        _mk_event("lease_stall_detected", task_id="T1"),
        _mk_event("dor_failure", task_id="T1", payload={"stage": "scoper"}),
        _mk_event(
            "retrieval_breakdown",
            task_id="T1",
            agent_name="scoper",
            payload={"totals": {"tokens_in": 50, "tokens_out": 25}, "sources": {}},
        ),
    ]
    result = metrics_rollup.aggregate(events)
    assert result["totals"]["events"] == 5
    assert result["totals"]["tasks_seen"] == 1
    assert result["totals"]["stalls_detected"] == 1
    assert result["totals"]["dor_failures"] == 1
    assert result["totals"]["tokens_in"] == 50
    assert result["totals"]["tokens_out"] == 25


def test_ac11_determinism_byte_identical_json() -> None:
    events = [
        _mk_event("synth_publish", payload={"status": "ok"}),
        _mk_event("lease_stall_detected", task_id="Z"),
        _mk_event(
            "retrieval_breakdown",
            agent_name="scoper",
            payload={"totals": {"tokens_in": 1, "tokens_out": 1}, "sources": {"graph": {"tokens_in": 1, "tokens_out": 1}}},
        ),
    ]
    r1 = json.dumps(metrics_rollup.aggregate(events), sort_keys=True)
    r2 = json.dumps(metrics_rollup.aggregate(events), sort_keys=True)
    assert r1 == r2


def test_ac12_source_has_no_forbidden_imports() -> None:
    src = Path(metrics_rollup.__file__).read_text(encoding="utf-8")
    for mod in ("pandas", "numpy", "boto3", "open("):
        if mod == "open(":
            assert "open(" not in src, "metrics_rollup must not open files"
        else:
            assert not re.search(rf"\bimport\s+{mod}\b", src)
            assert not re.search(rf"\bfrom\s+{mod}\b", src)


def test_ac12_malformed_timestamp_does_not_raise() -> None:
    events = [
        _mk_event("scoper", task_id="T", timestamp="not-a-timestamp"),
        _mk_event("scoper", task_id="T", timestamp=""),
    ]
    result = metrics_rollup.aggregate(events)
    assert result["totals"]["events"] == 2
    assert "T" not in result["lead_time_by_task"]


def test_non_mapping_events_skipped() -> None:
    events = [_mk_event("scoper"), "garbage", 42, None]
    result = metrics_rollup.aggregate(events)
    assert result["totals"]["events"] == 1
