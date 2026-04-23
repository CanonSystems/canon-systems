<!-- CURSOR_PILOT_PROMPT: E4-T3 stall watchdog + unblock event -->

# E4-T3 Cursor-Pilot Prompt

## ROLE
You are the implementer for Canon Memory Platform v1, Wave 4, Task E4-T3 (Stall watchdog + unblock event). Work on branch `wave/4/canon-memory-v1` (tip `e4daacf` = E4-T2).

## TASK
Ship `canon stall-watchdog scan`: a stdlib-only, read-only, monkeypatchable CLI that probes `GET /state/checkpoint` for a fixed list of (task_id, workstream_id) pairs, classifies `lease.expires_at <= now_epoch` as STALLED, and emits one `lease_stall_detected` canonical event per stall to an NDJSON log (default `.canon/memory/events.ndjson`). The event payload embeds `_resolution_hint("lease_held")` from `checkpoint_cli` (imported, not duplicated) as `suggested_next_step`.

**Critical design decision locked by scoper:** probe is GET (NOT acquire). The state-api silently steals expired leases on acquire via `item_has_live_lease`, so acquire-probe is unsound. GET surfaces the expired `expires_at` verbatim and is side-effect-free.

## CONTEXT

### Probe semantics (from scoper analysis of `backend/state-api/state_api/models.py`)

- `item_has_live_lease(item, now)` returns `False` when `expires_at <= now` → server treats expired leases as "no lease", letting `POST /state/lease/acquire` succeed with a fresh token.
- `lease_from_item(item)` returns the `LeaseInfo` block (with `owner_agent_run_id`, `expires_at` as integer epoch seconds) whenever `lease_token` is set, **regardless** of liveness.
- Therefore: `GET /state/checkpoint` response body shape (200) includes `lease: {owner_agent_run_id: str, expires_at: int (epoch seconds)}` when a token is set, or `lease: null` when no lease.

### Canonical event pattern (reference: `src/canon_systems/retrieval_telemetry.py:41-83`)

```python
from canon_backend_shared.events import CanonicalEvent

def build_retrieval_breakdown_event(*, event_id, parent_event_id, ...) -> CanonicalEvent:
    payload = {...}
    return CanonicalEvent(
        schema_version=1,
        event_id=event_id, parent_event_id=parent_event_id,
        event_type="retrieval_breakdown",
        company_id=..., repository_id=..., plan_id=..., task_id=...,
        handoff_id=..., agent_name=..., agent_run_id=..., actor_id=...,
        model=..., timestamp=..., state_version=..., payload=payload,
    )
```

### `CanonicalEvent` envelope (from `backend/shared/canon_backend_shared/events.py`)

Fields (all required): `schema_version` (must be 1), `event_id`, `parent_event_id`, `event_type`, `company_id`, `repository_id`, `plan_id`, `task_id`, `handoff_id`, `agent_name`, `agent_run_id`, `actor_id`, `model`, `timestamp`, `state_version`, `payload`. Method: `to_dict()` returns a deep dict with `payload` copied.

### cli.py wiring points (confirmed in repo)

- Line 19: `from .resume_engine import run as run_resume_engine`  → ADD: `from .stall_watchdog import run as run_stall_watchdog`
- Lines 317-318: `resume_parser = sub.add_parser("resume", ...)` → ADD stall-watchdog subparser AFTER.
- Lines 531-532: `if args.command == "resume": return run_resume_engine(...)` → ADD dispatch AFTER.

## REPOSITORY

### Files to create (2)
1. `src/canon_systems/stall_watchdog.py`
2. `tests/test_stall_watchdog.py`

### Files to modify (4, all additive)
3. `src/canon_systems/cli.py` — 3 insertion points only (import, subparser, dispatch).
4. `CHANGELOG.md` — prepend E4-T3 bullet at top of `## [Unreleased] ### Added`.
5. `README.md` — add row after `canon resume` row in the CLI commands table.
6. `docs/SYSTEM-WORKFLOW.md` — add additive bullet in §3.

