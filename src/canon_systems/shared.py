"""Shared helpers for canon-systems session automation."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class IdentityContext:
    actor_id: str
    display_name: str
    email: str
    jira_account_id: str
    slack_user_id: str
    company_id: str
    default_repository_id: str


@dataclass(slots=True)
class RepoContext:
    company_id: str
    repository_id: str
    knowledge_api_url: str
    knowledge_worker_url: str
    memory_adapter_url: str
    artifact_bucket: str
    context_dir: Path


_CACHED_REPO_ROOT: Path | None = None
_LAYERED_MEMORY_ENV_APPLIED = False


def _git_toplevel_from_cwd() -> Path | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=Path.cwd(),
            text=True,
            check=False,
            capture_output=True,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return Path(out) if out else None


def repo_root() -> Path:
    global _CACHED_REPO_ROOT
    explicit = (
        os.environ.get("CANON_SYSTEMS_REPO_ROOT", "").strip()
        or os.environ.get("CANON_MEMORY_LAYER_REPO_ROOT", "").strip()
    )
    if explicit:
        resolved = Path(explicit).expanduser().resolve()
        _CACHED_REPO_ROOT = resolved
        return resolved
    if _CACHED_REPO_ROOT is not None:
        return _CACHED_REPO_ROOT
    git_root = _git_toplevel_from_cwd()
    if git_root is not None:
        _CACHED_REPO_ROOT = git_root.resolve()
        return _CACHED_REPO_ROOT
    _CACHED_REPO_ROOT = Path.cwd().resolve()
    return _CACHED_REPO_ROOT


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def merge_canon_systems_env_files(paths: list[Path]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in paths:
        if path.exists():
            merged.update(load_env_file(path))
    return merged


def _safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    cleaned = cleaned.strip("_.-")
    return cleaned or "unknown"


def _git_config_value(name: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "config", name],
            cwd=repo_root(),
            text=True,
            check=False,
            capture_output=True,
        )
    except Exception:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _default_actor_id() -> str:
    email = _git_config_value("user.email")
    if email:
        return f"usr_{_safe_slug(email.split('@', 1)[0].lower())}"
    name = _git_config_value("user.name")
    if name:
        return f"usr_{_safe_slug(name.lower())}"
    env_user = os.environ.get("USER", "").strip()
    if env_user:
        return f"usr_{_safe_slug(env_user.lower())}"
    return "usr_unknown"


def profile_path_candidates() -> list[Path]:
    explicit = os.environ.get("CANON_USER_PROFILE_PATH", "").strip()
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.append(Path.home() / ".canon" / "user-profile.json")
    candidates.append(repo_root() / ".canon" / "user-profile.json")
    return candidates


def _load_team_identity_registry() -> dict[str, dict[str, Any]]:
    path = repo_root() / ".canon" / "team-identities.json"
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    actors = parsed.get("actors") if isinstance(parsed, dict) else {}
    if not isinstance(actors, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for actor_id, value in actors.items():
        if isinstance(actor_id, str) and actor_id.strip() and isinstance(value, dict):
            out[actor_id.strip()] = value
    return out


def load_identity_context() -> IdentityContext:
    profile: dict[str, Any] = {}
    for path in profile_path_candidates():
        if path.exists():
            try:
                maybe_profile = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                maybe_profile = {}
            if isinstance(maybe_profile, dict) and maybe_profile:
                profile = maybe_profile
                break

    registry = _load_team_identity_registry()
    actor_id = (
        os.environ.get("CANON_ACTOR_ID", "").strip()
        or str(profile.get("actor_id", "")).strip()
        or _default_actor_id()
    )
    defaults = registry.get(actor_id, {})
    return IdentityContext(
        actor_id=actor_id,
        display_name=(
            os.environ.get("CANON_ACTOR_DISPLAY_NAME", "").strip()
            or str(profile.get("display_name", "")).strip()
            or str(defaults.get("display_name", "")).strip()
            or _git_config_value("user.name")
            or os.environ.get("USER", "unknown-user")
        ),
        email=(
            os.environ.get("CANON_ACTOR_EMAIL", "").strip()
            or str(profile.get("email", "")).strip()
            or str(defaults.get("email", "")).strip()
            or _git_config_value("user.email")
        ),
        jira_account_id=str(profile.get("jira_account_id", "")).strip()
        or str(defaults.get("jira_account_id", "")).strip(),
        slack_user_id=str(profile.get("slack_user_id", "")).strip()
        or str(defaults.get("slack_user_id", "")).strip(),
        company_id=(
            os.environ.get("CANON_COMPANY_ID", "").strip()
            or str(profile.get("company_id", "")).strip()
            or str(defaults.get("company_id", "")).strip()
        ),
        default_repository_id=(
            os.environ.get("CANON_DEFAULT_REPOSITORY_ID", "").strip()
            or str(profile.get("default_repository_id", "")).strip()
            or str(defaults.get("default_repository_id", "")).strip()
        ),
    )


def _repository_id_from_remote() -> str:
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_root(),
            text=True,
            check=False,
            capture_output=True,
        )
    except Exception:
        return ""
    if proc.returncode != 0:
        return ""
    raw = proc.stdout.strip()
    if raw.startswith("git@") and ":" in raw:
        host_part, path_part = raw.split(":", 1)
        host = host_part.split("@", 1)[1]
        return f"{host}/{path_part.removesuffix('.git')}"
    if raw.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(raw)
        path = parsed.path.strip("/").removesuffix(".git")
        if parsed.netloc and path:
            return f"{parsed.netloc}/{path}"
    return ""


def ensure_state_api_url_from_knowledge() -> None:
    """If no state plane URL is set, default ``CANON_STATE_API_URL`` to ``KNOWLEDGE_API_URL``.

    Checkpoint clients read ``CANON_STATE_API_URL``; ``memory-health`` accepts that or
    ``STATE_API_URL``. A dedicated state-api can still override either variable explicitly.
    """
    canon = (os.environ.get("CANON_STATE_API_URL") or "").strip()
    state = (os.environ.get("STATE_API_URL") or "").strip()
    if canon or state:
        return
    knowledge = (os.environ.get("KNOWLEDGE_API_URL") or "").strip().rstrip("/")
    if not knowledge:
        return
    os.environ["CANON_STATE_API_URL"] = knowledge


def apply_layered_canon_env_for_repo(root: Path) -> None:
    """Merge Canon env files for ``root`` into ``os.environ`` (``setdefault``), then AWS secrets.

    Used by ``canon memory-health`` on every run so probe URLs match hooks /
    ``load_repo_context``, which may take ``KNOWLEDGE_API_URL`` / ``MEMORY_ADAPTER_URL``
    from ``~/.canon/*.env`` or Secrets Manager—not only ``memory-layer.local.env``.

    Hooks still use :func:`ensure_layered_memory_env` (one-shot per process) for
    performance; this function has no global guard.
    """
    merged = merge_canon_systems_env_files(
        [
            Path.home() / ".canon" / "canon-systems.env",
            Path.home() / ".canon" / "canon-memory-layer.env",
            root / ".canon" / "memory-layer.team.env",
            root / ".canon" / "scoper-chat.env",
            Path.home() / ".canon" / "memory-layer.secrets.env",
            root / ".canon" / "memory-layer.local.env",
            root / ".canon" / "memory-layer.secrets.env",
        ]
    )
    for key, value in merged.items():
        if key.strip():
            os.environ.setdefault(key.strip(), value)
    from .aws_secrets import apply_canon_systems_secrets_from_aws

    apply_canon_systems_secrets_from_aws()
    ensure_state_api_url_from_knowledge()


def ensure_layered_memory_env() -> None:
    global _LAYERED_MEMORY_ENV_APPLIED
    if _LAYERED_MEMORY_ENV_APPLIED:
        return
    apply_layered_canon_env_for_repo(repo_root())
    _LAYERED_MEMORY_ENV_APPLIED = True


def resolve_auth_bearer(auth_profile: str) -> str:
    profile = (auth_profile or "knowledge_api").strip().lower()
    universal = os.environ.get("CANON_HTTP_BEARER_TOKEN", "").strip()
    if profile == "memory_adapter":
        return (
            os.environ.get("MEMORY_ADAPTER_BEARER_TOKEN", "").strip()
            or os.environ.get("MEMORY_ADAPTER_TOKEN", "").strip()
            or universal
        )
    if profile == "knowledge_worker":
        return (
            os.environ.get("KNOWLEDGE_WORKER_BEARER_TOKEN", "").strip()
            or os.environ.get("KNOWLEDGE_WORKER_TOKEN", "").strip()
            or universal
        )
    return (
        os.environ.get("KNOWLEDGE_API_BEARER_TOKEN", "").strip()
        or os.environ.get("KNOWLEDGE_API_TOKEN", "").strip()
        or universal
    )


def load_repo_context(identity: IdentityContext) -> RepoContext:
    ensure_layered_memory_env()
    root = repo_root()
    scoper_env = load_env_file(root / ".canon" / "scoper-chat.env")
    local_env = load_env_file(root / ".canon" / "memory-layer.local.env")
    company_id = (
        os.environ.get("COMPANY_ID", "").strip()
        or scoper_env.get("COMPANY_ID", "").strip()
        or local_env.get("COMPANY_ID", "").strip()
        or identity.company_id.strip()
        or "UNKNOWN_COMPANY"
    )
    repository_id = (
        os.environ.get("REPOSITORY_ID", "").strip()
        or scoper_env.get("REPOSITORY_ID", "").strip()
        or local_env.get("REPOSITORY_ID", "").strip()
        or identity.default_repository_id.strip()
        or _repository_id_from_remote()
        or root.name
    )
    ctx = root / ".canon" / "memory"
    ctx.mkdir(parents=True, exist_ok=True)
    return RepoContext(
        company_id=company_id,
        repository_id=repository_id,
        knowledge_api_url=(
            os.environ.get("KNOWLEDGE_API_URL", "").strip()
            or scoper_env.get("KNOWLEDGE_API_URL", "").strip()
            or local_env.get("KNOWLEDGE_API_URL", "").strip()
            or "http://localhost:8080"
        ).rstrip("/"),
        knowledge_worker_url=(
            os.environ.get("KNOWLEDGE_WORKER_URL", "").strip()
            or scoper_env.get("KNOWLEDGE_WORKER_URL", "").strip()
            or local_env.get("KNOWLEDGE_WORKER_URL", "").strip()
            or "http://localhost:8091"
        ).rstrip("/"),
        memory_adapter_url=(
            os.environ.get("MEMORY_ADAPTER_URL", "").strip()
            or local_env.get("MEMORY_ADAPTER_URL", "").strip()
            or "http://localhost:8090"
        ).rstrip("/"),
        artifact_bucket=(
            os.environ.get("SCOPE_ARTIFACT_BUCKET", "").strip()
            or scoper_env.get("SCOPE_ARTIFACT_BUCKET", "").strip()
            or local_env.get("SCOPE_ARTIFACT_BUCKET", "").strip()
            or "knowledge-dev"
        ),
        context_dir=ctx,
    )


def parse_hook_payload(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    in_path = Path(path)
    if not in_path.exists():
        return {}
    try:
        parsed = json.loads(in_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested = first_text(value, keys)
            if nested:
                return nested
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    return item.strip()
                if isinstance(item, dict):
                    nested = first_text(item, keys)
                    if nested:
                        return nested
    return ""


def request_json(
    *,
    url: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    actor_id: str = "",
    company_id: str = "",
    timeout_s: int = 20,
    auth_profile: str = "knowledge_api",
) -> tuple[int, dict[str, Any] | list[Any] | str]:
    ensure_layered_memory_env()
    headers = {"Accept": "application/json"}
    payload: bytes | None = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode("utf-8")

    bearer = resolve_auth_bearer(auth_profile)
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    else:
        profile = auth_profile.lower()
        if profile == "memory_adapter":
            api_key = os.environ.get("MEMORY_ADAPTER_API_KEY", "").strip()
        elif profile == "knowledge_worker":
            api_key = (
                os.environ.get("KNOWLEDGE_WORKER_API_KEY", "").strip()
                or os.environ.get("KNOWLEDGE_API_KEY", "").strip()
            )
        else:
            api_key = os.environ.get("KNOWLEDGE_API_KEY", "").strip()
        if api_key:
            headers["X-API-Key"] = api_key

    if actor_id:
        headers["X-Actor-Id"] = actor_id
    if company_id:
        headers["X-Company-Id"] = company_id

    req = urllib.request.Request(url=url, method=method, headers=headers, data=payload)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.getcode()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed = _try_parse_json(raw)
        return exc.code, parsed if parsed is not None else raw
    except urllib.error.URLError as exc:
        return 0, f"request failed: {exc.reason!s}"
    parsed = _try_parse_json(raw)
    return status, parsed if parsed is not None else raw


def _try_parse_json(raw: str) -> dict[str, Any] | list[Any] | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def now_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def artifact_identity(*, prefix: str, actor_id: str) -> tuple[str, str]:
    stamp = now_stamp()
    actor = _safe_slug(actor_id.lower())[:32]
    artifact_id = f"{prefix}_{stamp}_{actor}"
    version_id = f"ver_{artifact_id}"
    return artifact_id, version_id
