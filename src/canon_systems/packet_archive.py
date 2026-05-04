"""Packet/evidence archive helpers for the Canon CLI (S3 via state-api).

Canonical kind constants and deterministic keys live in ``canon_backend_shared.packet_archive``.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any

from canon_backend_shared.packet_archive import (
    ARCHIVE_RECORD_SCHEMA_VERSION,
    ArchiveValidationError,
    build_archive_object_key,
    build_archive_record_payload,
    normalize_archive_prefix,
    sha256_hex_digest,
    sanitize_key_segment,
    validate_artifact_kind,
)

__all__ = [
    "ARCHIVE_RECORD_SCHEMA_VERSION",
    "ArchiveValidationError",
    "build_archive_request_payload",
    "build_archive_object_key",
    "build_archive_record_payload",
    "dry_run_archive_record",
    "post_archive_to_state_api",
    "sha256_hex_digest",
    "validate_artifact_kind",
]


def _normalize_source_label(raw: str) -> str:
    t = str(raw).strip()
    if not t:
        raise ArchiveValidationError("source_label is required")
    if len(t) > 4096:
        raise ArchiveValidationError("source_label exceeds 4096 characters")
    if "\x00" in t:
        raise ArchiveValidationError("source_label contains NUL")
    return t


def build_archive_request_payload(
    *,
    body: bytes,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    handoff_id: str,
    phase: str,
    artifact_kind: str,
    source_label: str,
    content_type: str,
    agent_run_id: str = "",
    actor_id: str = "",
    outcome: str = "",
    status: str = "",
    evidence_subtype: str | None = None,
) -> dict[str, Any]:
    """JSON body for ``POST /state/archive`` (base64 body + declared digest for integrity)."""
    digest = sha256_hex_digest(body)
    validate_artifact_kind(artifact_kind, evidence_subtype=evidence_subtype)
    src = _normalize_source_label(source_label)
    for label, val in (
        ("company_id", company_id),
        ("repository_id", repository_id),
        ("plan_id", plan_id),
        ("task_id", task_id),
        ("workstream_id", workstream_id),
        ("handoff_id", handoff_id),
        ("phase", phase),
    ):
        sanitize_key_segment(val, label=label)
    payload: dict[str, Any] = {
        "schema_version": ARCHIVE_RECORD_SCHEMA_VERSION,
        "company_id": company_id,
        "repository_id": repository_id,
        "plan_id": plan_id,
        "task_id": task_id,
        "workstream_id": workstream_id,
        "handoff_id": handoff_id,
        "phase": phase,
        "artifact_kind": artifact_kind,
        "source_label": src,
        "content_type": content_type or "application/octet-stream",
        "body_base64": base64.standard_b64encode(body).decode("ascii"),
        "content_sha256": digest,
        "agent_run_id": agent_run_id,
        "actor_id": actor_id,
        "outcome": outcome,
        "status": status,
    }
    if evidence_subtype:
        payload["evidence_subtype"] = evidence_subtype
    return payload


def dry_run_archive_record(
    *,
    bucket: str,
    key_prefix: str,
    body: bytes,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    handoff_id: str,
    phase: str,
    artifact_kind: str,
    source_label: str,
    content_type: str,
    created_at: str,
    agent_run_id: str = "",
    actor_id: str = "",
    outcome: str = "",
    status: str = "",
    evidence_subtype: str | None = None,
) -> dict[str, Any]:
    """Resolve key + record metadata without touching S3 or state-api."""
    digest = sha256_hex_digest(body)
    validate_artifact_kind(artifact_kind, evidence_subtype=evidence_subtype)
    prefix = normalize_archive_prefix(key_prefix)
    key = build_archive_object_key(
        prefix=prefix,
        company_id=company_id,
        repository_id=repository_id,
        plan_id=plan_id,
        task_id=task_id,
        workstream_id=workstream_id,
        handoff_id=handoff_id,
        phase=phase,
        artifact_kind=artifact_kind,
        content_sha256_hex=digest,
        evidence_subtype=evidence_subtype,
    )
    return build_archive_record_payload(
        bucket=bucket,
        key=key,
        content_sha256_hex=digest,
        byte_length=len(body),
        content_type=content_type,
        created_at=created_at,
        company_id=company_id,
        repository_id=repository_id,
        plan_id=plan_id,
        task_id=task_id,
        workstream_id=workstream_id,
        handoff_id=handoff_id,
        phase=phase,
        artifact_kind=artifact_kind,
        source_label=source_label,
        agent_run_id=agent_run_id,
        actor_id=actor_id,
        outcome=outcome,
        status=status,
        evidence_subtype=evidence_subtype,
        s3_version_id=None,
    )


def post_archive_to_state_api(
    *,
    base_url: str,
    payload: dict[str, Any],
    timeout_seconds: float = 30.0,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    """POST JSON to ``/state/archive``. Returns status, parsed JSON body or error detail, headers."""
    root = base_url.rstrip("/")
    url = f"{root}/state/archive"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            headers = {k: v for k, v in resp.headers.items()}
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed if isinstance(parsed, dict) else {}, headers
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
        except Exception:
            detail = {"detail": e.reason}
        if isinstance(detail, dict) and "detail" in detail and isinstance(detail["detail"], dict):
            return e.code, dict(detail["detail"]), {}
        return e.code, detail if isinstance(detail, dict) else {}, {}


def default_state_api_base() -> str:
    return os.environ.get("CANON_STATE_API_URL", "http://127.0.0.1:8080").strip()
