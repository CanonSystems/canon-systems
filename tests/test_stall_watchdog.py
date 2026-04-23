"""Tests for canon stall-watchdog scan (E4-T3)."""

from __future__ import annotations

import json
from pathlib import Path

from canon_systems import cli, stall_watchdog
from canon_systems.checkpoint_cli import _resolution_hint


def _scope(extra: list[str] | None = None) -> list[str]:
    return [
        "scan",
        "--company-id", "c-1", "--repository-id", "r-1", "--plan-id", "p-1",
    ] + (extra or [])


def _queue(*responses):
    it = iter(responses)

    def _fake(url, *, timeout_ms):
        return next(it)

    return _fake


def _checkpoint_body(*, task_id: str, workstream_id: str = "ws-main", lease):
    return {
        "company_id": "c-1", "repository_id": "r-1", "plan_id": "p-1",
        "task_id": task_id, "workstream_id": workstream_id,
        "state_version": 3, "phase": "implementer", "phase_status": "in_progress",
        "lease": lease,
    }


def test_scan_single_stalled_task_emits_one_event(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)

    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps([{"task_id": "E4-T2", "workstream_id": "ws-main"}]))
    event_log = tmp_path / "events.ndjson"

    def _fake(url, *, timeout_ms):
        return (200, _checkpoint_body(
            task_id="E4-T2",
            lease={"owner_agent_run_id": "run-stale", "expires_at": NOW - 600},
        ), {})

    monkeypatch.setattr(stall_watchdog, "_http_request", _fake)

    rc = stall_watchdog.run(_scope([
        "--tasks-file", str(tasks_file),
        "--event-log", str(event_log),
    ]))
    assert rc == stall_watchdog.EXIT_OK

    out = capsys.readouterr().out.strip()
    envelope = json.loads(out)
    assert envelope["tasks_scanned"] == 1
    assert envelope["stalls_detected"] == 1
    assert envelope["events_emitted"] == 1
    assert envelope["degraded_tasks"] == []

    lines = event_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["event_type"] == "lease_stall_detected"
    assert event["task_id"] == "E4-T2"
    assert event["agent_name"] == "canon-stall-watchdog"
    assert event["handoff_id"] == ""
    assert event["state_version"] == 0
    assert event["payload"]["diagnostic"]["task_id"] == "E4-T2"
    assert event["payload"]["diagnostic"]["stale_owner_agent_run_id"] == "run-stale"
    assert event["payload"]["diagnostic"]["ttl_remaining_s"] == -600
    assert event["payload"]["suggested_next_step"] == _resolution_hint("lease_held")


def test_scan_live_lease_emits_no_event(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps([{"task_id": "E4-T1"}]))
    event_log = tmp_path / "events.ndjson"

    def _fake(url, *, timeout_ms):
        return (200, _checkpoint_body(
            task_id="E4-T1",
            lease={"owner_agent_run_id": "run-live", "expires_at": NOW + 600},
        ), {})

    monkeypatch.setattr(stall_watchdog, "_http_request", _fake)
    rc = stall_watchdog.run(_scope(["--tasks-file", str(tasks_file), "--event-log", str(event_log)]))
    assert rc == stall_watchdog.EXIT_OK
    envelope = json.loads(capsys.readouterr().out.strip())
    assert envelope["stalls_detected"] == 0
    assert envelope["events_emitted"] == 0
    assert not event_log.exists()


def test_scan_no_lease_emits_no_event(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps([{"task_id": "E4-T1"}]))
    event_log = tmp_path / "events.ndjson"

    def _fake(url, *, timeout_ms):
        return (200, _checkpoint_body(task_id="E4-T1", lease=None), {})

    monkeypatch.setattr(stall_watchdog, "_http_request", _fake)
    rc = stall_watchdog.run(_scope(["--tasks-file", str(tasks_file), "--event-log", str(event_log)]))
    assert rc == stall_watchdog.EXIT_OK
    envelope = json.loads(capsys.readouterr().out.strip())
    assert envelope["stalls_detected"] == 0
    assert envelope["events_emitted"] == 0


