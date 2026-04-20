"""Optional AWS Secrets Manager integration for memory-layer environment variables."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


def slug_canon_systems_segment(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    return cleaned.strip("-") or "unknown"


# First segment of Secrets Manager ids:
#   {prefix}/memory-layer__<company-slug>__<repo-slug>
# This is an **AWS namespace / environment label**, not the canon-systems
# Python package version (3.x) and not your app or repo display name.
# Older stacks used LEGACY_*; new installs default to DEFAULT_* until you
# migrate secrets in AWS or override via company-registry / .env.
DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX = "canon-memory-dev"
LEGACY_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX = "canon-systems-v2-dev"


def resolve_canon_systems_secret_id() -> str:
    explicit = (os.environ.get("MEMORY_LAYER_AWS_SECRET_ID") or "").strip()
    if explicit:
        return explicit
    prefix = (os.environ.get("MEMORY_LAYER_AWS_SECRET_NAME_PREFIX") or "").strip()
    company = (os.environ.get("COMPANY_ID") or "").strip()
    repo = (os.environ.get("REPOSITORY_ID") or "").strip()
    if not (prefix and company and repo):
        return ""
    return (
        f"{prefix}/memory-layer__{slug_canon_systems_segment(company)}__"
        f"{slug_canon_systems_segment(repo)}"
    )


def parse_secret_string(secret_string: str) -> dict[str, str]:
    stripped = secret_string.strip()
    if not stripped:
        return {}
    try:
        data: Any = json.loads(stripped)
    except json.JSONDecodeError:
        return _parse_dotenv_body(stripped)
    if isinstance(data, dict):
        out: dict[str, str] = {}
        for k, v in data.items():
            if not isinstance(k, str) or not k.strip():
                continue
            if isinstance(v, (str, int, float, bool)):
                out[k.strip()] = str(v)
            elif v is None:
                out[k.strip()] = ""
        return out
    return {}


def _parse_dotenv_body(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _cache_file_path() -> Path:
    return Path.home() / ".canon" / "memory-layer-aws-cache.json"


def _read_cache(secret_id: str, region_tag: str) -> dict[str, str] | None:
    if os.environ.get("MEMORY_LAYER_AWS_DISABLE_CACHE", "").strip().lower() in ("1", "true", "yes"):
        return None
    path = _cache_file_path()
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    if raw.get("secret_id") != secret_id or raw.get("region_tag") != region_tag:
        return None
    try:
        expires_at = float(raw.get("expires_at", 0))
    except (TypeError, ValueError):
        return None
    if time.time() > expires_at:
        return None
    env = raw.get("env")
    if not isinstance(env, dict):
        return None
    return {str(k): str(v) for k, v in env.items()}


def _write_cache(secret_id: str, region_tag: str, pairs: dict[str, str]) -> None:
    try:
        ttl = float(os.environ.get("MEMORY_LAYER_AWS_CACHE_TTL_SEC", "900"))
    except ValueError:
        ttl = 900.0
    ttl = max(60.0, ttl)
    path = _cache_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "secret_id": secret_id,
        "region_tag": region_tag,
        "expires_at": time.time() + ttl,
        "env": pairs,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _secretsmanager_client():
    try:
        import boto3
    except ImportError:
        return None
    region = (os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "").strip()
    if region:
        return boto3.client("secretsmanager", region_name=region)
    return boto3.client("secretsmanager")


def apply_canon_systems_secrets_from_aws() -> None:
    secret_id = resolve_canon_systems_secret_id()
    if not secret_id:
        return
    region_tag = (os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "default").strip()

    cached = _read_cache(secret_id, region_tag)
    if cached is not None:
        for k, v in cached.items():
            if k.strip():
                os.environ.setdefault(k.strip(), v)
        return

    client = _secretsmanager_client()
    if client is None:
        print(
            "memory-layer: boto3 is not installed; cannot read Secrets Manager.",
            file=sys.stderr,
        )
        return

    try:
        resp = client.get_secret_value(SecretId=secret_id)
    except Exception as exc:
        print(f"memory-layer: AWS Secrets Manager fetch failed: {exc}", file=sys.stderr)
        return

    raw = resp.get("SecretString")
    if not isinstance(raw, str) or not raw.strip():
        print("memory-layer: secret has no SecretString.", file=sys.stderr)
        return

    pairs = parse_secret_string(raw)
    if pairs:
        _write_cache(secret_id, region_tag, pairs)
    for k, v in pairs.items():
        if k.strip():
            os.environ.setdefault(k.strip(), v)
