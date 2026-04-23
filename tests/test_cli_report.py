"""Tests for E6-T2 `canon report` CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from canon_systems import report_cli


def _ev(
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
    event_id: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event_id": event_id or f"ev-{event_type}-{task_id}-{timestamp}",
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


def _write_ndjson(path: Path, events: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_missing_events_flag_exit_2() -> None:
    assert report_cli.run([]) == report_cli.EXIT_USAGE


def test_missing_file_exit_3() -> None:
    assert report_cli.run(["--events", "/does/not/exist.ndjson"]) == report_cli.EXIT_FILE_NOT_FOUND


def test_malformed_line_exit_4(tmp_path: Path) -> None:
    p = tmp_path / "bad.ndjson"
    p.write_text("not json\n", encoding="utf-8")
    assert report_cli.run(["--events", str(p)]) == report_cli.EXIT_MALFORMED


def test_supports_plan_id_since_until_by_flags(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events = [
        _ev("retrieval_breakdown", agent_name="scoper", plan_id="plan-1", timestamp="2026-04-01T00:00:00Z",
            payload={"totals": {"tokens_in": 10, "tokens_out": 5}, "sources": {}}),
        _ev("retrieval_breakdown", agent_name="scoper", plan_id="plan-1", timestamp="2026-04-23T10:00:00Z",
            payload={"totals": {"tokens_in": 20, "tokens_out": 10}, "sources": {}}),
        _ev("retrieval_breakdown", agent_name="scoper", plan_id="plan-2", timestamp="2026-04-23T10:00:00Z",
            payload={"totals": {"tokens_in": 999, "tokens_out": 999}, "sources": {}}),
    ]
    p = tmp_path / "events.ndjson"
    _write_ndjson(p, events)

    rc = report_cli.run([
        "--events", str(p),
        "--plan-id", "plan-1",
        "--since", "2026-04-15T00:00:00Z",
        "--until", "2026-04-30T00:00:00Z",
        "--by", "phase",
    ])
    assert rc == report_cli.EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["by"] == "phase"
    assert data["groups"]["scoper"] == {"tokens_in": 20, "tokens_out": 10}


def test_by_agent_behaves_like_by_phase(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events = [
        _ev("retrieval_breakdown", agent_name="implementer",
            payload={"totals": {"tokens_in": 7, "tokens_out": 3}, "sources": {}}),
    ]
    p = tmp_path / "events.ndjson"
    _write_ndjson(p, events)
    rc = report_cli.run(["--events", str(p), "--by", "agent"])
    assert rc == report_cli.EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["groups"]["implementer"] == {"tokens_in": 7, "tokens_out": 3}


def test_full_schema_emits_metrics_rollup(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events = [
        _ev("synth_publish", payload={"status": "ok"}),
        _ev("lease_stall_detected", task_id="T1"),
        _ev("retrieval_breakdown", agent_name="scoper",
            payload={"totals": {"tokens_in": 10, "tokens_out": 5},
                     "sources": {"graph": {"tokens_in": 10, "tokens_out": 5}}}),
    ]
    p = tmp_path / "events.ndjson"
    _write_ndjson(p, events)
    rc = report_cli.run(["--events", str(p), "--full"])
    assert rc == report_cli.EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["schema_version"] == 1
    assert data["totals"]["tokens_in"] == 10
    assert data["synth_publish"]["ok"] == 1
    assert data["stalls"]["total"] == 1


def test_full_schema_honors_scope_filters(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events = [
        _ev("synth_publish", company_id="acme", plan_id="p1", payload={"status": "ok"}),
        _ev("synth_publish", company_id="other", plan_id="p1", payload={"status": "ok"}),
    ]
    p = tmp_path / "events.ndjson"
    _write_ndjson(p, events)
    rc = report_cli.run([
        "--events", str(p),
        "--full",
        "--company-id", "acme",
        "--plan-id", "p1",
    ])
    assert rc == report_cli.EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["synth_publish"]["ok"] == 1
    assert data["scope"] == {"company_id": "acme", "repository_id": "", "plan_id": "p1"}


def test_format_csv_groupby_source(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events = [
        _ev("retrieval_breakdown",
            payload={"totals": {"tokens_in": 0, "tokens_out": 0},
                     "sources": {
                         "graph": {"tokens_in": 10, "tokens_out": 5},
                         "file": {"tokens_in": 2, "tokens_out": 1},
                     }}),
    ]
    p = tmp_path / "events.ndjson"
    _write_ndjson(p, events)
    rc = report_cli.run(["--events", str(p), "--by", "source", "--format", "csv"])
    assert rc == report_cli.EXIT_OK
    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    assert lines[0] == "source,tokens_in,tokens_out"
    assert "file,2,1" in lines
    assert "graph,10,5" in lines


def test_format_csv_full_emits_section_rows(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events = [
        _ev("synth_publish", payload={"status": "ok"}),
        _ev("synth_publish", payload={"status": "failed"}),
        _ev("dor_failure", payload={"stage": "scoper"}),
        _ev("retrieval_breakdown", agent_name="scoper",
            payload={"totals": {"tokens_in": 5, "tokens_out": 2},
                     "sources": {"graph": {"tokens_in": 5, "tokens_out": 2}}}),
    ]
    p = tmp_path / "events.ndjson"
    _write_ndjson(p, events)
    rc = report_cli.run(["--events", str(p), "--full", "--format", "csv"])
    assert rc == report_cli.EXIT_OK
    out = capsys.readouterr().out
    assert out.startswith("section,key,tokens_in,tokens_out,count\n")
    assert "synth_publish,ok,,,1" in out
    assert "synth_publish,failed,,,1" in out
    assert "dor_causes,scoper,,,1" in out
    assert "by_source,graph,5,2," in out


def test_since_until_filters_drop_out_of_window(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events = [
        _ev("retrieval_breakdown", timestamp="2026-01-01T00:00:00Z",
            payload={"totals": {"tokens_in": 100, "tokens_out": 100}, "sources": {}}),
        _ev("retrieval_breakdown", timestamp="2026-04-23T12:00:00Z",
            payload={"totals": {"tokens_in": 7, "tokens_out": 3}, "sources": {}}),
    ]
    p = tmp_path / "events.ndjson"
    _write_ndjson(p, events)
    rc = report_cli.run([
        "--events", str(p),
        "--since", "2026-04-01T00:00:00Z",
        "--by", "phase",
    ])
    assert rc == report_cli.EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["groups"]["scoper"] == {"tokens_in": 7, "tokens_out": 3}


def test_task_id_filter_in_groupby_mode(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events = [
        _ev("retrieval_breakdown", task_id="T-keep",
            payload={"totals": {"tokens_in": 1, "tokens_out": 1}, "sources": {}}),
        _ev("retrieval_breakdown", task_id="T-drop",
            payload={"totals": {"tokens_in": 9, "tokens_out": 9}, "sources": {}}),
    ]
    p = tmp_path / "events.ndjson"
    _write_ndjson(p, events)
    rc = report_cli.run(["--events", str(p), "--task-id", "T-keep", "--by", "phase"])
    assert rc == report_cli.EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["groups"]["scoper"] == {"tokens_in": 1, "tokens_out": 1}


def test_canon_cli_dispatches_report(monkeypatch: pytest.MonkeyPatch) -> None:
    from canon_systems import cli

    captured: dict[str, Any] = {}

    def fake_run(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr("canon_systems.cli.run_report_cli", fake_run)
    # argparse.REMAINDER needs `--` to pass leading optional flags through.
    rc = cli.main(["report", "--", "--events", "x.ndjson", "--by", "phase"])
    assert rc == 0
    # REMAINDER passes the `--` through as part of the captured args.
    assert "--events" in captured["argv"]
    assert "x.ndjson" in captured["argv"]
    assert "--by" in captured["argv"]
    assert "phase" in captured["argv"]


def test_determinism_json_output_is_stable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events = [
        _ev("synth_publish", payload={"status": "ok"}),
        _ev("retrieval_breakdown", agent_name="scoper",
            payload={"totals": {"tokens_in": 3, "tokens_out": 1},
                     "sources": {"graph": {"tokens_in": 3, "tokens_out": 1}}}),
    ]
    p = tmp_path / "events.ndjson"
    _write_ndjson(p, events)
    rc1 = report_cli.run(["--events", str(p), "--full"])
    out1 = capsys.readouterr().out
    rc2 = report_cli.run(["--events", str(p), "--full"])
    out2 = capsys.readouterr().out
    assert rc1 == rc2 == report_cli.EXIT_OK
    assert out1 == out2