def test_scan_404_not_stalled_not_degraded(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps([{"task_id": "E4-T1"}]))
    event_log = tmp_path / "events.ndjson"

    def _fake(url, *, timeout_ms):
        return (404, {"detail": "not found"}, {})

    monkeypatch.setattr(stall_watchdog, "_http_request", _fake)
    rc = stall_watchdog.run(_scope(["--tasks-file", str(tasks_file), "--event-log", str(event_log)]))
    assert rc == stall_watchdog.EXIT_OK
    envelope = json.loads(capsys.readouterr().out.strip())
    assert envelope["degraded_tasks"] == []
    assert envelope["stalls_detected"] == 0


def test_scan_transport_error_degrades(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps([{"task_id": "E4-T1"}]))
    event_log = tmp_path / "events.ndjson"

    def _fake(url, *, timeout_ms):
        return (0, None, {"X-Canon-Transport-Error": "ConnectionError"})

    monkeypatch.setattr(stall_watchdog, "_http_request", _fake)
    rc = stall_watchdog.run(_scope(["--tasks-file", str(tasks_file), "--event-log", str(event_log)]))
    assert rc == stall_watchdog.EXIT_TRANSPORT
    envelope = json.loads(capsys.readouterr().out.strip())
    assert envelope["degraded_tasks"] == [{"task_id": "E4-T1", "reason": "transport"}]


def test_scan_5xx_degrades(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps([{"task_id": "E4-T1"}]))
    event_log = tmp_path / "events.ndjson"

    def _fake(url, *, timeout_ms):
        return (500, {"detail": "boom"}, {})

    monkeypatch.setattr(stall_watchdog, "_http_request", _fake)
    rc = stall_watchdog.run(_scope(["--tasks-file", str(tasks_file), "--event-log", str(event_log)]))
    assert rc == stall_watchdog.EXIT_TRANSPORT
    envelope = json.loads(capsys.readouterr().out.strip())
    assert envelope["degraded_tasks"] == [{"task_id": "E4-T1", "reason": "http_500"}]


def test_done_signal_simulated_stall(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps([
        {"task_id": "E4-TA", "workstream_id": "ws-main"},
        {"task_id": "E4-TB", "workstream_id": "ws-main"},
    ]))
    event_log = tmp_path / "events.ndjson"

    monkeypatch.setattr(stall_watchdog, "_http_request", _queue(
        (200, _checkpoint_body(
            task_id="E4-TA",
            lease={"owner_agent_run_id": "run-a", "expires_at": NOW - 1},
        ), {}),
        (200, _checkpoint_body(
            task_id="E4-TB",
            lease={"owner_agent_run_id": "run-b", "expires_at": NOW + 999},
        ), {}),
    ))
    rc = stall_watchdog.run(_scope(["--tasks-file", str(tasks_file), "--event-log", str(event_log)]))
    assert rc == stall_watchdog.EXIT_OK
    envelope = json.loads(capsys.readouterr().out.strip())
    assert envelope["stalls_detected"] == 1
    assert envelope["events_emitted"] == 1
    assert envelope["degraded_tasks"] == []
    lines = event_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["task_id"] == "E4-TA"


def test_dry_run_writes_to_stderr_not_file(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps([{"task_id": "E4-T1"}]))
    event_log = tmp_path / "events.ndjson"

    def _fake(url, *, timeout_ms):
        return (200, _checkpoint_body(
            task_id="E4-T1",
            lease={"owner_agent_run_id": "x", "expires_at": NOW - 1},
        ), {})

    monkeypatch.setattr(stall_watchdog, "_http_request", _fake)
    rc = stall_watchdog.run(_scope([
        "--tasks-file", str(tasks_file),
        "--event-log", str(event_log),
        "--dry-run",
    ]))
    assert rc == stall_watchdog.EXIT_OK
    captured = capsys.readouterr()
    envelope = json.loads(captured.out.strip())
    assert envelope["events_emitted"] == 0
    assert envelope["event_log_path"] == "(stderr dry-run)"
    err_lines = captured.err.strip().splitlines()
    assert len(err_lines) == 1
    ev = json.loads(err_lines[0])
    assert ev["event_type"] == "lease_stall_detected"
    assert not event_log.exists()


