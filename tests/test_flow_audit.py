from __future__ import annotations

import json
from pathlib import Path

from canon_systems.checkpoints import REQUIRED_PHASES
from canon_systems.flow_audit import run


def _write_task_artifacts(root: Path, *, handoff_id: str, task_id: str) -> None:
    base = root / ".cursor" / "handoffs" / handoff_id / task_id
    base.mkdir(parents=True, exist_ok=True)
    (base / "scoper.md").write_text("HANDOFF_TO_CURSOR_PILOT\n", encoding="utf-8")
    (base / "cursor-pilot.md").write_text("CURSOR_PILOT_PROMPT\n", encoding="utf-8")
    (base / "qa-gate.md").write_text("GATE_RESULTS\nEND_GATE_RESULTS\n", encoding="utf-8")
    (base / "release-status.md").write_text("RELEASE_STATUS\nEND_RELEASE_STATUS\n", encoding="utf-8")


def _write_memory_health_evidence(
    root: Path,
    *,
    handoff_id: str,
    task_id: str,
    overall_status: str = "ok",
    schema_version: str = "1",
) -> None:
    base = root / ".cursor" / "handoffs" / handoff_id / task_id
    base.mkdir(parents=True, exist_ok=True)
    body = {
        "schema_version": schema_version,
        "overall_status": overall_status,
    }
    (base / "memory-health.json").write_text(json.dumps(body) + "\n", encoding="utf-8")


def _write_dor_rejection_with_telemetry(root: Path, *, handoff_id: str, task_id: str, stem: str) -> None:
    base = root / ".cursor" / "handoffs" / handoff_id / task_id
    rej_dir = base / "handoff-not-ready"
    dor_dir = base / "dor-failure"
    rej_dir.mkdir(parents=True, exist_ok=True)
    dor_dir.mkdir(parents=True, exist_ok=True)
    (rej_dir / f"{stem}.md").write_text(
        "HANDOFF_NOT_READY\nDOR_FAILURE_LOG:\n  stage: scoper\nEND_HANDOFF_NOT_READY\n",
        encoding="utf-8",
    )
    (dor_dir / f"{stem}.json").write_text(
        '{"handoff_id":"h1","stage":"scoper","missing_fields":["story.title"]}\n',
        encoding="utf-8",
    )
    (dor_dir / f"{stem}.status").write_text("exit_code: 0\n", encoding="utf-8")


def test_flow_audit_passes_for_valid_artifacts(tmp_path: Path, monkeypatch) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    plan = tmp_path / ".cursor" / "plans" / "plan.md"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("task_id: t1\nstatus: done\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
            "--plan-file",
            str(plan),
            "--require-release-status",
        ]
    )
    assert code == 0


def test_flow_audit_fails_when_missing_packet(tmp_path: Path, monkeypatch) -> None:
    base = tmp_path / ".cursor" / "handoffs" / "h1" / "t1"
    base.mkdir(parents=True, exist_ok=True)
    (base / "scoper.md").write_text("HANDOFF_TO_CURSOR_PILOT\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1"])
    assert code == 1


def test_flow_audit_sampling_can_skip(tmp_path: Path, monkeypatch) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--sample-rate", "0"])
    assert code == 0


def test_flow_audit_fails_when_rejection_missing_telemetry(tmp_path: Path, monkeypatch) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    base = tmp_path / ".cursor" / "handoffs" / "h1" / "t1" / "handoff-not-ready"
    base.mkdir(parents=True, exist_ok=True)
    (base / "cursor-pilot-20260424T010203Z.md").write_text(
        "HANDOFF_NOT_READY\nDOR_FAILURE_LOG:\n  stage: cursor-pilot-preflight\nEND_HANDOFF_NOT_READY\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1"])
    assert code == 1


