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
from typing import Any
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
        out.append(
            {
                "task_id": str(item["task_id"]),
                "workstream_id": str(item.get("workstream_id", default_ws)),
            }
        )
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
    qs = urlencode(
        {
            "company_id": company_id,
            "repository_id": repository_id,
            "plan_id": plan_id,
            "task_id": task_id,
            "workstream_id": workstream_id,
        }
    )
    url = f"{base_url}/state/checkpoint?{qs}"
    status, body, _h = _http_request(url, timeout_ms=timeout_ms)
    if status == 200 and isinstance(body, dict):
        return (
            str(body.get("phase")) if body.get("phase") else None,
            str(body.get("phase_status")) if body.get("phase_status") else None,
            None,
        )
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
    for task, (phase, status, degrade) in zip(tasks, scans, strict=True):
        if degrade is not None:
            continue
        next_phase = _first_incomplete_phase(phase, status)
        if next_phase is not None:
            return {
                "task_id": task["task_id"],
                "workstream_id": task["workstream_id"],
                "phase": next_phase,
            }
    return None


def _build_envelope(
    *,
    plan_id: str,
    company_id: str,
    repository_id: str,
    tasks: list[dict[str, str]],
    scans: list[tuple[str | None, str | None, str | None]],
) -> dict[str, Any]:
    resume_target = _compute_resume_target(tasks, scans)
    degraded = [{"task_id": t["task_id"], "reason": s[2]} for t, s in zip(tasks, scans) if s[2] is not None]
    tasks_completed = sum(
        1
        for phase, status, degrade in scans
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
        scans.append(
            _scan_task(
                base_url=base_url,
                company_id=args.company_id,
                repository_id=args.repository_id,
                plan_id=args.plan_id,
                task_id=task["task_id"],
                workstream_id=task["workstream_id"],
                timeout_ms=args.timeout_ms,
            )
        )

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
