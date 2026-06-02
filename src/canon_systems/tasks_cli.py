"""`canon task` — create and track assignable work items.

Tasks let teammates write work for each other to pick up, scoped per repo,
per company, or across several repos. The command is **local-first** and
**fail-open**: it always works against on-disk NDJSON ledgers, and treats any
remote sync (S3) as best-effort enrichment that never blocks the local action.

Ledger routing
--------------
- ``repo`` scope     -> ``<repo>/.canon/tasks/ledger.ndjson`` (git-tracked, so
  repo tasks travel with the repo to every teammate who pulls).
- ``company`` /
  ``multi_repo`` scope -> ``<CANON_TASKS_HOME or ~/.canon/tasks>/<company_id>/ledger.ndjson``
  (machine-global, shared across repos; cross-machine via ``canon task sync``).

Each mutation also appends a canonical event to
``<repo>/.canon/memory/events.ndjson`` (best-effort) so tasks are discoverable
through the existing memory/synthesis plane and ``canon ask``.

Subcommands
-----------
``create``, ``list``, ``show``, ``update``, ``comment``, ``assign``,
``status``, ``close``, ``reopen``, ``sync``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from . import tasks as core
from . import tasks_remote as remote
from .shared import load_identity_context, load_repo_context, repo_root

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_ERROR = 4

_LEDGER_NAME = "ledger.ndjson"


# ---------------------------------------------------------------------------
# Impure boundary: clock + id generation (overridable for tests).
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    override = os.environ.get("CANON_TASKS_NOW", "").strip()
    if override:
        return override
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_event_id() -> str:
    # Nanosecond prefix (zero-padded, fixed width) makes event_ids sort
    # chronologically. Materialization breaks timestamp ties by event_id, so
    # this keeps rapid same-second mutations folding in the order they occurred.
    return f"evt_{time.time_ns():020d}_{uuid.uuid4().hex[:8]}"


def _new_task_ref(actor_id: str) -> str:
    slug = "".join(ch for ch in actor_id.lower() if ch.isalnum())[:16] or "anon"
    return f"tsk_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_{slug}_{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------------------
# Ledger paths + IO
# ---------------------------------------------------------------------------
def _global_tasks_home() -> Path:
    override = os.environ.get("CANON_TASKS_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".canon" / "tasks"


def _company_ledger_path(company_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in company_id) or "UNKNOWN"
    return _global_tasks_home() / safe / _LEDGER_NAME


def _repo_ledger_path(root: Path) -> Path:
    return root / ".canon" / "tasks" / _LEDGER_NAME


def _read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            out.append(parsed)
    return out


def _append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def _emit_canonical_event(root: Path, event: dict[str, Any], ctx: Any) -> None:
    """Best-effort mirror into the repo memory event log. Never raises."""
    try:
        events_path = root / ".canon" / "memory" / "events.ndjson"
        events_path.parent.mkdir(parents=True, exist_ok=True)
        canonical = {
            "schema_version": 1,
            "event_type": "task_activity",
            "timestamp": event.get("timestamp", _now_iso()),
            "company_id": event.get("company_id", getattr(ctx, "company_id", "")),
            "repository_id": event.get("repository_id", getattr(ctx, "repository_id", "")),
            "actor_id": event.get("actor_id", ""),
            "payload": {
                "task_ref": event.get("task_ref", ""),
                "task_event_type": event.get("event_type", ""),
                "task_event_id": event.get("event_id", ""),
                "scope": event.get("scope", ""),
            },
        }
        with events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(canonical, sort_keys=True) + "\n")
    except OSError:
        return


# ---------------------------------------------------------------------------
# Context resolution
# ---------------------------------------------------------------------------
class _Ctx:
    def __init__(self) -> None:
        self.root = repo_root()
        identity = load_identity_context()
        repo = load_repo_context(identity)
        self.actor_id = identity.actor_id
        self.actor_display = identity.display_name
        self.company_id = repo.company_id
        self.repository_id = repo.repository_id


def _combined_state(ctx: _Ctx) -> tuple[dict[str, dict[str, Any]], bool | None]:
    """Materialize repo + company ledgers, unioned with the server stream.

    Returns ``(state, remote_status)`` where ``remote_status`` is ``None`` when
    no server is configured, ``True`` when the server stream was folded in, and
    ``False`` when a server is configured but unreachable (fail-open to local).
    """
    streams: list[list[dict[str, Any]]] = [
        _read_ledger(_repo_ledger_path(ctx.root)),
        _read_ledger(_company_ledger_path(ctx.company_id)),
    ]
    remote_status: bool | None = None
    if remote.remote_base():
        fetched = remote.fetch_events(ctx.company_id)
        if fetched is None:
            remote_status = False
        else:
            remote_status = True
            streams.append(fetched)
    merged = core.dedupe_events(*streams)
    return core.materialize(merged), remote_status


def _load_all_for_repo(ctx: _Ctx) -> dict[str, dict[str, Any]]:
    """Materialize the union of repo + company ledgers (+ server) for the company."""
    state, _ = _combined_state(ctx)
    return state


def _ledger_for_scope(ctx: _Ctx, scope: str) -> Path:
    if scope == "repo":
        return _repo_ledger_path(ctx.root)
    return _company_ledger_path(ctx.company_id)


def _find_ledger_with_task(ctx: _Ctx, task_ref: str) -> tuple[Path, dict[str, Any]] | None:
    """Locate the cache ledger that owns ``task_ref`` and return (path, task).

    Uses the combined (local + server) view so a task that lives only on the
    server can still be mutated; the chosen local ledger acts as offline cache.
    """
    state, _ = _combined_state(ctx)
    task = state.get(task_ref)
    if task is None:
        return None
    return _ledger_for_scope(ctx, str(task.get("scope", "company"))), task


def _record_event(ctx: _Ctx, event: dict[str, Any], ledger: Path) -> tuple[bool | None, str]:
    """Append event to local cache + memory mirror, then push to the server.

    Returns ``(remote_ok, detail)``: ``remote_ok`` is ``None`` when no server is
    configured, else the push result. Local write always happens (fail-open).
    """
    _append_event(ledger, event)
    _emit_canonical_event(ctx.root, event, ctx)
    if not remote.remote_base():
        return None, ""
    ok, detail = remote.push_event(event)
    return ok, detail


def _warn_remote(remote_ok: bool | None, detail: str) -> None:
    if remote_ok is False:
        print(
            f"note: server task-plane unreachable ({detail}); recorded locally, "
            "will reconcile on next reachable write/read.",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def _cmd_create(ctx: _Ctx, args: argparse.Namespace) -> int:
    try:
        scope = core.normalize_scope(args.scope)
    except core.TaskError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    repositories: list[str] = []
    repository_id = ""
    if scope == "repo":
        repository_id = (args.repo or ctx.repository_id or "").strip()
    elif scope == "multi_repo":
        repositories = [r.strip() for r in (args.repos or []) if r.strip()]
        if not repositories:
            print("error: --scope multi-repo requires --repos r1,r2,...", file=sys.stderr)
            return EXIT_USAGE

    fields: dict[str, Any] = {"title": args.title}
    if args.body:
        fields["body"] = args.body
    if args.assignee:
        fields["assignees"] = args.assignee
    if args.label:
        fields["labels"] = args.label
    if args.priority:
        fields["priority"] = args.priority
    if args.due:
        fields["due"] = args.due
    fields["status"] = "open"

    task_ref = (args.task_ref or _new_task_ref(ctx.actor_id)).strip()
    try:
        event = core.make_event(
            event_type=core.EVENT_CREATED,
            event_id=_new_event_id(),
            task_ref=task_ref,
            timestamp=_now_iso(),
            actor_id=ctx.actor_id,
            actor_display=ctx.actor_display,
            company_id=ctx.company_id,
            scope=scope,
            repository_id=repository_id,
            repositories=repositories,
            fields=fields,
        )
    except core.TaskError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    ledger = _ledger_for_scope(ctx, scope)
    remote_ok, detail = _record_event(ctx, event, ledger)
    _warn_remote(remote_ok, detail)

    if args.json:
        print(json.dumps(
            {"task_ref": task_ref, "ledger": str(ledger), "remote": remote_ok},
            sort_keys=True,
        ))
    else:
        print(f"created {task_ref} ({core.render_scope({'scope': scope, 'repository_id': repository_id, 'repositories': repositories, 'company_id': ctx.company_id})})")
        print(f"  ledger: {ledger}")
    return EXIT_OK


def _mutate(
    ctx: _Ctx,
    task_ref: str,
    *,
    fields: dict[str, Any] | None = None,
    comment: str = "",
    event_type: str = core.EVENT_UPDATED,
) -> int:
    found = _find_ledger_with_task(ctx, task_ref)
    if found is None:
        print(f"error: task {task_ref} not found in repo or company ledger", file=sys.stderr)
        return EXIT_NOT_FOUND
    ledger, _task = found
    try:
        event = core.make_event(
            event_type=event_type,
            event_id=_new_event_id(),
            task_ref=task_ref,
            timestamp=_now_iso(),
            actor_id=ctx.actor_id,
            actor_display=ctx.actor_display,
            company_id=ctx.company_id,
            fields=fields or {},
            comment=comment,
        )
    except core.TaskError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    remote_ok, detail = _record_event(ctx, event, ledger)
    _warn_remote(remote_ok, detail)
    return EXIT_OK


def _cmd_update(ctx: _Ctx, args: argparse.Namespace) -> int:
    fields: dict[str, Any] = {}
    if args.title is not None:
        fields["title"] = args.title
    if args.body is not None:
        fields["body"] = args.body
    if args.status:
        fields["status"] = args.status
    if args.priority:
        fields["priority"] = args.priority
    if args.due is not None:
        fields["due"] = args.due
    if args.branch is not None:
        fields["branch"] = args.branch
    if args.deployment is not None:
        fields["deployment"] = args.deployment
    if args.label:
        fields["labels"] = args.label
    if args.assignee:
        fields["assignees"] = args.assignee
    note = (getattr(args, "note", "") or "").strip()
    if not fields and not note:
        print(
            "error: nothing to update (pass --status/--assignee/--branch/"
            "--deployment/--note/...)",
            file=sys.stderr,
        )
        return EXIT_USAGE
    # A note attaches progress as a comment in the same logical update so branch/
    # deployment changes carry their "why" alongside the field change.
    if note and fields:
        _mutate(ctx, args.task_ref, comment=note, event_type=core.EVENT_COMMENTED)
    rc = _mutate(ctx, args.task_ref, fields=fields) if fields else _mutate(
        ctx, args.task_ref, comment=note, event_type=core.EVENT_COMMENTED
    )
    if rc == EXIT_OK and not args.json:
        print(f"updated {args.task_ref}")
    elif rc == EXIT_OK:
        print(json.dumps({"task_ref": args.task_ref, "updated": sorted(fields)}, sort_keys=True))
    return rc


def _cmd_comment(ctx: _Ctx, args: argparse.Namespace) -> int:
    text = args.text.strip()
    if not text:
        print("error: empty comment", file=sys.stderr)
        return EXIT_USAGE
    rc = _mutate(ctx, args.task_ref, comment=text, event_type=core.EVENT_COMMENTED)
    if rc == EXIT_OK:
        print(f"commented on {args.task_ref}")
    return rc


def _cmd_assign(ctx: _Ctx, args: argparse.Namespace) -> int:
    found = _find_ledger_with_task(ctx, args.task_ref)
    if found is None:
        print(f"error: task {args.task_ref} not found", file=sys.stderr)
        return EXIT_NOT_FOUND
    _, task = found
    current = set(task.get("assignees", []))
    if args.replace:
        new_assignees = set(args.actor)
    else:
        new_assignees = current | set(args.actor)
    rc = _mutate(ctx, args.task_ref, fields={"assignees": sorted(new_assignees)})
    if rc == EXIT_OK:
        print(f"assigned {args.task_ref} -> {', '.join(sorted(new_assignees)) or 'unassigned'}")
    return rc


def _cmd_status(ctx: _Ctx, args: argparse.Namespace) -> int:
    rc = _mutate(ctx, args.task_ref, fields={"status": args.new_status})
    if rc == EXIT_OK:
        print(f"{args.task_ref} -> {core.normalize_status(args.new_status)}")
    return rc


def _cmd_close(ctx: _Ctx, args: argparse.Namespace) -> int:
    status = "cancelled" if args.cancel else "done"
    fields: dict[str, Any] = {"status": status}
    rc = _mutate(ctx, args.task_ref, fields=fields, comment=args.comment or "")
    if rc == EXIT_OK:
        print(f"{args.task_ref} -> {status}")
    return rc


def _cmd_reopen(ctx: _Ctx, args: argparse.Namespace) -> int:
    rc = _mutate(ctx, args.task_ref, fields={"status": "open"})
    if rc == EXIT_OK:
        print(f"{args.task_ref} -> open")
    return rc


def _cmd_show(ctx: _Ctx, args: argparse.Namespace) -> int:
    state = _load_all_for_repo(ctx)
    task = state.get(args.task_ref)
    if task is None:
        print(f"error: task {args.task_ref} not found", file=sys.stderr)
        return EXIT_NOT_FOUND
    if args.json:
        print(json.dumps(task, sort_keys=True))
    else:
        print(core.render_task_detail(task))
    return EXIT_OK


def _cmd_list(ctx: _Ctx, args: argparse.Namespace) -> int:
    state = _load_all_for_repo(ctx)
    filters: dict[str, Any] = {
        "include_terminal": bool(args.all or args.status),
    }
    if args.status:
        filters["status"] = args.status
    if args.scope:
        filters["scope"] = args.scope
    if args.label:
        filters["label"] = args.label
    if args.assignee:
        filters["assignee"] = args.assignee
    if args.mine:
        filters["mine_actor"] = ctx.actor_id
    if not args.all_repos:
        # Default: only tasks relevant to the current repo (repo + multi-repo
        # touching it + all company-scoped tasks).
        filters["repository_id"] = ctx.repository_id

    selected = core.filter_and_sort(state.values(), **filters)
    if args.json:
        print(json.dumps(selected, sort_keys=True))
        return EXIT_OK
    if not selected:
        print("no tasks match")
        return EXIT_OK
    for task in selected:
        print(core.render_task_line(task))
    return EXIT_OK


def _cmd_next(ctx: _Ctx, args: argparse.Namespace) -> int:
    """Pick the single highest-priority open task — 'what should I do next?'.

    Defaults to work assigned to or authored by me in the current repo; pass
    ``--any`` to consider every open task touching this repo. This is the
    agent's entrypoint: it reads server truth, returns one task with full
    context (branch, deployment, comments), and the agent then works + updates it.
    """
    state, _ = _combined_state(ctx)
    filters: dict[str, Any] = {"include_terminal": False}
    if not args.all_repos:
        filters["repository_id"] = ctx.repository_id
    if not args.any:
        filters["mine_actor"] = ctx.actor_id
    if args.assignee:
        filters["assignee"] = args.assignee
    selected = core.filter_and_sort(state.values(), **filters)
    if not selected:
        if args.json:
            print(json.dumps({"task": None}, sort_keys=True))
        else:
            print("no open tasks match — you're clear.")
        return EXIT_OK
    top = selected[0]
    if args.json:
        print(json.dumps({"task": top}, sort_keys=True))
    else:
        print(core.render_task_detail(top))
    return EXIT_OK


def _cmd_sync(ctx: _Ctx, args: argparse.Namespace) -> int:
    """Push local events to the server (if configured), then best-effort S3 push/pull.

    When ``CANON_TASKS_API_URL``/``CANON_STATE_API_URL`` is set this backfills the
    server task plane with any local-only events (e.g. tasks imported before the
    server existed) and pulls the server stream back into the local cache. S3
    sync remains a fallback transport for environments without state-api.
    """
    if remote.remote_base():
        streams: list[list[dict[str, Any]]] = [
            _read_ledger(_repo_ledger_path(ctx.root)),
            _read_ledger(_company_ledger_path(ctx.company_id)),
        ]
        if getattr(args, "scan_localwork", False):
            lw = Path(
                os.environ.get("CANON_LOCALWORK_ROOT", str(Path.home() / "localwork"))
            ).expanduser()
            if lw.is_dir():
                for ledger in sorted(lw.glob("*/.canon/tasks/ledger.ndjson")):
                    streams.append(_read_ledger(ledger))
        local_events = core.dedupe_events(*streams)
        pushed = 0
        failed = 0
        for ev in local_events:
            if not str(ev.get("company_id", "")).strip():
                ev = {**ev, "company_id": ctx.company_id}
            ok, _detail = remote.push_event(ev)
            if ok:
                pushed += 1
            else:
                failed += 1
        fetched = remote.fetch_events(ctx.company_id)
        if fetched is not None:
            merged = core.dedupe_events(
                _read_ledger(_company_ledger_path(ctx.company_id)), fetched
            )
            cache = _company_ledger_path(ctx.company_id)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(
                "".join(json.dumps(ev, sort_keys=True) + "\n" for ev in merged),
                encoding="utf-8",
            )
        print(
            f"server sync: pushed {pushed} event(s)"
            + (f", {failed} failed" if failed else "")
            + (f", pulled {len(fetched)} from server" if fetched is not None else
               ", server unreachable for pull")
        )
        if not failed:
            return EXIT_OK

    bucket = (os.environ.get("CANON_TASKS_BUCKET", "") or "").strip()
    if not bucket:
        print(
            "sync: no CANON_TASKS_BUCKET configured; tasks remain local-only.\n"
            "  Set CANON_TASKS_BUCKET (and optional CANON_TASKS_PREFIX, default canon/tasks)\n"
            "  to enable cross-machine sync of company/multi-repo tasks.",
            file=sys.stderr,
        )
        return EXIT_OK
    prefix = (os.environ.get("CANON_TASKS_PREFIX", "") or "canon/tasks").strip().strip("/")
    safe_company = "".join(
        ch if ch.isalnum() or ch in "-_." else "_" for ch in ctx.company_id
    ) or "UNKNOWN"
    key = f"{prefix}/{safe_company}/{_LEDGER_NAME}"
    local_path = _company_ledger_path(ctx.company_id)

    try:
        import boto3  # type: ignore
    except Exception as exc:  # pragma: no cover - import guard
        print(f"sync: boto3 unavailable ({exc}); skipping remote sync.", file=sys.stderr)
        return EXIT_OK

    try:
        s3 = boto3.client("s3")
        remote_events: list[dict[str, Any]] = []
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            body = obj["Body"].read().decode("utf-8")
            for line in body.splitlines():
                line = line.strip()
                if line:
                    try:
                        parsed = json.loads(line)
                        if isinstance(parsed, dict):
                            remote_events.append(parsed)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            remote_events = []  # first sync / missing object is fine

        local_events = _read_ledger(local_path)
        merged = core.dedupe_events(local_events, remote_events)
        body_out = "".join(json.dumps(ev, sort_keys=True) + "\n" for ev in merged)

        # Write merged set back to local and remote (idempotent set-union).
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(body_out, encoding="utf-8")
        if not args.pull_only:
            s3.put_object(Bucket=bucket, Key=key, Body=body_out.encode("utf-8"))

        print(
            f"sync ok: {len(local_events)} local + {len(remote_events)} remote "
            f"-> {len(merged)} merged events (s3://{bucket}/{key})"
        )
        return EXIT_OK
    except Exception as exc:
        print(f"sync: remote sync failed ({exc}); local tasks unaffected.", file=sys.stderr)
        return EXIT_OK


# ---------------------------------------------------------------------------
# Parser + dispatch
# ---------------------------------------------------------------------------
def _csv_list(value: str) -> list[str]:
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon task",
        description="Create and track assignable tasks per repo, per company, or across repos.",
    )
    sub = p.add_subparsers(dest="task_command", required=True)

    c = sub.add_parser("create", help="Create a new task.")
    c.add_argument("title", help="Short task title.")
    c.add_argument("--body", default="", help="Longer description.")
    c.add_argument(
        "--scope",
        default="repo",
        help="repo (default) | company | multi-repo.",
    )
    c.add_argument("--repo", default="", help="repository_id for --scope repo (defaults to current).")
    c.add_argument("--repos", type=_csv_list, default=[], help="Comma list for --scope multi-repo.")
    c.add_argument(
        "--assignee",
        action="append",
        default=[],
        help="actor_id to assign (repeatable).",
    )
    c.add_argument("--label", action="append", default=[], help="Label (repeatable).")
    c.add_argument("--priority", default="", help="low|normal|high|urgent.")
    c.add_argument("--due", default="", help="Free-form due date (e.g. 2026-06-15).")
    c.add_argument("--task-ref", default="", help="Explicit task_ref (else auto-generated).")
    c.add_argument("--json", action="store_true")

    ls = sub.add_parser("list", help="List tasks relevant to the current repo.")
    ls.add_argument("--status", default="", help="Filter by status.")
    ls.add_argument("--scope", default="", help="Filter by scope.")
    ls.add_argument("--assignee", default="", help="Filter by assignee actor_id.")
    ls.add_argument("--label", default="", help="Filter by label.")
    ls.add_argument("--mine", action="store_true", help="Only tasks assigned to or authored by me.")
    ls.add_argument("--all", action="store_true", help="Include done/cancelled tasks.")
    ls.add_argument("--all-repos", action="store_true", help="Don't restrict to the current repo.")
    ls.add_argument("--json", action="store_true")

    nx = sub.add_parser("next", help="Show the single highest-priority open task to work on.")
    nx.add_argument("--any", action="store_true", help="Not just mine: any open task in this repo.")
    nx.add_argument("--all-repos", action="store_true", help="Don't restrict to the current repo.")
    nx.add_argument("--assignee", default="", help="Pick the next task for a specific actor_id.")
    nx.add_argument("--json", action="store_true")

    sh = sub.add_parser("show", help="Show one task in detail.")
    sh.add_argument("task_ref")
    sh.add_argument("--json", action="store_true")

    up = sub.add_parser("update", help="Update fields on a task.")
    up.add_argument("task_ref")
    up.add_argument("--title", default=None)
    up.add_argument("--body", default=None)
    up.add_argument("--status", default="")
    up.add_argument("--priority", default="")
    up.add_argument("--due", default=None)
    up.add_argument("--branch", default=None, help="Active branch for this task.")
    up.add_argument("--deployment", default=None, help="Deploy target/URL for this task.")
    up.add_argument("--note", default="", help="Progress note recorded as a comment.")
    up.add_argument("--label", action="append", default=[])
    up.add_argument("--assignee", action="append", default=[])
    up.add_argument("--json", action="store_true")

    cm = sub.add_parser("comment", help="Add a comment to a task.")
    cm.add_argument("task_ref")
    cm.add_argument("text")

    asg = sub.add_parser("assign", help="Assign a task to one or more actors.")
    asg.add_argument("task_ref")
    asg.add_argument("actor", nargs="+", help="actor_id(s) to assign.")
    asg.add_argument("--replace", action="store_true", help="Replace assignees instead of adding.")

    st = sub.add_parser("status", help="Set a task's status.")
    st.add_argument("task_ref")
    st.add_argument("new_status", help="open|in_progress|blocked|done|cancelled.")

    cl = sub.add_parser("close", help="Mark a task done (or --cancel).")
    cl.add_argument("task_ref")
    cl.add_argument("--cancel", action="store_true", help="Cancel instead of completing.")
    cl.add_argument("--comment", default="", help="Optional closing comment.")

    ro = sub.add_parser("reopen", help="Reopen a closed task.")
    ro.add_argument("task_ref")

    sy = sub.add_parser(
        "sync",
        help="Push local events to state-api and/or S3; pull server stream into company cache.",
    )
    sy.add_argument("--pull-only", action="store_true", help="Merge remote into local; don't push.")
    sy.add_argument(
        "--scan-localwork",
        action="store_true",
        help="Also push events from every <localwork>/*/.canon/tasks/ledger.ndjson "
        "(backfill multi-repo imports before server was live).",
    )

    return p


_HANDLERS = {
    "create": _cmd_create,
    "list": _cmd_list,
    "next": _cmd_next,
    "show": _cmd_show,
    "update": _cmd_update,
    "comment": _cmd_comment,
    "assign": _cmd_assign,
    "status": _cmd_status,
    "close": _cmd_close,
    "reopen": _cmd_reopen,
    "sync": _cmd_sync,
}


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    av = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parser.parse_args(av)
    except SystemExit as exc:
        code = exc.code
        return EXIT_OK if code in (0, None) else EXIT_USAGE

    try:
        ctx = _Ctx()
    except Exception as exc:  # pragma: no cover - context resolution guard
        print(f"error: could not resolve repo/identity context: {exc}", file=sys.stderr)
        return EXIT_ERROR

    handler = _HANDLERS.get(args.task_command)
    if handler is None:
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    return handler(ctx, args)


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