def test_flow_audit_passes_with_memory_health_evidence_ok(tmp_path: Path, monkeypatch) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_memory_health_evidence(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-memory-health"])
    assert code == 0


def test_flow_audit_fails_when_memory_health_evidence_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-memory-health"])
    assert code == 1
    out = capsys.readouterr().out
    assert "missing memory-health evidence" in out


def test_flow_audit_fails_when_memory_health_overall_status_not_ok(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_memory_health_evidence(tmp_path, handoff_id="h1", task_id="t1", overall_status="unhealthy")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-memory-health"])
    assert code == 1
    out = capsys.readouterr().out
    assert "overall_status='unhealthy' (expected 'ok')" in out


def test_flow_audit_passes_without_flag_when_memory_health_missing(tmp_path: Path, monkeypatch) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1"])
    assert code == 0


def _write_checkpoints(
    root: Path,
    *,
    handoff_id: str,
    task_id: str,
    override_phase: str | None = None,
    overrides: dict | None = None,
) -> None:
    base = root / ".cursor" / "handoffs" / handoff_id / task_id / "checkpoints"
    base.mkdir(parents=True, exist_ok=True)
    for phase in REQUIRED_PHASES:
        body: dict = {
            "schema_version": "1",
            "phase": phase,
            "task_id": task_id,
            "handoff_id": handoff_id,
            "state_version": 1,
        }
        if override_phase == phase and overrides:
            body.update(overrides)
        (base / f"{phase}.json").write_text(json.dumps(body) + "\n", encoding="utf-8")


def test_flow_audit_require_checkpoints_passes_when_all_five_valid(tmp_path: Path, monkeypatch) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_checkpoints(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-checkpoints"])
    assert code == 0


def test_flow_audit_require_checkpoints_fails_when_phase_file_missing(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_checkpoints(tmp_path, handoff_id="h1", task_id="t1")
    (tmp_path / ".cursor" / "handoffs" / "h1" / "t1" / "checkpoints" / "scoper.json").unlink()
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-checkpoints"])
    assert code == 1
    out = capsys.readouterr().out
    assert "flow-audit: FAILED" in out
    assert "missing checkpoint artifact" in out


def test_flow_audit_require_checkpoints_fails_when_schema_version_not_one(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_checkpoints(
        tmp_path, handoff_id="h1", task_id="t1", override_phase="scoper", overrides={"schema_version": "2"}
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-checkpoints"])
    assert code == 1
    out = capsys.readouterr().out
    assert "schema_version mismatch" in out


def test_flow_audit_require_checkpoints_fails_when_phase_field_mismatch(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_checkpoints(
        tmp_path, handoff_id="h1", task_id="t1", override_phase="cursor-pilot", overrides={"phase": "wrong"}
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-checkpoints"])
    assert code == 1
    out = capsys.readouterr().out
    assert "phase mismatch" in out


def test_flow_audit_require_checkpoints_fails_when_handoff_id_mismatch(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_checkpoints(
        tmp_path, handoff_id="h1", task_id="t1", override_phase="implementer", overrides={"handoff_id": "other"}
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-checkpoints"])
    assert code == 1
    out = capsys.readouterr().out
    assert "handoff_id mismatch" in out


def test_flow_audit_require_checkpoints_fails_when_task_id_mismatch(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_checkpoints(
        tmp_path, handoff_id="h1", task_id="t1", override_phase="qa-gate", overrides={"task_id": "t9"}
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-checkpoints"])
    assert code == 1
    out = capsys.readouterr().out
    assert "task_id mismatch" in out


def test_flow_audit_require_checkpoints_fails_when_state_version_missing_or_zero(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_checkpoints(tmp_path, handoff_id="h1", task_id="t1")
    cdir = tmp_path / ".cursor" / "handoffs" / "h1" / "t1" / "checkpoints"
    imp = cdir / "implementer.json"
    d0 = json.loads(imp.read_text(encoding="utf-8"))
    d0["state_version"] = 0
    imp.write_text(json.dumps(d0) + "\n", encoding="utf-8")
    qg = cdir / "qa-gate.json"
    d1 = json.loads(qg.read_text(encoding="utf-8"))
    del d1["state_version"]
    qg.write_text(json.dumps(d1) + "\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-checkpoints"])
    assert code == 1
    out = capsys.readouterr().out
    assert "state_version invalid" in out


def test_flow_audit_passes_without_require_checkpoints_without_checkpoints_dir(
    tmp_path: Path, monkeypatch
) -> None:
    base = tmp_path / ".cursor" / "handoffs" / "h1" / "t1"
    base.mkdir(parents=True, exist_ok=True)
    (base / "scoper.md").write_text("HANDOFF_TO_CURSOR_PILOT\n", encoding="utf-8")
    (base / "cursor-pilot.md").write_text("CURSOR_PILOT_PROMPT\n", encoding="utf-8")
    (base / "qa-gate.md").write_text("GATE_RESULTS\nEND_GATE_RESULTS\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1"])
    assert code == 0


def test_flow_audit_require_checkpoints_invalid_json_fails(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_checkpoints(tmp_path, handoff_id="h1", task_id="t1")
    (tmp_path / ".cursor" / "handoffs" / "h1" / "t1" / "checkpoints" / "scoper.json").write_text(
        "null\n", encoding="utf-8"
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-checkpoints"])
    assert code == 1
    out = capsys.readouterr().out
    assert "must be JSON object" in out
