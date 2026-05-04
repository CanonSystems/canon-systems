"""Tests for run-ledger GET client and readiness evaluation (ws1)."""

from __future__ import annotations

import ast
import json
import uuid
from pathlib import Path
from io import BytesIO
from unittest.mock import patch

import pytest

from canon_systems.readiness import (
    archive_ref_phase,
    build_readiness_report_for_record,
    evaluate_readiness,
    pick_latest_ledger_record,
    run_readiness_pipeline,
    summarize_validation_outcomes,
)
from canon_systems.run_ledger import (
    RunLedgerRecordNotFound,
    RunLedgerRequestFailed,
    RunLedgerServiceUnavailable,
    RunLedgerTransportError,
    get_run_ledger_from_state_api,
)


def _digest() -> str:
    return "a" * 64


def _archive(phase: str | None, *, kind: str, status: str | None = "completed") -> dict:
    ref: dict = {"content_sha256": _digest(), "artifact_kind": kind}
    if phase:
        ref["phase"] = phase
    if status:
        ref["status"] = status
    return ref


def test_archive_ref_phase_maps_builtin_kinds() -> None:
    assert archive_ref_phase(_archive(None, kind="packet_scoper")) == "scoper"
    assert archive_ref_phase(_archive(None, kind="packet_cursor_pilot")) == "cursor-pilot"
    assert archive_ref_phase(_archive(None, kind="packet_qa_gate")) == "qa-gate"
    assert archive_ref_phase(_archive(None, kind="packet_release_status")) == "release-status"
    assert archive_ref_phase(_archive(None, kind="packet_implementer")) == "implementer"


def test_pick_latest_prefers_updated_at() -> None:
    a = {"ledger_run_id": str(uuid.uuid4()), "created_at": "2026-05-04T10:00:00Z", "updated_at": "2026-05-04T11:00:00Z"}
    b = {"ledger_run_id": str(uuid.uuid4()), "created_at": "2026-05-04T12:00:00Z", "updated_at": "2026-05-04T10:30:00Z"}
    got = pick_latest_ledger_record([b, a])
    assert got["ledger_run_id"] == a["ledger_run_id"]


def test_summarize_validation_outcomes_filters_slots_only() -> None:
    rec = {
        "validation_outcomes": {
            "qa_validate": {"status": "pass", "verdict": "PASS"},
            "unknown_slot": {"x": 1},
            "flow_audit": {"status": "fail"},
        }
    }
    out = summarize_validation_outcomes(rec)
    assert "qa_validate" in out and "flow_audit" in out
    assert "unknown_slot" not in out


def _full_record(**extra: object) -> dict:
    rid = str(uuid.uuid4())
    base = {
        "schema_version": 1,
        "ledger_run_id": rid,
        "company_id": "IMC",
        "repository_id": "innermost",
        "plan_id": "p1",
        "task_id": "t1",
        "workstream_id": "ws",
        "handoff_id": "canon-readiness-gates",
        "phase": "release-orchestrator",
        "phase_status": "completed",
        "created_at": "2026-05-04T12:00:00Z",
        "archive_refs": [
            _archive("scoper", kind="packet_scoper"),
            _archive("cursor-pilot", kind="packet_cursor_pilot"),
            _archive("implementer", kind="packet_implementer"),
            _archive("qa-gate", kind="packet_qa_gate"),
            _archive("release-status", kind="packet_release_status"),
        ],
        "validation_outcomes": {"qa_validate": {"status": "pass", "exit_code": 0}},
        "commits": [{"sha": "abcd1234567890abcd1234567890abcd12345678"}],
        "pull_request": {"url": "https://example.com/pr/1", "number": 1},
        "deployment": {"environment": "staging", "status": "ok"},
    }
    base.update(extra)
    return base


