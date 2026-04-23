"""Install Canon Systems into a repository.

Copies the template hooks, rule, and subagent definitions into the target
repo's .cursor/ tree, merges .cursor/hooks.json, and pins the installed
canon-systems version in .canon/memory-layer.local.env so hooks can
detect version drift.
"""

from __future__ import annotations

import json
import os
import shutil
from importlib import resources
from pathlib import Path

from . import __version__
from .shared import load_env_file


_PKG_TEMPLATES = "canon_systems.templates"
_VERSION_KEY = "CANON_SYSTEMS_VERSION"
_LEGACY_VERSION_KEY = "CANON_MEMORY_LAYER_VERSION"


def _copy_template(resource_path: str, dest: Path, *, executable: bool = False) -> None:
    """Copy a package resource to dest. resource_path is dot-free path under templates/."""
    # resource_path like "hooks/memory-preflight.sh"
    parts = resource_path.split("/")
    package = ".".join([_PKG_TEMPLATES, *parts[:-1]]) if len(parts) > 1 else _PKG_TEMPLATES
    filename = parts[-1]
    with resources.files(package).joinpath(filename).open("rb") as src:
        data = src.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    if executable:
        dest.chmod(0o755)


def _merge_hook_entries(hooks: list[dict], entry: dict) -> list[dict]:
    out = [h for h in hooks if h.get("command") != entry["command"]]
    out.append(entry)
    return out


def _merge_hooks_json(repo_root: Path) -> None:
    hooks_json_path = repo_root / ".cursor" / "hooks.json"
    template_json = json.loads(
        resources.files(f"{_PKG_TEMPLATES}.hooks").joinpath("hooks.json").read_text(encoding="utf-8")
    )

    if hooks_json_path.exists():
        try:
            parsed = json.loads(hooks_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            parsed = {}
    else:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}

    parsed["version"] = int(parsed.get("version", 1) or 1)
    hooks = parsed.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}

    for event_name, entries in template_json.get("hooks", {}).items():
        current = hooks.get(event_name)
        if not isinstance(current, list):
            current = []
        for entry in entries:
            current = _merge_hook_entries(current, entry)
        hooks[event_name] = current

    parsed["hooks"] = hooks
    hooks_json_path.parent.mkdir(parents=True, exist_ok=True)
    hooks_json_path.write_text(json.dumps(parsed, indent=2) + "\n", encoding="utf-8")


_VAULT_GITIGN_START = "# >>> canon-systems:vault-sync >>>"
_VAULT_GITIGN_END = "# <<< canon-systems:vault-sync <<<"
_VAULT_GITIGN_BODY = "vault/\n.canon/memory/events.ndjson.lock\n"


def _apply_vault_sync_gitignore_block(repo_root: Path) -> None:
    path = repo_root / ".gitignore"
    expected = f"{_VAULT_GITIGN_START}\n{_VAULT_GITIGN_BODY}{_VAULT_GITIGN_END}\n"
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = ""
    if expected in text:
        return
    if _VAULT_GITIGN_START in text and _VAULT_GITIGN_END in text:
        a = text.index(_VAULT_GITIGN_START)
        b = text.index(_VAULT_GITIGN_END) + len(_VAULT_GITIGN_END)
        while b < len(text) and text[b] in "\n\r":
            b += 1
        text = text[:a] + text[b:]
    sep = "" if (not text or text.endswith("\n")) else "\n"
    path.write_text(text + sep + expected, encoding="utf-8")


