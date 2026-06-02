"""Event-sourced core for `canon task` — assignable work items.

This module is the pure, stdlib-only heart of the task system. It has **no**
filesystem discovery, network, or wall-clock side effects: callers pass in
events (already loaded from a ledger) and timestamps / ids (generated at the
impure boundary in :mod:`canon_systems.tasks_cli`). That keeps materialization
deterministic and trivially unit-testable, matching the event/NDJSON ethos used
elsewhere in canon-systems (canonical events, run ledger, synthesis).

Model
-----
A *task* is the fold of an append-only stream of *task events*. Each event is
one NDJSON line. Tasks can be scoped three ways:

- ``repo``       — belongs to one ``repository_id`` (ledger travels with the repo).
- ``company``    — belongs to a ``company_id``, spans all its repos.
- ``multi_repo`` — belongs to a ``company_id`` and an explicit list of repos.

Merging two ledgers (local + remote sync) is a set-union keyed by ``event_id``;
events are idempotent, so re-applying a ledger never double-counts.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

SCHEMA_VERSION = 1

SCOPES: tuple[str, ...] = ("repo", "company", "multi_repo")
STATUSES: tuple[str, ...] = ("open", "in_progress", "blocked", "done", "cancelled")
PRIORITIES: tuple[str, ...] = ("low", "normal", "high", "urgent")
TERMINAL_STATUSES: frozenset[str] = frozenset({"done", "cancelled"})

EVENT_CREATED = "task_created"
EVENT_UPDATED = "task_updated"
EVENT_COMMENTED = "task_commented"
EVENT_TYPES: tuple[str, ...] = (EVENT_CREATED, EVENT_UPDATED, EVENT_COMMENTED)

# Fields a `task_updated` event may set, with their normalizers.
_LIST_FIELDS: tuple[str, ...] = ("assignees", "repositories", "labels")
_SCALAR_FIELDS: tuple[str, ...] = ("title", "body", "status", "priority", "due")

_PRIORITY_RANK: dict[str, int] = {"urgent": 0, "high": 1, "normal": 2, "low": 3}


class TaskError(ValueError):
    """Raised when an event or task input fails validation."""


def normalize_scope(scope: str) -> str:
    s = (scope or "").strip().lower().replace("-", "_")
    if s in ("multirepo", "multi"):
        s = "multi_repo"
    if s not in SCOPES:
        raise TaskError(f"invalid scope {scope!r}; expected one of {', '.join(SCOPES)}")
    return s


def normalize_status(status: str) -> str:
    s = (status or "").strip().lower().replace("-", "_")
    if s == "todo":
        s = "open"
    if s == "closed":
        s = "done"
    if s not in STATUSES:
        raise TaskError(f"invalid status {status!r}; expected one of {', '.join(STATUSES)}")
    return s


def normalize_priority(priority: str) -> str:
    p = (priority or "").strip().lower()
    if not p:
        return "normal"
    if p not in PRIORITIES:
        raise TaskError(f"invalid priority {priority!r}; expected one of {', '.join(PRIORITIES)}")
    return p


def _clean_list(values: Iterable[Any]) -> list[str]:
    """Dedupe + sort string items, dropping blanks. Deterministic ordering."""
    seen: set[str] = set()
    for v in values:
        s = str(v).strip()
        if s:
            seen.add(s)
    return sorted(seen)


def validate_event(event: Mapping[str, Any]) -> None:
    """Raise :class:`TaskError` if ``event`` is not a well-formed task event."""
    if not isinstance(event, Mapping):
        raise TaskError("event must be a mapping")
    etype = event.get("event_type")
    if etype not in EVENT_TYPES:
        raise TaskError(f"invalid event_type {etype!r}")
    for key in ("event_id", "task_ref", "timestamp", "actor_id"):
        if not str(event.get(key, "")).strip():
            raise TaskError(f"event missing required field {key!r}")
    if etype == EVENT_CREATED:
        normalize_scope(str(event.get("scope", "")))


def make_event(
    *,
    event_type: str,
    event_id: str,
    task_ref: str,
    timestamp: str,
    actor_id: str,
    actor_display: str = "",
    company_id: str = "",
    scope: str = "",
    repository_id: str = "",
    repositories: Iterable[str] | None = None,
    fields: Mapping[str, Any] | None = None,
    comment: str = "",
) -> dict[str, Any]:
    """Build a well-formed, normalized task event dict (NDJSON-ready)."""
    if event_type not in EVENT_TYPES:
        raise TaskError(f"invalid event_type {event_type!r}")
    event: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "event_type": event_type,
        "event_id": str(event_id).strip(),
        "task_ref": str(task_ref).strip(),
        "timestamp": str(timestamp).strip(),
        "actor_id": str(actor_id).strip(),
    }
    if actor_display.strip():
        event["actor_display"] = actor_display.strip()
    if company_id.strip():
        event["company_id"] = company_id.strip()
    if event_type == EVENT_CREATED:
        event["scope"] = normalize_scope(scope)
        if event["scope"] == "repo" and repository_id.strip():
            event["repository_id"] = repository_id.strip()
        if event["scope"] == "multi_repo":
            event["repositories"] = _clean_list(repositories or [])
        elif repository_id.strip():
            event["repository_id"] = repository_id.strip()
    if comment.strip():
        event["comment"] = comment.strip()
    normalized_fields = _normalize_fields(fields or {})
    if normalized_fields:
        event["fields"] = normalized_fields
    validate_event(event)
    return event


def _normalize_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in fields.items():
        if key in _LIST_FIELDS:
            out[key] = _clean_list(value if isinstance(value, (list, tuple, set)) else [value])
        elif key == "status":
            out[key] = normalize_status(str(value))
        elif key == "priority":
            out[key] = normalize_priority(str(value))
        elif key in _SCALAR_FIELDS:
            out[key] = str(value).strip()
    return out


def _sort_events(events: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    # (timestamp, event_id) gives a total, deterministic order independent of
    # ledger file order — so local + synced ledgers fold identically.
    return sorted(events, key=lambda e: (str(e.get("timestamp", "")), str(e.get("event_id", ""))))


def _new_task(event: Mapping[str, Any]) -> dict[str, Any]:
    scope = normalize_scope(str(event.get("scope", "company")))
    return {
        "task_ref": str(event["task_ref"]),
        "schema_version": SCHEMA_VERSION,
        "title": "",
        "body": "",
        "scope": scope,
        "company_id": str(event.get("company_id", "")),
        "repository_id": str(event.get("repository_id", "")),
        "repositories": list(event.get("repositories", []) or []),
        "author_id": str(event.get("actor_id", "")),
        "author_display": str(event.get("actor_display", "")),
        "assignees": [],
        "labels": [],
        "status": "open",
        "priority": "normal",
        "due": "",
        "created_at": str(event.get("timestamp", "")),
        "updated_at": str(event.get("timestamp", "")),
        "comments": [],
        "history": [],
    }


def _apply_fields(task: dict[str, Any], fields: Mapping[str, Any], event: Mapping[str, Any]) -> None:
    actor = str(event.get("actor_id", ""))
    ts = str(event.get("timestamp", ""))
    for key, value in fields.items():
        if key == "status":
            old = task.get("status")
            if old != value:
                task["history"].append(
                    {"ts": ts, "actor": actor, "change": f"status: {old} -> {value}"}
                )
            task["status"] = value
        elif key in _LIST_FIELDS:
            task[key] = list(value)
        elif key in _SCALAR_FIELDS:
            task[key] = value


def fold_event(state: dict[str, dict[str, Any]], event: Mapping[str, Any]) -> None:
    """Apply one (pre-validated) event to the materialized ``state`` in place."""
    ref = str(event.get("task_ref", ""))
    etype = event.get("event_type")
    if etype == EVENT_CREATED and ref not in state:
        state[ref] = _new_task(event)
    if ref not in state:
        # Update/comment for a task we never saw created — synthesize a stub so
        # partial ledgers (mid-sync) still surface the task rather than dropping it.
        state[ref] = _new_task(event)
    task = state[ref]
    fields = event.get("fields") or {}
    if fields:
        _apply_fields(task, fields, event)
    if etype == EVENT_COMMENTED and str(event.get("comment", "")).strip():
        task["comments"].append(
            {
                "ts": str(event.get("timestamp", "")),
                "actor": str(event.get("actor_id", "")),
                "actor_display": str(event.get("actor_display", "")),
                "text": str(event.get("comment", "")).strip(),
            }
        )
    ts = str(event.get("timestamp", ""))
    if ts > task["updated_at"]:
        task["updated_at"] = ts


def materialize(events: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Fold an event stream into ``{task_ref: task}``. Deterministic."""
    state: dict[str, dict[str, Any]] = {}
    for event in _sort_events(events):
        try:
            validate_event(event)
        except TaskError:
            continue  # skip malformed lines, never abort the whole ledger
        fold_event(state, event)
    return state


