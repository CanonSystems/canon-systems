<!-- CURSOR_PILOT_PROMPT: E4-T1 orchestrator resume engine -->

# E4-T1 Cursor-Pilot Prompt

## ROLE
You are the implementer for Canon Memory Platform v1, Wave 4, Task E4-T1 (Orchestrator resume engine). Work on branch `wave/4/canon-memory-v1` (tip `58adaa3`).

## TASK
Implement `canon resume --plan-id <id>`: a stdlib-only, read-only, idempotent CLI that scans checkpoints via state-api `GET /state/checkpoint` for a given plan_id and prints the first incomplete (task_id, phase) pair as a structured JSON envelope.

## CONTEXT

### Why read-only + idempotent
Per backlog AC "idempotent re-entry; no duplicate canonical events": the resume engine MUST NOT write checkpoints, acquire leases, or emit any canonical event. It is pure observability. Running it twice on unchanged plan state MUST produce byte-identical stdout. The operator (or parent agent) uses its output to decide which agent to re-invoke; the re-invocation itself happens OUTSIDE this module.

### State-api wire shape (READ-ONLY reference)
- `GET /state/checkpoint?company_id=X&repository_id=Y&plan_id=Z&task_id=T&workstream_id=W`
- 200: checkpoint body including `phase`, `phase_status`, `state_version`, ... (see `backend/state-api/state_api/checkpoints.py` for exact schema — do NOT import; just call the HTTP endpoint).
- 404: `{"detail": {"error": "not_found", "pk": "...", "sk": "..."}}` — task has no checkpoint yet.
- 5xx / transport: treat as degraded.

### Phase ordering (backlog §B union)
`["scoper", "cursor-pilot", "implementer", "qa-gate", "release-orchestrator"]`

A task is "fully complete" iff its checkpoint has `phase == "release-orchestrator"` AND `phase_status == "completed"`. Any other state means the task is resumable at the first phase whose `phase_status != "completed"` (with `missing → scoper`).

### Existing seam patterns
- `src/canon_systems/checkpoint_cli.py` — reference for `_http_request`, `_resolve_base_url`, `_emit_stdout_json`, `_emit_stderr_json`, exit-code catalog. DO NOT MODIFY; duplicate the helpers you need in `resume_engine.py`.
- `src/canon_systems/report_cli.py` — reference for `run(argv) → int` + `main()` + stub-style CLI patterns; also the REMAINDER wiring pattern in `cli.py`.
- `src/canon_systems/cli.py` around lines 17 (imports), 309-311 (graph subparser), 517-518 (dispatch) — mirror exactly for the `resume` subcommand.

## REPOSITORY

### New files (2)
1. `src/canon_systems/resume_engine.py`
2. `tests/test_resume_engine.py`

### Modified files (4)
3. `src/canon_systems/cli.py` — additive `resume` subparser + dispatch.
4. `CHANGELOG.md` — prepend E4-T1 bullet.
5. `README.md` — additive `canon resume` row in the commands table.
6. `docs/SYSTEM-WORKFLOW.md` — additive bullet.

