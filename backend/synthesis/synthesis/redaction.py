"""E5-T1 allowlist redaction: CanonicalEvent → SafeEvent projection.

Sole enforcement point for docs/VAULT-LAYOUT.md §5. Unknown fields and unknown
payload keys are silently dropped — no logs, no warnings, no telemetry.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, cast

from canon_backend_shared.events import CanonicalEvent

SAFE_ENVELOPE_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "event_id",
        "parent_event_id",
        "event_type",
        "plan_id",
        "task_id",
        "handoff_id",
        "agent_name",
        "timestamp",
        "state_version",
    }
)
SCOPE_SAFE_ALIASED: frozenset[str] = frozenset(
    {
        "company_id",
        "repository_id",
        "agent_run_id",
        "actor_id",
    }
)
FRONTMATTER_ANCHOR_ORDER: tuple[str, ...] = ("schema_version", "event_id")


@dataclass(frozen=True)
class SafeEvent:
    frontmatter: dict[str, Any]
    path_shorthashes: dict[str, str]
    payload: dict[str, Any]
    event_type: str
    event_id: str


def shorthash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def _project_retrieval_breakdown(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "phase" in payload and isinstance(
        (ph := payload.get("phase")), (str, int, float, bool, type(None))
    ):
        out["phase"] = ph
    if "agent" in payload and isinstance(
        (ag := payload.get("agent")), (str, int, float, bool, type(None))
    ):
        out["agent"] = ag
    if "sources" in payload and isinstance(payload["sources"], Mapping):
        src = cast(Mapping[str, Any], payload["sources"])
        keys = ("graph", "state", "canonical", "file")
        bucket: dict[str, Any] = {}
        for b in keys:
            if b not in src or not isinstance(src[b], Mapping):
                continue
            m = src[b]
            d: dict[str, Any] = {}
            if "tokens_in" in m:
                d["tokens_in"] = m["tokens_in"]
            if "tokens_out" in m:
                d["tokens_out"] = m["tokens_out"]
            if d:
                bucket[b] = d
        if bucket:
            out["sources"] = bucket
    return out


def _project_lease_stall(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    diag = payload.get("diagnostic")
    if isinstance(diag, Mapping):
        dmap = cast(Mapping[str, Any], diag)
        inner: dict[str, Any] = {}
        if "expires_at" in dmap:
            inner["expires_at"] = dmap["expires_at"]
        if "owner_suffix" in dmap:
            inner["owner_suffix"] = dmap["owner_suffix"]
        if inner:
            out["diagnostic"] = inner
    sns = payload.get("suggested_next_step")
    if isinstance(sns, Mapping) and "message" in cast(Mapping[str, Any], sns):
        out["suggested_next_step"] = {
            "message": cast(Mapping[str, Any], sns)["message"]
        }
    return out


def _lease_merge_owner_to_suffix(
    payload: Mapping[str, Any], out: dict[str, Any]
) -> None:
    pdiag = payload.get("diagnostic")
    if not isinstance(pdiag, Mapping):
        return
    pdm = cast(Mapping[str, Any], pdiag)
    if "owner" not in pdm:
        return
    odiag = out.setdefault("diagnostic", {})
    if not isinstance(odiag, dict):
        return
    if odiag.get("owner_suffix") not in (None, ""):
        return
    odiag["owner_suffix"] = shorthash(str(pdm["owner"]))


def _project_checkpoint_write(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "phase" in payload and isinstance(
        (ph := payload.get("phase")), (str, int, float, bool, type(None))
    ):
        out["phase"] = ph
    if "state_version" in payload and isinstance(
        (sv := payload.get("state_version")), (str, int, float, bool, type(None))
    ):
        out["state_version"] = sv
    return out


def project_payload(event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if event_type == "retrieval_breakdown":
        return _project_retrieval_breakdown(payload)
    if event_type == "lease_stall_detected":
        return _project_lease_stall(payload)
    if event_type == "checkpoint_write":
        return _project_checkpoint_write(payload)
    return {}


def project_safe(ev: CanonicalEvent) -> SafeEvent:
    all_fields = {
        "schema_version": ev.schema_version,
        "event_id": ev.event_id,
        "parent_event_id": ev.parent_event_id,
        "event_type": ev.event_type,
        "plan_id": ev.plan_id,
        "task_id": ev.task_id,
        "handoff_id": ev.handoff_id,
        "agent_name": ev.agent_name,
        "timestamp": ev.timestamp,
        "state_version": ev.state_version,
    }
    frontmatter = {k: v for k, v in all_fields.items() if k in SAFE_ENVELOPE_FIELDS}
    path_shorthashes = {
        "company_shorthash": shorthash(ev.company_id),
        "repo_shorthash": shorthash(ev.repository_id),
        "agent_run_suffix": shorthash(ev.agent_run_id),
        "actor_suffix": shorthash(ev.actor_id),
    }
    p = project_payload(ev.event_type, ev.payload)
    if ev.event_type == "lease_stall_detected":
        _lease_merge_owner_to_suffix(ev.payload, p)
    return SafeEvent(
        frontmatter=frontmatter,
        path_shorthashes=path_shorthashes,
        payload=p,
        event_type=ev.event_type,
        event_id=ev.event_id,
    )
