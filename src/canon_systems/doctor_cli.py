"""`canon doctor` — local wiring diagnostics (tenant, cache, brittle URLs)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from .aws_secrets import _cache_file_path, resolve_canon_systems_secret_id
from .shared import load_env_file, repo_root

_IPV4_IN_URL = re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?")


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

    secret_id = ""
    for k, v in local.items():
        ks, vs = k.strip(), (v or "").strip()
        if ks and vs:
            os.environ.setdefault(ks, vs)
    if company_env:
        os.environ.setdefault("COMPANY_ID", company_env)
    if repo_env:
        os.environ.setdefault("REPOSITORY_ID", repo_env)
    try:
        secret_id = resolve_canon_systems_secret_id()
    except Exception:
        secret_id = ""

    if args.fix_cache:
        cpath = _cache_file_path()
        if cpath.is_file():
            cpath.unlink()
            if not args.json:
                print(f"canon doctor: removed {cpath}", file=sys.stderr)

    out: dict[str, object] = {
        "repo_root": str(root),
        "memory_layer_local_env": str(env_path),
        "company_id_file": company_env,
        "repository_id_file": repo_env,
        "context_latest_company_id": ctx_company,
        "context_latest_repository_id": ctx_repo,
        "tenant_context_mismatch": mismatch,
        "resolved_secret_id": secret_id,
        "aws_secret_cache": cache,
        "env_files_with_literal_ipv4_urls": [
            {"path": a, "key": b, "value": c} for a, b, c in ip_hits
        ],
    }

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=True))
        return 1 if mismatch or ip_hits else 0

    print(f"repo_root: {root}")
    print(f"wiring: {env_path} ({'ok' if env_path.is_file() else 'MISSING'})")
    print(f"COMPANY_ID (file/env): {company_env or '(unset)'}")
    print(f"REPOSITORY_ID (file/env): {repo_env or '(unset)'}")
    if secret_id:
        print(f"resolved Secrets Manager id: {secret_id}")
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

    return 1 if mismatch or ip_hits else 0


__all__ = ["run"]