### Forbidden surfaces
- `backend/**` (state-api + shared READ-ONLY; `CanonicalEvent` imported only).
- `infra/**`, `.cursor/rules/**`, `.cursor/plans/**`.
- `src/canon_systems/*.py` except `cli.py` (additive only) and the new `stall_watchdog.py`.
- `src/canon_systems/templates/**` (E4-T4 owns template edits).
- `docs/runbooks/**` (E4-T4).
- Any existing `tests/*.py` — only new `tests/test_stall_watchdog.py`.

## IMPLEMENTATION SPECIFICATION

### 1. `src/canon_systems/stall_watchdog.py` (NEW)

```python
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

CanonicalEvent is imported (Wave-3 discipline); `class CanonicalEvent` MUST NOT appear
in this module.

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
```

### 2. `src/canon_systems/cli.py` additive wiring (3 insertion points)

**At line 19** (after `from .resume_engine import run as run_resume_engine`), ADD:
```python
from .stall_watchdog import run as run_stall_watchdog
```

**At line 318** (after `resume_parser.add_argument("args", nargs=argparse.REMAINDER)`), ADD:
```python
    stall_watchdog_parser = sub.add_parser(
        "stall-watchdog",
        help="Scan for stalled leases and emit lease_stall_detected events (read-only).",
    )
    stall_watchdog_parser.add_argument("args", nargs=argparse.REMAINDER)
```

**At line 532** (after `return run_resume_engine(list(getattr(args, "args", [])))`), ADD:
```python
    if args.command == "stall-watchdog":
        return run_stall_watchdog(list(getattr(args, "args", [])))
```

Do NOT modify any other part of cli.py.

### 3. `tests/test_stall_watchdog.py` (NEW, ≥13 tests)