def test_event_log_default_path_appends(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)
    monkeypatch.chdir(tmp_path)
    tasks_a = tmp_path / "a.json"
    tasks_b = tmp_path / "b.json"
    tasks_a.write_text(json.dumps([{"task_id": "E4-T1"}]))
    tasks_b.write_text(json.dumps([{"task_id": "E4-T2"}]))
    default_log = tmp_path / ".canon" / "memory" / "events.ndjson"

    def _fake_stall(url, *, timeout_ms):
        return (200, _checkpoint_body(
            task_id="E4-T1",
            lease={"owner_agent_run_id": "o1", "expires_at": NOW - 1},
        ), {})

    monkeypatch.setattr(stall_watchdog, "_http_request", _fake_stall)
    assert stall_watchdog.run(_scope(["--tasks-file", str(tasks_a)])) == stall_watchdog.EXIT_OK
    capsys.readouterr()

    def _fake_stall_b(url, *, timeout_ms):
        return (200, _checkpoint_body(
            task_id="E4-T2",
            lease={"owner_agent_run_id": "o2", "expires_at": NOW - 2},
        ), {})

    monkeypatch.setattr(stall_watchdog, "_http_request", _fake_stall_b)
    assert stall_watchdog.run(_scope(["--tasks-file", str(tasks_b)])) == stall_watchdog.EXIT_OK

    lines = default_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["task_id"] == "E4-T1"
    assert json.loads(lines[1])["task_id"] == "E4-T2"


def test_tasks_file_and_handoffs_dir_mutually_exclusive(monkeypatch, tmp_path):
    f1 = tmp_path / "tasks.json"
    f1.write_text(json.dumps([{"task_id": "E4-T1"}]))
    d1 = tmp_path / "handoffs"
    d1.mkdir()
    rc = stall_watchdog.run(_scope(["--tasks-file", str(f1), "--handoffs-dir", str(d1)]))
    assert rc == stall_watchdog.EXIT_USAGE


def test_handoffs_dir_discovers_e_t_subdirs(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)
    handoffs = tmp_path / "handoffs"
    (handoffs / "E4-T3").mkdir(parents=True)
    (handoffs / "E4-T4").mkdir(parents=True)
    (handoffs / "other").mkdir()

    monkeypatch.setattr(stall_watchdog, "_http_request", lambda url, *, timeout_ms: (404, {}, {}))

    rc = stall_watchdog.run(_scope(["--handoffs-dir", str(handoffs)]))
    assert rc == stall_watchdog.EXIT_OK
    envelope = json.loads(capsys.readouterr().out.strip())
    assert envelope["tasks_scanned"] == 2


def test_canonical_event_import_not_redefined():
    src = Path(stall_watchdog.__file__).read_text(encoding="utf-8")
    assert "class CanonicalEvent" not in src
    assert "from canon_backend_shared.events import CanonicalEvent" in src


def test_cli_wiring_passes_args_to_subcommand(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)
    monkeypatch.delenv("CANON_SYSTEMS_REPO_ROOT", raising=False)
    monkeypatch.delenv("CANON_MEMORY_LAYER_REPO_ROOT", raising=False)
    monkeypatch.setattr(cli, "detect_repo_root", lambda explicit="": tmp_path)
    monkeypatch.setattr(cli, "_maybe_auto_rewire", lambda root, command: None)
    monkeypatch.setattr(cli, "_maybe_auto_rewire_all", lambda command: None)
    monkeypatch.setattr("canon_systems.self_update.try_self_update", lambda *a, **k: None)

    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps([{"task_id": "E4-T2"}]))
    event_log = tmp_path / "events.ndjson"

    def _fake(url, *, timeout_ms):
        return (200, _checkpoint_body(
            task_id="E4-T2",
            lease={"owner_agent_run_id": "run-stale", "expires_at": NOW - 600},
        ), {})

    monkeypatch.setattr(stall_watchdog, "_http_request", _fake)

    code = cli.main([
        "stall-watchdog", "scan",
        "--company-id", "c-1", "--repository-id", "r-1", "--plan-id", "p-1",
        "--tasks-file", str(tasks_file),
        "--event-log", str(event_log),
    ])
    assert code == 0
    envelope = json.loads(capsys.readouterr().out.strip())
    assert envelope["tasks_scanned"] == 1
    assert envelope["stalls_detected"] == 1
    assert envelope["events_emitted"] == 1
