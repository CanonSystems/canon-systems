#!/usr/bin/env python3
"""Validate memory secret endpoints and probe connectivity."""

from __future__ import annotations

import argparse
import json
import socket
from urllib.parse import urlparse

_MEMORY_HTTPS_URL_KEYS = (
    "KNOWLEDGE_API_URL",
    "KNOWLEDGE_WORKER_URL",
    "MEMORY_ADAPTER_URL",
    "CANON_STATE_API_URL",
)


def _client(profile: str, region: str):
    import boto3

    session = boto3.Session(profile_name=profile or None, region_name=region)
    return session.client("secretsmanager")


def _is_ip_host(host: str) -> bool:
    try:
        socket.inet_aton(host)
        return True
    except OSError:
        return False


def _probe(host: str, port: int, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "ok"
    except OSError as exc:
        return False, str(exc)


def validate_memory_url(*, key: str, value: str, timeout: float) -> tuple[bool, str, dict[str, object]]:
    """Return (ok, detail, info) for one URL. Empty value for CANON_STATE_API_URL skips checks."""
    info: dict[str, object] = {"key": key, "value": value}
    if key == "CANON_STATE_API_URL" and not (value or "").strip():
        info["skipped"] = True
        return True, "skipped (optional; may default from KNOWLEDGE_API_URL at runtime)", info
    if not (value or "").strip():
        return False, "missing value", info
    parsed = urlparse(value)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    info["host"] = host
    info["port"] = port
    info["scheme"] = parsed.scheme
    if parsed.scheme != "https":
        return False, "expected https:// for stable memory-plane URLs", info
    if not host:
        return False, "missing host", info
    if _is_ip_host(host):
        return False, "host is a literal IPv4 (use stable DNS)", info
    ok, detail = _probe(host, int(port), timeout)
    info["connect_ok"] = ok
    return ok, detail, info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--secret-id", required=True)
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args(argv)

    client = _client(args.profile, args.region)
    raw = client.get_secret_value(SecretId=args.secret_id)["SecretString"]
    payload = json.loads(raw)

    failures = 0
    for key in _MEMORY_HTTPS_URL_KEYS:
        value = str(payload.get(key, "")).strip()
        ok, detail, info = validate_memory_url(key=key, value=value, timeout=args.timeout)
        print(f"{key}: {value or '(empty)'}")
        print(f"  ok={ok} detail={detail} info={info}")
        if not ok:
            failures += 1

    if failures:
        print(f"validation failed: {failures} issue(s) detected")
        return 1
    print("validation passed: stable https:// DNS endpoints reachable (or CANON_STATE_API_URL omitted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
