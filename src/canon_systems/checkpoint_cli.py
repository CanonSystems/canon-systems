"""Checkpoint + lease client CLI over state-api (GET/PUT /state/checkpoint, POST /state/lease/*)."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

# Transport / synthetic metadata in response headers (not sent over wire from server)
_HDR_TRANSPORT_ERR = "X-Canon-Cli-Transport-Error"
_HDR_TRANSPORT_URL = "X-Canon-Cli-Transport-Url"

ENV_BASE = "CANON_STATE_API_URL"
_DEFAULT_BASE = "http://localhost:8080"
_DEFAULT_TIMEOUT_MS = 10000

_WRITE_WHITELIST = frozenset(
    {"inputs", "outputs", "decisions", "open_questions", "last_event_id"},
)

EXIT_OK = 0
EXIT_VERSION_CONFLICT = 1
EXIT_LEASE_DENIED = 2
EXIT_NOT_FOUND = 3
EXIT_USAGE = 4
EXIT_TRANSPORT = 5


def _clamp_timeout(ms: int) -> int:
    return max(100, min(60000, ms))


def _emit_stdout_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=True, sort_keys=False) + "\n", end="", file=sys.stdout)


def _emit_stderr_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=True, sort_keys=False) + "\n", end="", file=sys.stderr)


def _unwrap_detail(body: Any) -> Any:
    if not isinstance(body, dict) or "detail" not in body:
        return body
    d = body.get("detail")
    if isinstance(d, (dict, list)):
        return d
    return body


def _header_get(headers: dict[str, str], name: str) -> str:
    if not name:
        return ""
    n = name.lower()
    for k, v in headers.items():
        if k.lower() == n:
            return v
    return ""


def _scope_dict(args: argparse.Namespace) -> dict[str, str]:
    return {
        "company_id": args.company_id,
        "repository_id": args.repository_id,
        "plan_id": args.plan_id,
        "task_id": args.task_id,
        "workstream_id": args.workstream_id,
    }


def _resolve_base_url(args: argparse.Namespace) -> str:
    if getattr(args, "base_url", None):
        u = str(args.base_url).strip()
    else:
        u = os.environ.get(ENV_BASE, "").strip() or _DEFAULT_BASE
    return u.rstrip("/")


def _http_request(
    method: str, url: str, body: dict[str, Any] | None, timeout_ms: int
) -> tuple[int, dict[str, Any] | list[Any] | None, dict[str, str]]:
    to_s = max(timeout_ms, 1) / 1000.0
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=True).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=to_s) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            status = int(resp.getcode() or 0)
            head = {k: v for k, v in resp.headers.items()}
            j: dict[str, Any] | list[Any] | None
            if raw.strip():
                try:
                    parsed: Any = json.loads(raw)
                    j = parsed if isinstance(parsed, (dict, list)) else None
                except json.JSONDecodeError:
                    j = None
            else:
                j = None
            return (status, j, head)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        j = None
        if raw.strip():
            try:
                p2: Any = json.loads(raw)
                if isinstance(p2, dict):
                    j = p2
                elif isinstance(p2, list):
                    j = p2
            except json.JSONDecodeError:
                j = None
        head: dict[str, str] = {k: v for k, v in exc.headers.items()} if exc.headers else {}
        return (int(exc.code or 0), j, head)
    except (urllib.error.URLError, TimeoutError, OSError, socket.gaierror) as exc:
        return (
            -1,
            None,
            {
                _HDR_TRANSPORT_ERR: str(exc)[:2000],
                _HDR_TRANSPORT_URL: url,
            },
        )


def _transport_stderr_envelope(
    method: str, url: str, headers: dict[str, str]
) -> dict[str, str]:
    msg = headers.get(_HDR_TRANSPORT_ERR) or "transport error"
    return {"error": "transport", "message": msg, "url": url}


def _is_transport(
    status: int,
) -> bool:
    return status < 0


def _is_server_transport(status: int) -> bool:
    return status >= 500


def _cmd_read(args: argparse.Namespace) -> int:
    base = _resolve_base_url(args)
    tmo = _clamp_timeout(args.timeout_ms)
    qs = urlencode(
        {
            "company_id": args.company_id,
            "repository_id": args.repository_id,
            "plan_id": args.plan_id,
            "task_id": args.task_id,
            "workstream_id": args.workstream_id,
        }
    )
    url = f"{base}/state/checkpoint?{qs}"
    st, j, h = _http_request("GET", url, None, tmo)
    if _is_transport(st):
        _emit_stderr_json(
            _transport_stderr_envelope("GET", url, h)
        )
        return EXIT_TRANSPORT
    if _is_server_transport(st):
        d = _unwrap_detail(j) if isinstance(j, dict) else j
        _emit_stderr_json(
            {"error": "transport", "message": f"HTTP {st}", "url": url, "detail": d},
        )
        return EXIT_TRANSPORT
    if st == 200 and isinstance(j, (dict, list)):
        _emit_stdout_json(j)
        return EXIT_OK
    if st == 404:
        raw = j if isinstance(j, dict) else {}
        d = _unwrap_detail(raw)
        if isinstance(d, dict) and d.get("error") == "not_found" and "pk" in d and "sk" in d:
            out = {k: d[k] for k in ("error", "pk", "sk") if k in d}
        else:
            out = {"error": "not_found", "detail": d}
        _emit_stderr_json(out)
        return EXIT_NOT_FOUND
    if st == 422:
        d = _unwrap_detail(j) if isinstance(j, dict) else j
        _emit_stderr_json({"error": "validation", "detail": d})
        return EXIT_USAGE
    d = _unwrap_detail(j) if isinstance(j, dict) else j
    _emit_stderr_json({"error": "unexpected", "http_status": st, "detail": d})
    return EXIT_USAGE


def _load_write_merged(args: argparse.Namespace) -> dict[str, Any] | int:
    extra: dict[str, Any] = {}
    if args.body_file and args.stdin:
        return EXIT_USAGE
    if args.body_file:
        p = str(args.body_file)
        try:
            with open(p, encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as e:
            _emit_stderr_json({"error": "body_file", "message": str(e), "path": p})
            return EXIT_USAGE
        if not raw.strip():
            return extra
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            _emit_stderr_json({"error": "json", "message": str(e)})
            return EXIT_USAGE
        if not isinstance(data, dict):
            _emit_stderr_json({"error": "json", "message": "body must be a JSON object"})
            return EXIT_USAGE
        for k in data:
            if k not in _WRITE_WHITELIST:
                _emit_stderr_json(
                    {
                        "error": "forbidden_key",
                        "key": k,
                        "allowed": sorted(_WRITE_WHITELIST),
                    }
                )
                return EXIT_USAGE
        extra = {k: v for k, v in data.items() if v is not None}
    elif args.stdin:
        raw = sys.stdin.read()
        if not raw.strip():
            return extra
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            _emit_stderr_json({"error": "json", "message": str(e)})
            return EXIT_USAGE
        if not isinstance(data, dict):
            _emit_stderr_json({"error": "json", "message": "body must be a JSON object"})
            return EXIT_USAGE
        for k in data:
            if k not in _WRITE_WHITELIST:
                _emit_stderr_json(
                    {
                        "error": "forbidden_key",
                        "key": k,
                        "allowed": sorted(_WRITE_WHITELIST),
                    }
                )
                return EXIT_USAGE
        extra = {k: v for k, v in data.items() if v is not None}
    return extra


def _cmd_write(args: argparse.Namespace) -> int:
    merged = _load_write_merged(args)
    if isinstance(merged, int):
        return merged
    base = _resolve_base_url(args)
    tmo = _clamp_timeout(args.timeout_ms)
    url = f"{base}/state/checkpoint"
    body: dict[str, Any] = {
        **(_scope_dict(args)),
        "handoff_id": args.handoff_id,
        "phase": args.phase,
        "phase_status": args.phase_status,
        "state_version": int(args.expected_version),
        "lease_token": args.lease_token,
        **merged,
    }
    st, j, h = _http_request("PUT", url, body, tmo)
    if _is_transport(st):
        _emit_stderr_json(_transport_stderr_envelope("PUT", url, h))
        return EXIT_TRANSPORT
    if _is_server_transport(st):
        d = _unwrap_detail(j) if isinstance(j, dict) else j
        _emit_stderr_json(
            {"error": "transport", "message": f"HTTP {st}", "url": url, "detail": d},
        )
        return EXIT_TRANSPORT
    if st == 200 and isinstance(j, dict):
        _emit_stdout_json(j)
        ev = _header_get(h, "X-Canon-Event-Id")
        if ev:
            print(f"canon checkpoint: event_id={ev}\n", end="", file=sys.stderr)
        return EXIT_OK
    if st == 409:
        raw = j if isinstance(j, dict) else {}
        d = _unwrap_detail(raw)
        if isinstance(d, dict) and d.get("error") == "state_version_conflict":
            o = {k: d[k] for k in ("error", "expected", "actual") if k in d}
            _emit_stderr_json(o)
            return EXIT_VERSION_CONFLICT
        if isinstance(d, dict):
            # Un-enumerated 409 → exit 2; omit lease_token if server ever echoed it
            o = {k: v for k, v in d.items() if k != "lease_token"}
            _emit_stderr_json(o)
            return EXIT_LEASE_DENIED
        _emit_stderr_json({"error": "conflict", "detail": d})
        return EXIT_LEASE_DENIED
    if st == 404:
        raw = j if isinstance(j, dict) else {}
        d = _unwrap_detail(raw)
        if isinstance(d, dict) and "pk" in d and "sk" in d:
            _emit_stderr_json(d)
        else:
            _emit_stderr_json({"error": "not_found", "detail": d})
        return EXIT_NOT_FOUND
    if st == 422:
        d = _unwrap_detail(j) if isinstance(j, dict) else j
        _emit_stderr_json({"error": "validation", "detail": d})
        return EXIT_USAGE
    d = _unwrap_detail(j) if isinstance(j, dict) else j
    _emit_stderr_json({"error": "unexpected", "http_status": st, "detail": d})
    return EXIT_USAGE


def _cmd_lease_acquire(args: argparse.Namespace) -> int:
    try:
        ttl = int(args.ttl_seconds)
    except (TypeError, ValueError):
        _emit_stderr_json({"error": "usage", "message": "ttl-seconds must be an integer"})
        return EXIT_USAGE
    if not 1 <= ttl <= 3600:
        _emit_stderr_json(
            {
                "error": "usage",
                "message": "ttl_seconds must be between 1 and 3600 inclusive",
            }
        )
        return EXIT_USAGE
    base = _resolve_base_url(args)
    tmo = _clamp_timeout(args.timeout_ms)
    url = f"{base}/state/lease/acquire"
    body: dict[str, Any] = {
        **(_scope_dict(args)),
        "owner_agent_run_id": args.owner_agent_run_id,
        "owner_actor_id": args.owner_actor_id,
        "ttl_seconds": ttl,
    }
    st, j, h = _http_request("POST", url, body, tmo)
    if _is_transport(st):
        _emit_stderr_json(_transport_stderr_envelope("POST", url, h))
        return EXIT_TRANSPORT
    if _is_server_transport(st):
        d = _unwrap_detail(j) if isinstance(j, dict) else j
        _emit_stderr_json(
            {"error": "transport", "message": f"HTTP {st}", "url": url, "detail": d},
        )
        return EXIT_TRANSPORT
    if st == 200 and isinstance(j, dict):
        _emit_stdout_json(j)
        return EXIT_OK
    if st == 409:
        raw = j if isinstance(j, dict) else {}
        d = _unwrap_detail(raw)
        if isinstance(d, dict) and d.get("error") == "lease_held":
            _emit_stderr_json(
                {
                    "error": "lease_held",
                    "owner_agent_run_id": d.get("owner_agent_run_id"),
                    "expires_at": d.get("expires_at"),
                }
            )
            return EXIT_LEASE_DENIED
        if isinstance(d, dict):
            o = {k: v for k, v in d.items() if k != "lease_token"}
            _emit_stderr_json(o)
            return EXIT_LEASE_DENIED
        _emit_stderr_json({"error": "lease_denied", "detail": d})
        return EXIT_LEASE_DENIED
    if st == 422:
        d = _unwrap_detail(j) if isinstance(j, dict) else j
        _emit_stderr_json({"error": "validation", "detail": d})
        return EXIT_USAGE
    d = _unwrap_detail(j) if isinstance(j, dict) else j
    _emit_stderr_json({"error": "unexpected", "http_status": st, "detail": d})
    return EXIT_USAGE


def _cmd_lease_renew(args: argparse.Namespace) -> int:
    try:
        ttl = int(args.ttl_seconds)
    except (TypeError, ValueError):
        _emit_stderr_json({"error": "usage", "message": "ttl-seconds must be an integer"})
        return EXIT_USAGE
    if not 1 <= ttl <= 3600:
        _emit_stderr_json(
            {
                "error": "usage",
                "message": "ttl_seconds must be between 1 and 3600 inclusive",
            }
        )
        return EXIT_USAGE
    base = _resolve_base_url(args)
    tmo = _clamp_timeout(args.timeout_ms)
    url = f"{base}/state/lease/renew"
    body: dict[str, Any] = {
        "scope_ids": _scope_dict(args),
        "lease_token": args.lease_token,
        "ttl_seconds": ttl,
    }
    st, j, h = _http_request("POST", url, body, tmo)
    if _is_transport(st):
        _emit_stderr_json(_transport_stderr_envelope("POST", url, h))
        return EXIT_TRANSPORT
    if _is_server_transport(st):
        d = _unwrap_detail(j) if isinstance(j, dict) else j
        _emit_stderr_json(
            {"error": "transport", "message": f"HTTP {st}", "url": url, "detail": d},
        )
        return EXIT_TRANSPORT
    if st == 200 and isinstance(j, dict):
        out = {k: j[k] for k in ("lease_token", "expires_at") if k in j}
        _emit_stdout_json(out)
        return EXIT_OK
    if st == 409:
        raw = j if isinstance(j, dict) else {}
        d = _unwrap_detail(raw)
        _emit_stderr_json(d if isinstance(d, dict) else {"detail": d})
        return EXIT_LEASE_DENIED
    if st == 422:
        d2 = _unwrap_detail(j) if isinstance(j, dict) else j
        _emit_stderr_json({"error": "validation", "detail": d2})
        return EXIT_USAGE
    d = _unwrap_detail(j) if isinstance(j, dict) else j
    _emit_stderr_json({"error": "unexpected", "http_status": st, "detail": d})
    return EXIT_USAGE


def _cmd_lease_release(args: argparse.Namespace) -> int:
    base = _resolve_base_url(args)
    tmo = _clamp_timeout(args.timeout_ms)
    url = f"{base}/state/lease/release"
    body: dict[str, Any] = {
        "scope_ids": _scope_dict(args),
        "lease_token": args.lease_token,
    }
    st, j, h = _http_request("POST", url, body, tmo)
    if _is_transport(st):
        _emit_stderr_json(_transport_stderr_envelope("POST", url, h))
        return EXIT_TRANSPORT
    if _is_server_transport(st):
        d = _unwrap_detail(j) if isinstance(j, dict) else j
        _emit_stderr_json(
            {"error": "transport", "message": f"HTTP {st}", "url": url, "detail": d},
        )
        return EXIT_TRANSPORT
    if st == 200 and isinstance(j, dict):
        _emit_stdout_json({"released": bool(j.get("released", True))})
        return EXIT_OK
    if st == 409:
        raw = j if isinstance(j, dict) else {}
        d = _unwrap_detail(raw)
        _emit_stderr_json(d if isinstance(d, dict) else {"detail": d})
        return EXIT_LEASE_DENIED
    if st == 422:
        d2 = _unwrap_detail(j) if isinstance(j, dict) else j
        _emit_stderr_json({"error": "validation", "detail": d2})
        return EXIT_USAGE
    d = _unwrap_detail(j) if isinstance(j, dict) else j
    _emit_stderr_json({"error": "unexpected", "http_status": st, "detail": d})
    return EXIT_USAGE


def _add_scope(p: argparse.ArgumentParser) -> None:
    p.add_argument("--company-id", required=True, help="Scope company_id.")
    p.add_argument("--repository-id", required=True, help="Scope repository_id.")
    p.add_argument("--plan-id", required=True, help="Scope plan_id.")
    p.add_argument("--task-id", required=True, help="Scope task_id.")
    p.add_argument("--workstream-id", required=True, help="Scope workstream_id.")


def _add_common(p: argparse.ArgumentParser) -> None:
    _add_scope(p)
    p.add_argument(
        "--base-url",
        default=None,
        help=f"State API base URL (overrides {ENV_BASE} and default {_DEFAULT_BASE!r}).",
    )
    p.add_argument(
        "--timeout-ms",
        type=int,
        default=_DEFAULT_TIMEOUT_MS,
        help=f"Request timeout in ms (default {_DEFAULT_TIMEOUT_MS}; clamp 100-60000).",
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon checkpoint",
        description="State-api checkpoint and lease tools (JSON in/out).",
    )
    sp = p.add_subparsers(dest="checkpoint_command", required=True)
    pr = sp.add_parser("read", help="GET /state/checkpoint for scope (query string).")
    _add_common(pr)

    pw = sp.add_parser("write", help="PUT /state/checkpoint (optimistic version + lease).")
    _add_common(pw)
    pw.add_argument("--handoff-id", required=True, help="Handoff id.")
    pw.add_argument("--phase", required=True, help="Phase label.")
    pw.add_argument("--phase-status", required=True, help="Phase status string.")
    pw.add_argument(
        "--expected-version",
        type=int,
        required=True,
        help="Expected state_version (optimistic lock; wire field state_version).",
    )
    pw.add_argument("--lease-token", required=True, help="Lease token proof.")
    bg = pw.add_mutually_exclusive_group()
    bg.add_argument("--body-file", default="", metavar="PATH", help="JSON object with whitelisted keys.")
    bg.add_argument(
        "--stdin",
        action="store_true",
        help="Read whitelisted keys JSON from stdin (mutually exclusive with --body-file).",
    )

    pa = sp.add_parser("lease-acquire", help="POST /state/lease/acquire (flat body).")
    _add_common(pa)
    pa.add_argument("--owner-agent-run-id", required=True, help="Owner agent run id.")
    pa.add_argument("--owner-actor-id", required=True, help="Owner actor id.")
    pa.add_argument(
        "--ttl-seconds",
        type=int,
        required=True,
        help="Lease TTL (1-3600).",
    )

    pnr = sp.add_parser("lease-renew", help="POST /state/lease/renew (nested scope_ids).")
    _add_common(pnr)
    pnr.add_argument("--lease-token", required=True, help="Current lease token.")
    pnr.add_argument("--ttl-seconds", type=int, required=True, help="New TTL (1-3600).")

    pnl = sp.add_parser("lease-release", help="POST /state/lease/release (nested scope_ids).")
    _add_common(pnl)
    pnl.add_argument("--lease-token", required=True, help="Lease token to release.")

    return p


def run(argv: list[str] | None = None) -> int:
    p = _build_parser()
    av = list(sys.argv[1:] if argv is None else argv)
    try:
        args = p.parse_args(av)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return EXIT_OK
        return EXIT_USAGE
    if args.checkpoint_command == "read":
        return _cmd_read(args)
    if args.checkpoint_command == "write":
        return _cmd_write(args)
    if args.checkpoint_command == "lease-acquire":
        return _cmd_lease_acquire(args)
    if args.checkpoint_command == "lease-renew":
        return _cmd_lease_renew(args)
    if args.checkpoint_command == "lease-release":
        return _cmd_lease_release(args)
    return EXIT_USAGE
