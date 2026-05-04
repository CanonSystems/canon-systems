"""Tests for shared packet archive schema + deterministic keys."""

from __future__ import annotations

import pytest

from canon_backend_shared.packet_archive import (
    ARCHIVE_RECORD_SCHEMA_VERSION,
    ArchiveValidationError,
    build_archive_object_key,
    build_archive_record_payload,
    normalize_archive_prefix,
    normalize_sha256_hex,
    packet_archived_event_payload,
    sanitize_key_segment,
    sha256_hex_digest,
    validate_artifact_kind,
)


def test_normalize_sha256_accepts_lowercase_hex() -> None:
    h = "a" * 64
    assert normalize_sha256_hex(h) == h
    assert normalize_sha256_hex(h.upper()) == h


def test_normalize_sha256_rejects_bad_digest() -> None:
    with pytest.raises(ArchiveValidationError):
        normalize_sha256_hex("not-a-hash")
    with pytest.raises(ArchiveValidationError):
        normalize_sha256_hex("ab" * 31)  # too short


def test_sanitize_segment_rejects_traversal() -> None:
    with pytest.raises(ArchiveValidationError):
        sanitize_key_segment("a/../b", label="x")
    with pytest.raises(ArchiveValidationError):
        sanitize_key_segment("", label="x")


def test_deterministic_key_includes_sha_and_is_stable() -> None:
    sha = sha256_hex_digest(b"hello")
    k1 = build_archive_object_key(
        prefix="canon/packets",
        company_id="CSC",
        repository_id="canon-systems",
        plan_id="p1",
        task_id="t1",
        workstream_id="ws1",
        handoff_id="h1",
        phase="scoper",
        artifact_kind="packet_scoper",
        content_sha256_hex=sha,
    )
    k2 = build_archive_object_key(
        prefix="canon/packets",
        company_id="CSC",
        repository_id="canon-systems",
        plan_id="p1",
        task_id="t1",
        workstream_id="ws1",
        handoff_id="h1",
        phase="scoper",
        artifact_kind="packet_scoper",
        content_sha256_hex=sha,
    )
    assert k1 == k2
    assert sha in k1
    assert k1.startswith("canon/packets/v1/")


def test_different_content_yields_different_keys() -> None:
    base = dict(
        prefix="p",
        company_id="c",
        repository_id="r",
        plan_id="pl",
        task_id="tk",
        workstream_id="w",
        handoff_id="h",
        phase="implementer",
        artifact_kind="packet_implementer",
    )
    k1 = build_archive_object_key(**base, content_sha256_hex=sha256_hex_digest(b"1"))
    k2 = build_archive_object_key(**base, content_sha256_hex=sha256_hex_digest(b"2"))
    assert k1 != k2


def test_normalize_archive_prefix_strips_slashes() -> None:
    assert normalize_archive_prefix("/a/b/") == "a/b"


def test_validate_extension_evidence_kind() -> None:
    validate_artifact_kind("evidence_merge_gate_custom", evidence_subtype=None)


def test_packet_archived_event_allowlist_drops_body_and_credential_extras() -> None:
    rec = build_archive_record_payload(
        bucket="bkt.test",
        key="k",
        content_sha256_hex="a" * 64,
        byte_length=3,
        content_type="text/plain",
        created_at="2026-05-04T00:00:00Z",
        company_id="c",
        repository_id="r",
        plan_id="p",
        task_id="t",
        workstream_id="w",
        handoff_id="h",
        phase="qa-gate",
        artifact_kind="packet_qa_gate",
        source_label="/tmp/x.md",
    )
    rec["body_base64"] = "e30="
    rec["bearer_token"] = "secret"
    rec["authorization"] = "Bearer x"
    pay = packet_archived_event_payload(rec)
    for forbidden in ("body_base64", "bearer_token", "authorization", "body", "content"):
        assert forbidden not in pay
    allowed = {
        "artifact_kind",
        "phase",
        "handoff_id",
        "plan_id",
        "task_id",
        "workstream_id",
        "source_label",
        "content_sha256",
        "byte_length",
        "content_type",
        "s3_key",
        "s3_uri",
        "s3_bucket",
        "created_at",
        "agent_run_id",
        "actor_id",
        "outcome",
        "status",
        "schema_version",
        "evidence_subtype",
        "s3_version_id",
    }
    assert set(pay.keys()) <= allowed


def test_packet_archived_event_payload_omits_unknown_keys() -> None:
    rec = build_archive_record_payload(
        bucket="bkt.test",
        key="k",
        content_sha256_hex="a" * 64,
        byte_length=3,
        content_type="text/plain",
        created_at="2026-05-04T00:00:00Z",
        company_id="c",
        repository_id="r",
        plan_id="p",
        task_id="t",
        workstream_id="w",
        handoff_id="h",
        phase="qa-gate",
        artifact_kind="packet_qa_gate",
        source_label="/tmp/x.md",
    )
    pay = packet_archived_event_payload(rec)
    assert ARCHIVE_RECORD_SCHEMA_VERSION == pay["schema_version"]
    assert "body_base64" not in pay
    assert pay["content_sha256"] == rec["content_sha256"]