def dedupe_events(*event_streams: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Union of events across ledgers, keyed by ``event_id`` (idempotent merge)."""
    by_id: dict[str, dict[str, Any]] = {}
    for stream in event_streams:
        for ev in stream:
            eid = str(ev.get("event_id", "")).strip()
            if eid and eid not in by_id:
                by_id[eid] = dict(ev)
    return [by_id[k] for k in sorted(by_id.keys())]


def task_matches(
    task: Mapping[str, Any],
    *,
    status: str | None = None,
    assignee: str | None = None,
    mine_actor: str | None = None,
    scope: str | None = None,
    repository_id: str | None = None,
    company_id: str | None = None,
    label: str | None = None,
    include_terminal: bool = False,
) -> bool:
    """Return True when ``task`` passes every supplied filter."""
    if status:
        if task.get("status") != normalize_status(status):
            return False
    elif not include_terminal and task.get("status") in TERMINAL_STATUSES:
        return False
    if scope and task.get("scope") != normalize_scope(scope):
        return False
    if company_id and str(task.get("company_id", "")) != company_id:
        return False
    if repository_id and not _task_touches_repo(task, repository_id):
        return False
    if assignee and assignee not in task.get("assignees", []):
        return False
    if mine_actor and not _is_mine(task, mine_actor):
        return False
    if label and label not in task.get("labels", []):
        return False
    return True


def _task_touches_repo(task: Mapping[str, Any], repository_id: str) -> bool:
    if task.get("scope") == "repo":
        return str(task.get("repository_id", "")) == repository_id
    if task.get("scope") == "multi_repo":
        return repository_id in task.get("repositories", [])
    # company-scoped tasks apply to every repo in the company
    return True


def _is_mine(task: Mapping[str, Any], actor: str) -> bool:
    return actor in task.get("assignees", []) or str(task.get("author_id", "")) == actor


def sort_tasks(tasks: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Open work first, by priority then most-recently-updated, then ref."""

    def key(t: Mapping[str, Any]) -> tuple[int, int, str, str]:
        terminal = 1 if t.get("status") in TERMINAL_STATUSES else 0
        prio = _PRIORITY_RANK.get(str(t.get("priority", "normal")), 2)
        # newest updated first => invert by using reverse string compare via prefix trick
        return (terminal, prio, _invert(str(t.get("updated_at", ""))), str(t.get("task_ref", "")))

    return [dict(t) for t in sorted(tasks, key=key)]


def _invert(s: str) -> str:
    # Map each char to its complement so ascending sort yields descending order.
    return "".join(chr(0x10FFFF - ord(c)) if ord(c) < 0x10FFFF else c for c in s)


def filter_and_sort(
    tasks: Iterable[Mapping[str, Any]], **filters: Any
) -> list[dict[str, Any]]:
    selected = [dict(t) for t in tasks if task_matches(t, **filters)]
    return sort_tasks(selected)


# ---------------------------------------------------------------------------
# Rendering helpers (used by the CLI for human-readable output).
# ---------------------------------------------------------------------------

_STATUS_BADGE = {
    "open": "[ ]",
    "in_progress": "[~]",
    "blocked": "[!]",
    "done": "[x]",
    "cancelled": "[-]",
}


def render_scope(task: Mapping[str, Any]) -> str:
    scope = task.get("scope")
    if scope == "repo":
        return f"repo:{task.get('repository_id', '?')}"
    if scope == "multi_repo":
        repos = ",".join(task.get("repositories", [])) or "?"
        return f"multi:{repos}"
    return f"company:{task.get('company_id', '?')}"


def render_task_line(task: Mapping[str, Any]) -> str:
    badge = _STATUS_BADGE.get(str(task.get("status", "open")), "[ ]")
    prio = str(task.get("priority", "normal"))
    prio_tag = f" !{prio}" if prio in ("high", "urgent") else ""
    assignees = ",".join(task.get("assignees", [])) or "unassigned"
    return (
        f"{badge} {task.get('task_ref', '?')}  {task.get('title', '')}"
        f"{prio_tag}  ->{assignees}  ({render_scope(task)})"
    )


def render_task_detail(task: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"{task.get('task_ref', '?')}: {task.get('title', '')}")
    lines.append(f"  status:    {task.get('status', 'open')}")
    lines.append(f"  priority:  {task.get('priority', 'normal')}")
    lines.append(f"  scope:     {render_scope(task)}")
    author = task.get("author_display") or task.get("author_id", "")
    lines.append(f"  author:    {author}")
    lines.append(f"  assignees: {', '.join(task.get('assignees', [])) or 'unassigned'}")
    if task.get("labels"):
        lines.append(f"  labels:    {', '.join(task.get('labels', []))}")
    if task.get("due"):
        lines.append(f"  due:       {task.get('due')}")
    lines.append(f"  created:   {task.get('created_at', '')}")
    lines.append(f"  updated:   {task.get('updated_at', '')}")
    if task.get("body"):
        lines.append("  body:")
        for ln in str(task.get("body", "")).splitlines() or [""]:
            lines.append(f"    {ln}")
    comments = task.get("comments", [])
    if comments:
        lines.append("  comments:")
        for c in comments:
            who = c.get("actor_display") or c.get("actor", "")
            lines.append(f"    - [{c.get('ts', '')}] {who}: {c.get('text', '')}")
    history = task.get("history", [])
    if history:
        lines.append("  history:")
        for h in history:
            lines.append(f"    - [{h.get('ts', '')}] {h.get('actor', '')}: {h.get('change', '')}")
    return "\n".join(lines)
