"""Tests for ``canon readiness check`` (CLI flags, JSON snapshot, exit codes)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from canon_systems.cli import main as canon_main
from canon_systems.readiness import READINESS_SCHEMA_VERSION
from canon_systems.readiness_cli import run as run_readiness_cli
from canon_systems.run_ledger import RunLedgerRequestFailed, RunLedgerServiceUnavailable


def _digest() -> str:
    return "a" * 64


def _archive(phase: str | None, *, kind: str) -> dict[str, object]:
    ref: dict[str, object] = {"content_sha256": _digest(), "artifact_kind": kind}
    if phase:
        ref["phase"] = phase
    ref["status"] = "completed"
    return ref


def _full_ledger_record() -> dict[str, object]:
    import uuid

    rid = str(uuid.uuid4())
    return {
        "schema_version": 1,
        "ledger_run_id": rid,
        "company_id": "C",
        "repository_id": "R",
        "plan_id": "P",
        "task_id": "T",
        "workstream_id": "W",
        "handoff_id": "H",
        "phase": "qa-gate",
        "phase_status": "completed",
        "created_at": "2026-05-04T12:00:00Z",
        "archive_refs": [
            _archive("scoper", kind="packet_scoper"),
            _archive("cursor-pilot", kind="packet_cursor_pilot"),
            _archive("implementer", kind="packet_implementer"),
            _archive("qa-gate", kind="packet_qa_gate"),
            _archive("release-status", kind="packet_release_status"),
        ],
    }


def test_ac1_requires_scope_flags() -> None:
    with pytest.raises(SystemExit) as exc:
        run_readiness_cli(["check", "--company-id", "C"])
    assert exc.value.code == 2


def test_readiness_check_help_documents_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Docs contract (ws4): help text lists scope, query, output, and run-ledger hook."""
    with pytest.raises(SystemExit) as exc:
        run_readiness_cli(["check", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for token in (
        "--company-id",
        "--repository-id",
        "--plan-id",
        "--task-id",
        "--workstream-id",
        "--handoff-id",
        "--ledger-run-id",
        "--state-api-url",
        "--limit",
        "--output",
        "--quiet",
        "/state/run-ledger",
    ):
        assert token in out


def test_ac5_snapshot_keys_and_schema(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def _fetch(**_kw: object) -> dict[str, object]:
        return {"items": [_full_ledger_record()], "count": 1}

    with patch("canon_systems.readiness.get_run_ledger_from_state_api", _fetch):
        out_path = tmp_path / "readiness.json"
        code = run_readiness_cli(
            [
                "check",
                "--company-id",
                "C",
                "--repository-id",
                "R",
                "--plan-id",
                "P",
                "--task-id",
                "T",
                "--workstream-id",
                "W",
                "--handoff-id",
                "H",
                "--output",
                str(out_path),
            ],
        )
    assert code == 0
    captured = capsys.readouterr()
    stdout_obj = json.loads(captured.out.strip())
    assert stdout_obj["schema_version"] == READINESS_SCHEMA_VERSION
    for k in (
        "company_id",
        "repository_id",
        "plan_id",
        "task_id",
        "workstream_id",
        "handoff_id",
        "overall_status",
        "ready",
        "checks",
        "records",
        "missing",
        "failures",
        "warnings",
        "generated_at",
    ):
        assert k in stdout_obj
    disk = json.loads(out_path.read_text(encoding="utf-8"))
    assert disk == stdout_obj
    assert disk["ready"] is True


def test_ac5_output_matches_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def _fetch(**_kw: object) -> dict[str, object]:
        return {"items": [_full_ledger_record()], "count": 1}

    path = tmp_path / "r.json"
    with patch("canon_systems.readiness.get_run_ledger_from_state_api", _fetch):
        code = run_readiness_cli(
            [
                "check",
                "--company-id",
                "C",
                "--repository-id",
                "R",
                "--plan-id",
                "P",
                "--task-id",
                "T",
                "--workstream-id",
                "W",
                "--handoff-id",
                "H",
                "--output",
                str(path),
            ],
        )
    assert code == 0
    from_stdout = json.loads(capsys.readouterr().out.strip())
    from_disk = json.loads(path.read_text(encoding="utf-8"))
    assert from_stdout == from_disk


def test_ac6_exit_0_when_ready() -> None:
    def _fetch(**_kw: object) -> dict[str, object]:
        return {"items": [_full_ledger_record()], "count": 1}

    with patch("canon_systems.readiness.get_run_ledger_from_state_api", _fetch):
        code = run_readiness_cli(
            [
                "check",
                "--company-id",
                "C",
                "--repository-id",
                "R",
                "--plan-id",
                "P",
                "--task-id",
                "T",
                "--workstream-id",
                "W",
                "--handoff-id",
                "H",
            ],
        )
    assert code == 0


def test_ac6_exit_1_when_not_ready() -> None:
    def _fetch(**_kw: object) -> dict[str, object]:
        return {"items": [], "count": 0}

    with patch("canon_systems.readiness.get_run_ledger_from_state_api", _fetch):
        code = run_readiness_cli(
            [
                "check",
                "--company-id",
                "C",
                "--repository-id",
                "R",
                "--plan-id",
                "P",
                "--task-id",
                "T",
                "--workstream-id",
                "W",
                "--handoff-id",
                "H",
            ],
        )
    assert code == 1


def test_ac6_exit_2_invalid_limit() -> None:
    code = run_readiness_cli(
        [
            "check",
            "--company-id",
            "C",
            "--repository-id",
            "R",
            "--plan-id",
            "P",
            "--task-id",
            "T",
            "--workstream-id",
            "W",
            "--handoff-id",
            "H",
            "--limit",
            "0",
        ],
    )
    assert code == 2


@pytest.mark.parametrize(
    "exc_class,msg",
    [
        (RunLedgerRequestFailed, "bad request"),
        (RunLedgerServiceUnavailable, "no table"),
    ],
)
def test_ac2_query_errors_exit_2(
    exc_class: type[Exception],
    msg: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fetch(**_kw: object) -> dict[str, object]:
        raise exc_class(msg)

    with patch("canon_systems.readiness.get_run_ledger_from_state_api", _fetch):
        code = run_readiness_cli(
            [
                "check",
                "--company-id",
                "C",
                "--repository-id",
                "R",
                "--plan-id",
                "P",
                "--task-id",
                "T",
                "--workstream-id",
                "W",
                "--handoff-id",
                "H",
            ],
        )
    assert code == 2
    err = json.loads(capsys.readouterr().err.strip())
    assert err["error"] == "run_ledger_query_failed"
    assert err["exception"] == exc_class.__name__
    assert msg in err["message"]


def test_custom_evaluate_readiness_drives_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    def _fetch(**_kw: object) -> dict[str, object]:
        return {"items": [_full_ledger_record()], "count": 1}

    def _always_fail(**_kw: object) -> dict[str, object]:
        return {
            "schema_version": READINESS_SCHEMA_VERSION,
            "company_id": "C",
            "repository_id": "R",
            "plan_id": "P",
            "task_id": "T",
            "workstream_id": "W",
            "handoff_id": "H",
            "ledger_run_id": None,
            "query_mode": "latest_scoped",
            "overall_status": "fail",
            "ready": False,
            "checks": [],
            "records": [],
            "missing": [],
            "failures": [{"code": "x", "message": "y"}],
            "warnings": [],
            "validation_summary": {},
            "commits": [],
            "pull_request": None,
            "deployment": None,
            "generated_at": "2026-05-04T12:00:00Z",
        }

    with (
        patch("canon_systems.readiness.get_run_ledger_from_state_api", _fetch),
        patch("canon_systems.readiness_cli.evaluate_readiness", _always_fail),
    ):
        code = run_readiness_cli(
            [
                "check",
                "--company-id",
                "C",
                "--repository-id",
                "R",
                "--plan-id",
                "P",
                "--task-id",
                "T",
                "--workstream-id",
                "W",
                "--handoff-id",
                "H",
            ],
        )
    assert code == 1
    body = json.loads(capsys.readouterr().out.strip())
    assert body["ready"] is False


def test_explicit_ledger_run_id_uses_single_record_shape(capsys: pytest.CaptureFixture[str]) -> None:
    rec = _full_ledger_record()

    def _fetch(**kw: object) -> dict[str, object]:
        assert kw["ledger_run_id"] == rec["ledger_run_id"]
        return {"ledger_run_id": rec["ledger_run_id"], "record": rec}

    with patch("canon_systems.readiness.get_run_ledger_from_state_api", _fetch):
        code = run_readiness_cli(
            [
                "check",
                "--company-id",
                "C",
                "--repository-id",
                "R",
                "--plan-id",
                "P",
                "--task-id",
                "T",
                "--workstream-id",
                "W",
                "--handoff-id",
                "H",
                "--ledger-run-id",
                str(rec["ledger_run_id"]),
            ],
        )
    assert code == 0
    o = json.loads(capsys.readouterr().out.strip())
    assert o["ledger_run_id"] == rec["ledger_run_id"]
    assert len(o["records"]) == 1


def test_top_level_readiness_check_help_lists_core_flags(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC2: public ``canon readiness check --help`` matches readiness_cli flags."""
    with pytest.raises(SystemExit) as ei:
        canon_main(["--repo-root", str(tmp_path), "readiness", "check", "--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "--ledger-run-id" in out
    assert "--state-api-url" in out
    assert "--limit" in out


def test_canon_main_dispatches_readiness_check(capsys: pytest.CaptureFixture[str]) -> None:
    def _fetch(**_kw: object) -> dict[str, object]:
        return {"items": [_full_ledger_record()], "count": 1}

    with patch("canon_systems.readiness.get_run_ledger_from_state_api", _fetch):
        code = canon_main(
            [
                "readiness",
                "check",
                "--company-id",
                "C",
                "--repository-id",
                "R",
                "--plan-id",
                "P",
                "--task-id",
                "T",
                "--workstream-id",
                "W",
                "--handoff-id",
                "H",
            ],
        )
    assert code == 0
    assert "ready" in capsys.readouterr().out
