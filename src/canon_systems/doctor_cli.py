"""`canon doctor` — local wiring diagnostics (tenant, cache, brittle URLs)."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import socket
import sys
import time
import urllib.parse
from pathlib import Path

from .aws_secrets import _cache_file_path, build_aws_secrets_resolution_attestation
from .shared import _resolve_ipv4_via_dig, _runtime_canon_version_string, load_env_file, repo_root

_IPV4_IN_URL = re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?")

# Canonical Secrets Manager keys that should use stable https:// DNS (not raw task IPs).
CANONICAL_MEMORY_HTTPS_KEYS: tuple[str, ...] = (
    "KNOWLEDGE_API_URL",
    "KNOWLEDGE_WORKER_URL",
    "MEMORY_ADAPTER_URL",
    "CANON_STATE_API_URL",
)

# Same keys as layered merge: process env wins via ``setdefault`` over repo-local file values.
_DOCTOR_ENV_PRECEDENCE_KEYS: tuple[str, ...] = (
    "AWS_PROFILE",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
)


def _scan_env_files_for_raw_ips(paths: list[Path]) -> list[tuple[str, str, str]]:
    """Return list of (path, key, value) for lines that look like URLs with literal IPv4."""
    hits: list[tuple[str, str, str]] = []
    for path in paths:
        if not path.is_file():
            continue
        data = load_env_file(path)
        for key, value in sorted(data.items()):
            v = (value or "").strip()
            if not v or "://" not in v:
                continue
            if _IPV4_IN_URL.search(v):
                hits.append((str(path), key, v))
    return hits


def _context_tenant(root: Path) -> tuple[str, str]:
    md = root / ".canon" / "memory" / "context-latest.md"
    if not md.is_file():
        return "", ""
    text = md.read_text(encoding="utf-8", errors="replace")
    company = ""
    repo = ""
    for line in text.splitlines():
        if "company_id:" in line and "`" in line:
            parts = line.split("`")
            if len(parts) >= 2:
                company = parts[1].strip()
        if "repository_id:" in line and "`" in line:
            parts = line.split("`")
            if len(parts) >= 2:
                repo = parts[1].strip()
    return company, repo


def _package_version() -> str:
    """Same version as ``canon --version`` / loaded ``canon_systems.__version__``."""
    return _runtime_canon_version_string()


def _host_from_knowledge_base(url: str) -> str | None:
    u = (url or "").strip()
    if not u or "://" not in u:
        return None
    try:
        host = urllib.parse.urlparse(u).hostname
    except ValueError:
        return None
    if not host:
        return None
    if re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", host):
        return None
    return host


def _read_cache_env_loose() -> dict[str, str]:
    """Read ``env`` from the secrets cache JSON even if TTL expired (for diagnostics)."""
    path = _cache_file_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    env = raw.get("env")
    if not isinstance(env, dict):
        return {}
    return {str(k): str(v) for k, v in env.items()}


def _memory_hostname_for_doctor(local: dict[str, str]) -> str | None:
    h = _host_from_knowledge_base(local.get("KNOWLEDGE_API_URL", ""))
    if h:
        return h
    cached = _read_cache_env_loose()
    return _host_from_knowledge_base(cached.get("KNOWLEDGE_API_URL", ""))


def _libc_resolver_tcp_ok(host: str, port: int = 443) -> bool:
    try:
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        return True
    except OSError:
        return False


def _curl_resolve_healthz_snippet(*, host: str, ipv4: str, canon_version: str) -> str:
    health = f"https://{host}/healthz"
    ua = f"canon-systems/{canon_version}"
    return (
        "curl -sS "
        f"-A {shlex.quote(ua)} "
        f"--resolve {shlex.quote(f'{host}:443:{ipv4}')} "
        f"{shlex.quote(health)}"
    )


def _dns_warp_check(local: dict[str, str]) -> dict[str, object]:
    host = _memory_hostname_for_doctor(local)
    if not host:
        return {
            "status": "skipped",
            "reason": "no KNOWLEDGE_API_URL hostname in .canon/memory-layer.local.env or ~/.canon/memory-layer-aws-cache.json",
        }
    libc_ok = _libc_resolver_tcp_ok(host, 443)
    dig_a = _resolve_ipv4_via_dig(host)
    split = bool(dig_a and not libc_ok)
    ver = _package_version()
    snippet = _curl_resolve_healthz_snippet(host=host, ipv4=dig_a, canon_version=ver) if dig_a else ""
    return {
        "status": "ok",
        "memory_hostname": host,
        "libc_resolver_ok": libc_ok,
        "dig_a_record": dig_a or None,
        "likely_split_dns_cloudflare_warp": split,
        "note": (
            "macOS libc resolver failed but dig found an A record — typical of Cloudflare WARP "
            "(127.0.2.x DNS). `canon` 3.5.1+ works around this for Canon HTTP clients; raw curl "
            "needs --resolve or a WARP split-tunnel / system DNS adjustment."
        )
        if split
        else "",
        "curl_resolve_healthz": snippet,
    }


def _doctor_env_precedence_attestation(
    local: dict[str, str], before_tracked: dict[str, str]
) -> dict[str, object]:
    """Detect process-env vs repo-local `memory-layer.local.env` shadowing (same rules as layered setdefault)."""
    mismatches: list[dict[str, str]] = []
    for key in _DOCTOR_ENV_PRECEDENCE_KEYS:
        layered = (local.get(key) or "").strip()
        proc = (before_tracked.get(key) or "").strip()
        effective = (os.environ.get(key) or "").strip()
        if layered and proc and layered != proc and effective == proc:
            mismatches.append(
                {
                    "env_key": key,
                    "process_env_value": proc,
                    "layered_file_value": layered,
                    "effective_value": effective,
                    "reason": "process_env_shadows_layered_file",
                }
            )
    return {
        "schema_version": 1,
        "tracked_keys": list(_DOCTOR_ENV_PRECEDENCE_KEYS),
        "mismatches": mismatches,
        "credential_resolution_degraded": bool(mismatches),
        "layered_env_source": "memory-layer.local.env",
        "layered_env_apply_observed": True,
    }


def _build_doctor_credential_attestation(
    local: dict[str, str], before_tracked: dict[str, str]
) -> dict[str, object]:
    """Non-secret credential + Secrets Manager attestation aligned with doctor's env merge."""
    aws_block = build_aws_secrets_resolution_attestation()
    env_block = _doctor_env_precedence_attestation(local, before_tracked)
    degraded = bool(env_block.get("credential_resolution_degraded")) or bool(
        aws_block.get("credential_resolution_degraded")
    )
    return {
        "schema_version": 1,
        "aws_secrets_resolution": aws_block,
        "env_precedence": env_block,
        "credential_resolution_degraded": degraded,
    }


