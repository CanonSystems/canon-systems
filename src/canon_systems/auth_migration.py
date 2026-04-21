"""Auth + ingress migration helpers for phased rollout."""

from __future__ import annotations

import argparse
from pathlib import Path

from .install_wizard import detect_repo_root
from .shared import load_env_file

_MIGRATION_KEYS = (
    "CANON_AUTH_PHASE",
    "CANON_AUTH_MODE",
    "CANON_AUTH_PREVIOUS_PHASE",
    "CANON_AUTH_PREVIOUS_MODE",
    "CANON_AUTH_PREVIOUS_KNOWLEDGE_API_URL",
    "CANON_AUTH_PREVIOUS_KNOWLEDGE_WORKER_URL",
    "CANON_AUTH_PREVIOUS_MEMORY_ADAPTER_URL",
    "KNOWLEDGE_API_URL",
    "KNOWLEDGE_WORKER_URL",
    "MEMORY_ADAPTER_URL",
)


def _env_path(root: Path) -> Path:
    return root / ".canon" / "memory-layer.local.env"


def _write_env(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"{k}={v}" for k, v in sorted(values.items())) + "\n"
    path.write_text(body, encoding="utf-8")


def _base_url(domain: str, scheme: str) -> str:
    cleaned_domain = domain.strip().strip("/")
    if "://" in cleaned_domain:
        return cleaned_domain.rstrip("/")
    cleaned_scheme = (scheme or "https").strip().rstrip(":/")
    return f"{cleaned_scheme}://{cleaned_domain}".rstrip("/")


def _print_status(env: dict[str, str], root: Path) -> None:
    print(f"Repo: {root}")
    for key in _MIGRATION_KEYS:
        value = env.get(key, "")
        if value:
            print(f"{key}={value}")


def _phase_mode(phase: str) -> str:
    if phase in ("prepare", "canary"):
        return "dual"
    if phase == "enforce":
        return "cognito"
    return "legacy"


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="canon auth-migration",
        description=(
            "Manage phased auth migration (prepare/canary/enforce/rollback) "
            "for this repository."
        ),
    )
    parser.add_argument(
        "phase",
        choices=("status", "prepare", "canary", "enforce", "rollback"),
        help="Show status or apply the selected migration phase.",
    )
    parser.add_argument(
        "--repo-root",
        default="",
        help="Target repository root (defaults to detected git top-level).",
    )
    parser.add_argument(
        "--domain",
        default="memory.canon-systems.com",
        help="Canonical domain used for endpoint URL writes.",
    )
    parser.add_argument(
        "--scheme",
        default="https",
        help="URL scheme for domain endpoints (https by default).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended changes without writing env files.",
    )
    args = parser.parse_args(argv)

    root = detect_repo_root(args.repo_root)
    env_path = _env_path(root)
    env = load_env_file(env_path) if env_path.exists() else {}
    previous = dict(env)

    if args.phase == "status":
        _print_status(env, root)
        return 0

    if args.phase == "rollback":
        env["CANON_AUTH_PHASE"] = "rollback"
        env["CANON_AUTH_MODE"] = previous.get("CANON_AUTH_PREVIOUS_MODE", "legacy")
        for key, previous_key in (
            ("KNOWLEDGE_API_URL", "CANON_AUTH_PREVIOUS_KNOWLEDGE_API_URL"),
            ("KNOWLEDGE_WORKER_URL", "CANON_AUTH_PREVIOUS_KNOWLEDGE_WORKER_URL"),
            ("MEMORY_ADAPTER_URL", "CANON_AUTH_PREVIOUS_MEMORY_ADAPTER_URL"),
        ):
            previous_value = previous.get(previous_key, "").strip()
            if previous_value:
                env[key] = previous_value
    else:
        target_url = _base_url(args.domain, args.scheme)
        env["CANON_AUTH_PREVIOUS_PHASE"] = previous.get("CANON_AUTH_PHASE", "")
        env["CANON_AUTH_PREVIOUS_MODE"] = previous.get("CANON_AUTH_MODE", "")
        env["CANON_AUTH_PREVIOUS_KNOWLEDGE_API_URL"] = previous.get("KNOWLEDGE_API_URL", "")
        env["CANON_AUTH_PREVIOUS_KNOWLEDGE_WORKER_URL"] = previous.get("KNOWLEDGE_WORKER_URL", "")
        env["CANON_AUTH_PREVIOUS_MEMORY_ADAPTER_URL"] = previous.get("MEMORY_ADAPTER_URL", "")
        env["CANON_AUTH_PHASE"] = args.phase
        env["CANON_AUTH_MODE"] = _phase_mode(args.phase)
        env["KNOWLEDGE_API_URL"] = target_url
        env["KNOWLEDGE_WORKER_URL"] = target_url
        env["MEMORY_ADAPTER_URL"] = target_url

    if args.dry_run:
        print("Dry run only; proposed migration state:")
        _print_status(env, root)
        return 0

    _write_env(env_path, env)
    print(f"Updated auth migration phase in {env_path}")
    _print_status(env, root)
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
