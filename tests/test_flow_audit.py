from __future__ import annotations

from pathlib import Path

from canon_systems.flow_audit import run


def _write_task_artifacts(root: Path, *, handoff_id: str, task_id: str) -> None:
    base = root / ".cursor" / "handoffs" / handoff_id / task_id
    base.mkdir(parents=True, exist_ok=True)
    (base / "scoper.md").write_text("HANDOFF_TO_CURSOR_PILOT\n", encoding="utf-8")
    (base / "cursor-pilot.md").write_text("CURSOR_PILOT_PROMPT\n", encoding="utf-8")
    (base / "qa-gate.md").write_text("GATE_RESULTS\nEND_GATE_RESULTS\n", encoding="utf-8")
    (base / "release-status.md").write_text("RELEASE_STATUS\nEND_RELEASE_STATUS\n", encoding="utf-8")


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