def _cache_status() -> dict[str, object]:
    path = _cache_file_path()
    out: dict[str, object] = {"path": str(path), "exists": path.is_file()}
    if not path.is_file():
        return out
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        out["error"] = str(exc)
        return out
    if isinstance(raw, dict):
        out["secret_id"] = raw.get("secret_id", "")
        try:
            exp = float(raw.get("expires_at", 0))
            out["expires_at_unix"] = exp
            out["expires_in_sec"] = max(0.0, exp - time.time())
        except (TypeError, ValueError):
            pass
    return out


def run(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="canon doctor",
        description=(
            "Diagnose common Canon wiring issues: tenant env vs last preflight context, "
            "AWS secret cache staleness, and http://IP literals in env files."
        ),
    )
    p.add_argument(
        "--fix-cache",
        action="store_true",
        help="Delete ~/.canon/memory-layer-aws-cache.json if it exists (forces next command to refetch Secrets Manager).",
    )
    p.add_argument(
        "--curl-resolve-snippet",
        action="store_true",
        help=(
            "Print a one-line curl that uses --resolve to reach KNOWLEDGE_API_URL /healthz "
            "(for hosts where libc cannot resolve but dig can, e.g. Cloudflare WARP)."
        ),
    )
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON to stdout.")
    args = p.parse_args(argv)

    root = repo_root()
    env_path = root / ".canon" / "memory-layer.local.env"
    local = load_env_file(env_path) if env_path.is_file() else {}
    company_env = (local.get("COMPANY_ID") or os.environ.get("COMPANY_ID", "")).strip()
    repo_env = (local.get("REPOSITORY_ID") or os.environ.get("REPOSITORY_ID", "")).strip()

    scan_paths = [
        Path.home() / ".canon" / "canon-systems.env",
        Path.home() / ".canon" / "canon-memory-layer.env",
        Path.home() / ".canon" / "memory-layer.secrets.env",
        root / ".canon" / "memory-layer.team.env",
        root / ".canon" / "scoper-chat.env",
        env_path,
        root / ".canon" / "memory-layer.secrets.env",
    ]
    ip_hits = _scan_env_files_for_raw_ips(scan_paths)
    ctx_company, ctx_repo = _context_tenant(root)
    cache = _cache_status()

    mismatch = False
    if company_env and ctx_company and company_env != ctx_company:
        mismatch = True
    if repo_env and ctx_repo and repo_env != ctx_repo:
        mismatch = True

    before_tracked = {k: (os.environ.get(k) or "").strip() for k in _DOCTOR_ENV_PRECEDENCE_KEYS}
    for k, v in local.items():
        ks, vs = k.strip(), (v or "").strip()
        if ks and vs:
            os.environ.setdefault(ks, vs)
    if company_env:
        os.environ.setdefault("COMPANY_ID", company_env)
    if repo_env:
        os.environ.setdefault("REPOSITORY_ID", repo_env)
    credential_attestation = _build_doctor_credential_attestation(local, before_tracked)
    aws_res = credential_attestation.get("aws_secrets_resolution")
    secret_id = ""
    if isinstance(aws_res, dict):
        sid = aws_res.get("resolved_secret_id", "")
        secret_id = sid if isinstance(sid, str) else ""

    if args.fix_cache:
        cpath = _cache_file_path()
        if cpath.is_file():
            cpath.unlink()
            if not args.json:
                print(f"canon doctor: removed {cpath}", file=sys.stderr)

    dns_info = _dns_warp_check(local)

    if args.curl_resolve_snippet:
        snippet = dns_info.get("curl_resolve_healthz") if isinstance(dns_info, dict) else ""
        if not isinstance(snippet, str) or not snippet.strip():
            print(
                "canon doctor: no curl --resolve snippet (set KNOWLEDGE_API_URL or refresh AWS cache).",
                file=sys.stderr,
            )
            return 1
        print(snippet)
        return 0

    out: dict[str, object] = {
        "repo_root": str(root),
        "memory_layer_local_env": str(env_path),
        "company_id_file": company_env,
        "repository_id_file": repo_env,
        "context_latest_company_id": ctx_company,
        "context_latest_repository_id": ctx_repo,
        "tenant_context_mismatch": mismatch,
        "credential_attestation": credential_attestation,
        "resolved_secret_id": secret_id,
        "aws_secret_cache": cache,
        "canonical_memory_https_url_keys": list(CANONICAL_MEMORY_HTTPS_KEYS),
        "env_files_with_literal_ipv4_urls": [
            {"path": a, "key": b, "value": c} for a, b, c in ip_hits
        ],
        "dns": dns_info,
    }

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=True))
        return 1 if mismatch or ip_hits else 0

    aws_att = credential_attestation["aws_secrets_resolution"]
    if not isinstance(aws_att, dict):
        aws_att = {}
    env_prec = credential_attestation["env_precedence"]
    if not isinstance(env_prec, dict):
        env_prec = {}
    eff_prof = (aws_att.get("effective_aws_profile") or "").strip() or "(unset)"
    repo_prof = (local.get("AWS_PROFILE") or "").strip() or "(unset)"
    res_status = ""
    res_obj = aws_att.get("resolution")
    if isinstance(res_obj, dict):
        res_status = str(res_obj.get("status", "") or "")
    cache_hit = aws_att.get("cache_hit_when_known")
    if cache_hit is True:
        cache_hit_s = "hit"
    elif cache_hit is False:
        cache_hit_s = "miss"
    else:
        cache_hit_s = "n/a"

    print(f"repo_root: {root}")
    print(f"wiring: {env_path} ({'ok' if env_path.is_file() else 'MISSING'})")
    print(f"COMPANY_ID (file/env): {company_env or '(unset)'}")
    print(f"REPOSITORY_ID (file/env): {repo_env or '(unset)'}")
    print(
        "credential resolution: "
        f"effective AWS_PROFILE={eff_prof!r} | "
        f"repo-local AWS_PROFILE (file)={repo_prof!r} | "
        f"resolution={res_status or '(n/a)'} | "
        f"cache_hit={cache_hit_s}"
    )
    if secret_id:
        print(f"resolved Secrets Manager id: {secret_id}")
    mismatches = env_prec.get("mismatches") if isinstance(env_prec.get("mismatches"), list) else []
    if mismatches:
        for m in mismatches:
            if not isinstance(m, dict):
                continue
            key = m.get("env_key", "env")
            proc_v = m.get("process_env_value", "")
            file_v = m.get("layered_file_value", "")
            print(
                f"WARNING: process {key}={proc_v!r} shadows repo-local memory-layer.local.env "
                f"({key}={file_v!r}) — unset {key} in your shell or align values so Canon uses the intended profile.",
                file=sys.stderr,
            )
    print(f"context-latest.md: company_id={ctx_company or '(none)'} repository_id={ctx_repo or '(none)'}")
    if mismatch:
        print(
            "WARNING: preflight context tenant differs from repo wiring — "
            "run `env -u COMPANY_ID -u REPOSITORY_ID canon preflight \"tenant check\"` "
            "or clear stray tenant vars in your shell/Cursor.",
            file=sys.stderr,
        )
    c = cache
    if c.get("exists"):
        print(f"AWS secret cache: {c.get('path')} (secret_id={c.get('secret_id', '')!r})")
        if "expires_in_sec" in c:
            print(f"  approx. TTL remaining: {int(float(c['expires_in_sec']))}s")
    else:
        print("AWS secret cache: (none)")
    print(
        "After changing Secrets Manager JSON, clear cache: "
        "`canon doctor --fix-cache` or `rm -f ~/.canon/memory-layer-aws-cache.json`"
    )
    print(
        "Secrets Manager canonical shape: stable https:// DNS (same host is OK) for "
        + ", ".join(CANONICAL_MEMORY_HTTPS_KEYS)
        + "; MEMORY_ADAPTER_URL may match KNOWLEDGE_API_URL when POST /memory/search is on knowledge-api."
    )
    if ip_hits:
        print("WARNING: literal IPv4 URLs in env files (brittle on Fargate / redeploy):", file=sys.stderr)
        for path_s, key, val in ip_hits:
            print(f"  {path_s} :: {key}={val}", file=sys.stderr)
        print(
            "Prefer a stable DNS name (ALB/NLB) in KNOWLEDGE_* / MEMORY_ADAPTER_URL — see platform docs.",
            file=sys.stderr,
        )
    else:
        print("env scan: no http(s)://x.x.x.x URLs found in standard Canon env paths")

    if isinstance(dns_info, dict) and dns_info.get("status") == "ok":
        host = dns_info.get("memory_hostname", "")
        libc = dns_info.get("libc_resolver_ok")
        dig_a = dns_info.get("dig_a_record")
        split = dns_info.get("likely_split_dns_cloudflare_warp")
        print(
            f"dns check: host={host!r} libc_resolver_ok={libc} dig_a_record={dig_a!r}",
        )
        if split:
            print(
                "WARNING: split-brain DNS (libc cannot resolve; dig can) — often Cloudflare WARP. "
                "Canon CLI 3.5.1+ uses a dig fallback for HTTP(S). For raw curl, run:\n  "
                f"  canon doctor --curl-resolve-snippet",
                file=sys.stderr,
            )
        elif dig_a and libc:
            print("dns check: libc and dig agree; plain curl should resolve this host.")
    elif isinstance(dns_info, dict) and dns_info.get("status") == "skipped":
        print(f"dns check: skipped ({dns_info.get('reason', '')})")

    return 1 if mismatch or ip_hits else 0


__all__ = ["run", "CANONICAL_MEMORY_HTTPS_KEYS"]
