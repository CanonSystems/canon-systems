from __future__ import annotations

import json
from pathlib import Path

import pytest

from canon_systems.checkpoints import REQUIRED_PHASES
from canon_systems.dor_telemetry import DorTelemetryLabels, collect_dor_telemetry_errors
from canon_systems import cli as canon_cli
from canon_systems.flow_audit import (
    DEPLOY_ATTESTATION_FILENAME,
    STALE_DEPLOY_VERDICT,
    run,
)


def _write_task_artifacts(root: Path, *, handoff_id: str, task_id: str) -> None:
    base = root / ".cursor" / "handoffs" / handoff_id / task_id
    base.mkdir(parents=True, exist_ok=True)
    (base / "scoper.md").write_text("HANDOFF_TO_CURSOR_PILOT\n", encoding="utf-8")
    (base / "cursor-pilot.md").write_text("CURSOR_PILOT_PROMPT\n", encoding="utf-8")
    (base / "qa-gate.md").write_text("GATE_RESULTS\nEND_GATE_RESULTS\n", encoding="utf-8")
    (base / "release-status.md").write_text("RELEASE_STATUS\nEND_RELEASE_STATUS\n", encoding="utf-8")


_DEPLOY_SHA_A40 = "a" * 40
_DEPLOY_SHA_B40 = "b" * 40


def _write_deploy_attestation(
    root: Path,
    *,
    handoff_id: str,
    task_id: str,
    **overrides: object,
) -> Path:
    """Write ``deployment-smoke.json`` with sane defaults (schema v1)."""
    base = root / ".cursor" / "handoffs" / handoff_id / task_id
    base.mkdir(parents=True, exist_ok=True)
    body: dict[str, object] = {
        "schema_version": "1",
        "handoff_id": handoff_id,
        "task_id": task_id,
        "environment": "dev",
        "base_url": "https://dev.example.invalid/",
        "expected_branch": "feature/canon-run-ledger-readiness",
        "expected_head_sha": _DEPLOY_SHA_A40,
        "deployed_commit_sha": _DEPLOY_SHA_A40,
        "smoke_verdict": "pass",
        "checked_at": "2026-05-04T12:00:00Z",
        "evidence_refs": [],
    }
    body.update(overrides)
    path = base / DEPLOY_ATTESTATION_FILENAME
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    return path


def _deploy_audit_green_run(tmp_path: Path, monkeypatch) -> int:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_deploy_attestation(tmp_path, handoff_id="h1", task_id="t1")
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    return run(
        [
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
            "--require-deploy-attestation",
        ]
    )


def test_flow_audit_passes_with_deploy_attestation_for_current_sha(tmp_path: Path, monkeypatch) -> None:
    """AC3: ``--require-deploy-attestation`` passes when deployment-smoke.json is valid."""
    assert _deploy_audit_green_run(tmp_path, monkeypatch) == 0


def test_deploy_attestation_accepts_current_deployed_sha(tmp_path: Path, monkeypatch) -> None:
    """AC1: matched deployed_commit_sha satisfies branch/deploy proof."""
    assert _deploy_audit_green_run(tmp_path, monkeypatch) == 0


def test_flow_audit_fails_when_deploy_attestation_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-deploy-attestation"])
    assert code == 1
    assert "missing deploy attestation evidence" in capsys.readouterr().out


