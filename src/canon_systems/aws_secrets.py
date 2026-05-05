"""Optional AWS Secrets Manager integration for memory-layer environment variables."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Literal


def _boto3_available() -> bool:
    try:
        import boto3  # noqa: F401

        return True
    except ImportError:
        return False


def build_aws_secrets_resolution_attestation() -> dict[str, Any]:
    """Structured, non-secret diagnostics for Secrets Manager resolution and cache state.

    Safe for JSON logs: no secret values, no bearer tokens.
    """
    secret_id = resolve_canon_systems_secret_id()
    explicit_secret_id_env = bool((os.environ.get("MEMORY_LAYER_AWS_SECRET_ID") or "").strip())
    profile = (os.environ.get("AWS_PROFILE") or "").strip()
    region = (os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "").strip()
    region_tag = region if region else "default"
    cache_path = _cache_file_path()
    cache_exists = cache_path.exists()
    disable_cache = os.environ.get("MEMORY_LAYER_AWS_DISABLE_CACHE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )

    cache_hit: bool | None = None
    resolution_status: Literal[
        "no_secret_id",
        "cache_disabled",
        "cache_hit",
        "cache_miss",
    ] = "no_secret_id"

    if not secret_id:
        cache_hit = None
        resolution_status = "no_secret_id"
        requires_boto_fetch = False
    elif disable_cache:
        cache_hit = False
        resolution_status = "cache_disabled"
        requires_boto_fetch = True
    else:
        cached_payload = _read_cache(secret_id, region_tag)
        if cached_payload is not None:
            cache_hit = True
            resolution_status = "cache_hit"
            requires_boto_fetch = False
        else:
            cache_hit = False
            resolution_status = "cache_miss"
            requires_boto_fetch = True

    boto3_ok = _boto3_available()
    secrets_resolution_degraded = bool(requires_boto_fetch and not boto3_ok)

    return {
        "effective_aws_profile": profile,
        "effective_aws_region": region,
        "resolved_secret_id": secret_id,
        "memory_layer_aws_secret_id_from_explicit_env": explicit_secret_id_env,
        "cache_path": str(cache_path.expanduser().resolve()),
        "cache_exists": cache_exists,
        "cache_disabled": disable_cache,
        "cache_respects_ttl": _cache_respects_ttl(),
        "repo_mirror_disabled": _repo_mirror_disabled(),
        "cache_hit_when_known": cache_hit,
        "resolution": {
            "status": resolution_status,
            "boto3_available": boto3_ok,
        },
        "credential_resolution_degraded": secrets_resolution_degraded,
    }


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


def _secret_id_exists(secret_id: str, *, region: str) -> bool:
    """Return True if Secrets Manager has this id (DescribeSecret)."""
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        return False
    if not region.strip():
        return False
    try:
        client = boto3.client("secretsmanager", region_name=region.strip())
        client.describe_secret(SecretId=secret_id)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "ResourceNotFoundException":
            return False
        return False
    except Exception:
        return False


def discover_memory_layer_secret_prefix(
    company_id: str,
    repository_id: str,
    *,
    region: str,
    profile: str,
) -> str | None:
    """Pick a prefix whose full secret id exists in AWS, or None.

    Tries ``canon-memory-dev`` then the legacy ``canon-systems-v2-dev``.
    Uses ``AWS_PROFILE`` / region from the caller's environment — set them
    before calling (``canon setup`` does this after writing credentials).
    """
    saved: dict[str, str | None] = {}
    keys = ("AWS_PROFILE", "AWS_REGION", "AWS_DEFAULT_REGION")
    for k in keys:
        saved[k] = os.environ.get(k)
    try:
        if profile.strip():
            os.environ["AWS_PROFILE"] = profile.strip()
        if region.strip():
            os.environ["AWS_REGION"] = region.strip()
            os.environ["AWS_DEFAULT_REGION"] = region.strip()

        for prefix in (
            DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX,
            LEGACY_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX,
        ):
            sid = (
                f"{prefix}/memory-layer__{slug_canon_systems_segment(company_id)}__"
                f"{slug_canon_systems_segment(repository_id)}"
            )
            if _secret_id_exists(sid, region=region):
                return prefix
        return None
    finally:
        for k, old in saved.items():
            if old is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old


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


def _cache_respects_ttl() -> bool:
    """If true, treat ``expires_at`` in the home cache as a hard invalidation.

    Default is **false**: the on-disk cache under ``~/.canon/memory-layer-aws-cache.json`` is
    a **durable** snapshot until deleted (``canon doctor --fix-cache``), so a TTL expiry does
    not suddenly drop hydrated URLs/tokens from the process when AWS is temporarily
    unavailable. Set ``MEMORY_LAYER_AWS_CACHE_RESPECT_TTL=1`` to restore strict expiry.
    """
    return os.environ.get("MEMORY_LAYER_AWS_CACHE_RESPECT_TTL", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


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
    if _cache_respects_ttl():
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
    # Metadata only when TTL is not used for reads (default). Kept for diagnostics / future use.
    try:
        ttl = float(os.environ.get("MEMORY_LAYER_AWS_CACHE_TTL_SEC", "604800"))
    except ValueError:
        ttl = 604800.0
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


def _repo_mirror_disabled() -> bool:
    return os.environ.get("MEMORY_LAYER_AWS_DISABLE_REPO_MIRROR", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _format_repo_mirror_body(pairs: dict[str, str]) -> str:
    lines: list[str] = []
    for key in sorted(pairs.keys()):
        k = key.strip()
        if not k:
            continue
        val = str(pairs[k])
        if "\n" in val or "\r" in val:
            escaped = val.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k}="{escaped}"')
        elif any(ch in val for ch in (" ", "#", '"', "'")):
            escaped = val.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k}="{escaped}"')
        else:
            lines.append(f"{k}={val}")
    lines.append("")  # trailing newline
    return "\n".join(lines)


def _repo_secrets_mirror_path() -> Path | None:
    try:
        from .shared import repo_root
    except ImportError:
        return None
    return repo_root() / ".canon" / "memory-layer.secrets.env"


def _repo_mirror_needs_write(path: Path) -> bool:
    try:
        return not path.exists() or path.stat().st_size == 0
    except OSError:
        return True


def _repo_mirror_force_refresh() -> bool:
    return os.environ.get("MEMORY_LAYER_AWS_FORCE_REFRESH", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def read_repo_secrets_mirror() -> dict[str, str]:
    """Read the repo-local mirror, returning no secrets if disabled/missing/empty."""
    if _repo_mirror_disabled():
        return {}
    path = _repo_secrets_mirror_path()
    if path is None or not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    return _parse_dotenv_body(raw)


def apply_pairs_to_environ(pairs: dict[str, str]) -> None:
    for k, v in pairs.items():
        if k.strip():
            os.environ.setdefault(k.strip(), v)


def write_repo_secrets_mirror(pairs: dict[str, str], *, force: bool = False) -> None:
    """Persist hydrated secret keys next to the repo (gitignored). Best-effort only."""
    if _repo_mirror_disabled() or not pairs:
        return
    path = _repo_secrets_mirror_path()
    if path is None:
        return
    if not force and not _repo_mirror_needs_write(path):
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        body = _format_repo_mirror_body(pairs)
        path.write_text(body, encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
    except OSError:
        return


def refresh_repo_secrets_mirror_if_missing(pairs: dict[str, str]) -> None:
    """Write repo mirror when missing/empty (e.g. after loading durable home cache)."""
    write_repo_secrets_mirror(pairs, force=False)


def apply_canon_systems_secrets_from_aws() -> None:
    secret_id = resolve_canon_systems_secret_id()
    if not secret_id:
        return
    region_tag = (os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "default").strip()

    mirrored = read_repo_secrets_mirror()
    if mirrored and not _repo_mirror_force_refresh():
        apply_pairs_to_environ(mirrored)
        return

    cached = _read_cache(secret_id, region_tag)
    if cached is not None:
        apply_pairs_to_environ(cached)
        refresh_repo_secrets_mirror_if_missing(cached)
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
        write_repo_secrets_mirror(pairs, force=True)
    apply_pairs_to_environ(pairs)