Key patterns:
- All tests monkeypatch `canon_systems.stall_watchdog._http_request`.
- Use `capsys` for stdout/stderr. Use `tmp_path` for event-log targets (override `--event-log` so tests don't touch the real `.canon/memory/events.ndjson`).
- For the `time.time()` / `_now_epoch()` seam, either monkeypatch `canon_systems.stall_watchdog.time.time` to return a fixed value, or compute test expectations dynamically from the real `_now_epoch()`. Prefer monkeypatching `stall_watchdog._now_epoch` (exists as a helper) via `monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: 1_700_000_000)`.

Skeleton for one test (replicate for others):

```python
import json
from pathlib import Path
from canon_systems import stall_watchdog


def _scope(extra: list[str] | None = None) -> list[str]:
    return [
        "scan",
        "--company-id", "c-1", "--repository-id", "r-1", "--plan-id", "p-1",
    ] + (extra or [])


def test_scan_single_stalled_task_emits_one_event(monkeypatch, tmp_path, capsys):
    NOW = 1_700_000_000
    monkeypatch.setattr(stall_watchdog, "_now_epoch", lambda: NOW)

    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps([{"task_id": "E4-T2", "workstream_id": "ws-main"}]))
    event_log = tmp_path / "events.ndjson"

    def _fake(url, *, timeout_ms):
        return (200, {
            "company_id": "c-1", "repository_id": "r-1", "plan_id": "p-1",
            "task_id": "E4-T2", "workstream_id": "ws-main",
            "state_version": 3, "phase": "implementer", "phase_status": "in_progress",
            "lease": {"owner_agent_run_id": "run-stale", "expires_at": NOW - 600},
        }, {})
    monkeypatch.setattr(stall_watchdog, "_http_request", _fake)

    rc = stall_watchdog.run(_scope([
        "--tasks-file", str(tasks_file),
        "--event-log", str(event_log),
    ]))
    assert rc == stall_watchdog.EXIT_OK

    out = capsys.readouterr().out.strip()
    envelope = json.loads(out)
    assert envelope["tasks_scanned"] == 1
    assert envelope["stalls_detected"] == 1
    assert envelope["events_emitted"] == 1
    assert envelope["degraded_tasks"] == []

    lines = event_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["event_type"] == "lease_stall_detected"
    assert event["task_id"] == "E4-T2"
    assert event["agent_name"] == "canon-stall-watchdog"
    assert event["handoff_id"] == ""
    assert event["state_version"] == 0
    assert event["payload"]["diagnostic"]["task_id"] == "E4-T2"
    assert event["payload"]["diagnostic"]["stale_owner_agent_run_id"] == "run-stale"
    assert event["payload"]["diagnostic"]["ttl_remaining_s"] == -600
    # suggested_next_step is _resolution_hint("lease_held") verbatim
    from canon_systems.checkpoint_cli import _resolution_hint
    assert event["payload"]["suggested_next_step"] == _resolution_hint("lease_held")
```

**Mandatory test list** (exact names, ≥13):
1. `test_scan_single_stalled_task_emits_one_event`
2. `test_scan_live_lease_emits_no_event` (lease with `expires_at = NOW + 600`)
3. `test_scan_no_lease_emits_no_event` (body has `lease: null`)
4. `test_scan_404_not_stalled_not_degraded` (404 → not stalled, not degraded)
5. `test_scan_transport_error_degrades` (status 0 → exit 5, `reason: "transport"`)
6. `test_scan_5xx_degrades` (status 500 → exit 5, `reason: "http_500"`)
7. `test_done_signal_simulated_stall` — queue of responses: task A stalled, task B live → exactly one event for A; `stalls_detected == 1`, `events_emitted == 1`, `degraded_tasks == []`, exit 0.
8. `test_dry_run_writes_to_stderr_not_file` — stalled task + `--dry-run` + `--event-log <tmp>`; assert event line on stderr, assert event-log file does NOT exist (or is empty), `envelope["events_emitted"] == 0`, `envelope["event_log_path"] == "(stderr dry-run)"`.
9. `test_event_log_default_path_appends` — two sequential `run()` calls each with a stalled task; assert event log has 2 lines (append semantics).
10. `test_tasks_file_and_handoffs_dir_mutually_exclusive` — `--tasks-file a --handoffs-dir b` → exit 4.
11. `test_handoffs_dir_discovers_e_t_subdirs` — tmp_path with `E4-T3/`, `E4-T4/`, `other/` subdirs; scan hits only 2 (assert `tasks_scanned == 2`).
12. `test_canonical_event_import_not_redefined` — read `stall_watchdog.py` source; assert `"class CanonicalEvent"` NOT in source, assert `"from canon_backend_shared.events import CanonicalEvent"` IS.
13. `test_cli_wiring_passes_args_to_subcommand` — call `canon_systems.cli.main(["stall-watchdog", "scan", ...])` with patched `_http_request`; assert the envelope is produced. Use `monkeypatch.setattr("sys.argv", ["canon", "stall-watchdog", "scan", ...])` or call `cli.main(argv=...)` if `main` accepts argv — inspect `cli.py` to confirm. If `cli.main` does not accept argv, monkeypatch `sys.argv` and catch `SystemExit`.

**For the stateful queue pattern** (done_signal test):

```python
def _queue(*responses):
    it = iter(responses)
    def _fake(url, *, timeout_ms):
        return next(it)
    return _fake
```

### 4. `CHANGELOG.md` prepend (TOP of `## [Unreleased] ### Added`, ABOVE E4-T2 bullet)

```markdown
- **E4-T3** `canon stall-watchdog scan` stall watchdog + unblock event: stdlib-only, read-only GET-probe CLI that scans a scoped list of (task_id, workstream_id) pairs (via `--tasks-file` or `--handoffs-dir`), classifies any checkpoint whose `lease.expires_at <= now_epoch` as STALLED, and emits one `lease_stall_detected` canonical event per stall to `.canon/memory/events.ndjson` (or `--event-log <path>`, or stderr under `--dry-run`). Event payload carries `diagnostic` evidence (stale owner, expires_at, ttl_remaining_s) plus `suggested_next_step` imported verbatim from `checkpoint_cli._resolution_hint("lease_held")` (zero drift). Uses GET (not acquire) because the state-api silently steals expired leases on acquire — GET surfaces expired `expires_at` verbatim and is side-effect-free. Exit 5 on any degraded probe (stricter than `canon resume` by design: a missed stall probe may hide the actual stall). `CanonicalEvent` imported from `backend/shared` (Wave-3 discipline; never redefined). New `tests/test_stall_watchdog.py` (≥13 cases) covers the simulated-stall done signal, dry-run stderr, append semantics, and the canonical-event-import-not-redefined source scan.
```

### 5. `README.md` — add row after `canon resume` row

Find the existing `| canon resume ...` row in the CLI commands table and add this row immediately after it:

```markdown
| `canon stall-watchdog scan --plan-id <p> --company-id <c> --repository-id <r> (--tasks-file <path> \| --handoffs-dir <path>) [--event-log <path>] [--dry-run]` | Detect stalled leases via GET probes and emit `lease_stall_detected` canonical events (read-only; idempotent). Exit 5 on any degraded probe. |
```

Do NOT reflow or reorder any other row.

### 6. `docs/SYSTEM-WORKFLOW.md` — add additive bullet in §3

Append a bullet (adjacent to the existing resume-engine + E4-T2 bullets in §3):

```markdown
- **E4-T3 stall watchdog (`canon stall-watchdog scan`):** Read-only GET-probe scanner that detects stalled leases (`lease.expires_at <= now_epoch`) and emits one `lease_stall_detected` canonical event per stall (default target `.canon/memory/events.ndjson`; `--dry-run` routes to stderr). Event payload embeds a `suggested_next_step` copy-pasteable `canon checkpoint lease-acquire` command imported verbatim from `checkpoint_cli._resolution_hint("lease_held")`. Deliberately uses GET (not `POST /state/lease/acquire`) because the state-api silently steals expired leases on acquire, destroying stall evidence. Exit 5 on any degraded probe.
```

## REASONING

1. Read scoper packet `.cursor/handoffs/canon-memory-v1/E4-T3/scoper.md` to confirm all decisions are anchored (GET-probe, event_type, resolution_hint import, exit codes, default paths).
2. Read `src/canon_systems/retrieval_telemetry.py` for the CanonicalEvent build pattern.
3. Read `src/canon_systems/checkpoint_cli.py` to confirm `_resolution_hint` exists and returns `{message, command}` (both `.get("lease_held")`).
4. Read `src/canon_systems/cli.py` lines 15-25, 315-320, 525-535 to confirm exact insertion points.
5. Write `src/canon_systems/stall_watchdog.py` using the skeleton above.
6. Write `tests/test_stall_watchdog.py` with the 13 named tests.
7. Apply the 3 additive edits to `cli.py`.
8. Prepend CHANGELOG bullet; add README row; add SYSTEM-WORKFLOW bullet.
9. Run `pytest tests/test_stall_watchdog.py -q` → expect ≥13 passes.
10. Run `pytest -q` → expect ≥363 passes (350 + ≥13 new).
11. Smoke: `python3 -m canon_systems.cli stall-watchdog scan --help` returns exit 0.
12. Emit `HANDOFF_TO_QA` to `.cursor/handoffs/canon-memory-v1/E4-T3/implementer.md`.

## OUTPUT FORMAT

Write full implementer packet with `HANDOFF_TO_QA` block containing:
- `handoff_id: handoff_20260423_e4t3_stall_watchdog`
- `task_id: E4-T3`
- `branch: wave/4/canon-memory-v1`
- `files_modified:` 6 paths (2 new + 4 modified)
- `acceptance_criteria:` 13 entries each with `status: MET`, `evidence`, `run_result`, `covering_tests` as YAML block-style list of bare pytest node IDs / file paths (NO prefixes).
- `suite_result:` pytest summary (focused + full).

## STOP CONDITIONS

Stop and surface blocker if:
- `_resolution_hint("lease_held")` return shape is not `{message, command}`.
- `CanonicalEvent` has changed signature in `backend/shared`.
- `cli.py` has been restructured away from the REMAINDER pattern.
- Any test would require editing an existing test file.
- The state-api response shape does not include a `lease` field on GET 200 (the test mocks this field explicitly; if the actual server doesn't, the mocks are the contract for Wave 4 waiver).
