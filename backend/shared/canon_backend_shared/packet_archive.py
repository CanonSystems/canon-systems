"""Shared packet/evidence archive contract (v1): kinds, key segments, SHA-256 helpers.

Used by ``canon-systems`` CLI and ``state-api`` so keys and validation stay aligned.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any

ARCHIVE_RECORD_SCHEMA_VERSION = 1

# Phase packets (five canonical phases + implementer shard handoffs)
PACKET_SCOPER = "packet_scoper"
PACKET_CURSOR_PILOT = "packet_cursor_pilot"
PACKET_IMPLEMENTER = "packet_implementer"
PACKET_IMPLEMENTER_SHARD = "packet_implementer_shard"
PACKET_QA_GATE = "packet_qa_gate"
PACKET_RELEASE_STATUS = "packet_release_status"

# DoR / rejection plane
PACKET_HANDOFF_NOT_READY = "packet_handoff_not_ready"
DOR_TELEMETRY = "dor_telemetry"

# Evidence blobs (typed labels; run-ledger storage is out of scope here)
EVIDENCE_MEMORY_HEALTH = "evidence_memory_health"
EVIDENCE_DEPLOYMENT_SMOKE = "evidence_deployment_smoke"
EVIDENCE_RUNTIME = "evidence_runtime"
EVIDENCE_BROWSER = "evidence_browser"
EVIDENCE_SHELL = "evidence_shell"

PHASE_PACKET_KINDS: frozenset[str] = frozenset(
    {
        PACKET_SCOPER,
        PACKET_CURSOR_PILOT,
        PACKET_IMPLEMENTER,
        PACKET_IMPLEMENTER_SHARD,
        PACKET_QA_GATE,
        PACKET_RELEASE_STATUS,
    }
)
HANDOFF_PACKET_KINDS: frozenset[str] = frozenset({PACKET_HANDOFF_NOT_READY})
DOR_KINDS: frozenset[str] = frozenset({DOR_TELEMETRY})
EVIDENCE_KINDS: frozenset[str] = frozenset(
    {
        EVIDENCE_MEMORY_HEALTH,
        EVIDENCE_DEPLOYMENT_SMOKE,
        EVIDENCE_RUNTIME,
        EVIDENCE_BROWSER,
        EVIDENCE_SHELL,
    }
)

ALL_BUILTIN_ARTIFACT_KINDS: frozenset[str] = (
    PHASE_PACKET_KINDS | HANDOFF_PACKET_KINDS | DOR_KINDS | EVIDENCE_KINDS
)

# Future QA / custom evidence: evidence_<slug> without expanding the run ledger.
_EVIDENCE_EXTENSION_PATTERN = re.compile(r"^evidence_[a-z0-9][a-z0-9_-]{0,126}$")

_SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class ArchiveValidationError(ValueError):
    """Raised when scope fields, artifact kind, or hash segments are unsafe or invalid."""


def normalize_sha256_hex(value: str) -> str:
    """Lowercase 64-char SHA-256 hex digest."""
    v = str(value).strip().lower()
    if _SHA256_HEX_PATTERN.match(v) is None:
        raise ArchiveValidationError("content_sha256 must be a 64-char lowercase hex SHA-256 digest")
    return v


def sha256_hex_digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sanitize_key_segment(raw: str, *, label: str) -> str:
    """Reject path traversal and separators; normalize tenant/key segments."""
    s = str(raw).strip()
    if not s:
        raise ArchiveValidationError(f"{label} must be non-empty")
    if "/" in s or "\\" in s:
        raise ArchiveValidationError(f"{label} must not contain path separators")
    if s in (".", "..") or ".." in s:
        raise ArchiveValidationError(f"{label} must not contain '.' traversal segments")
    if len(s) > 256:
        raise ArchiveValidationError(f"{label} exceeds maximum length (256)")
    return s


def validate_artifact_kind(kind: str, *, evidence_subtype: str | None) -> None:
    k = str(kind).strip()
    if not k:
        raise ArchiveValidationError("artifact_kind is required")
    if k in ALL_BUILTIN_ARTIFACT_KINDS:
        if k == PACKET_IMPLEMENTER_SHARD and not (evidence_subtype or "").strip():
            raise ArchiveValidationError(
                "packet_implementer_shard requires evidence_subtype (shard id / label)"
            )
        return
    if _EVIDENCE_EXTENSION_PATTERN.fullmatch(k) is None:
        raise ArchiveValidationError(
            "artifact_kind must be a built-in kind or match evidence_<slug> "
            "(lowercase letters, digits, underscore, hyphen; max length 128)"
        )


def normalize_archive_prefix(prefix: str) -> str:
    p = str(prefix).strip().strip("/")
    if not p:
        return ""
    # Prefix may contain slashes for organizational grouping; split and sanitize each piece.
    parts: list[str] = []
    for piece in p.split("/"):
        piece = piece.strip()
        if not piece:
            continue
        parts.append(sanitize_key_segment(piece, label="archive_prefix_segment"))
    return "/".join(parts)


def build_archive_object_key(
    *,
    prefix: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    handoff_id: str,
    phase: str,
    artifact_kind: str,
    content_sha256_hex: str,
    evidence_subtype: str | None = None,
) -> str:
    """Deterministic, tenant-scoped, content-addressed S3 object key (v1 layout)."""
    norm_prefix = normalize_archive_prefix(prefix)
    digest = normalize_sha256_hex(content_sha256_hex)
    segments = [
        sanitize_key_segment(company_id, label="company_id"),
        sanitize_key_segment(repository_id, label="repository_id"),
        sanitize_key_segment(plan_id, label="plan_id"),
        sanitize_key_segment(task_id, label="task_id"),
        sanitize_key_segment(workstream_id, label="workstream_id"),
        sanitize_key_segment(handoff_id, label="handoff_id"),
        sanitize_key_segment(phase, label="phase"),
        sanitize_key_segment(artifact_kind, label="artifact_kind"),
    ]
    est = (evidence_subtype or "").strip()
    if est:
        segments.append(sanitize_key_segment(est, label="evidence_subtype"))
    segments.append(digest)
    tail = "/".join(segments)
    if norm_prefix:
        return f"{norm_prefix}/v1/{tail}"
    return f"v1/{tail}"


def normalize_bucket_name(raw: str) -> str:
    """Minimal bucket validation (operator-supplied; must not carry path semantics)."""
    b = str(raw).strip()
    if not b:
        raise ArchiveValidationError("s3 bucket name is required")
    if "/" in b or "\\" in b or ".." in b:
        raise ArchiveValidationError("s3 bucket name must not contain path separators")
    if len(b) > 63:
        raise ArchiveValidationError("s3 bucket name exceeds 63 characters")
    return b


def build_archive_record_payload(
    *,
    bucket: str,
    key: str,
    content_sha256_hex: str,
    byte_length: int,
    content_type: str,
    created_at: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    handoff_id: str,
    phase: str,
    artifact_kind: str,
    source_label: str,
    agent_run_id: str = "",
    actor_id: str = "",
    outcome: str = "",
    status: str = "",
    evidence_subtype: str | None = None,
    s3_version_id: str | None = None,
) -> dict[str, Any]:
    """Structured archive record (API/CLI JSON). Full bodies are never included."""
    bucket_s = normalize_bucket_name(bucket)
    record: dict[str, Any] = {
        "schema_version": ARCHIVE_RECORD_SCHEMA_VERSION,
        "company_id": company_id,
        "repository_id": repository_id,
        "plan_id": plan_id,
        "task_id": task_id,
        "workstream_id": workstream_id,
        "handoff_id": handoff_id,
        "phase": phase,
        "artifact_kind": artifact_kind,
        "source_label": source_label,
        "s3_bucket": bucket_s,
        "s3_key": key,
        "s3_uri": f"s3://{bucket_s}/{key}",
        "content_sha256": normalize_sha256_hex(content_sha256_hex),
        "byte_length": int(byte_length),
        "content_type": content_type or "application/octet-stream",
        "created_at": created_at,
        "agent_run_id": agent_run_id or "",
        "actor_id": actor_id or "",
        "outcome": outcome or "",
        "status": status or "",
    }
    if evidence_subtype:
        record["evidence_subtype"] = evidence_subtype
    if s3_version_id:
        record["s3_version_id"] = s3_version_id
    return record


def packet_archived_event_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    """Subset of archive metadata suitable for canonical ``packet_archived`` events (no bodies)."""
    keys = (
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
    )
    out: dict[str, Any] = {}
    for k in keys:
        if k not in record:
            continue
        val = record[k]
        if val is None or val == "":
            continue
        out[k] = val
    return out


# Mapping for docs / UX (filename hint -> kind)
CANONICAL_MARKDOWN_PACKET_FILENAMES: dict[str, str] = {
    "scoper.md": PACKET_SCOPER,
    "cursor-pilot.md": PACKET_CURSOR_PILOT,
    "implementer.md": PACKET_IMPLEMENTER,
    "qa-gate.md": PACKET_QA_GATE,
    "release-status.md": PACKET_RELEASE_STATUS,
}