def _env_o(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def _pin_version(repo_root: Path) -> None:
    """Write CANON_SYSTEMS_VERSION=<installed> into .canon/memory-layer.local.env.

    Also strips the legacy CANON_MEMORY_LAYER_VERSION key if present, so a
    single source of truth lives in the file going forward.
    """
    env_path = repo_root / ".canon" / "memory-layer.local.env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_env_file(env_path) if env_path.exists() else {}
    existing.pop(_LEGACY_VERSION_KEY, None)
    existing[_VERSION_KEY] = __version__
    body = "\n".join(f"{k}={v}" for k, v in sorted(existing.items())) + "\n"
    env_path.write_text(body, encoding="utf-8")


def enable_repo(  # noqa: PLR0912
    repo_root: Path,
    *,
    install_vault_sync: bool = False,
    company_id: str | None = None,
    repository_id: str | None = None,
    plan_id: str | None = None,
    bucket: str | None = None,
    prefix: str | None = None,
    vault_target_dir: Path | str | None = None,
    interval_seconds: int = 10,
) -> None:
    cursor_dir = repo_root / ".cursor"
    hooks_dir = cursor_dir / "hooks"
    rules_dir = cursor_dir / "rules"
    agents_dir = cursor_dir / "agents"

    # Install hook scripts (bash wrappers that invoke the installed CLI).
    _copy_template("hooks/memory-preflight.sh", hooks_dir / "memory-preflight.sh", executable=True)
    _copy_template("hooks/memory-capture.sh", hooks_dir / "memory-capture.sh", executable=True)
    _copy_template("hooks/vault-sync-preflight.sh", hooks_dir / "vault-sync-preflight.sh", executable=True)

    # Merge hooks.json (preserve any pre-existing hooks; dedupe by command).
    _merge_hooks_json(repo_root)

    _apply_vault_sync_gitignore_block(repo_root)

    # Install repo-level Cursor rule.
    _copy_template("rules/memory-layer-defaults.mdc", rules_dir / "memory-layer-defaults.mdc")

    # Install repo-level subagents (project-planner, scoper, cursor-pilot, implementer, qa-gate, release-orchestrator).
    for name in (
        "project-planner.md",
        "scoper.md",
        "cursor-pilot.md",
        "implementer.md",
        "qa-gate.md",
        "release-orchestrator.md",
    ):
        _copy_template(f"agents/{name}", agents_dir / name)

    # Pin installed version for drift detection.
    _pin_version(repo_root)

    if install_vault_sync:
        from .vault_sync import install_service

        cid = (company_id or _env_o("CANON_COMPANY_ID") or "").strip()
        rid = (repository_id or _env_o("CANON_REPOSITORY_ID") or "").strip()
        pid = (plan_id or _env_o("CANON_PLAN_ID") or "").strip()
        bkt = (bucket or _env_o("CANON_VAULT_BUCKET") or "").strip()
        pfx = (prefix or _env_o("CANON_VAULT_PREFIX") or "").strip()
        if not all((cid, rid, pid, bkt, pfx)):
            raise ValueError(
                "install_vault_sync requires company_id, repository_id, plan_id, bucket, prefix "
                "(flags on enable-repo or CANON_COMPANY_ID / CANON_REPOSITORY_ID / CANON_PLAN_ID / "
                "CANON_VAULT_BUCKET / CANON_VAULT_PREFIX in the environment)"
            )
        tdir: Path
        if vault_target_dir is not None and str(vault_target_dir).strip():
            tdir = Path(vault_target_dir).expanduser().resolve()
        else:
            tdir = (repo_root / "vault").resolve()
        elog = (repo_root / ".canon" / "memory" / "events.ndjson").resolve()
        install_service(
            company_id=cid,
            repository_id=rid,
            plan_id=pid,
            bucket=bkt,
            prefix=pfx,
            target_dir=tdir,
            interval_seconds=int(interval_seconds),
            event_log=elog,
        )


def install_user_scope() -> None:
    """Install the user-level rule + subagents under ~/.cursor/ for fallback use.

    These apply when the user opens a repo that hasn't been enabled yet —
    the autosetup rule offers to run `canon setup`, and the subagents are
    available immediately even in unwired repos.
    """
    home = Path.home() / ".cursor"
    (home / "rules").mkdir(parents=True, exist_ok=True)
    (home / "agents").mkdir(parents=True, exist_ok=True)
    _copy_template("rules/canon-autosetup.mdc", home / "rules" / "canon-autosetup.mdc")
    _copy_template("rules/memory-layer-defaults.mdc", home / "rules" / "memory-layer-defaults.mdc")
    for name in (
        "project-planner.md",
        "scoper.md",
        "cursor-pilot.md",
        "implementer.md",
        "qa-gate.md",
        "release-orchestrator.md",
    ):
        _copy_template(f"agents/{name}", home / "agents" / name)


# Back-compat no-op for callers that still import PRE_HOOK/POST_HOOK strings.
# The real hook bodies now live in templates/hooks/.
PRE_HOOK = ""
POST_HOOK = ""


__all__ = ["enable_repo", "install_user_scope", "PRE_HOOK", "POST_HOOK"]
