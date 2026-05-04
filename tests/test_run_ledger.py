"""Tests for run ledger schema, DynamoDB key isolation, and archive ingest (ws1)."""

from __future__ import annotations

import uuid

import pytest

from canon_backend_shared.run_ledger import (
    RunLedgerValidationError,
    archive_record_to_ledger_reference,
    assert_ledger_key_isolation_against_checkpoint,
    build_run_ledger_pk,
    build_run_ledger_sk,
    ledger_keys_for_record,
    validate_run_ledger_record,
)

from canon_systems.run_ledger import merge_archive_snapshots_into_record


def _minimal_record(**overrides: object) -> dict:
    run_id = str(uuid.uuid4())
    base = {
        "ledger_run_id": run_id,
        "company_id": "CSC",
        "repository_id": "canon-systems",
        "plan_id": "canon_plan",
        "task_id": "run-ledger",
        "workstream_id": "ws1",
        "handoff_id": "canon-readiness-gates",
        "phase": "implementer",
        "phase_status": "in_progress",
        "created_at": "2026-05-04T12:00:00Z",
        "schema_version": 1,
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


def test_ac1_validate_minimal_round_trip() -> None:
    raw = _minimal_record()
    out = validate_run_ledger_record(raw)
    assert out["schema_version"] == 1
    assert out["company_id"] == "CSC"
    assert out["ledger_run_id"] == raw["ledger_run_id"]
    assert out["archive_refs"] == []
    assert out["validation_outcomes"] == {}
    assert "verdict" not in out


def test_ac1_optional_verdict_validation_outcomes_commits_pr_deployment() -> None:
    rid = str(uuid.uuid4())
    raw = _minimal_record(
        ledger_run_id=rid,
        verdict="PASS",
        updated_at="2026-05-04T13:00:00Z",
        validation_outcomes={
            "qa_validate": {"status": "pass", "exit_code": 0, "checked_at": "2026-05-04T12:05:00Z"},
            "flow_audit": {"verdict": "PASS"},
            "memory_health": {"status": "pass"},
            "ci": {"status": "pass", "job_url": "https://ci.example/run/1"},
            "deployment_smoke": {"status": "skipped", "summary": "n/a"},
            "merge_readiness": {"status": "pending"},
        },
        commits=[{"sha": "abcdef0", "label": "main"}, {"sha": "a" * 40}],
        pull_request={"url": "https://github.com/org/repo/pull/42", "number": 42},
        deployment={
            "environment": "staging",
            "status": "succeeded",
            "deployed_at": "2026-05-04T12:07:00Z",
        },
        source_event_ids=["evt-1"],
        agent_run_id="agent-1",
        actor_id="composer-2-fast",
    )
    out = validate_run_ledger_record(raw)
    assert out["verdict"] == "PASS"
    assert out["validation_outcomes"]["qa_validate"]["exit_code"] == 0
    assert out["pull_request"]["number"] == 42
    assert out["deployment"]["environment"] == "staging"
    assert out["commits"][0]["sha"] == "abcdef0"
    assert out["source_event_ids"] == ["evt-1"]


def test_ac4_archive_reference_requires_digest_and_kind() -> None:
    with pytest.raises(RunLedgerValidationError):
        archive_record_to_ledger_reference({"content_sha256": "a" * 64})

    ref = archive_record_to_ledger_reference(
        {
            "s3_uri": "s3://bk/k",
            "s3_key": "k",
            "content_sha256": "b" * 64,
            "artifact_kind": "packet_scoper",
            "phase": "scoper",
            "status": "ok",
            "outcome": "uploaded",
            "archive_event_id": "evt-arch-1",
        }
    )
    assert ref["s3_uri"] == "s3://bk/k"
    assert ref["content_sha256"] == "b" * 64
    assert ref["artifact_kind"] == "packet_scoper"
    assert "body_base64" not in ref


def test_ac4_rejects_body_like_fields_on_archive() -> None:
    with pytest.raises(RunLedgerValidationError):
        archive_record_to_ledger_reference(
            {
                "content_sha256": "c" * 64,
                "artifact_kind": "packet_scoper",
                "body_base64": "e30=",
            }
        )


def test_ac5_unknown_validation_slot_rejected() -> None:
    raw = _minimal_record(validation_outcomes={"unknown_gate": {"status": "pass"}})
    with pytest.raises(RunLedgerValidationError):
        validate_run_ledger_record(raw)


def test_checkpoint_vs_ledger_keys_never_collide() -> None:
    c, r, p, t, w = "CSC", "canon-systems", "plan1", "task1", "stream1"
    run_id = str(uuid.uuid4())
    chk_pk = f"{c}#{r}"
    chk_sk = f"{p}#{t}#{w}"
    l_pk = build_run_ledger_pk(company_id=c, repository_id=r)
    l_sk = build_run_ledger_sk(plan_id=p, task_id=t, workstream_id=w, ledger_run_id=run_id)

    assert l_pk != chk_pk
    assert l_sk != chk_sk
    assert_ledger_key_isolation_against_checkpoint(
        ledger_pk=l_pk,
        ledger_sk=l_sk,
        checkpoint_pk=chk_pk,
        checkpoint_sk=chk_sk,
    )


def test_ledger_keys_for_record_matches_builders() -> None:
    raw = validate_run_ledger_record(_minimal_record())
    pk, sk = ledger_keys_for_record(raw)
    assert pk == build_run_ledger_pk(
        company_id=raw["company_id"],
        repository_id=raw["repository_id"],
    )
    assert sk == build_run_ledger_sk(
        plan_id=raw["plan_id"],
        task_id=raw["task_id"],
        workstream_id=raw["workstream_id"],
        ledger_run_id=raw["ledger_run_id"],
    )


def test_collision_assert_raises() -> None:
    with pytest.raises(RunLedgerValidationError):
        assert_ledger_key_isolation_against_checkpoint(
            ledger_pk="a",
            ledger_sk="b",
            checkpoint_pk="a",
            checkpoint_sk="b",
        )


def test_top_level_body_field_rejected() -> None:
    raw = _minimal_record()
    raw["body"] = "oops"
    with pytest.raises(RunLedgerValidationError):
        validate_run_ledger_record(raw)


def test_archive_reference_drops_non_allowlisted_fields() -> None:
    """Metadata refs on ledger rows never carry through ad-hoc secret-like keys."""
    ref = archive_record_to_ledger_reference(
        {
            "content_sha256": "d" * 64,
            "artifact_kind": "packet_scoper",
            "phase": "scoper",
            "s3_uri": "s3://b/k",
            "authorization": "Bearer should-not-appear",
            "signed_url": "https://example/presigned?sig=secret",
        }
    )
    assert "authorization" not in ref
    assert "signed_url" not in ref
    assert ref["content_sha256"] == "d" * 64


def test_merge_archive_snapshots_into_record_helpers() -> None:
    rid = str(uuid.uuid4())
    base = _minimal_record(ledger_run_id=rid)
    snap = {
        "content_sha256": "f" * 64,
        "artifact_kind": "packet_qa_gate",
        "phase": "qa-gate",
        "s3_key": "k",
        "s3_uri": "s3://b/k",
    }
    merged = merge_archive_snapshots_into_record(base, [snap])
    assert len(merged["archive_refs"]) == 1
    assert merged["archive_refs"][0]["artifact_kind"] == "packet_qa_gate"
