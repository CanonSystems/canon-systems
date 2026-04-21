#!/usr/bin/env python3
"""Rewrite memory-layer secrets to canonical domain-based endpoints."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _client(profile: str, region: str) -> Any:
    import boto3

    session = boto3.Session(profile_name=profile or None, region_name=region)
    return session.client("secretsmanager")


def _is_memory_secret(name: str) -> bool:
    return "/memory-layer__" in name


def _rewrite_payload(payload: dict[str, Any], base_url: str, phase: str) -> dict[str, Any]:
    updated = dict(payload)
    updated["KNOWLEDGE_API_URL"] = base_url
    updated["KNOWLEDGE_WORKER_URL"] = base_url
    updated["MEMORY_ADAPTER_URL"] = base_url
    updated["CANON_AUTH_PHASE"] = phase
    updated["CANON_AUTH_MODE"] = "cognito" if phase == "enforce" else "dual"
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="", help="AWS profile name.")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--prefix", default="canon-memory-dev")
    parser.add_argument("--domain", default="memory.canon-systems.com")
    parser.add_argument("--scheme", default="https")
    parser.add_argument("--phase", default="prepare", choices=("prepare", "canary", "enforce"))
    parser.add_argument("--apply", action="store_true", help="Write updated values back to secrets.")
    args = parser.parse_args(argv)

    base_url = f"{args.scheme}://{args.domain}".rstrip("/")
    client = _client(args.profile, args.region)
    paginator = client.get_paginator("list_secrets")
    matched: list[str] = []

    for page in paginator.paginate():
        for secret in page.get("SecretList", []):
            name = secret.get("Name", "")
            if not isinstance(name, str):
                continue
            if not name.startswith(f"{args.prefix}/"):
                continue
            if not _is_memory_secret(name):
                continue
            matched.append(name)

    if not matched:
        print("No matching secrets found.")
        return 0

    print(f"Found {len(matched)} matching secret(s).")
    for name in matched:
        value = client.get_secret_value(SecretId=name)["SecretString"]
        payload = json.loads(value)
        updated = _rewrite_payload(payload, base_url, args.phase)
        print(f"- {name}")
        print(f"  KNOWLEDGE_API_URL: {payload.get('KNOWLEDGE_API_URL', '')} -> {updated['KNOWLEDGE_API_URL']}")
        print(f"  CANON_AUTH_PHASE: {payload.get('CANON_AUTH_PHASE', '')} -> {updated['CANON_AUTH_PHASE']}")
        if args.apply:
            client.put_secret_value(SecretId=name, SecretString=json.dumps(updated))
            print("  wrote updated secret value")
        else:
            print("  dry-run only (use --apply to persist)")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