### Forbidden surfaces
- backend/**, infra/**, .cursor/rules/**, .cursor/plans/**
- Template files under src/canon_systems/templates/ (E4-T4 owns template + runbook wiring)
- Any src/canon_systems/*.py OTHER THAN cli.py (additive) and resume_engine.py (new)

## IMPLEMENTATION SPECIFICATION

### `src/canon_systems/resume_engine.py`

```python
"""canon resume: read-only orchestrator resume engine (stdlib-only, idempotent, no canonical events)."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

EXIT_OK = 0
EXIT_NOT_FOUND = 3
EXIT_USAGE = 4
EXIT_TRANSPORT = 5

ENV_BASE = "CANON_STATE_API_URL"
_DEFAULT_BASE = "http://localhost:8080"
_DEFAULT_TIMEOUT_MS = 10000
_DEFAULT_WS = "ws-main"

PHASE_ORDER: tuple[str, ...] = (
    "scoper",
    "cursor-pilot",
    "implementer",
    "qa-gate",
    "release-orchestrator",
)


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
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
        return (0, None, {"X-Canon-Transport-Error": type(exc).__name__})


def _resolve_base_url(args: argparse.Namespace) -> str:
    if getattr(args, "base_url", None):
        u = str(args.base_url).strip()
    else:
        u = os.environ.get(ENV_BASE, "").strip() or _DEFAULT_BASE
    return u.rstrip("/")


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


def _first_incomplete_phase(phase: str | None, phase_status: str | None) -> str | None:
    """Returns the first phase that is not 'completed', or None if fully complete."""
    if phase is None:
        return PHASE_ORDER[0]
    if phase not in PHASE_ORDER:
        return PHASE_ORDER[0]
    idx = PHASE_ORDER.index(phase)
    if phase_status == "completed":
        if idx + 1 >= len(PHASE_ORDER):
            return None
        return PHASE_ORDER[idx + 1]
    return phase


def _scan_task(
    *,
    base_url: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    timeout_ms: int,
) -> tuple[str | None, str | None, str | None]:
    """Returns (phase, phase_status, degrade_reason)."""
    qs = urlencode({
        "company_id": company_id,
        "repository_id": repository_id,
        "plan_id": plan_id,
        "task_id": task_id,
        "workstream_id": workstream_id,
    })
    url = f"{base_url}/state/checkpoint?{qs}"
    status, body, _h = _http_request(url, timeout_ms=timeout_ms)
    if status == 200 and isinstance(body, dict):
        return (str(body.get("phase")) if body.get("phase") else None,
                str(body.get("phase_status")) if body.get("phase_status") else None,
                None)
    if status == 404:
        return (None, None, None)
    if status == 0:
        return (None, None, "transport")
    if 500 <= status <= 599:
        return (None, None, f"http_{status}")
    return (None, None, f"http_{status}")


def _compute_resume_target(
    tasks: list[dict[str, str]],
    scans: list[tuple[str | None, str | None, str | None]],
) -> dict[str, str] | None:
    for task, (phase, status, _degrade) in zip(tasks, scans):
        next_phase = _first_incomplete_phase(phase, status)
        if next_phase is not None:
            return {
                "task_id": task["task_id"],
                "workstream_id": task["workstream_id"],
                "phase": next_phase,
            }
    return None


def _build_envelope(
    *, plan_id: str, company_id: str, repository_id: str,
    tasks: list[dict[str, str]],
    scans: list[tuple[str | None, str | None, str | None]],
) -> dict[str, Any]:
    resume_target = _compute_resume_target(tasks, scans)
    degraded = [{"task_id": t["task_id"], "reason": s[2]}
                for t, s in zip(tasks, scans) if s[2] is not None]
    tasks_completed = sum(
        1 for phase, status, degrade in scans
        if degrade is None and phase == PHASE_ORDER[-1] and status == "completed"
    )
    resume_available = resume_target is not None and len(degraded) < len(tasks)
    return {
        "plan_id": plan_id,
        "company_id": company_id,
        "repository_id": repository_id,
        "resume_target": resume_target,
        "tasks_scanned": len(tasks),
        "tasks_completed": tasks_completed,
        "degraded_tasks": degraded,
        "resume_available": resume_available,
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon resume",
        description="Print the first incomplete (task_id, phase) pair for a plan (read-only).",
    )
    p.add_argument("--plan-id", required=True)
    p.add_argument("--company-id", required=True)
    p.add_argument("--repository-id", required=True)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--tasks-file", default=None)
    src.add_argument("--handoffs-dir", default=None)
    p.add_argument("--workstream-id-default", default=_DEFAULT_WS)
    p.add_argument("--base-url", default=None)
    p.add_argument("--timeout-ms", type=int, default=_DEFAULT_TIMEOUT_MS)
    return p


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    av = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parser.parse_args(av)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return EXIT_OK
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
    scans: list[tuple[str | None, str | None, str | None]] = []
    for task in tasks:
        scans.append(_scan_task(
            base_url=base_url,
            company_id=args.company_id,
            repository_id=args.repository_id,
            plan_id=args.plan_id,
            task_id=task["task_id"],
            workstream_id=task["workstream_id"],
            timeout_ms=args.timeout_ms,
        ))

    envelope = _build_envelope(
        plan_id=args.plan_id,
        company_id=args.company_id,
        repository_id=args.repository_id,
        tasks=tasks,
        scans=scans,
    )
    print(json.dumps(envelope, sort_keys=True))

    all_degraded = len(envelope["degraded_tasks"]) == len(tasks) and len(tasks) > 0
    if all_degraded:
        return EXIT_TRANSPORT
    return EXIT_OK


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
```

### `src/canon_systems/cli.py` additive edits

**Import** (add near the existing `from .report_cli import run as run_report_cli`):
```python
from .resume_engine import run as run_resume_engine
```

**Subparser** (add after the `report_parser` block):
```python
    resume_parser = sub.add_parser("resume", help="Orchestrator resume engine (read-only)")
    resume_parser.add_argument("args", nargs=argparse.REMAINDER)
```

**Dispatch** (add after the `report` dispatch):
```python
    if args.command == "resume":
        return run_resume_engine(list(getattr(args, "args", [])))
```

### `tests/test_resume_engine.py`

Write ≥12 tests. Use `monkeypatch` on `canon_systems.resume_engine._http_request` to return canned `(status, body, headers)` tuples. Include:

1. `test_resume_cli_help_returns_0` — `run(["--help"])` returns 0.
2. `test_both_task_sources_is_usage_error` — `--tasks-file a --handoffs-dir b` exits 4.
3. `test_neither_task_source_is_usage_error` — neither flag exits 4.
4. `test_missing_tasks_file_is_not_found` — non-existent `--tasks-file` exits 4 with `"error": "usage"` (since our load path raises OSError → usage).
5. `test_resume_target_first_incomplete_phase` — task A `phase=qa-gate, status=completed`, task B `phase=implementer, status=in_progress` → target = task B / `implementer`.
6. `test_resume_target_none_when_all_complete` — all tasks `phase=release-orchestrator, status=completed` → `resume_target: null`, `resume_available: false`, exit 0.
7. `test_resume_missing_checkpoint_points_to_scoper` — task returns 404 → next phase = scoper.
8. `test_crash_restart_scenario_task_b_cursor_pilot` — A fully done, B has `phase=cursor-pilot, status=completed` → target B / `implementer`.
9. `test_idempotent_byte_equal_on_double_invocation` — run twice with same stubs, capture stdout both times, assert equality.
10. `test_no_event_emission_in_module_source` — read `resume_engine.py` source, assert no `CanonicalEvent` or `event_type` references (static check).
11. `test_transport_error_all_tasks_exit_5` — all tasks return `(0, None, {...})` → exit 5.
12. `test_transport_error_partial_degrade_resume_unavailable` — 1 of 2 tasks transport, 1 task returns 200 completed → exit 0, `resume_available=false`.
13. `test_output_envelope_keys_sorted` — stdout JSON has sorted top-level keys.
14. `test_handoffs_dir_discovery` — given a tmp_path with `E4-T1/`, `E4-T2/`, `other/` subdirs, only the `E<N>-T<N>` dirs are included.

Use `capsys` for stdout/stderr capture. Do NOT spawn subprocesses.

### `CHANGELOG.md` prepend

```
- **E4-T1** `canon resume --plan-id <id>` orchestrator resume engine: stdlib-only, read-only, idempotent scanner over state-api checkpoints. Emits a structured JSON envelope identifying the first incomplete (task_id, phase) pair per the canonical 5-phase order (scoper → cursor-pilot → implementer → qa-gate → release-orchestrator). Task discovery via `--tasks-file` (JSON) or `--handoffs-dir` (E<N>-T<N> subdirectory scan). Degrades gracefully when state-api is unreachable; exit 5 iff every task is transport-degraded. Zero canonical events emitted (verified by a static-source assertion).
```

### `README.md` additive row

```
| `canon resume --plan-id <id> --company-id <c> --repository-id <r> (--tasks-file <path> \| --handoffs-dir <path>)` | Print the first incomplete (task_id, phase) pair for a plan as structured JSON (read-only; idempotent). |
```

### `docs/SYSTEM-WORKFLOW.md` additive bullet (place in §3 or §5.1)

```
- **Resume engine (`canon resume`)**: Read-only, idempotent scanner over state-api checkpoints. Given a `--plan-id` + tenant scope and a task list (via `--tasks-file` or `--handoffs-dir`), it returns a JSON envelope identifying the first incomplete `(task_id, phase)` pair per the canonical 5-phase order (`scoper → cursor-pilot → implementer → qa-gate → release-orchestrator`). The engine emits zero canonical events — operators (or the parent agent) use the output to decide which agent to re-invoke; the re-invocation itself happens elsewhere. Running `canon resume` twice on unchanged plan state yields byte-identical stdout.
```

## REASONING

1. Read the existing `src/canon_systems/checkpoint_cli.py` HTTP seam and exit-code layout to confirm we can safely duplicate (not import) the helpers.
2. Read `src/canon_systems/cli.py` around the `graph` / `report` subparser pattern.
3. Read `backend/state-api/state_api/checkpoints.py` (READ-ONLY) to confirm the checkpoint response shape includes `phase` and `phase_status`.
4. Write `resume_engine.py` with the exact skeleton above.
5. Wire `cli.py` additively (3 edits: import, subparser, dispatch).
6. Author `tests/test_resume_engine.py` with 14 tests.
7. Update CHANGELOG / README / SYSTEM-WORKFLOW additively.
8. Run `pytest tests/test_resume_engine.py -q` → expect 14 passes.
9. Run `pytest -q` at repo root → expect 333 passes (319 baseline + 14 new).
10. Smoke-test: `python3 -m canon_systems.cli resume --help` exits 0.
11. Emit `HANDOFF_TO_QA` to `.cursor/handoffs/canon-memory-v1/E4-T1/implementer.md`.

## OUTPUT FORMAT

`HANDOFF_TO_QA` with:
- `handoff_id: handoff_20260422_e4t1_resume_engine`
- `branch: wave/4/canon-memory-v1`
- `files_modified:` exact list (6 paths: 2 new + 4 modified)
- `acceptance_criteria:` 14 ACs each with `status: MET`, `evidence`, `run_result`, and `covering_tests:` (YAML block-style list of pytest node ids / file paths, no prefixes)
- `suite_result:` pytest summary lines for focused + full runs

## STOP CONDITIONS

Stop and surface a blocker (do not improvise) if:
- `backend/state-api/state_api/checkpoints.py` no longer returns `phase` + `phase_status` in the GET body.
- `cli.py` subparser pattern has been refactored away from REMAINDER.
- Any forbidden-surface edit would be required.
- The static-source check in test-10 cannot be satisfied (e.g., you need an internal helper literally named `event_type`).
