"""canon stall-watchdog: read-only GET-probe watchdog that emits lease_stall_detected events.

Probe is GET /state/checkpoint (not POST /state/lease/acquire). The state-api server
treats `expires_at <= now` as 'no live lease' and allows a new owner's acquire to
succeed with 200, silently stealing the token — so acquire-probing destroys the stall
evidence. GET surfaces expired expires_at verbatim and is pure/idempotent.

Exit codes (stricter than E4-T1 resume_engine by design: a missed probe may hide the
actual stall, so partial degradation → exit 5):
    0  clean scan (0 or more stalls detected + events emitted successfully)
    4  usage
    5  any degraded probe OR event-log write failure

CanonicalEvent is imported (Wave-3 discipline); do not define that envelope type in
this module (no local ``class`` named ``CanonicalEvent``).

Cross-module intentional import: `_resolution_hint` is pulled from `checkpoint_cli` to
avoid drift in the `suggested_next_step` hint. This is an intra-package private import
(single source of truth for the lease-held recovery message).
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from canon_backend_shared.events import CanonicalEvent

from .checkpoint_cli import _resolution_hint  # intentional intra-package private import

EXIT_OK = 0
EXIT_USAGE = 4
EXIT_TRANSPORT = 5

ENV_BASE = "CANON_STATE_API_URL"
_DEFAULT_BASE = "http://localhost:8080"
_DEFAULT_TIMEOUT_MS = 10000
_DEFAULT_WS = "ws-main"
_DEFAULT_EVENT_LOG = ".canon/memory/events.ndjson"
_DEFAULT_PROBE_OWNER_SUFFIX = "canon-stall-watchdog"
_STALL_EVENT_TYPE = "lease_stall_detected"


def _now_epoch() -> int:
    return int(time.time())


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _epoch_to_utc_iso(epoch: int) -> str:
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _http_request(
    url: str, *, timeout_ms: int
) -> tuple[int, dict[str, Any] | list[Any] | None, dict[str, str]]:
    """GET-only HTTP seam (monkeypatchable in tests). Returns (status, body-json-or-None, headers)."""
    req = urllib.request.Request(url=url, method="GET", headers={"Accept": "application/json"})
    to_s = max(1, timeout_ms) / 1000.0
    try:
        with urllib.request.urlopen(req, timeout=to_s) as resp:  # noqa: S310
            raw = resp.read()
            status = int(resp.getcode() or 0)
            headers = {k: v for k, v in resp.headers.items()}
            try:
                body = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                body = None
            return (status, body, headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read() or b""
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = None
        headers = {k: v for k, v in (exc.headers.items() if exc.headers else [])}
        return (int(exc.code), body, headers)
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
        return (0, None, {"X-Canon-Transport-Error": type(exc).__name__})


def _resolve_base_url(args: argparse.Namespace) -> str:
    if getattr(args, "base_url", None):
        u = str(args.base_url).strip()
    else:
        u = os.environ.get(ENV_BASE, "").strip() or _DEFAULT_BASE
    return u.rstrip("/")


def _clamp_timeout(ms: int) -> int:
    return max(100, min(60000, int(ms)))


def _load_tasks_from_file(path: Path, default_ws: str) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("--tasks-file must contain a JSON array")
    out: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict) or "task_id" not in item:
            raise ValueError("each task entry must be an object with task_id")
        out.append({
            "task_id": str(item["task_id"]),
            "workstream_id": str(item.get("workstream_id", default_ws)),
        })
    return out


def _load_tasks_from_handoffs(path: Path, default_ws: str) -> list[dict[str, str]]:
    if not path.is_dir():
        raise FileNotFoundError(path)
    import re
    pat = re.compile(r"^E\d+-T\d+$")
    items = sorted(p.name for p in path.iterdir() if p.is_dir() and pat.match(p.name))
    return [{"task_id": name, "workstream_id": default_ws} for name in items]


def _classify_probe(
    status: int, body: dict[str, Any] | list[Any] | None, now_epoch: int
) -> tuple[str, dict[str, Any] | None]:
    """Returns ('stalled'|'live'|'not_stalled'|'degraded', detail_or_none).

    detail for 'stalled' = {owner_agent_run_id, expires_at, ttl_remaining_s}.
    detail for 'degraded' = {reason: "transport"|"http_<N>"}.
    """
    if status == 200 and isinstance(body, dict):
        lease = body.get("lease")
        if not isinstance(lease, dict):
            return ("not_stalled", None)
        try:
            expires_at = int(lease.get("expires_at", 0))
        except (TypeError, ValueError):
            return ("not_stalled", None)
        if expires_at <= now_epoch:
            return ("stalled", {
                "owner_agent_run_id": str(lease.get("owner_agent_run_id", "")),
                "expires_at": expires_at,
                "ttl_remaining_s": expires_at - now_epoch,
            })
        return ("live", None)
    if status == 404:
        return ("not_stalled", None)
    if status == 0:
        return ("degraded", {"reason": "transport"})
    return ("degraded", {"reason": f"http_{status}"})


def _scan_task(
    *,
    base_url: str,
    company_id: str, repository_id: str, plan_id: str,
    task_id: str, workstream_id: str,
    timeout_ms: int, now_epoch: int,
) -> tuple[str, dict[str, Any] | None]:
    qs = urlencode({
        "company_id": company_id, "repository_id": repository_id,
        "plan_id": plan_id, "task_id": task_id, "workstream_id": workstream_id,
    })
    url = f"{base_url}/state/checkpoint?{qs}"
    status, body, _h = _http_request(url, timeout_ms=timeout_ms)
    return _classify_probe(status, body, now_epoch)


def build_lease_stall_event(
    *,
    company_id: str, repository_id: str, plan_id: str, task_id: str, workstream_id: str,
    stale_owner_agent_run_id: str, expires_at_epoch: int,
    observed_at_epoch: int,
) -> CanonicalEvent:
    diagnostic = {
        "task_id": task_id,
        "workstream_id": workstream_id,
        "stale_owner_agent_run_id": stale_owner_agent_run_id,
        "expires_at_utc": _epoch_to_utc_iso(expires_at_epoch),
        "observed_at_utc": _epoch_to_utc_iso(observed_at_epoch),
        "ttl_remaining_s": expires_at_epoch - observed_at_epoch,
    }
    suggested = _resolution_hint("lease_held")
    payload = {
        "diagnostic": diagnostic,
        "suggested_next_step": suggested,
    }
    return CanonicalEvent(
        schema_version=1,
        event_id="ev-" + uuid.uuid4().hex,
        parent_event_id="",
        event_type=_STALL_EVENT_TYPE,
        company_id=company_id,
        repository_id=repository_id,
        plan_id=plan_id,
        task_id=task_id,
        handoff_id="",
        agent_name="canon-stall-watchdog",
        agent_run_id="run-" + uuid.uuid4().hex[:16],
        actor_id="",
        model="",
        timestamp=_epoch_to_utc_iso(observed_at_epoch),
        state_version=0,
        payload=payload,
    )


def _emit_event(event: CanonicalEvent, *, event_log: Path | None, dry_run: bool) -> tuple[bool, str | None]:
    """Returns (success, error_reason_or_None)."""
    line = json.dumps(event.to_dict(), sort_keys=True, ensure_ascii=True) + "\n"
    if dry_run:
        sys.stderr.write(line)
        return (True, None)
    assert event_log is not None
    try:
        event_log.parent.mkdir(parents=True, exist_ok=True)
        with open(event_log, "a", encoding="utf-8") as fh:
            fh.write(line)
        return (True, None)
    except OSError:
        return (False, "event_log_write")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon stall-watchdog",
        description="Detect stalled leases via GET probes and emit lease_stall_detected canonical events.",
    )
    sub = p.add_subparsers(dest="stall_command", required=True)
    scan = sub.add_parser("scan", help="Scan tasks for stalled leases.")
    scan.add_argument("--company-id", required=True)
    scan.add_argument("--repository-id", required=True)
    scan.add_argument("--plan-id", required=True)
    src = scan.add_mutually_exclusive_group(required=True)
    src.add_argument("--tasks-file", default=None)
    src.add_argument("--handoffs-dir", default=None)
    scan.add_argument("--workstream-id-default", default=_DEFAULT_WS)
    scan.add_argument("--base-url", default=None)
    scan.add_argument("--timeout-ms", type=int, default=_DEFAULT_TIMEOUT_MS)
    scan.add_argument("--event-log", default=_DEFAULT_EVENT_LOG)
    scan.add_argument("--dry-run", action="store_true")
    scan.add_argument("--probe-owner-suffix", default=_DEFAULT_PROBE_OWNER_SUFFIX,
                      help="Reserved for future acquire-diagnostic probe (unused by GET probe).")
    return p


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    av = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parser.parse_args(av)
    except SystemExit as exc:
        code = exc.code
        return EXIT_OK if code in (0, None) else EXIT_USAGE

    if args.stall_command != "scan":
        return EXIT_USAGE

    try:
        if args.tasks_file:
            tasks = _load_tasks_from_file(Path(args.tasks_file), args.workstream_id_default)
        else:
            tasks = _load_tasks_from_handoffs(Path(args.handoffs_dir), args.workstream_id_default)
    except FileNotFoundError as exc:
        print(json.dumps({"error": "not_found", "path": str(exc)}, sort_keys=True), file=sys.stderr)
        return EXIT_USAGE
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"error": "usage", "detail": str(exc)}, sort_keys=True), file=sys.stderr)
        return EXIT_USAGE

    base_url = _resolve_base_url(args)
    timeout_ms = _clamp_timeout(args.timeout_ms)
    now_epoch = _now_epoch()

    event_log_path: Path | None = None
    if not args.dry_run:
        event_log_path = Path(args.event_log)

    stalls = 0
    events_emitted = 0
    degraded_tasks: list[dict[str, str]] = []

    for task in tasks:
        kind, detail = _scan_task(
            base_url=base_url,
            company_id=args.company_id, repository_id=args.repository_id, plan_id=args.plan_id,
            task_id=task["task_id"], workstream_id=task["workstream_id"],
            timeout_ms=timeout_ms, now_epoch=now_epoch,
        )
        if kind == "stalled":
            assert detail is not None
            stalls += 1
            event = build_lease_stall_event(
                company_id=args.company_id, repository_id=args.repository_id, plan_id=args.plan_id,
                task_id=task["task_id"], workstream_id=task["workstream_id"],
                stale_owner_agent_run_id=str(detail["owner_agent_run_id"]),
                expires_at_epoch=int(detail["expires_at"]),
                observed_at_epoch=now_epoch,
            )
            ok, err = _emit_event(event, event_log=event_log_path, dry_run=args.dry_run)
            if ok and not args.dry_run:
                events_emitted += 1
            elif not ok:
                degraded_tasks.append({"task_id": task["task_id"], "reason": err or "event_log_write"})
        elif kind == "degraded":
            assert detail is not None
            degraded_tasks.append({"task_id": task["task_id"], "reason": str(detail["reason"])})
        # "live" and "not_stalled" are no-ops

    envelope = {
        "plan_id": args.plan_id,
        "company_id": args.company_id,
        "repository_id": args.repository_id,
        "tasks_scanned": len(tasks),
        "stalls_detected": stalls,
        "events_emitted": events_emitted,
        "event_log_path": "(stderr dry-run)" if args.dry_run else str(event_log_path),
        "degraded_tasks": degraded_tasks,
    }
    print(json.dumps(envelope, sort_keys=True))

    if degraded_tasks:
        return EXIT_TRANSPORT
    return EXIT_OK


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
