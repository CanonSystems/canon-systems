"""`canon release publish-on-pass`: auto-publish hook on RELEASE_STATUS PASS.

On a release whose `qa_gate`, `ci_gate`, and `merge_gate` all equal
``PASS`` this module:

1. Invokes ``canon synth publish`` exactly once (subprocess seam;
   retries with bounded exponential backoff on transient failure).
2. Optionally POSTs a small JSON payload to
   ``CANON_PUBLISH_NOTIFIER_URL`` so downstream ``canon vault sync``
   listeners refresh near-instantly instead of waiting for the next
   10-second tick.
3. Persists a per-release sentinel under
   ``.canon/release-publish/<plan_id>/<release_id>.json`` so a second
   invocation for the same release is a byte-identical no-op.

All S3 writes continue to flow through the already-audited
``canon synth publish`` binary; the AC9 source-scan keeps this module
free of direct boto3 write calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from canon_backend_shared.events import CanonicalEvent

from .stall_watchdog import _emit_event

PUBLISH_EXIT_OK = 0
PUBLISH_EXIT_USAGE = 2
PUBLISH_EXIT_CONFIG = 4
PUBLISH_EXIT_FAILED = 5

_DEFAULT_BACKOFF_BASE = 1.0
_DEFAULT_BACKOFF_CAP = 60.0
_DEFAULT_RETRIES = 3
_DEFAULT_NOTIFIER_TIMEOUT = 5.0

_sleep: Callable[[float], None] = time.sleep
_run_subprocess: Callable[..., Any] = subprocess.run


def _http_post(url: str, body: bytes, *, timeout: float) -> int:
    """Default HTTP POST seam. Returns the HTTP status code; raises on network error."""
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - user-supplied URL is by design
        return int(getattr(resp, "status", 200))


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _env_first(flag: str | None, env: str) -> str | None:
    raw = (flag or "").strip() if flag is not None else ""
    if raw:
        return raw
    v = os.environ.get(env, "").strip()
    return v or None


def _clamp_int(raw: str | None, default: int, *, lo: int, hi: int) -> int:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        v = int(str(raw).strip())
    except ValueError:
        return default
    return max(lo, min(hi, v))


def _clamp_float(raw: str | None, default: float, *, lo: float, hi: float) -> float:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        v = float(str(raw).strip())
    except ValueError:
        return default
    return max(lo, min(hi, v))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon release",
        description="Release lifecycle helpers (auto-publish on PASS).",
    )
    sub = p.add_subparsers(dest="subcommand", required=True)

    pub = sub.add_parser(
        "publish-on-pass",
        help="Trigger `canon synth publish` when a release hits PASS (idempotent, retry-safe).",
    )
    pub.add_argument("--release-status-file", default="", help="Path to the release-status.md or release-status.json packet.")
    pub.add_argument("--release-status-json", default="", help="Inline JSON RELEASE_STATUS body (overrides --release-status-file).")
    pub.add_argument("--release-id", default="", help="Stable identifier for this release/wave (defaults to hash of status body).")
    pub.add_argument("--plan-id", default=None)
    pub.add_argument("--company-id", default=None)
    pub.add_argument("--repository-id", default=None)
    pub.add_argument("--bucket", default=None)
    pub.add_argument("--prefix", default=None)
    pub.add_argument("--events-file", default=None)
    pub.add_argument("--cutoff-timestamp", default=None)
    pub.add_argument("--notifier-url", default=None)
    pub.add_argument("--retries", default=None)
    pub.add_argument("--backoff-base", default=None)
    pub.add_argument("--backoff-cap", default=None)
    pub.add_argument("--notifier-timeout", default=None)
    pub.add_argument("--state-dir", default="", help="Override idempotence sentinel dir (default: <repo>/.canon/release-publish).")
    pub.add_argument("--canon-bin", default="canon", help="Path to the `canon` binary used for the publish subprocess.")
    pub.add_argument("--event-log", default="", help="Override canonical event log path.")
    pub.add_argument("--dry-run", action="store_true")
    return p


# ---------------------------------------------------------------------------
# Release-status packet parsing
# ---------------------------------------------------------------------------


_YAML_KEY = re.compile(r'^\s*(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*"?(?P<val>[^"\n]*?)"?\s*$')


def _parse_release_status(text: str) -> dict[str, str]:
    """Tolerantly extract release-status fields from YAML or JSON bodies."""
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                return {str(k): str(v) for k, v in obj.items() if isinstance(v, (str, int, float, bool))}
        except json.JSONDecodeError:
            pass
    out: dict[str, str] = {}
    in_block = False
    for line in text.splitlines():
        if line.strip() == "RELEASE_STATUS":
            in_block = True
            continue
        if line.strip() == "END_RELEASE_STATUS":
            in_block = False
            continue
        if not in_block and "RELEASE_STATUS" not in text:
            in_block = True
        if not in_block:
            continue
        m = _YAML_KEY.match(line)
        if not m:
            continue
        out[m.group("key")] = m.group("val").strip()
    return out


def _should_publish(status: dict[str, str]) -> tuple[bool, str]:
    for gate in ("qa_gate", "ci_gate", "merge_gate"):
        val = status.get(gate, "").upper()
        if val != "PASS":
            return False, f"{gate}={val or 'MISSING'}"
    return True, "all_gates_pass"


# ---------------------------------------------------------------------------
# Idempotence sentinel
# ---------------------------------------------------------------------------


def _state_dir(root: Path | None, override: str) -> Path:
    if override.strip():
        return Path(override).expanduser().resolve()
    base = root if root is not None else Path.cwd()
    return (base / ".canon" / "release-publish").resolve()


def _sentinel_path(state_dir: Path, plan_id: str, release_id: str) -> Path:
    safe_release = re.sub(r"[^a-zA-Z0-9._-]+", "_", release_id)
    return state_dir / plan_id / f"{safe_release}.json"


def _already_published(path: Path) -> bool:
    return path.is_file()


def _write_sentinel(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Publish subprocess + retry loop
# ---------------------------------------------------------------------------


def _publish_argv(args: argparse.Namespace, resolved: dict[str, str]) -> list[str]:
    cutoff = resolved.get("cutoff_timestamp") or _utc_ts()
    argv = [
        str(args.canon_bin),
        "synth",
        "publish",
        "--plan-id", resolved["plan_id"],
        "--company-id", resolved["company_id"],
        "--repository-id", resolved["repository_id"],
        "--bucket", resolved["bucket"],
        "--prefix", resolved["prefix"],
        "--cutoff-timestamp", cutoff,
        "--events-file", resolved["events_file"],
    ]
    if resolved.get("task_id"):
        argv += ["--task-id", resolved["task_id"]]
    if args.dry_run:
        argv.append("--dry-run")
    return argv


def _invoke_publish(
    argv: list[str],
    *,
    retries: int,
    backoff_base: float,
    backoff_cap: float,
) -> tuple[int, list[float]]:
    """Run the publish subprocess with bounded exponential backoff.

    Returns ``(final_exit_code, sleeps)`` where ``sleeps`` is the list of
    sleep durations the helper requested between attempts (matches
    E5-T6 vault-sync math: ``min(base * 2 ** (k-1), cap)``).
    """
    retries = max(1, min(10, retries))
    sleeps: list[float] = []
    last_code = 1
    for attempt in range(1, retries + 1):
        completed = _run_subprocess(argv, check=False)
        last_code = int(getattr(completed, "returncode", 1))
        if last_code == 0:
            return last_code, sleeps
        if attempt == retries:
            return last_code, sleeps
        delay = min(backoff_base * (2 ** (attempt - 1)), backoff_cap)
        sleeps.append(delay)
        _sleep(delay)
    return last_code, sleeps


# ---------------------------------------------------------------------------
# Event emission
# ---------------------------------------------------------------------------


def _event_log_path(override: str) -> Path:
    if override.strip():
        return Path(override).expanduser().resolve()
    return Path.cwd() / ".canon" / "memory" / "events.ndjson"


def _new_event(
    event_type: str,
    *,
    resolved: dict[str, str],
    payload: dict[str, Any],
) -> CanonicalEvent:
    return CanonicalEvent(
        schema_version=1,
        event_id=str(uuid.uuid4()),
        parent_event_id="",
        event_type=event_type,
        company_id=resolved.get("company_id", ""),
        repository_id=resolved.get("repository_id", ""),
        plan_id=resolved.get("plan_id", ""),
        task_id=resolved.get("task_id", ""),
        handoff_id=resolved.get("handoff_id", ""),
        agent_name="release-orchestrator",
        agent_run_id=os.environ.get("CANON_AGENT_RUN_ID", "") or str(uuid.uuid4()),
        actor_id=os.environ.get("CANON_ACTOR_ID", "") or "release-orchestrator",
        model=os.environ.get("CANON_MODEL", "") or "inherit",
        timestamp=_utc_ts(),
        state_version=1,
        payload=payload,
    )


def _emit_synth_publish_event(
    *,
    resolved: dict[str, str],
    status: str,
    attempts: int,
    release_id: str,
    event_log: Path,
    dry_run: bool,
) -> str:
    ev = _new_event(
        "synth_publish",
        resolved=resolved,
        payload={
            "status": status,
            "attempts": attempts,
            "release_id": release_id,
            "bucket": resolved.get("bucket", ""),
            "prefix": resolved.get("prefix", ""),
        },
    )
    _emit_event(ev, event_log=event_log, dry_run=dry_run)
    return ev.event_id


def _emit_vault_sync_notified_event(
    *,
    resolved: dict[str, str],
    release_id: str,
    publish_event_id: str,
    notifier_url: str,
    http_status: int,
    event_log: Path,
    dry_run: bool,
) -> None:
    ev = _new_event(
        "vault_sync_notified",
        resolved=resolved,
        payload={
            "release_id": release_id,
            "publish_event_id": publish_event_id,
            "notifier_url": notifier_url,
            "http_status": http_status,
        },
    )
    _emit_event(ev, event_log=event_log, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Notifier
# ---------------------------------------------------------------------------


def _notify(url: str, payload: dict[str, Any], *, timeout: float) -> tuple[bool, int, str]:
    """Best-effort POST. Never raises. Returns (ok, http_status, err)."""
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    try:
        status = _http_post(url, body, timeout=timeout)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return False, 0, str(exc)
    ok = 200 <= status < 300
    return ok, status, "" if ok else f"http_{status}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _resolve(args: argparse.Namespace, status: dict[str, str]) -> dict[str, str]:
    def pick(flag_name: str, env: str, *, status_key: str | None = None) -> str:
        flag_val = getattr(args, flag_name, None)
        v = _env_first(flag_val, env)
        if v:
            return v
        if status_key and status.get(status_key, "").strip():
            return status[status_key].strip()
        return ""

    return {
        "plan_id": pick("plan_id", "CANON_PLAN_ID", status_key="plan_id"),
        "company_id": pick("company_id", "CANON_COMPANY_ID", status_key="company_id"),
        "repository_id": pick("repository_id", "CANON_REPOSITORY_ID", status_key="repository_id"),
        "bucket": pick("bucket", "CANON_VAULT_BUCKET"),
        "prefix": pick("prefix", "CANON_VAULT_PREFIX"),
        "events_file": pick("events_file", "CANON_EVENTS_FILE"),
        "cutoff_timestamp": pick("cutoff_timestamp", "CANON_PUBLISH_CUTOFF"),
        "task_id": (status.get("task_id", "") or "").strip(),
        "handoff_id": (status.get("handoff_id", "") or "").strip(),
    }


def _load_status_text(args: argparse.Namespace) -> tuple[str, int | None, str]:
    if args.release_status_json.strip():
        return args.release_status_json, None, ""
    path = (args.release_status_file or "").strip()
    if not path:
        return "", PUBLISH_EXIT_USAGE, "release-status body not provided"
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        return "", PUBLISH_EXIT_USAGE, f"release-status file not found: {file_path}"
    try:
        return file_path.read_text(encoding="utf-8"), None, ""
    except OSError as exc:
        return "", PUBLISH_EXIT_USAGE, f"release-status read failed: {exc}"


def _print_envelope(envelope: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(envelope, sort_keys=True) + "\n")
    sys.stdout.flush()


def _print_error(payload: dict[str, Any]) -> None:
    sys.stderr.write(json.dumps(payload, sort_keys=True) + "\n")
    sys.stderr.flush()


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.subcommand != "publish-on-pass":
        parser.print_help(sys.stderr)
        return PUBLISH_EXIT_USAGE

    body, err_code, err_msg = _load_status_text(args)
    if err_code is not None:
        _print_error({"error": "usage", "reason": err_msg})
        return err_code

    status = _parse_release_status(body)
    should, reason = _should_publish(status)

    release_id = (args.release_id or "").strip()
    if not release_id:
        digest = hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()[:16]
        release_id = f"release-{digest}"

    state_dir = _state_dir(Path.cwd(), args.state_dir)
    event_log = _event_log_path(args.event_log)
    retries = _clamp_int(
        args.retries if args.retries is not None else os.environ.get("CANON_PUBLISH_RETRIES"),
        _DEFAULT_RETRIES,
        lo=1,
        hi=10,
    )
    backoff_base = _clamp_float(
        args.backoff_base if args.backoff_base is not None else os.environ.get("CANON_PUBLISH_BACKOFF_BASE"),
        _DEFAULT_BACKOFF_BASE,
        lo=0.1,
        hi=60.0,
    )
    backoff_cap = _clamp_float(
        args.backoff_cap if args.backoff_cap is not None else os.environ.get("CANON_PUBLISH_BACKOFF_CAP"),
        _DEFAULT_BACKOFF_CAP,
        lo=1.0,
        hi=300.0,
    )
    notifier_timeout = _clamp_float(
        args.notifier_timeout if args.notifier_timeout is not None else os.environ.get("CANON_PUBLISH_NOTIFIER_TIMEOUT"),
        _DEFAULT_NOTIFIER_TIMEOUT,
        lo=0.5,
        hi=60.0,
    )
    notifier_url = _env_first(args.notifier_url, "CANON_PUBLISH_NOTIFIER_URL") or ""

    if not should:
        _print_envelope({
            "action": "skipped",
            "reason": "non_pass",
            "detail": reason,
            "release_id": release_id,
        })
        return PUBLISH_EXIT_OK

    resolved = _resolve(args, status)
    missing = [k for k in ("plan_id", "company_id", "repository_id", "bucket", "prefix", "events_file") if not resolved.get(k)]
    if missing:
        _print_error({"error": "config", "missing": missing})
        return PUBLISH_EXIT_CONFIG

    sentinel = _sentinel_path(state_dir, resolved["plan_id"], release_id)
    if _already_published(sentinel):
        _print_envelope({
            "action": "skipped",
            "reason": "already_published",
            "release_id": release_id,
            "sentinel": str(sentinel),
        })
        return PUBLISH_EXIT_OK

    argv_publish = _publish_argv(args, resolved)
    exit_code, sleeps = _invoke_publish(
        argv_publish,
        retries=retries,
        backoff_base=backoff_base,
        backoff_cap=backoff_cap,
    )

    attempts = len(sleeps) + 1 if exit_code == 0 else retries
    status_str = "ok" if exit_code == 0 else "failed"
    publish_event_id = _emit_synth_publish_event(
        resolved=resolved,
        status=status_str,
        attempts=attempts,
        release_id=release_id,
        event_log=event_log,
        dry_run=args.dry_run,
    )

    if exit_code != 0:
        _print_error({
            "error": "publish_failed",
            "exit_code": exit_code,
            "attempts": attempts,
            "release_id": release_id,
        })
        return PUBLISH_EXIT_FAILED

    if not args.dry_run:
        _write_sentinel(sentinel, {
            "plan_id": resolved["plan_id"],
            "release_id": release_id,
            "publish_event_id": publish_event_id,
            "timestamp": _utc_ts(),
            "bucket": resolved["bucket"],
            "prefix": resolved["prefix"],
        })

    notifier_result: dict[str, Any] = {"attempted": False}
    if notifier_url:
        notifier_result["attempted"] = True
        payload = {
            "plan_id": resolved["plan_id"],
            "release_id": release_id,
            "publish_cutoff": resolved.get("cutoff_timestamp", "") or _utc_ts(),
            "event_id": publish_event_id,
        }
        ok, http_status, err = _notify(notifier_url, payload, timeout=notifier_timeout)
        notifier_result.update({"ok": ok, "http_status": http_status, "error": err})
        if ok:
            _emit_vault_sync_notified_event(
                resolved=resolved,
                release_id=release_id,
                publish_event_id=publish_event_id,
                notifier_url=notifier_url,
                http_status=http_status,
                event_log=event_log,
                dry_run=args.dry_run,
            )
        else:
            sys.stderr.write(
                json.dumps({
                    "vault_sync_notifier_failed": True,
                    "url": notifier_url,
                    "http_status": http_status,
                    "error": err,
                }, sort_keys=True) + "\n"
            )
            sys.stderr.flush()

    _print_envelope({
        "action": "published",
        "release_id": release_id,
        "attempts": attempts,
        "publish_event_id": publish_event_id,
        "notifier": notifier_result,
        "sleeps": sleeps,
    })
    return PUBLISH_EXIT_OK


if __name__ == "__main__":
    raise SystemExit(run())
