"""canon synth publish: idempotent diff-only driver for SynthesisPublisher.

Reads canonical events from a JSONL file, renders a deterministic VaultBundle
via backend/synthesis generate_vault, and publishes to S3 with content-hash
diff-only writes. Safe to invoke repeatedly.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_TRANSPORT = 2
EXIT_USAGE = 4

# --- E5-T5 show-verb exit-code catalog -------------------------------------
# NOTE: coexists with legacy EXIT_OK / EXIT_USAGE / EXIT_TRANSPORT above
# (publish tests import the legacy names). The `show` subverb MUST use only
# the SHOW_EXIT_* names below.
SHOW_EXIT_OK = 0
SHOW_EXIT_USAGE = 2
SHOW_EXIT_NOT_FOUND = 3
SHOW_EXIT_DENIED = 4
SHOW_EXIT_TRANSPORT = 5

_REQUIRED_EVENT_FIELDS = (
    "schema_version",
    "event_id",
    "parent_event_id",
    "event_type",
    "company_id",
    "repository_id",
    "plan_id",
    "task_id",
    "handoff_id",
    "agent_name",
    "agent_run_id",
    "actor_id",
    "model",
    "timestamp",
    "state_version",
    "payload",
)


def _ensure_repo_backend_import_path() -> None:
    """Make `canon_backend_shared` + `synthesis` importable in monorepo dev/test."""
    root = Path(os.environ.get("CANON_SYSTEMS_REPO_ROOT", str(Path.cwd()))).resolve()
    for sub in ("backend/shared", "backend/synthesis"):
        p = root / sub
        if p.is_dir():
            s = str(p)
            if s not in sys.path:
                sys.path.insert(0, s)


def _s3_client_factory(aws_region: str, aws_profile: str) -> Any:
    """Return a boto3 S3 client. Monkeypatched in tests to return a dict-fake."""
    import boto3  # lazy import to keep --help cheap and avoid hard dep at import-time

    session = boto3.Session(
        profile_name=aws_profile or None,
        region_name=aws_region or None,
    )
    return session.client("s3")


def _load_events(path: Path) -> list[Any]:
    from canon_backend_shared.events import CanonicalEvent

    raw = path.read_text(encoding="utf-8")
    out: list[Any] = []
    for ln_no, ln in enumerate(raw.splitlines(), start=1):
        s = ln.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {ln_no}: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"line {ln_no}: expected JSON object")
        for k in _REQUIRED_EVENT_FIELDS:
            if k not in obj:
                raise ValueError(f"line {ln_no}: missing field '{k}'")
        if obj["schema_version"] != 1:
            raise ValueError(f"line {ln_no}: schema_version must be 1")
        ev = CanonicalEvent(
            schema_version=int(obj["schema_version"]),
            event_id=str(obj["event_id"]),
            parent_event_id=str(obj["parent_event_id"]),
            event_type=str(obj["event_type"]),
            company_id=str(obj["company_id"]),
            repository_id=str(obj["repository_id"]),
            plan_id=str(obj["plan_id"]),
            task_id=str(obj["task_id"]),
            handoff_id=str(obj["handoff_id"]),
            agent_name=str(obj["agent_name"]),
            agent_run_id=str(obj["agent_run_id"]),
            actor_id=str(obj["actor_id"]),
            model=str(obj["model"]),
            timestamp=str(obj["timestamp"]),
            state_version=int(obj["state_version"]),
            payload=dict(obj["payload"]),
        )
        out.append(ev)
    return out


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon synth",
        description="Synthesis vault publishing driver (internal).",
    )
    sub = p.add_subparsers(dest="subcommand", required=True)

    pub = sub.add_parser("publish", help="Publish vault bundle to S3 (idempotent, diff-only).")
    pub.add_argument("--events-file", required=True)
    pub.add_argument("--plan-id", required=True)
    pub.add_argument("--company-id", required=True)
    pub.add_argument("--repository-id", required=True)
    pub.add_argument("--cutoff-timestamp", required=True, help="ISO-8601 Z; only events strictly after are included.")
    pub.add_argument("--bucket", required=True)
    pub.add_argument("--prefix", required=True, help="S3 key prefix (e.g. 'vaults/c1/r1').")
    pub.add_argument("--task-id", default=None)
    pub.add_argument("--dry-run", action="store_true")
    pub.add_argument("--aws-region", default="")
    pub.add_argument("--aws-profile", default="")

    show = sub.add_parser("show", help="Stream Obsidian vault markdown from S3 (read-only).")
    show.add_argument("--plan-id", default=None)
    show.add_argument("--task-id", default=None)
    show.add_argument("--company-id", default=None)
    show.add_argument("--repository-id", default=None)
    show.add_argument("--cutoff-ts", default=None, help="ISO-8601 Z; exclude pages with frontmatter timestamp strictly after this.")
    show.add_argument("--format", choices=("markdown", "json"), default="markdown")
    show.add_argument("--bucket", default=None)
    show.add_argument("--prefix", default=None, help="S3 key prefix (e.g. 'vaults/c1/r1').")
    show.add_argument("--aws-region", default="")
    show.add_argument("--aws-profile", default="")
    show.add_argument("--event-log", default=None)
    show.add_argument("--dry-run", action="store_true")
    return p


def _print_envelope(envelope: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(envelope, sort_keys=True) + "\n")
    sys.stdout.flush()


def _print_error(payload: dict[str, Any]) -> None:
    sys.stderr.write(json.dumps(payload, sort_keys=True) + "\n")
    sys.stderr.flush()


_SHOW_PHASE_FILES: tuple[str, ...] = (
    "scoper.md",
    "cursor-pilot.md",
    "implementer.md",
    "qa-gate.md",
    "release-orchestrator.md",
)


# <READ-ONLY-REGION-BEGIN id="synth-show" reason="AC9 forbidden-method scan target">
#   Must not reference: put_object, put_object_acl, put_object_tagging,
#   put_object_retention, put_object_legal_hold, put_bucket_policy,
#   put_bucket_acl, delete_object, delete_objects, delete_object_tagging,
#   copy_object, copy, upload_file, upload_fileobj, upload_part,
#   upload_part_copy, create_multipart_upload, complete_multipart_upload,
#   abort_multipart_upload, restore_object, write_get_object_response.


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso_z(value: str) -> datetime:
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _extract_frontmatter_timestamp(body: bytes) -> str | None:
    text = body.decode("utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    for line in block.splitlines():
        m = re.match(r"^\s*timestamp:\s+(.+)$", line)
        if not m:
            continue
        val = m.group(1).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            return val[1:-1]
        return val
    return None


def _extract_event_ids(body: bytes) -> list[str]:
    text = body.decode("utf-8", errors="replace")
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    block = text[3:end]
    m = re.search(r"event_ids:\s*\[([^\]]*)\]", block)
    if m:
        inner = m.group(1)
        if inner.strip():
            return re.findall(r'"([^"]+)"', inner) or re.findall(r"'([^']+)'", inner) or [x.strip() for x in inner.split(",") if x.strip()]
    m2 = re.match(r"^\s*event_id:\s+(.+)$", block, re.MULTILINE)
    if m2:
        val = m2.group(1).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            return [val[1:-1]]
        if val and val not in ("null", "~"):
            return [val]
    in_list = False
    acc: list[str] = []
    for line in block.splitlines():
        if re.match(r"^\s*event_ids:\s*$", line):
            in_list = True
            continue
        if in_list:
            mo = re.match(r'^\s*-\s+"([^"]+)"\s*$', line)
            if mo:
                acc.append(mo.group(1))
                continue
            mo2 = re.match(r"^\s*-\s+'([^']+)'\s*$", line)
            if mo2:
                acc.append(mo2.group(1))
                continue
            if line.strip() and not line.lstrip().startswith("-"):
                in_list = False
    if acc:
        return acc
    return []


def _apply_cutoff_filter(body: bytes, cutoff_ts: str | None) -> bool:
    """True = include; False = exclude (frontmatter timestamp > cutoff)."""
    if not cutoff_ts:
        return True
    ts = _extract_frontmatter_timestamp(body)
    if not ts:
        return True
    try:
        t_page = _parse_iso_z(ts)
        t_cut = _parse_iso_z(cutoff_ts)
        if t_page.tzinfo is None:
            t_page = t_page.replace(tzinfo=timezone.utc)
        if t_cut.tzinfo is None:
            t_cut = t_cut.replace(tzinfo=timezone.utc)
    except (ValueError, OSError, TypeError):
        return True
    return t_page <= t_cut


def _page_kind(slug: str, plan_id: str) -> str:
    if slug == f"plans/{plan_id}/index.md":
        return "plan"
    if slug.endswith("/index.md") and f"plans/{plan_id}/tasks/" in slug:
        return "task"
    base = Path(slug).name.replace(".md", "")
    return base


def _task_ids_in_vault(all_pages: set[str], plan_id: str) -> list[str]:
    pfx = f"plans/{plan_id}/tasks/"
    tids: set[str] = set()
    for rel in all_pages:
        if rel.startswith(pfx):
            rest = rel[len(pfx) :]
            part = rest.split("/")[0]
            if part:
                tids.add(part)
    return sorted(tids)


def _canonical_stream_order(plan_id: str, all_pages: set[str], task_filter: str | None) -> list[str]:
    plan_idx = f"plans/{plan_id}/index.md"
    tids = _task_ids_in_vault(all_pages, plan_id)
    if task_filter is not None:
        tids = [task_filter]
    out: list[str] = [plan_idx]
    for tid in tids:
        tpre = f"plans/{plan_id}/tasks/{tid}/"
        for name in (f"index.md",) + _SHOW_PHASE_FILES:
            s = f"{tpre}{name}"
            if s in all_pages:
                out.append(s)
    return out


def _resolve_required_ids(args: argparse.Namespace) -> dict[str, Any]:
    def pick(flag: str | None, env: str) -> str | None:
        raw = (flag or "").strip() if flag is not None else ""
        if raw:
            return raw
        v = os.environ.get(env, "").strip()
        return v or None

    out = {
        "plan_id": pick(getattr(args, "plan_id", None), "CANON_PLAN_ID"),
        "company_id": pick(getattr(args, "company_id", None), "CANON_COMPANY_ID"),
        "repository_id": pick(getattr(args, "repository_id", None), "CANON_REPOSITORY_ID"),
        "bucket": pick(getattr(args, "bucket", None), "CANON_VAULT_BUCKET"),
        "prefix": pick(getattr(args, "prefix", None), "CANON_VAULT_PREFIX"),
        "task_id": pick(getattr(args, "task_id", None), "CANON_TASK_ID"),
        "cutoff_ts": pick(getattr(args, "cutoff_ts", None), "CANON_SYNTH_CUTOFF_TS"),
        "event_log": pick(getattr(args, "event_log", None), "CANON_EVENT_LOG"),
    }
    required_spec = (
        ("plan_id", "plan_id", "--plan-id", "CANON_PLAN_ID"),
        ("company_id", "company_id", "--company-id", "CANON_COMPANY_ID"),
        ("repository_id", "repository_id", "--repository-id", "CANON_REPOSITORY_ID"),
        ("bucket", "bucket", "--bucket", "CANON_VAULT_BUCKET"),
        ("prefix", "prefix", "--prefix", "CANON_VAULT_PREFIX"),
    )
    for key, name, fl, env in required_spec:
        if not out.get(key):
            raise ValueError(f"missing required identifier: {name} (set {fl} or {env})")
    return out


def _new_show_event(
    *,
    event_id: str,
    plan_id: str,
    company_id: str,
    repository_id: str,
    task_id: str | None,
    cutoff_ts: str | None,
    bucket: str,
    prefix: str,
    page_count: int,
    byte_count: int,
    result: str,
    format_name: str,
) -> Any:
    from canon_backend_shared.events import CanonicalEvent

    p: dict[str, Any] = {
        "plan_id": plan_id,
        "task_id": task_id,
        "cutoff_ts": cutoff_ts,
        "bucket": bucket,
        "prefix": prefix,
        "page_count": page_count,
        "byte_count": byte_count,
        "result": result,
        "format": format_name,
    }
    return CanonicalEvent(
        schema_version=1,
        event_id=event_id,
        parent_event_id="",
        event_type="synth_show",
        company_id=company_id,
        repository_id=repository_id,
        plan_id=plan_id,
        task_id=task_id or "",
        handoff_id=f"synth-show:{plan_id}",
        agent_name="synth-cli",
        agent_run_id=event_id[:8],
        actor_id="cli",
        model="synth_show",
        timestamp=_utc_iso_z(),
        state_version=1,
        payload=p,
    )


def _emit_retrieval_event(
    *,
    byte_count: int,
    ctx: dict[str, Any],
) -> None:
    from .retrieval_telemetry import RetrievalBreakdown, SourceCounts, build_retrieval_breakdown_event
    from .stall_watchdog import _emit_event

    eid = str(uuid.uuid4())
    br = build_retrieval_breakdown_event(
        event_id=eid,
        parent_event_id="",
        company_id=str(ctx.get("company_id", "")),
        repository_id=str(ctx.get("repository_id", "")),
        plan_id=str(ctx.get("plan_id", "")),
        task_id=str(ctx.get("task_id") or ""),
        handoff_id=f"synth-show:{ctx.get('plan_id', '')}",
        agent_name="synth-cli",
        agent_run_id=eid[:8],
        actor_id="cli",
        model="synth_show",
        timestamp=_utc_iso_z(),
        state_version=1,
        breakdown=RetrievalBreakdown(
            graph=SourceCounts(0, 0),
            state=SourceCounts(0, 0),
            canonical=SourceCounts(0, byte_count),
            file=SourceCounts(0, 0),
        ),
    )
    _emit_event(br, event_log=ctx.get("event_log_path"), dry_run=bool(ctx.get("dry_run")))


def _emit_synth_show_event(
    *,
    ctx: dict[str, Any],
    page_count: int,
    byte_count: int,
    result: str,
    format_name: str,
) -> None:
    from .stall_watchdog import _emit_event

    ev = _new_show_event(
        event_id=str(uuid.uuid4()),
        plan_id=str(ctx["plan_id"]),
        company_id=str(ctx["company_id"]),
        repository_id=str(ctx["repository_id"]),
        task_id=ctx.get("task_id") if ctx.get("task_id") is not None else None,
        cutoff_ts=ctx.get("cutoff_ts"),
        bucket=str(ctx["bucket"]),
        prefix=str(ctx["prefix"]),
        page_count=page_count,
        byte_count=byte_count,
        result=result,
        format_name=format_name,
    )
    _emit_event(ev, event_log=ctx.get("event_log_path"), dry_run=bool(ctx.get("dry_run")))


def _render_markdown_stream(
    slugs: list[str], reader: Any, sys_stdout: Any, *, cutoff_ts: str | None
) -> tuple[int, int]:
    npg = 0
    nbytes = 0
    for slug in slugs:
        b = reader.read_page(slug)
        if not _apply_cutoff_filter(b, cutoff_ts):
            continue
        npg += 1
        nbytes += len(b)
        s = b.decode("utf-8", errors="replace")
        chunk = s if s.endswith("\n") else s + "\n"
        sys_stdout.write(chunk)
        sys_stdout.flush()
    return npg, nbytes


def _render_json_envelope(
    *,
    slugs: list[str],
    reader: Any,
    plan_id: str,
    task_scope: str | None,
    bucket: str,
    prefix: str,
    cutoff_ts: str | None,
    ctx: dict[str, Any],
) -> tuple[str, int, int]:
    from .retrieval_telemetry import RetrievalBreakdown, SourceCounts, build_retrieval_breakdown_event
    from .synth_show_reader import NotFound

    pages_out: list[dict[str, Any]] = []
    byte_count = 0
    for slug in slugs:
        try:
            b = reader.read_page(slug)
        except NotFound:
            continue
        if not _apply_cutoff_filter(b, cutoff_ts):
            continue
        md = b.decode("utf-8", errors="replace")
        eids = _extract_event_ids(b)
        kind = _page_kind(slug, plan_id)
        pages_out.append(
            {
                "slug": slug,
                "kind": kind,
                "markdown": md,
                "event_ids": eids,
            }
        )
        byte_count += len(b)

    page_count = len(pages_out)
    eid = str(uuid.uuid4())
    rbe = build_retrieval_breakdown_event(
        event_id=eid,
        parent_event_id="",
        company_id=str(ctx["company_id"]),
        repository_id=str(ctx["repository_id"]),
        plan_id=plan_id,
        task_id=str(ctx.get("task_id") or ""),
        handoff_id=f"synth-show:{plan_id}",
        agent_name="synth-cli",
        agent_run_id=eid[:8],
        actor_id="cli",
        model="synth_show",
        timestamp=_utc_iso_z(),
        state_version=1,
        breakdown=RetrievalBreakdown(
            graph=SourceCounts(0, 0),
            state=SourceCounts(0, 0),
            canonical=SourceCounts(0, byte_count),
            file=SourceCounts(0, 0),
        ),
    )
    env: dict[str, Any] = {
        "schema_version": 1,
        "plan_id": plan_id,
        "task_id": task_scope,
        "cutoff_ts": cutoff_ts,
        "bucket": bucket,
        "prefix": prefix,
        "pages": pages_out,
        "retrieval_breakdown": dict(rbe.payload),
        "page_count": page_count,
        "byte_count": byte_count,
    }
    return json.dumps(env, sort_keys=True, ensure_ascii=True) + "\n", page_count, byte_count


def _show(args: argparse.Namespace) -> int:
    from botocore.exceptions import ClientError

    from .shared import ensure_layered_memory_env
    from .stall_watchdog import _DEFAULT_EVENT_LOG
    from .synth_show_reader import AccessDenied, NotFound, SynthShowReader

    ensure_layered_memory_env()
    try:
        rctx = _resolve_required_ids(args)
    except ValueError as exc:
        _print_error({"error": "usage", "detail": str(exc)})
        stub: dict[str, Any] = {
            "plan_id": "",
            "company_id": "",
            "repository_id": "",
            "bucket": "",
            "prefix": "",
            "task_id": None,
            "event_log_path": (None if args.dry_run else Path(_DEFAULT_EVENT_LOG)),
            "dry_run": bool(args.dry_run),
        }
        _emit_retrieval_event(byte_count=0, ctx=stub)
        _emit_synth_show_event(
            ctx=stub, page_count=0, byte_count=0, result="error", format_name=str(args.format)
        )
        return SHOW_EXIT_USAGE

    rctx["dry_run"] = bool(args.dry_run)
    elog = rctx.get("event_log")
    if args.dry_run:
        rctx["event_log_path"] = None
    else:
        rctx["event_log_path"] = Path(elog) if elog else Path(_DEFAULT_EVENT_LOG)

    plan_id = str(rctx["plan_id"])
    cutoff = rctx.get("cutoff_ts")
    tid = rctx.get("task_id")
    if isinstance(tid, str) and tid.strip():
        task_filter = tid.strip()
    else:
        task_filter = None
    rctx["task_id"] = task_filter

    fmt = str(args.format)
    out = sys.stdout

    try:
        client = _s3_client_factory(getattr(args, "aws_region", "") or "", getattr(args, "aws_profile", "") or "")
    except Exception as exc:  # noqa: BLE001
        _print_error({"error": "transport", "detail": f"s3_factory: {exc!r}"})
        rctx2 = {**rctx, "event_log_path": rctx.get("event_log_path")}
        _emit_retrieval_event(byte_count=0, ctx=rctx2)
        _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="error", format_name=fmt)
        return SHOW_EXIT_TRANSPORT

    reader = SynthShowReader(bucket=str(rctx["bucket"]), prefix=str(rctx["prefix"]), s3_client=client)

    plan_idx = f"plans/{plan_id}/index.md"
    try:
        reader.read_page(plan_idx)
    except NotFound:
        _print_error(
            {
                "error": "not_found",
                "detail": f"no vault rendered for plan_id={plan_id} (prefix={rctx['prefix']})",
            }
        )
        rctx2 = {**rctx, "event_log_path": rctx.get("event_log_path")}
        _emit_retrieval_event(byte_count=0, ctx=rctx2)
        _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="not_found", format_name=fmt)
        return SHOW_EXIT_NOT_FOUND
    except AccessDenied as e:
        _print_error({"error": "denied", "detail": f"s3 access denied: {e.op}"})
        rctx2 = {**rctx, "event_log_path": rctx.get("event_log_path")}
        _emit_retrieval_event(byte_count=0, ctx=rctx2)
        _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="denied", format_name=fmt)
        return SHOW_EXIT_DENIED
    except ClientError as e:
        _print_error({"error": "transport", "detail": f"{type(e).__name__}: {e!s}"})
        rctx2 = {**rctx, "event_log_path": rctx.get("event_log_path")}
        _emit_retrieval_event(byte_count=0, ctx=rctx2)
        _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="error", format_name=fmt)
        return SHOW_EXIT_TRANSPORT

    try:
        all_pages_list = reader.list_pages()
    except AccessDenied as e:
        _print_error({"error": "denied", "detail": f"s3 access denied: {e.op}"})
        rctx2 = {**rctx, "event_log_path": rctx.get("event_log_path")}
        _emit_retrieval_event(byte_count=0, ctx=rctx2)
        _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="denied", format_name=fmt)
        return SHOW_EXIT_DENIED
    except ClientError as e:
        _print_error({"error": "transport", "detail": f"{type(e).__name__}: {e!s}"})
        rctx2 = {**rctx, "event_log_path": rctx.get("event_log_path")}
        _emit_retrieval_event(byte_count=0, ctx=rctx2)
        _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="error", format_name=fmt)
        return SHOW_EXIT_TRANSPORT

    all_pages = set(all_pages_list)
    slugs = _canonical_stream_order(plan_id, all_pages, task_filter)
    rctx2 = {**rctx, "event_log_path": rctx.get("event_log_path")}

    if fmt == "json":
        try:
            body, pc, bc = _render_json_envelope(
                slugs=slugs,
                reader=reader,
                plan_id=plan_id,
                task_scope=task_filter,
                bucket=str(rctx["bucket"]),
                prefix=str(rctx["prefix"]),
                cutoff_ts=cutoff,
                ctx=rctx2,
            )
        except AccessDenied as e:
            _print_error({"error": "denied", "detail": f"s3 access denied: {e.op}"})
            _emit_retrieval_event(byte_count=0, ctx=rctx2)
            _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="denied", format_name=fmt)
            return SHOW_EXIT_DENIED
        except ClientError as e:
            _print_error({"error": "transport", "detail": f"{type(e).__name__}: {e!s}"})
            _emit_retrieval_event(byte_count=0, ctx=rctx2)
            _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="error", format_name=fmt)
            return SHOW_EXIT_TRANSPORT
        _emit_retrieval_event(byte_count=bc, ctx=rctx2)
        _emit_synth_show_event(ctx=rctx2, page_count=pc, byte_count=bc, result="found", format_name=fmt)
        out.write(body)
        out.flush()
        return SHOW_EXIT_OK

    try:
        pc, bc = _render_markdown_stream(slugs, reader, out, cutoff_ts=cutoff)
    except NotFound:
        # Should not happen if stream built from all_pages; treat as not_found.
        _print_error(
            {
                "error": "not_found",
                "detail": f"no vault rendered for plan_id={plan_id} (prefix={rctx['prefix']})",
            }
        )
        _emit_retrieval_event(byte_count=0, ctx=rctx2)
        _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="not_found", format_name=fmt)
        return SHOW_EXIT_NOT_FOUND
    except AccessDenied as e:
        _print_error({"error": "denied", "detail": f"s3 access denied: {e.op}"})
        _emit_retrieval_event(byte_count=0, ctx=rctx2)
        _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="denied", format_name=fmt)
        return SHOW_EXIT_DENIED
    except ClientError as e:
        _print_error({"error": "transport", "detail": f"{type(e).__name__}: {e!s}"})
        _emit_retrieval_event(byte_count=0, ctx=rctx2)
        _emit_synth_show_event(ctx=rctx2, page_count=0, byte_count=0, result="error", format_name=fmt)
        return SHOW_EXIT_TRANSPORT

    _emit_retrieval_event(byte_count=bc, ctx=rctx2)
    _emit_synth_show_event(ctx=rctx2, page_count=pc, byte_count=bc, result="found", format_name=fmt)
    return SHOW_EXIT_OK


# <READ-ONLY-REGION-END id="synth-show">


def _publish(args: argparse.Namespace) -> int:
    from synthesis.generator import generate_vault
    from synthesis.publisher import SynthesisPublisher
    from synthesis.sources import InMemoryEventSource

    events_path = Path(args.events_file)
    try:
        events = _load_events(events_path)
    except FileNotFoundError:
        _print_error({"error": "usage", "detail": f"events-file not found: {events_path}"})
        return EXIT_USAGE
    except ValueError as exc:
        _print_error({"error": "usage", "detail": str(exc)})
        return EXIT_USAGE
    except OSError as exc:
        _print_error({"error": "usage", "detail": f"io: {exc}"})
        return EXIT_USAGE

    src = InMemoryEventSource(events)
    filtered = list(
        src.iter_events(
            plan_id=args.plan_id,
            task_id=args.task_id,
            cutoff_timestamp=args.cutoff_timestamp,
        )
    )
    bundle = generate_vault(
        filtered,
        company_id=args.company_id,
        repository_id=args.repository_id,
        cutoff_timestamp=args.cutoff_timestamp,
    )
    pages_rendered = len(bundle.pages)

    base_envelope: dict[str, Any] = {
        "bucket": args.bucket,
        "prefix": args.prefix,
        "plan_id": args.plan_id,
        "company_id": args.company_id,
        "repository_id": args.repository_id,
        "task_id": args.task_id,
        "cutoff_timestamp": args.cutoff_timestamp,
        "dry_run": bool(args.dry_run),
        "events_read": len(events),
        "pages_rendered": pages_rendered,
        "written": 0,
        "skipped": 0,
        "keys_written": [],
    }

    if args.dry_run:
        _print_envelope(base_envelope)
        return EXIT_OK

    try:
        client = _s3_client_factory(args.aws_region, args.aws_profile)
    except Exception as exc:  # noqa: BLE001 — boundary mapping
        _print_error({"error": "transport", "detail": f"s3_factory: {exc!r}"})
        return EXIT_TRANSPORT

    publisher = SynthesisPublisher(bucket=args.bucket, s3_client=client, prefix=args.prefix)
    try:
        result = publisher.publish(bundle)
    except Exception as exc:  # noqa: BLE001 — boundary mapping of ClientError/Boto3Error/OSError
        _print_error({"error": "transport", "detail": f"{type(exc).__name__}: {exc}"})
        return EXIT_TRANSPORT

    base_envelope["written"] = int(result.written)
    base_envelope["skipped"] = int(result.skipped)
    base_envelope["keys_written"] = list(result.keys_written)
    _print_envelope(base_envelope)
    return EXIT_OK


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    av = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parser.parse_args(av)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return EXIT_OK
        if av and av[0] == "show":
            return SHOW_EXIT_USAGE
        return EXIT_USAGE

    # Inject repo-root into environment for peer modules that honor it.
    os.environ.setdefault("CANON_SYSTEMS_REPO_ROOT", str(Path.cwd()))
    _ensure_repo_backend_import_path()

    if args.subcommand == "publish":
        return _publish(args)
    if args.subcommand == "show":
        return _show(args)
    return EXIT_USAGE


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
