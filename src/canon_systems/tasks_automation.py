"""Automatic task ↔ session wiring for Cursor hooks and memory capture."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from . import tasks as core

ACTIVE_CONTEXT_REL = Path(".canon") / "tasks" / "active-context.json"
_TASK_REF_RE = re.compile(r"\b(tsk_[a-zA-Z0-9_]+)\b")
_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```")
_BRANCH_RE = re.compile(
    r"(?:branch[:\s]+[`']?([^\s`']+)[`']?|"
    r"on\s+[`']?(feat|fix|chore|wave|task)/[a-zA-Z0-9._/-]+[`']?)",
    re.IGNORECASE,
)
_PR_RE = re.compile(r"github\.com/[^\s)]+/pull/(\d+)", re.IGNORECASE)
_DEPLOY_RE = re.compile(
    r"(?:deploy(?:ed)?\s+(?:to\s+)?|live\s+on\s+)([a-zA-Z0-9][a-zA-Z0-9._:/-]{4,80})",
    re.IGNORECASE,
)
_AUTO_PREFIX = "[auto] "
_SKIP_OPENERS = (
    "sure",
    "okay",
    "ok",
    "got it",
    "i'll ",
    "i will ",
    "let me ",
    "one moment",
    "working on",
)


def _auto_note_enabled() -> bool:
    return os.environ.get("CANON_TASKS_AUTO_NOTE", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _min_assistant_chars() -> int:
    raw = os.environ.get("CANON_TASKS_AUTO_NOTE_MIN_CHARS", "80").strip()
    try:
        return max(20, int(raw))
    except ValueError:
        return 80


def _max_note_chars() -> int:
    raw = os.environ.get("CANON_TASKS_AUTO_NOTE_MAX_CHARS", "420").strip()
    try:
        return max(80, min(2000, int(raw)))
    except ValueError:
        return 420


def _normalize_note_text(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", (text or "").strip())
    return collapsed


def note_fingerprint(text: str) -> str:
    body = _normalize_note_text(text)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub(" ", text or "")


def _last_comment_text(task: Mapping[str, Any]) -> str:
    comments = task.get("comments")
    if not isinstance(comments, list) or not comments:
        return ""
    last = comments[-1]
    if isinstance(last, dict):
        return str(last.get("text", "")).strip()
    return str(last).strip()


def _is_low_signal_assistant(text: str) -> bool:
    low = _normalize_note_text(text).lower()
    if not low:
        return True
    if len(low) < 24:
        return True
    for opener in _SKIP_OPENERS:
        if low.startswith(opener) and len(low) < 140:
            return True
    if low in {"done", "done.", "complete", "completed", "finished"}:
        return True
    return False


def _pick_summary_lines(text: str, *, max_chars: int) -> str:
    """Prefer markdown section headers and bullet lines over raw dumps."""
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("```"):
            continue
        if line.startswith("|") and line.count("|") >= 2:
            continue
        lines.append(line)
    if not lines:
        return _normalize_note_text(text)[:max_chars]

    picked: list[str] = []
    in_summary = False
    for line in lines:
        header = line.lstrip("#").strip().lower()
        if header in (
            "summary",
            "done",
            "completed",
            "what changed",
            "changes",
            "test plan",
            "result",
            "status",
        ):
            in_summary = True
            continue
        if line.startswith("#") and in_summary:
            break
        if line.startswith(("-", "*", "•")) or in_summary:
            picked.append(line.lstrip("-*• ").strip())
        elif not picked and len(line) > 20:
            picked.append(line)
        if sum(len(x) + 2 for x in picked) >= max_chars:
            break

    if not picked:
        picked = [lines[0]]
    out = " · ".join(picked)
    return out[:max_chars].rstrip(" ·")


def distill_progress_note(user_text: str, assistant_text: str) -> str | None:
    """Build a short progress note from a Cursor turn, or None if not worth recording."""
    if not _auto_note_enabled():
        return None
    ast = _strip_code_fences(assistant_text).strip()
    if len(ast) < _min_assistant_chars() or _is_low_signal_assistant(ast):
        return None

    max_chars = _max_note_chars() - len(_AUTO_PREFIX)
    body = _pick_summary_lines(ast, max_chars=max_chars)
    if len(_normalize_note_text(body)) < 32:
        return None

    user = _normalize_note_text(user_text)
    if user and len(user) <= 100:
        body = f"Q: {user} → {body}"
    return _AUTO_PREFIX + body[:max_chars]


def extract_progress_fields(*texts: str) -> dict[str, str]:
    """Best-effort branch / PR / deployment hints from assistant prose."""
    joined = "\n".join(t for t in texts if t)
    fields: dict[str, str] = {}
    pr = _PR_RE.search(joined)
    if pr:
        fields["deployment"] = f"PR #{pr.group(1)}"
    dep = _DEPLOY_RE.search(joined)
    if dep and "deployment" not in fields:
        fields["deployment"] = dep.group(1).strip()
    br = _BRANCH_RE.search(joined)
    if br:
        candidate = (br.group(1) or br.group(2) or "").strip()
        if candidate and not candidate.startswith("http"):
            fields["branch"] = candidate
    return fields


def should_record_auto_note(
    task: Mapping[str, Any],
    note: str,
    *,
    turn_fingerprint: str,
    active_context: Mapping[str, Any] | None,
) -> bool:
    """Suppress duplicate or near-duplicate auto-notes (hook retries, echo)."""
    norm = _normalize_note_text(note)
    if not norm.startswith(_AUTO_PREFIX):
        return False
    last = _normalize_note_text(_last_comment_text(task))
    if last and note_fingerprint(last) == note_fingerprint(norm):
        return False
    ctx = active_context or {}
    if ctx.get("last_turn_fingerprint") == turn_fingerprint:
        return False
    if ctx.get("last_auto_note_hash") == note_fingerprint(norm):
        return False
    return True


def merge_active_after_note(
    payload: dict[str, Any],
    *,
    note: str,
    turn_fingerprint: str,
) -> dict[str, Any]:
    out = dict(payload)
    out["last_auto_note_hash"] = note_fingerprint(note)
    out["last_turn_fingerprint"] = turn_fingerprint
    out["last_auto_note_at"] = _now_iso()
    return out


def targets_for_session_notes(
    *,
    state: Mapping[str, Mapping[str, Any]],
    mentioned_refs: list[str],
    active_ref: str,
    max_targets: int = 6,
) -> list[str]:
    """Tasks that should receive an auto-note this turn (batch/plan friendly)."""
    refs: list[str] = []
    seen: set[str] = set()
    for ref in mentioned_refs:
        if ref in state and ref not in seen:
            seen.add(ref)
            refs.append(ref)
    if active_ref and active_ref in state and active_ref not in seen:
        refs.insert(0, active_ref)
    if not refs and active_ref and active_ref in state:
        refs = [active_ref]
    return refs[:max_targets]


def active_context_path(repo_root: Path) -> Path:
    return repo_root / ACTIVE_CONTEXT_REL


def read_active_context(repo_root: Path) -> dict[str, Any] | None:
    path = active_context_path(repo_root)
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def write_active_context(repo_root: Path, payload: dict[str, Any]) -> None:
    path = active_context_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def clear_active_context(repo_root: Path) -> None:
    path = active_context_path(repo_root)
    try:
        path.unlink()
    except OSError:
        return


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_task_refs(*texts: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for text in texts:
        for match in _TASK_REF_RE.findall(text or ""):
            if match not in seen:
                seen.add(match)
                out.append(match)
    return out


def pick_active_task(
    state: dict[str, dict[str, Any]],
    *,
    actor_id: str,
    repository_id: str,
    any_actor: bool = False,
) -> dict[str, Any] | None:
    """Prefer in-progress mine tasks, else highest-priority open mine task."""
    filters: dict[str, Any] = {
        "include_terminal": False,
        "repository_id": repository_id,
    }
    if not any_actor:
        filters["mine_actor"] = actor_id

    in_progress = core.filter_and_sort(
        [t for t in state.values() if t.get("status") == "in_progress"],
        **filters,
    )
    if in_progress:
        return in_progress[0]

    open_tasks = core.filter_and_sort(state.values(), **filters)
    return open_tasks[0] if open_tasks else None


def build_active_payload(task: dict[str, Any], *, actor_id: str, repository_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "task_ref": task.get("task_ref", ""),
        "title": task.get("title", ""),
        "status": task.get("status", ""),
        "priority": task.get("priority", "normal"),
        "assignees": list(task.get("assignees") or []),
        "branch": task.get("branch", ""),
        "deployment": task.get("deployment", ""),
        "actor_id": actor_id,
        "repository_id": repository_id,
        "refreshed_at": _now_iso(),
    }


def format_preflight_message(
    *,
    open_tasks: list[dict[str, Any]],
    active: dict[str, Any] | None,
) -> str:
    lines: list[str] = []
    if active and active.get("task_ref"):
        ref = active["task_ref"]
        title = active.get("title", "")
        status = active.get("status", "open")
        branch = (active.get("branch") or "").strip()
        lines.append(
            f"Active Canon task for this session: {ref} ({status}) — {title}"
        )
        if branch:
            lines.append(f"  branch: {branch}")
        deploy = (active.get("deployment") or "").strip()
        if deploy:
            lines.append(f"  deployment: {deploy}")
        lines.append(
            "Memory capture and progress notes run automatically each turn "
            f"(task {ref}). Use canon task update for branch/deploy overrides."
        )
    if not open_tasks:
        return "\n".join(lines)

    lines.append(
        "You have %d open Canon task(s) for you in this repo:" % len(open_tasks)
    )
    active_ref = (active or {}).get("task_ref", "")
    shown = 0
    for t in open_tasks:
        ref = t.get("task_ref", "?")
        if ref == active_ref:
            continue
        prio = t.get("priority", "normal")
        tag = " !%s" % prio if prio in ("high", "urgent") else ""
        lines.append("  - %s: %s%s" % (ref, t.get("title", ""), tag))
        shown += 1
        if shown >= 9:
            break
    extra = len(open_tasks) - shown - (1 if active_ref else 0)
    if extra > 0:
        lines.append("  ... and %d more (canon task list --mine)" % extra)
    return "\n".join(lines)