def test_flow_audit_fails_when_deployed_sha_differs_from_expected_sha(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_deploy_attestation(
        tmp_path,
        handoff_id="h1",
        task_id="t1",
        deployed_commit_sha=_DEPLOY_SHA_B40,
    )
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-deploy-attestation"])
    assert code == 1
    assert "deployed_commit_sha does not match expected_head_sha" in capsys.readouterr().out


def test_flow_audit_fails_when_deploy_attestation_lacks_build_or_sha(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_deploy_attestation(
        tmp_path,
        handoff_id="h1",
        task_id="t1",
        deployed_commit_sha="",
        deployed_build_id="",
    )
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-deploy-attestation"])
    assert code == 1
    assert "deployed_commit_sha and/or deployed_build_id" in capsys.readouterr().out


def test_flow_audit_deploy_attestation_requires_expected_branch(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC1/AC3: deployment-smoke evidence records the branch identity, not just a SHA."""
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_deploy_attestation(
        tmp_path,
        handoff_id="h1",
        task_id="t1",
        expected_branch="",
    )
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-deploy-attestation"])
    assert code == 1
    assert "expected_branch" in capsys.readouterr().out


def test_flow_audit_deploy_attestation_invalid_json(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    base = tmp_path / ".cursor" / "handoffs" / "h1" / "t1"
    (base / DEPLOY_ATTESTATION_FILENAME).write_text("{broken\n", encoding="utf-8")
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-deploy-attestation"])
    assert code == 1
    assert "invalid JSON in deploy attestation evidence" in capsys.readouterr().out


def test_flow_audit_deploy_attestation_identity_mismatch(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    path = _write_deploy_attestation(tmp_path, handoff_id="h1", task_id="t1")
    body = json.loads(path.read_text(encoding="utf-8"))
    body["handoff_id"] = "wrong"
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-deploy-attestation"])
    assert code == 1
    assert "handoff_id mismatch" in capsys.readouterr().out


def test_flow_audit_deploy_attestation_stale_verdict(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC1/AC3: ``environment_smoke_not_proof_of_branch`` fails attestation."""
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_deploy_attestation(tmp_path, handoff_id="h1", task_id="t1", smoke_verdict=STALE_DEPLOY_VERDICT)
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1", "--require-deploy-attestation"])
    assert code == 1
    out = capsys.readouterr().out
    assert STALE_DEPLOY_VERDICT in out
    assert "smoke_verdict=" in out


def test_flow_audit_deploy_attestation_build_id_proof_passes(tmp_path: Path, monkeypatch) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_deploy_attestation(
        tmp_path,
        handoff_id="h1",
        task_id="t1",
        deployed_commit_sha="",
        deployed_build_id="build-99",
        expected_build_id="build-99",
    )
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert run(["--handoff-id", "h1", "--task-id", "t1", "--require-deploy-attestation"]) == 0


def test_flow_audit_deploy_attestation_sampling_skip_does_not_validate_file(
    tmp_path: Path, monkeypatch
) -> None:
    """Sampling short-circuit must not open ``deployment-smoke.json``."""

    def _boom(*_a, **_k):  # pragma: no cover
        raise AssertionError("deploy attestation must not validate when sample skips")

    monkeypatch.setattr("canon_systems.flow_audit._collect_deploy_attestation_errors", _boom)
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        ["--handoff-id", "h1", "--task-id", "t1", "--sample-rate", "0", "--require-deploy-attestation"]
    )
    assert code == 0


def test_public_cli_flow_audit_forwards_require_deploy_attestation(tmp_path: Path, monkeypatch) -> None:
    """AC4: top-level ``canon flow-audit`` passes ``--require-deploy-attestation`` through to ``flow_audit.run``."""
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_deploy_attestation(tmp_path, handoff_id="h1", task_id="t1")
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.delenv("CANON_SYSTEMS_REPO_ROOT", raising=False)
    monkeypatch.delenv("CANON_MEMORY_LAYER_REPO_ROOT", raising=False)
    code = canon_cli.main(
        [
            "--repo-root",
            str(tmp_path),
            "flow-audit",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
            "--require-deploy-attestation",
        ]
    )
    assert code == 0


def test_public_cli_flow_audit_deploy_sampling_skip_does_not_validate_file(
    tmp_path: Path, monkeypatch
) -> None:
    """AC4: sampling skip via public CLI must not invoke deploy attestation validation."""

    def _boom(*_a, **_k):  # pragma: no cover
        raise AssertionError("deploy attestation must not validate when sample skips")

    monkeypatch.setattr("canon_systems.flow_audit._collect_deploy_attestation_errors", _boom)
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.delenv("CANON_SYSTEMS_REPO_ROOT", raising=False)
    monkeypatch.delenv("CANON_MEMORY_LAYER_REPO_ROOT", raising=False)
    code = canon_cli.main(
        [
            "--repo-root",
            str(tmp_path),
            "flow-audit",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
            "--sample-rate",
            "0",
            "--require-deploy-attestation",
        ]
    )
    assert code == 0


def test_public_cli_flow_audit_forwards_require_checkpoints(
    tmp_path: Path, monkeypatch
) -> None:
    """ws2-cli-parity: top-level ``canon flow-audit`` forwards ``--require-checkpoints``."""
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_checkpoints(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.delenv("CANON_SYSTEMS_REPO_ROOT", raising=False)
    monkeypatch.delenv("CANON_MEMORY_LAYER_REPO_ROOT", raising=False)
    code = canon_cli.main(
        [
            "--repo-root",
            str(tmp_path),
            "flow-audit",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
            "--require-checkpoints",
        ]
    )
    assert code == 0


def test_top_level_help_lists_flow_audit_require_checkpoints(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC2/AC4: public parser documents checkpoint gate flag."""
    with pytest.raises(SystemExit) as ei:
        canon_cli.main(["--repo-root", str(tmp_path), "flow-audit", "--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "--require-checkpoints" in out
    assert "--require-deploy-attestation" in out


def test_flow_audit_passes_without_flag_when_deploy_attestation_missing(tmp_path: Path, monkeypatch) -> None:
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    _write_dor_rejection_with_telemetry(tmp_path, handoff_id="h1", task_id="t1", stem="scoper-20260424T010203Z")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert run(["--handoff-id", "h1", "--task-id", "t1"]) == 0


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
        json.dumps(
            {
                "handoff_id": handoff_id,
                "stage": "scoper",
                "task_id": task_id,
                "missing_fields": ["story.title"],
            }
        )
        + "\n",
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


def test_flow_audit_ac1_invokes_collect_dor_telemetry_errors_for_task(
    tmp_path: Path, monkeypatch
) -> None:
    """AC1: flow-audit delegates DoR validation to ``collect_dor_telemetry_errors_for_task``."""
    calls: list[dict] = []

    def recorder(**kwargs) -> list[str]:
        calls.append(kwargs)
        return []

    monkeypatch.setattr(
        "canon_systems.flow_audit.collect_dor_telemetry_errors_for_task",
        recorder,
    )
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert run(["--handoff-id", "h1", "--task-id", "t1"]) == 0
    assert len(calls) == 1
    kw = calls[0]
    assert kw["root"] == tmp_path.resolve()
    assert kw["handoff_id"] == "h1"
    assert kw["task_id"] == "t1"
    assert kw["require_task_identity"] is True
    assert kw["bulk_error_if_no_json"] is True
    assert kw["labels"] == DorTelemetryLabels.flow_audit()


def test_flow_audit_ac5_sample_rate_skip_does_not_call_dor_helper(
    tmp_path: Path, monkeypatch
) -> None:
    """AC5: sampling short-circuit leaves non-DoR behavior unchanged — no DoR helper when skipped."""

    def should_not_run(**kwargs) -> list[str]:  # pragma: no cover
        raise AssertionError("collect_dor_telemetry_errors_for_task must not run when skipped")

    monkeypatch.setattr(
        "canon_systems.flow_audit.collect_dor_telemetry_errors_for_task",
        should_not_run,
    )
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


def _flow_dor_dirs(root: Path, *, handoff_id: str, task_id: str, stem: str) -> tuple[Path, Path]:
    base = root / ".cursor" / "handoffs" / handoff_id / task_id
    rej_dir = base / "handoff-not-ready"
    dor_dir = base / "dor-failure"
    rej_dir.mkdir(parents=True, exist_ok=True)
    dor_dir.mkdir(parents=True, exist_ok=True)
    rej_path = rej_dir / f"{stem}.md"
    rej_path.write_text(
        "HANDOFF_NOT_READY\nDOR_FAILURE_LOG:\n  stage: x\nEND_HANDOFF_NOT_READY\n",
        encoding="utf-8",
    )
    return dor_dir, rej_path


def test_flow_audit_dor_telemetry_invalid_json_and_non_object_paths(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC2: flow-audit surfaces telemetry paths using flow-audit phrasing."""
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    dor_dir, _rej = _flow_dor_dirs(tmp_path, handoff_id="h1", task_id="t1", stem="fe1")
    (dor_dir / "fe1.json").write_text("broken\n", encoding="utf-8")
    (dor_dir / "fe1.status").write_text("exit_code: 0\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1"])
    out = capsys.readouterr().out
    assert code == 1
    assert "invalid JSON in telemetry file:" in out
    assert str(dor_dir / "fe1.json") in out

    (dor_dir / "fe1.json").write_text('"scalar"\n', encoding="utf-8")
    code2 = run(["--handoff-id", "h1", "--task-id", "t1"])
    out2 = capsys.readouterr().out
    assert code2 == 1
    assert "telemetry payload must be object:" in out2


def test_flow_audit_dor_telemetry_bulk_warns_when_no_json_files(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC2: actionable dor-failure directory when rejections exist without telemetry JSON."""
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    base = tmp_path / ".cursor" / "handoffs" / "h1" / "t1"
    rej_dir = base / "handoff-not-ready"
    dor_dir = base / "dor-failure"
    rej_dir.mkdir(parents=True, exist_ok=True)
    dor_dir.mkdir(parents=True, exist_ok=True)
    (rej_dir / "bulk1.md").write_text("HANDOFF_NOT_READY\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1"])
    out = capsys.readouterr().out
    assert code == 1
    assert "HANDOFF_NOT_READY packets exist but no DoR telemetry JSON files found under" in out
    assert str(dor_dir) in out


def test_flow_audit_ac4_telemetry_status_requires_exit_code_marker(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC4: status files must contain ``exit_code:`` (shared helper rule; flow-audit exit 1)."""
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    dor_dir, _rej = _flow_dor_dirs(tmp_path, handoff_id="h1", task_id="t1", stem="ac4mark")
    (dor_dir / "ac4mark.json").write_text(
        json.dumps({"handoff_id": "h1", "stage": "scoper", "task_id": "t1"}),
        encoding="utf-8",
    )
    (dor_dir / "ac4mark.status").write_text("status without colon pattern\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--handoff-id", "h1", "--task-id", "t1"])
    out = capsys.readouterr().out
    assert code == 1
    assert "telemetry status missing exit_code marker:" in out


def test_flow_audit_dor_telemetry_identity_and_exit_code_marker(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC3/AC4: identity fields and exit_code marker via flow-audit."""
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    dor_dir, _rej = _flow_dor_dirs(tmp_path, handoff_id="h1", task_id="t1", stem="fid")

    def expect(payload: str, status_body: str, needle: str) -> None:
        (dor_dir / "fid.json").write_text(payload + "\n", encoding="utf-8")
        (dor_dir / "fid.status").write_text(status_body, encoding="utf-8")
        c = run(["--handoff-id", "h1", "--task-id", "t1"])
        o = capsys.readouterr().out
        assert c == 1, o
        assert needle in o

    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    expect(
        '{"handoff_id":"x","stage":"scoper","task_id":"t1"}',
        "exit_code: 0\n",
        "telemetry handoff_id mismatch",
    )
    expect(
        '{"handoff_id":"h1","stage":"   ","task_id":"t1"}',
        "exit_code: 0\n",
        "telemetry stage missing",
    )
    expect(
        '{"handoff_id":"h1","stage":"scoper","task_id":"other"}',
        "exit_code: 0\n",
        "telemetry task_id mismatch",
    )
    expect(
        '{"handoff_id":"h1","stage":"scoper","task_id":"t1"}',
        "status without colon pattern\n",
        "telemetry status missing exit_code marker:",
    )


def test_collect_dor_telemetry_flow_audit_labels_match_cli(tmp_path: Path, monkeypatch) -> None:
    """Helper-level: flow-audit label bundle matches CLI output tokens."""
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    _write_task_artifacts(tmp_path, handoff_id="h1", task_id="t1")
    dor_dir, rej_path = _flow_dor_dirs(tmp_path, handoff_id="h1", task_id="t1", stem="hl")
    errs = collect_dor_telemetry_errors(
        rejection_packets=[rej_path],
        telemetry_dir=dor_dir,
        handoff_id="h1",
        task_id="t1",
        labels=DorTelemetryLabels.flow_audit(),
        require_task_identity=True,
        bulk_error_if_no_json=True,
    )
    assert any("missing DoR telemetry JSON for rejection packet:" in e for e in errs)
    assert any(str(rej_path) in e for e in errs)