def test_build_readiness_report_ready_when_packets_present() -> None:
    rec = _full_record()
    rep = build_readiness_report_for_record(
        record=rec,
        company_id=rec["company_id"],
        repository_id=rec["repository_id"],
        plan_id=rec["plan_id"],
        task_id=rec["task_id"],
        workstream_id=rec["workstream_id"],
        handoff_id=rec["handoff_id"],
        ledger_run_id_resolved=rec["ledger_run_id"],
        query_mode="by_run_id",
        limit_hit_warning=False,
    )
    assert rep["schema_version"] == 1
    assert rep["ready"] is True
    assert rep["overall_status"] == "pass"
    assert rep["missing"] == []
    assert rep["failures"] == []
    assert rep["validation_summary"]["qa_validate"]["status"] == "pass"
    assert rep["commits"]
    assert rep["pull_request"]["number"] == 1
    assert rep["deployment"]["environment"] == "staging"
    assert "checks" in rep and len(rep["checks"]) >= 5


def test_missing_phase_not_ready() -> None:
    rec = _full_record()
    rec["archive_refs"] = [x for x in rec["archive_refs"] if x.get("phase") != "scoper"]
    rep = build_readiness_report_for_record(
        record=rec,
        company_id=rec["company_id"],
        repository_id=rec["repository_id"],
        plan_id=rec["plan_id"],
        task_id=rec["task_id"],
        workstream_id=rec["workstream_id"],
        handoff_id=rec["handoff_id"],
        ledger_run_id_resolved=rec["ledger_run_id"],
        query_mode="latest_scoped",
        limit_hit_warning=False,
    )
    assert rep["ready"] is False
    assert "scoper" in rep["missing"]
    assert any(f["code"] == "missing_archive_phase" for f in rep["failures"])


def test_implementer_shard_kind_satisfies_implementer() -> None:
    rec = _full_record()
    rec["archive_refs"] = [
        x for x in rec["archive_refs"] if x.get("phase") != "implementer"
    ] + [_archive("implementer", kind="packet_implementer_shard")]
    rep = build_readiness_report_for_record(
        record=rec,
        company_id=rec["company_id"],
        repository_id=rec["repository_id"],
        plan_id=rec["plan_id"],
        task_id=rec["task_id"],
        workstream_id=rec["workstream_id"],
        handoff_id=rec["handoff_id"],
        ledger_run_id_resolved=rec["ledger_run_id"],
        query_mode="by_run_id",
        limit_hit_warning=False,
    )
    assert rep["ready"] is True


def test_evidence_ref_implementer_shard_without_archive_impl() -> None:
    rec = _full_record()
    rec["archive_refs"] = [x for x in rec["archive_refs"] if x.get("phase") != "implementer"]
    rec["evidence_refs"] = [{"ref_kind": "implementer_shard_qa", "uri": "s3://x/y"}]
    rep = build_readiness_report_for_record(
        record=rec,
        company_id=rec["company_id"],
        repository_id=rec["repository_id"],
        plan_id=rec["plan_id"],
        task_id=rec["task_id"],
        workstream_id=rec["workstream_id"],
        handoff_id=rec["handoff_id"],
        ledger_run_id_resolved=rec["ledger_run_id"],
        query_mode="by_run_id",
        limit_hit_warning=False,
    )
    assert rep["ready"] is True


def test_readiness_snapshot_omits_body_fields() -> None:
    rec = _full_record(
        body="top-level packet text",
        body_base64="Ym9keQ==",
        archive_refs=[
            _archive("scoper", kind="packet_scoper"),
            {**_archive("cursor-pilot", kind="packet_cursor_pilot"), "content": "pilot body"},
            _archive("implementer", kind="packet_implementer"),
            _archive("qa-gate", kind="packet_qa_gate"),
            _archive("release-status", kind="packet_release_status"),
        ],
        evidence_refs=[{"ref_kind": "qa", "body": "evidence body"}],
    )
    rep = build_readiness_report_for_record(
        record=rec,
        company_id=rec["company_id"],
        repository_id=rec["repository_id"],
        plan_id=rec["plan_id"],
        task_id=rec["task_id"],
        workstream_id=rec["workstream_id"],
        handoff_id=rec["handoff_id"],
        ledger_run_id_resolved=rec["ledger_run_id"],
        query_mode="by_run_id",
        limit_hit_warning=False,
    )
    dumped = json.dumps(rep["records"])
    assert "top-level packet text" not in dumped
    assert "Ym9keQ==" not in dumped
    assert "pilot body" not in dumped
    assert "evidence body" not in dumped


