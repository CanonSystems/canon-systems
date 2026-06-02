"""Server-side task plane keys + validation (shared by state-api and the CLI).

Tasks are assignable work items, event-sourced like the local ledger but stored
server-authoritatively so any machine can ask "what's next", mark a task done,
attribute branch/deployment/progress, and reassign — independent of any repo's
git checkout state.

This module is **pure** (stdlib only): it derives DynamoDB keys and validates
event envelopes. The authoritative event *constructor* + materialization fold
lives in ``canon_systems.tasks`` (the client); the server stores normalized
events and returns them for the client to fold. Keeping derivation here lets the
server and client agree on keys without a client→server import.

Key shape (disjoint from checkpoint / run-ledger items):

- ``pk = "{company_id}#tasks"``
- event rows: ``sk = "{task_ref}#evt#{event_id}"``

A company's task stream is a single partition; one task's events share the
``{task_ref}#evt#`` sort-key prefix.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

TASK_EVENT_SCHEMA_VERSION = 1

TASKS_PK_TAIL = "tasks"
_EVENT_INFIX = "evt"

TASK_EVENT_TYPES: frozenset[str] = frozenset(
    {"task_created", "task_updated", "task_commented"}
)

_SEGMENT_FORBIDDEN = re.compile(r"[#|\\/]")

# Required envelope fields on every task event row.
_REQUIRED_FIELDS: tuple[str, ...] = (
    "event_id",
    "event_type",
    "task_ref",
    "timestamp",
    "actor_id",
    "company_id",
)


class TaskValidationError(ValueError):
    """Raised when a task event envelope is unsafe or structurally invalid."""


def sanitize_segment(value: str, *, label: str) -> str:
    """Return a trimmed key segment, rejecting separators that would corrupt keys."""
    s = str(value or "").strip()
    if not s:
        raise TaskValidationError(f"{label} must be a non-empty string")
    if _SEGMENT_FORBIDDEN.search(s):
        raise TaskValidationError(f"{label} must not contain '#', '|', '\\\\', or '/'")
    return s


def build_tasks_pk(*, company_id: str) -> str:
    c = sanitize_segment(company_id, label="company_id")
    return f"{c}#{TASKS_PK_TAIL}"


def build_task_event_sk(*, task_ref: str, event_id: str) -> str:
    t = sanitize_segment(task_ref, label="task_ref")
    e = sanitize_segment(event_id, label="event_id")
    return f"{t}#{_EVENT_INFIX}#{e}"


def task_event_sk_prefix(*, task_ref: str) -> str:
    t = sanitize_segment(task_ref, label="task_ref")
    return f"{t}#{_EVENT_INFIX}#"


def validate_task_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Validate + shallow-normalize a task event envelope for server storage.

    Does not re-derive task semantics (the client already normalized fields);
    it enforces the required envelope, the event-type enum, and key-safe
    ``company_id`` / ``task_ref`` / ``event_id`` segments so keys never corrupt.
    Returns a plain dict copy (without ``pk``/``sk``).
    """
    if not isinstance(event, Mapping):
        raise TaskValidationError("event must be a mapping")
    record = {k: v for k, v in event.items() if k not in ("pk", "sk")}
    for key in _REQUIRED_FIELDS:
        if not str(record.get(key, "")).strip():
            raise TaskValidationError(f"event missing required field {key!r}")
    if record.get("event_type") not in TASK_EVENT_TYPES:
        raise TaskValidationError(f"invalid event_type {record.get('event_type')!r}")
    # Key-safety on segments used to build pk/sk.
    sanitize_segment(str(record["company_id"]), label="company_id")
    sanitize_segment(str(record["task_ref"]), label="task_ref")
    sanitize_segment(str(record["event_id"]), label="event_id")
    record.setdefault("schema_version", TASK_EVENT_SCHEMA_VERSION)
    return record


def event_keys(event: Mapping[str, Any]) -> tuple[str, str]:
    """Return (pk, sk) for a validated event mapping."""
    pk = build_tasks_pk(company_id=str(event["company_id"]))
    sk = build_task_event_sk(
        task_ref=str(event["task_ref"]), event_id=str(event["event_id"])
    )
    return pk, sk


def events_equivalent(stored: Mapping[str, Any], desired: Mapping[str, Any]) -> bool:
    """True when two stored event rows are the same logical event (idempotent re-put)."""
    import json

    a = {k: v for k, v in stored.items() if k not in ("pk", "sk")}
    b = {k: v for k, v in desired.items() if k not in ("pk", "sk")}
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(
        b, sort_keys=True, default=str
    )
