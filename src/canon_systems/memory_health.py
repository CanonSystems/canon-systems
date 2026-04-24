"""Probe memory platform backends via /healthz; emit JSON and exit for merge gates."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .shared import apply_layered_canon_env_for_repo, canon_urlopen, load_env_file, repo_root

SCHEMA_VERSION = "1"

BACKENDS: dict[str, str] = {
    "canonical": "KNOWLEDGE_API_URL",
    "mempalace": "MEMORY_ADAPTER_URL",
    "state": "STATE_API_URL",
    "graph": "AXON_SERVICE_URL",
}

_DEFAULT_REQUIRED: tuple[str, ...] = ("canonical", "mempalace")
_BACKENDS_ORDER: tuple[str, ...] = ("canonical", "mempalace", "state", "graph")

# Match shared.load_repo_context defaults for the two always-resolvable bases.
_HARDCODED_BASE_URL: dict[str, str] = {
    "canonical": "http://localhost:8080",
    "mempalace": "http://localhost:8090",
}

# Checkpoint / resume code uses CANON_STATE_API_URL; keep STATE_API_URL first for precedence.
_STATE_URL_ENV_KEYS: tuple[str, ...] = ("STATE_API_URL", "CANON_STATE_API_URL")


def _env_keys_for_backend(name: str, primary_var: str) -> tuple[str, ...]:
    if name == "state":
        return _STATE_URL_ENV_KEYS
    return (primary_var,)


_DEFAULT_TIMEOUT_MS = 2000
_TIMEOUT_MIN_MS = 100
_TIMEOUT_MAX_MS = 60000

_ENV_TIMEOUT = "CANON_MEMORY_HEALTH_TIMEOUT_MS"
_ENV_REQUIRED = "CANON_MEMORY_HEALTH_REQUIRED"


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, indent=2) + "\n"


def _trunc_err(msg: str, *, max_len: int = 200) -> str:
    line = " ".join(msg.split())
    if len(line) <= max_len:
        return line
    return line[: max(0, max_len - 1)] + "…"


def _parse_body_status(obj: Any) -> str | None:
    if not isinstance(obj, dict) or "status" not in obj:
        return None
    raw = obj.get("status")
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw.strip().lower() or None
    return str(raw).lower()


def _probe(url: str, timeout_ms: int) -> dict[str, Any]:
    """Single-flight GET; never raises. `timeout_ms` is applied as urllib timeout in seconds."""
    t0 = time.perf_counter()
    out: dict[str, Any] = {
        "http_status": 0,
        "body_text": "",
        "body_json": None,
        "error": None,
        "latency_ms": 0,
    }
    to_s = max(timeout_ms, 1) / 1000.0
    req = urllib.request.Request(url=url, method="GET", headers={"Accept": "application/json"})
    try:
        with canon_urlopen(req, timeout_s=to_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            out["http_status"] = int(resp.getcode() or 0)
            out["body_text"] = raw
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                out["body_json"] = None
            else:
                out["body_json"] = parsed if isinstance(parsed, dict) else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        out["http_status"] = int(exc.code or 0)
        out["body_text"] = raw
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            out["body_json"] = None
        else:
            out["body_json"] = parsed if isinstance(parsed, dict) else None
        out["error"] = f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        out["error"] = str(exc.reason) if exc.reason is not None else f"URLError: {exc!r}"
    except OSError as exc:
        out["error"] = str(exc)
    out["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    return out


def _healthz_url(base: str) -> str:
    return f"{base.rstrip('/')}/healthz"


def _resolve_env_urls(root: Path) -> dict[str, str | None]:
    """Per backend: process env > memory-layer.local.env > scoper-chat.env > hard default (first two)."""
    local = load_env_file(root / ".canon" / "memory-layer.local.env")
    scop = load_env_file(root / ".canon" / "scoper-chat.env")
    out: dict[str, str | None] = {}
    for name, var in BACKENDS.items():
        keys = _env_keys_for_backend(name, var)
        v = ""
        for k in keys:
            v = os.environ.get(k, "").strip()
            if v:
                break
        if v:
            out[name] = v.rstrip("/")
            continue
        for k in keys:
            v = (local.get(k) or "").strip()
            if v:
                break
        if v:
            out[name] = v.rstrip("/")
            continue
        for k in keys:
            v = (scop.get(k) or "").strip()
            if v:
                break
        if v:
            out[name] = v.rstrip("/")
            continue
        if name in _HARDCODED_BASE_URL:
            out[name] = _HARDCODED_BASE_URL[name].rstrip("/")
        else:
            out[name] = None
    return out


def _resolve_timeout_ms(cli_val: int | None, env_val: str | None) -> int:
    if cli_val is not None:
        n = int(cli_val)
        if _TIMEOUT_MIN_MS <= n <= _TIMEOUT_MAX_MS:
            return n
        print(
            f"memory-health: invalid --timeout-ms {cli_val!r}; using default {_DEFAULT_TIMEOUT_MS}ms",
            file=sys.stderr,
        )
        return _DEFAULT_TIMEOUT_MS
    if env_val is not None and str(env_val).strip() != "":
        try:
            n = int(str(env_val).strip())
        except ValueError:
            print(
                f"memory-health: invalid {_ENV_TIMEOUT}={env_val!r}; "
                f"using default {_DEFAULT_TIMEOUT_MS}ms",
                file=sys.stderr,
            )
            return _DEFAULT_TIMEOUT_MS
        if _TIMEOUT_MIN_MS <= n <= _TIMEOUT_MAX_MS:
            return n
        print(
            f"memory-health: invalid {_ENV_TIMEOUT}={env_val!r}; using default {_DEFAULT_TIMEOUT_MS}ms",
            file=sys.stderr,
        )
        return _DEFAULT_TIMEOUT_MS
    return _DEFAULT_TIMEOUT_MS


def _parse_csv(s: str) -> list[str]:
    return [p.strip().lower() for p in s.split(",") if p.strip()]


def _resolve_required(cli_csv: str | None) -> tuple[set[str], list[str]]:
    """(known required names, unknown token names) — AC5: CLI > env > default."""
    if cli_csv is not None:
        if not str(cli_csv).strip():
            return set(), []
        found: set[str] = set()
        unknown: list[str] = []
        for p in _parse_csv(str(cli_csv)):
            if p in BACKENDS:
                found.add(p)
            else:
                unknown.append(p)
        return found, unknown

    if _ENV_REQUIRED in os.environ:
        raw = os.environ.get(_ENV_REQUIRED, "")
        if not raw.strip():
            return set(), []
        found = set()
        unknown = []
        for p in _parse_csv(raw):
            if p in BACKENDS:
                found.add(p)
            else:
                unknown.append(p)
        return found, unknown

    return set(_DEFAULT_REQUIRED), []


def _classify(
    *,
    name: str,
    is_required: bool,
    base_url: str | None,
    probe: dict[str, Any],
) -> dict[str, Any]:
    if base_url is None or not str(base_url).strip():
        return {
            "name": name,
            "required": is_required,
            "endpoint_ref": "",
            "status": "not_configured",
            "latency_ms": 0,
            "version": None,
            "last_error": "URL not set",
        }

    ref = _healthz_url(str(base_url).strip())
    err = probe.get("error")
    http = int(probe.get("http_status") or 0)
    body_j = probe.get("body_json")
    lat = int(probe.get("latency_ms") or 0)
    is_json = isinstance(body_j, dict)

    last_err: str | None = None
    st: str

    # Distinguish transport failures (http==0) from HTTP error responses.
    if http and (http < 200 or http > 299):
        st = "unreachable" if is_required else "not_deployed"
        last_err = _trunc_err(f"HTTP {http} ({ref})")
    elif http == 0 and err is not None:
        st = "unreachable"
        last_err = _trunc_err(f"{err} ({ref})")
    elif http == 0:
        st = "unreachable"
        last_err = _trunc_err(f"request failed ({ref})")
    else:
        if not is_json:
            st = "degraded"
            last_err = "non-JSON body"
        else:
            sval = _parse_body_status(body_j)
            if sval is None or sval in ("ok", "healthy"):
                st = "ok"
            elif sval == "scaffold":
                st = "degraded"
            else:
                st = "degraded"
                last_err = f"body.status={sval!r}"
        if st == "ok":
            last_err = None

    if is_required and st == "not_deployed":
        st = "unreachable"
        if not last_err:
            last_err = _trunc_err(f"required backend not healthy ({ref})")

    bdict = body_j if is_json else None
    ver: str | None
    if bdict is not None and bdict.get("version") is not None:
        ver = bdict.get("version") if isinstance(bdict.get("version"), str) else str(bdict.get("version"))
    else:
        ver = None
    if st == "ok":
        last_err = None

    return {
        "name": name,
        "required": is_required,
        "endpoint_ref": ref,
        "status": st,
        "latency_ms": lat,
        "version": ver,
        "last_error": last_err,
    }


def _synth_unknown(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "required": True,
        "endpoint_ref": "",
        "status": "unknown_backend",
        "latency_ms": 0,
        "version": None,
        "last_error": f"unknown backend {name!r}",
    }


def _overall_status(rows: list[dict[str, Any]]) -> tuple[str, int]:
    """AC3: exit 0 iff every required row has status ok; no unknown rows."""
    for r in rows:
        if r.get("status") == "unknown_backend":
            return "unhealthy", 1
    required_rows = [r for r in rows if r.get("required") is True]
    for r in required_rows:
        if r.get("status") != "ok":
            return "unhealthy", 1
    # Optionals that are intentionally unset (no URL) are plug-and-play noise —
    # only flag degraded when an optional backend *was* configured but is unhealthy.
    optionals = [r for r in rows if r.get("required") is not True]
    for x in optionals:
        if x.get("status") == "not_configured":
            continue
        if x.get("status") != "ok":
            return "degraded", 0
    return "ok", 0


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="canon memory-health",
        description="Probe /healthz on memory platform backends; emit a JSON report to stdout.",
    )
    parser.add_argument(
        "--required",
        default=None,
        metavar="CSV",
        help=f"Comma-separated required backends (overrides {_ENV_REQUIRED}).",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=None,
        help=f"Per-backend probe budget in ms (default {_DEFAULT_TIMEOUT_MS}; max {_TIMEOUT_MAX_MS}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON output (default; idempotent).",
    )
    parser.add_argument(
        "--output",
        default="",
        metavar="PATH",
        help="Also write the JSON report to this path.",
    )
    parser.add_argument("--verbose", action="store_true", help="Log probe details to stderr.")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return int(code) if isinstance(code, int) else 1

    _ = args.json  # idempotent; stdout is always JSON

    root = os.environ.get("CANON_SYSTEMS_REPO_ROOT", "").strip()
    root_p = Path(root).expanduser().resolve() if root else repo_root()
    if root:
        os.environ["CANON_SYSTEMS_REPO_ROOT"] = str(root_p)
    # Match hooks / ask: URLs may live only in ~/.canon/*.env or AWS secrets.
    apply_layered_canon_env_for_repo(root_p)

    required_known, unknown_required = _resolve_required(args.required)
    # Required membership for known backends: explicit list or default pair.
    if args.required is not None or _ENV_REQUIRED in os.environ:
        must: set[str] = set(required_known)
    else:
        must = set(_DEFAULT_REQUIRED)

    timeout_ms = _resolve_timeout_ms(
        args.timeout_ms,
        os.environ.get(_ENV_TIMEOUT),
    )
    env_urls = _resolve_env_urls(root_p)

    rows: list[dict[str, Any]] = []
    for name in _BACKENDS_ORDER:
        is_req = name in must
        base = env_urls.get(name)
        if args.verbose:
            print(f"memory-health: probing {name} base={base!r}", file=sys.stderr)
        if base:
            p = _probe(_healthz_url(base), timeout_ms)
        else:
            p = {
                "http_status": 0,
                "body_text": "",
                "body_json": None,
                "error": None,
                "latency_ms": 0,
            }
        if args.verbose and base:
            print(
                f"memory-health:   -> status={p.get('http_status')} "
                f"latency_ms={p.get('latency_ms')}",
                file=sys.stderr,
            )
        row = _classify(name=name, is_required=is_req, base_url=base, probe=p)
        rows.append(row)

    for unk in unknown_required:
        rows.append(_synth_unknown(unk))

    overall, code = _overall_status(rows)
    if unknown_required:
        overall = "unhealthy"

    out_obj: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall_status": overall,
        "required_set": sorted(must) + sorted(unknown_required),
        "timeout_ms": timeout_ms,
        "backends": rows,
    }
    text = _json_dumps(out_obj)
    print(text, end="", file=sys.stdout)
    if args.output:
        outp = Path(args.output)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(text, encoding="utf-8")

    if unknown_required:
        return 1
    return code