def test_bad_archive_status_warns_not_pass() -> None:
    rec = _full_record()
    for ref in rec["archive_refs"]:
        if ref.get("phase") == "implementer":
            ref["status"] = "failed"
    rep = build_readiness_report_for_record(
        record=rec,
        company_id=rec["company_id"],
        repository_id=rec["repository_id"],
        plan_id=rec["plan_id"],
        task_id=rec["task_id"],
        workstream_id=rec["workstream_id"],
        handoff_id=rec["handoff_id"],
        ledger_run_id_resolved=rec["ledger_run_id"],
        query_mode="by_run_id",
        limit_hit_warning=False,
    )
    assert rep["overall_status"] == "warn"
    assert rep["ready"] is False
    assert rep["warnings"]


def test_evaluate_latest_scoped_empty_items() -> None:
    def fetch(**_: object) -> dict:
        return {"items": [], "count": 0}

    rep = evaluate_readiness(
        base_url="http://example.invalid",
        company_id="IMC",
        repository_id="innermost",
        plan_id="p",
        task_id="t",
        workstream_id="w",
        handoff_id="h",
        fetcher=fetch,
    )
    assert rep["ready"] is False
    assert rep["records"] == []


def test_evaluate_explicit_run_not_found() -> None:
    rid = str(uuid.uuid4())

    def fetch(**_: object) -> dict:
        raise RunLedgerRecordNotFound("missing")

    rep = evaluate_readiness(
        base_url="http://example.invalid",
        company_id="IMC",
        repository_id="innermost",
        plan_id="p",
        task_id="t",
        workstream_id="w",
        handoff_id="h",
        ledger_run_id=rid,
        fetcher=fetch,
    )
    assert rep["ready"] is False
    assert any(f["code"] == "ledger_record_missing" for f in rep["failures"])


def test_evaluate_by_run_id_returns_record() -> None:
    rec = _full_record()

    def fetch(**_: object) -> dict:
        return {"ledger_run_id": rec["ledger_run_id"], "record": rec}

    rep = evaluate_readiness(
        base_url="http://example.invalid",
        company_id="IMC",
        repository_id="innermost",
        plan_id="p1",
        task_id="t1",
        workstream_id="ws",
        handoff_id="canon-readiness-gates",
        ledger_run_id=rec["ledger_run_id"],
        fetcher=fetch,
    )
    assert rep["ready"] is True


def test_get_run_ledger_http_404_raises_not_found() -> None:
    url = "http://stub/state/run-ledger"
    body = json.dumps({"detail": {"error": "not_found", "message": "row missing"}}).encode()
    err = __import__("urllib.error", fromlist=["HTTPError"]).HTTPError(url, 404, "Not Found", {}, BytesIO(body))

    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(RunLedgerRecordNotFound):
            get_run_ledger_from_state_api(
                base_url="http://stub",
                company_id="IMC",
                repository_id="innermost",
                plan_id="p",
                task_id="t",
                workstream_id="w",
                ledger_run_id=str(uuid.uuid4()),
            )


@pytest.mark.parametrize(
    "code,exc_type",
    [
        (400, RunLedgerRequestFailed),
        (503, RunLedgerServiceUnavailable),
        (500, RunLedgerRequestFailed),
    ],
)
def test_get_run_ledger_http_errors(code: int, exc_type: type[Exception]) -> None:
    url = "http://stub/state/run-ledger"
    body = json.dumps({"detail": {"error": "x", "message": "bad"}}).encode()
    err = __import__("urllib.error", fromlist=["HTTPError"]).HTTPError(url, code, "Err", {}, BytesIO(body))

    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(exc_type):
            get_run_ledger_from_state_api(
                base_url="http://stub",
                company_id="IMC",
                repository_id="innermost",
                plan_id="p",
                task_id="t",
                workstream_id="w",
            )


