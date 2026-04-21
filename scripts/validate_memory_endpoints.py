#!/usr/bin/env python3
"""Validate memory secret endpoints and probe connectivity."""

from __future__ import annotations

import argparse
import json
import socket
from urllib.parse import urlparse


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
    for key in ("KNOWLEDGE_API_URL", "KNOWLEDGE_WORKER_URL", "MEMORY_ADAPTER_URL"):
        value = str(payload.get(key, "")).strip()
        parsed = urlparse(value)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        ip_flag = _is_ip_host(host)
        ok, detail = _probe(host, int(port), args.timeout) if host else (False, "missing host")
        status = "ok" if ok else "fail"
        print(f"{key}: {value}")
        print(f"  host={host} port={port} raw_ip={ip_flag} connect={status} detail={detail}")
        if ip_flag or not ok:
            failures += 1

    if failures:
        print(f"validation failed: {failures} issue(s) detected")
        return 1
    print("validation passed: all endpoints reachable and domain-based")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
