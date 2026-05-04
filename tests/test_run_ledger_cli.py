"""CLI run-ledger: dry-run and HTTP PUT helpers: no live DynamoDB/AWS required."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from canon_backend_shared.run_ledger import RunLedgerValidationError

from canon_systems.cli import main as canon_main
from canon_systems.run_ledger import (
    RUN_LEDGER_STATE_PATH,
    post_run_ledger_to_state_api,
    prepare_cli_run_ledger_record,
)
from canon_systems.run_ledger_cli import run as run_run_ledger_cli


def _minimal_record(**overrides: object) -> dict:
    rid = str(uuid.uuid4())
    base = {
        "ledger_run_id": rid,
        "company_id": "CSC",
        "repository_id": "canon-systems",
        "plan_id": "canon_plan",
        "task_id": "run-ledger",
        "workstream_id": "ws-test",
        "handoff_id": "canon-readiness-gates",
        "phase": "implementer",
        "phase_status": "completed",
        "created_at": "2026-05-04T12:00:00Z",
        "schema_version": 1,
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


def test_ac6_dry_run_prints_normalized_record(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    payload = _minimal_record()
    f = tmp_path / "ledger.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    code = run_run_ledger_cli(
        ["--record-file", str(f), "--dry-run"],
    )
    assert code == 0
    parsed = json.loads(capsys.readouterr().out.strip())
    assert parsed["ledger_run_id"] == payload["ledger_run_id"]
    assert parsed["archive_refs"] == []
    assert parsed["schema_version"] == 1


def test_ac6_merge_archive_json_adds_refs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    base_f = tmp_path / "ledger.json"
    base_f.write_text(json.dumps(_minimal_record()), encoding="utf-8")
    arch_f = tmp_path / "snaps.json"
    arch_f.write_text(
        json.dumps(
            [
                {
                    "content_sha256": "a" * 64,
                    "artifact_kind": "packet_implementer",
                    "phase": "implementer",
                    "s3_uri": "s3://dry/a",
                },
            ]
        ),
        encoding="utf-8",
    )
    code = run_run_ledger_cli(
        [
            "--record-file",
            str(base_f),
            "--merge-archive-json",
            str(arch_f),
            "--dry-run",
        ],
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out.strip())
    assert len(out["archive_refs"]) == 1
    assert out["archive_refs"][0]["content_sha256"] == "a" * 64
    assert out["archive_refs"][0]["artifact_kind"] == "packet_implementer"


def test_cli_rejects_forbidden_body_on_archive_merge(tmp_path: Path) -> None:
    base_f = tmp_path / "ledger.json"
    base_f.write_text(json.dumps(_minimal_record()), encoding="utf-8")
    arch_f = tmp_path / "bad.json"
    arch_f.write_text(
        json.dumps(
            [
                {
                    "content_sha256": "b" * 64,
                    "artifact_kind": "packet_scoper",
                    "body": "no",
                },
            ]
        ),
        encoding="utf-8",
    )
    code = run_run_ledger_cli(
        ["--record-file", str(base_f), "--merge-archive-json", str(arch_f), "--dry-run"],
    )
    assert code == 2


def test_merge_archive_json_rejects_non_object_entries(tmp_path: Path) -> None:
    base_f = tmp_path / "ledger.json"
    base_f.write_text(json.dumps(_minimal_record()), encoding="utf-8")
    arch_f = tmp_path / "bad.json"
    arch_f.write_text(json.dumps([{"content_sha256": "c" * 64, "artifact_kind": "k"}, 3]), encoding="utf-8")
    code = run_run_ledger_cli(["--record-file", str(base_f), "--merge-archive-json", str(arch_f), "--dry-run"])
    assert code == 2


def test_prepare_cli_optional_snapshots_none() -> None:
    out = prepare_cli_run_ledger_record(_minimal_record(), None)
    assert out["task_id"] == "run-ledger"


def test_prepare_cli_snapshots_must_be_mappings_only() -> None:
    with pytest.raises(RunLedgerValidationError):
        prepare_cli_run_ledger_record(_minimal_record(), [{"content_sha256": "d" * 64}])  # missing artifact_kind


def test_post_run_ledger_to_state_api_puts_json() -> None:
    rec = prepare_cli_run_ledger_record(_minimal_record(), None)
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({"stored": True}).encode("utf-8")
    mock_resp.headers = {"X-Canon-Event-Id": "ev-ws3"}
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = None

    with patch("canon_systems.run_ledger.urllib.request.urlopen", return_value=mock_cm) as u:
        status, body, hdrs = post_run_ledger_to_state_api(
            base_url="http://127.0.0.1:9999",
            record=rec,
            timeout_seconds=5.0,
        )

    assert status == 200
    assert body.get("stored") is True
    assert hdrs.get("X-Canon-Event-Id") == "ev-ws3"
    req = u.call_args[0][0]
    assert req.get_full_url() == f"http://127.0.0.1:9999{RUN_LEDGER_STATE_PATH}"
    assert req.get_method() == "PUT"
    assert req.data == json.dumps(rec, separators=(",", ":"), sort_keys=True).encode("utf-8")


def test_run_ledger_post_branch_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps(_minimal_record()), encoding="utf-8")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"record": true}'
    mock_resp.headers = {"X-Canon-Event-Id": "e2"}
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = None
    with patch("canon_systems.run_ledger.urllib.request.urlopen", return_value=mock_cm):
        code = run_run_ledger_cli(
            ["--record-file", str(p), "--state-api-url", "http://127.0.0.1:5999"],
        )
    assert code == 0
    out = json.loads(capsys.readouterr().out.strip())
    assert out["_event_id"] == "e2"
    assert out["record"] is True


def test_top_level_run_ledger_help_lists_record_and_merge_flags(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC2: public ``canon run-ledger --help`` matches run_ledger_cli."""
    with pytest.raises(SystemExit) as ei:
        canon_main(["--repo-root", str(tmp_path), "run-ledger", "--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "--record-file" in out
    assert "--merge-archive-json" in out
    assert "--dry-run" in out


def test_canon_main_dispatches_run_ledger_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    payload = _minimal_record()
    f = tmp_path / "y.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    rc = canon_main(["run-ledger", "--record-file", str(f), "--dry-run"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out.strip())
    assert parsed["ledger_run_id"] == payload["ledger_run_id"]