def test_get_run_ledger_transport_error() -> None:
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timed out")):
        with pytest.raises(RunLedgerTransportError):
            get_run_ledger_from_state_api(
                base_url="http://stub",
                company_id="IMC",
                repository_id="innermost",
                plan_id="p",
                task_id="t",
                workstream_id="w",
            )


def test_evaluate_readiness_only_invokes_fetcher_no_writes() -> None:
    calls: list[dict[str, object]] = []

    def fetch(**kwargs: object) -> dict:
        calls.append(dict(kwargs))
        rec = _full_record()
        return {"items": [rec], "count": 1}

    rep = evaluate_readiness(
        base_url="http://example.invalid",
        company_id="IMC",
        repository_id="innermost",
        plan_id="p1",
        task_id="t1",
        workstream_id="ws",
        handoff_id="canon-readiness-gates",
        fetcher=fetch,
    )
    assert len(calls) == 1
    assert calls[0]["ledger_run_id"] is None
    assert rep["ready"] is True


def test_run_readiness_pipeline_is_fetch_only_diagnostic() -> None:
    rec = _full_record()
    calls: list[dict[str, object]] = []

    def fetch(**kwargs: object) -> dict:
        calls.append(dict(kwargs))
        return {"record": rec}

    rep = run_readiness_pipeline(
        company_id=rec["company_id"],
        repository_id=rec["repository_id"],
        plan_id=rec["plan_id"],
        task_id=rec["task_id"],
        workstream_id=rec["workstream_id"],
        handoff_id=rec["handoff_id"],
        ledger_run_id=str(rec["ledger_run_id"]),
        state_api_url="http://example.invalid",
        fetcher=fetch,
    )
    assert len(calls) == 1
    assert rep["ready"] is True


def test_readiness_module_has_no_archive_or_ledger_put_imports() -> None:
    """AC5: readiness evaluation stays read-only — no PUT/POST client wiring."""
    path = Path(__file__).resolve().parents[1] / "src" / "canon_systems" / "readiness.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert "canon_systems.packet_archive" not in imported
    banned = (
        "post_run_ledger_to_state_api",
        "post_archive_to_state_api",
    )
    source = path.read_text(encoding="utf-8")
    for name in banned:
        assert name not in source


def test_public_docs_retain_storage_boundary_contract() -> None:
    """AC4/AC5: docs keep cross-repo storage-boundary language / local packets."""
    root = Path(__file__).resolve().parents[1]
    wf = (root / "docs" / "SYSTEM-WORKFLOW.md").read_text(encoding="utf-8")
    runtime = (root / "docs" / "MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md").read_text(encoding="utf-8")
    plan = (root / "docs" / "MEMORY-PLATFORM-PLAN.md").read_text(encoding="utf-8")
    low = wf.lower()
    assert ".cursor/handoffs" in wf and ".cursor/handoffs" in plan
    assert "get `/state/run-ledger`" in low or "/state/run-ledger" in low
    assert "read-only" in low or "does not mutate" in low
    assert "#run_ledger" in wf or "run_ledger" in wf
    assert "packet_archived" in wf.lower()
    assert "packet_archived_event_payload" in runtime
    assert "disjoint" in plan.lower() or "separate" in plan.lower()


def test_limit_hit_sets_warning() -> None:
    older = _full_record()
    older["ledger_run_id"] = str(uuid.uuid4())
    older["updated_at"] = "2026-05-04T09:00:00Z"
    newer = _full_record()
    newer["ledger_run_id"] = str(uuid.uuid4())
    newer["updated_at"] = "2026-05-04T12:00:00Z"

    def fetch(**_: object) -> dict:
        return {"items": [older, newer], "count": 2}

    rep = evaluate_readiness(
        base_url="http://x",
        company_id="IMC",
        repository_id="innermost",
        plan_id="p1",
        task_id="t1",
        workstream_id="ws",
        handoff_id="canon-readiness-gates",
        limit=2,
        fetcher=fetch,
    )
    assert rep["ledger_run_id"] == newer["ledger_run_id"]
    assert any("limit" in w.lower() for w in rep["warnings"])
