#!/usr/bin/env python3
"""Clone a Canon memory-layer secret (JSON SecretString) in AWS Secrets Manager.

Use this when onboarding a new repository/tenant by copying URLs and bearer material
from an existing secret to a newly created secret id (same shape as
``{prefix}/memory-layer__<company-slug>__<repo-slug>``).

Typical flows:

- Dry-run (default): validate source exists and print destination secret id::
    python scripts/clone_memory_layer_secret.py \\
      --profile canon-systems-v2 --region us-east-1 \\
      --from-company CSC --from-repository other-repo \\
      --to-company CSC --to-repository new-repo \\
      --prefix canon-memory-dev

- Apply (create destination or replace value)::
    python scripts/clone_memory_layer_secret.py ... --apply

- Explicit ids instead of tenant slugs::
    python scripts/clone_memory_layer_secret.py \\
      --source-secret-id canon-memory-dev/memory-layer__csc__template \\
      --dest-secret-id canon-memory-dev/memory-layer__csc__new-repo \\
      --apply

Uses the same slug rules as ``canon_systems.aws_secrets`` (hyphen-separated
identifiers from COMPANY_ID / REPOSITORY_ID).

Requirements: boto3, AWS credentials (profile / env), Secrets Manager IAM
permissions on get on the source and create/put on the destination."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


def _slug(segment: str) -> str:
    cleaned = segment.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    return cleaned.strip("-") or "unknown"


def _memory_layer_secret_name(prefix: str, company_id: str, repository_id: str) -> str:
    pfx = prefix.strip().rstrip("/")
    return f"{pfx}/memory-layer__{_slug(company_id)}__{_slug(repository_id)}"


def _client(profile: str, region: str) -> Any:
    import boto3

    session = boto3.Session(profile_name=profile or None, region_name=region)
    return session.client("secretsmanager")


def _secret_exists(client: Any, secret_id: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        client.describe_secret(SecretId=secret_id)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "ResourceNotFoundException":
            return False
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", default="", help="AWS profile name.")
    parser.add_argument("--region", default="us-east-1")

    grp = parser.add_argument_group(
        "source / destination",
        "Provide either explicit secret ids (--source-secret-id / --dest-secret-id) "
        "or (--from-company, --from-repository) and (--to-company, --to-repository) with --prefix.",
    )
    grp.add_argument("--prefix", default="canon-memory-dev", help="MEMORY_LAYER_AWS_SECRET_NAME_PREFIX value.")
    grp.add_argument("--source-secret-id", default="", metavar="SECRET_ID")
    grp.add_argument("--dest-secret-id", default="", metavar="SECRET_ID")
    grp.add_argument("--from-company", default="", metavar="COMPANY_ID")
    grp.add_argument("--from-repository", default="", metavar="REPOSITORY_ID")
    grp.add_argument("--to-company", default="", metavar="COMPANY_ID")
    grp.add_argument("--to-repository", default="", metavar="REPOSITORY_ID")
    grp.add_argument(
        "--apply",
        action="store_true",
        help="Create destination secret if missing or replace SecretString when it exists.",
    )

    args = parser.parse_args(argv)

    prefix = args.prefix.strip() or "canon-memory-dev"

    source_sid = args.source_secret_id.strip()
    if not source_sid:
        if not (args.from_company.strip() and args.from_repository.strip()):
            parser.error("Set --source-secret-id or both --from-company and --from-repository.")
        source_sid = _memory_layer_secret_name(prefix, args.from_company, args.from_repository)

    dest_sid = args.dest_secret_id.strip()
    if not dest_sid:
        if not (args.to_company.strip() and args.to_repository.strip()):
            parser.error("Set --dest-secret-id or both --to-company and --to-repository.")
        dest_sid = _memory_layer_secret_name(prefix, args.to_company, args.to_repository)

    if dest_sid == source_sid:
        print("error: source and destination must differ.", file=sys.stderr)
        return 2

    client = _client(args.profile, args.region)

    resp = client.get_secret_value(SecretId=source_sid)
    raw = resp.get("SecretString")
    if not isinstance(raw, str) or not raw.strip():
        print(f"error: secret {source_sid} has empty SecretString.", file=sys.stderr)
        return 1

    payload = raw.strip()

    exists = _secret_exists(client, dest_sid)

    print(f"Source:      {source_sid}")
    print(f"Destination: {dest_sid} ({'exists' if exists else 'missing'})")
    try:
        parsed = json.loads(payload)
        n_keys = len(parsed) if isinstance(parsed, dict) else 0
    except json.JSONDecodeError:
        n_keys = 0
    if n_keys:
        print(f"Payload:     JSON object ({n_keys} top-level keys).")
    else:
        print("Payload:     non-JSON or empty.")

    if not args.apply:
        print("")
        print("Dry run only. Re-run with --apply to write the destination.")
        return 0

    if exists:
        client.put_secret_value(SecretId=dest_sid, SecretString=payload)
        print(f"Replaced SecretString: {dest_sid}")
    else:
        client.create_secret(Name=dest_sid, SecretString=payload)
        print(f"Created secret: {dest_sid}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise

