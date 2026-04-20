"""Interactive plug-and-play setup of canon-systems for a target repository."""

from __future__ import annotations

import argparse
import configparser
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def detect_repo_root(explicit: str = "") -> Path:
    if explicit.strip():
        return Path(explicit).expanduser().resolve()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=Path.cwd(),
            text=True,
            check=False,
            capture_output=True,
        )
    except OSError:
        return Path.cwd().resolve()
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip()).resolve()
    return Path.cwd().resolve()


def git_repository_id(root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            text=True,
            check=False,
            capture_output=True,
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    raw = proc.stdout.strip()
    if raw.startswith("git@") and ":" in raw:
        host_part, path_part = raw.split(":", 1)
        host = host_part.split("@", 1)[1]
        path = path_part.removesuffix(".git")
        return f"{host}/{path}"
    if raw.startswith(("http://", "https://")):
        from urllib.parse import urlparse

        parsed = urlparse(raw)
        path = parsed.path.strip("/").removesuffix(".git")
        if parsed.netloc and path:
            return f"{parsed.netloc}/{path}"
    return ""


def load_company_registry(root: Path) -> dict[str, Any]:
    local_candidates = (
        root / ".canon" / "company-registry.local.json",
        root / ".canon" / "company-registry.json",
        Path.home() / ".canon" / "company-registry.json",
    )
    for path in local_candidates:
        if not path.exists():
            continue
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    example = Path(__file__).resolve().parents[2] / "examples" / "company-registry.example.json"
    if example.exists():
        try:
            parsed = json.loads(example.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def company_entry(registry: dict[str, Any], company_id: str) -> dict[str, Any]:
    companies = registry.get("companies")
    if not isinstance(companies, dict):
        return {}
    value = companies.get(company_id)
    return value if isinstance(value, dict) else {}


def read_secret(prompt: str) -> str:
    try:
        import getpass
    except ImportError:
        return input(prompt)
    return getpass.getpass(prompt)


def upsert_aws_credentials(profile: str, access_key_id: str, secret_key: str) -> None:
    cred_path = Path.home() / ".aws" / "credentials"
    cred_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    cfg = configparser.ConfigParser()
    if cred_path.exists():
        cfg.read(cred_path)
    if not cfg.has_section(profile):
        cfg.add_section(profile)
    cfg.set(profile, "aws_access_key_id", access_key_id)
    cfg.set(profile, "aws_secret_access_key", secret_key)
    with cred_path.open("w", encoding="utf-8") as fh:
        cfg.write(fh)
    os.chmod(cred_path, 0o600)


def upsert_aws_config(profile: str, region: str) -> None:
    cfg_path = Path.home() / ".aws" / "config"
    cfg_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    cfg = configparser.ConfigParser()
    if cfg_path.exists():
        cfg.read(cfg_path)
    section = f"profile {profile}"
    if not cfg.has_section(section):
        cfg.add_section(section)
    cfg.set(section, "region", region)
    with cfg_path.open("w", encoding="utf-8") as fh:
        cfg.write(fh)
    os.chmod(cfg_path, 0o600)


def write_machine_env(profile: str, region: str) -> Path:
    """Write machine-level AWS env to ~/.canon/canon-systems.env.

    Also prunes the legacy ~/.canon/canon-memory-layer.env on new runs so
    we don't leave two stale files side by side. `shared.py` still reads
    the legacy path as a fallback for machines that haven't rerun setup.
    """
    canon_home = Path.home() / ".canon"
    canon_home.mkdir(mode=0o700, exist_ok=True)
    path = canon_home / "canon-systems.env"
    path.write_text(
        "\n".join(
            (
                "# Written by canon setup",
                f"AWS_PROFILE={profile}",
                f"AWS_REGION={region}",
                f"AWS_DEFAULT_REGION={region}",
                "",
            )
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)
    legacy = canon_home / "canon-memory-layer.env"
    if legacy.exists():
        try:
            legacy.unlink()
        except OSError:
            pass
    return path


def merge_local_env(root: Path, updates: dict[str, str]) -> Path:
    from .shared import load_env_file

    path = root / ".canon" / "memory-layer.local.env"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_env_file(path) if path.exists() else {}
    existing.update({k: v for k, v in updates.items() if v})
    body = "\n".join(f"{k}={v}" for k, v in sorted(existing.items())) + "\n"
    path.write_text(body, encoding="utf-8")
    return path


def ensure_boto3() -> None:
    py = sys.executable
    try:
        subprocess.run([py, "-c", "import boto3"], check=True, capture_output=True)
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    subprocess.run([py, "-m", "pip", "install", "boto3"], check=False)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Configure canon-systems for current repo.")
    parser.add_argument("--repo-root", default="", help="Repository root to configure.")
    parser.add_argument("--non-interactive", action="store_true")
    args = parser.parse_args(argv)

    root = detect_repo_root(args.repo_root)
    registry = load_company_registry(root)
    companies = registry.get("companies") if isinstance(registry.get("companies"), dict) else {}
    default_company = next(iter(companies.keys()), "FMO") if companies else "FMO"
    detected_repo_id = git_repository_id(root)

    from .aws_secrets import DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX

    if args.non_interactive:
        company_id = os.environ.get("MEMORY_LAYER_COMPANY_ID", default_company).strip()
        profile = os.environ.get("MEMORY_LAYER_AWS_PROFILE", "canon-systems").strip()
        region = os.environ.get("AWS_REGION", "us-east-1").strip()
        repo_id = os.environ.get("REPOSITORY_ID", detected_repo_id).strip()
        prefix = os.environ.get("MEMORY_LAYER_AWS_SECRET_NAME_PREFIX", "").strip()
        access_key = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
    else:
        print("Canon Systems setup")
        print(f"Target repo: {root}")
        if detected_repo_id:
            print(f"Detected REPOSITORY_ID: {detected_repo_id}")
        if companies:
            print(f"Known companies: {', '.join(companies.keys())}")
        company_id = input(f"Company ID [{default_company}]: ").strip() or default_company
        ent = company_entry(registry, company_id)
        print(
            "\nAWS credentials profile — a short LABEL on this machine only. It becomes the\n"
            "section name in ~/.aws/credentials, e.g. [memory-layer-edward]. It is NOT your\n"
            "AWS console sign-in username and NOT your access key. Pick any name you like;\n"
            "use the same name you already use in ~/.aws/credentials if keys are there.\n"
        )
        profile = (
            input(
                "AWS credentials profile "
                f"[{str(ent.get('suggested_aws_profile', '')).strip() or 'canon-systems'}]: "
            ).strip()
            or str(ent.get("suggested_aws_profile", "")).strip()
            or "canon-systems"
        )
        region = input(f"AWS region [{str(ent.get('aws_region', '')).strip() or 'us-east-1'}]: ").strip() or str(
            ent.get("aws_region", "")
        ).strip() or "us-east-1"
        repo_id = input(f"REPOSITORY_ID [{detected_repo_id}]: ").strip() or detected_repo_id
        from .aws_secrets import (
            DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX,
            LEGACY_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX,
        )
        from .shared import load_env_file

        prior_local = load_env_file(root / ".canon" / "memory-layer.local.env")
        suggested_prefix = (
            prior_local.get("MEMORY_LAYER_AWS_SECRET_NAME_PREFIX", "").strip()
            or str(ent.get("aws_secret_name_prefix", "")).strip()
            or DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX
        )
        print(
            "\nAWS Secrets Manager **name prefix** (first path segment before "
            "`/memory-layer__/...`). It is your **cloud namespace** (often "
            "dev vs prod), not the `canon-systems` CLI version and not your "
            "repo name. Older deployments used "
            f"`{LEGACY_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX}`; the current "
            f"default for new work is `{DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX}` "
            "(press Enter unless your secrets still live under the legacy prefix).\n"
        )
        prefix = input(f"Secrets name prefix [{suggested_prefix}]: ").strip() or suggested_prefix
        print(
            "Optional: paste IAM access key id + secret to WRITE them under the profile above.\n"
            "Press Enter for AWS_ACCESS_KEY_ID to skip (use SSO or keys already in that profile).\n"
        )
        access_key = input("AWS_ACCESS_KEY_ID (AKIA..., or Enter to skip): ").strip()
        secret_key = read_secret("AWS_SECRET_ACCESS_KEY (or Enter to skip): ").strip() if access_key else ""

    if not prefix:
        prefix = (
            str(company_entry(registry, company_id).get("aws_secret_name_prefix", "")).strip()
            or DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX
        )

    from .aws_secrets import slug_canon_systems_segment

    _secret_preview = (
        f"{prefix}/memory-layer__{slug_canon_systems_segment(company_id)}__"
        f"{slug_canon_systems_segment(repo_id)}"
    )
    print("")
    print(f"AWS Secrets Manager will load secret (must exist in {region}):")
    print(f"  {_secret_preview}")
    print("If that name does not match AWS, fix COMPANY_ID / REPOSITORY_ID / prefix,")
    print("or later set MEMORY_LAYER_AWS_SECRET_ID in .canon/memory-layer.local.env.")
    print("")

    if access_key and not secret_key:
        print("AWS secret key required when access key is provided.", file=sys.stderr)
        return 1
    if secret_key and not access_key:
        print("AWS access key required when secret key is provided.", file=sys.stderr)
        return 1

    if access_key and secret_key:
        upsert_aws_credentials(profile, access_key, secret_key)
    else:
        print("Skipping ~/.aws/credentials write (expecting SSO or preconfigured profile).")
    upsert_aws_config(profile, region)
    machine_env = write_machine_env(profile, region)
    repo_env = merge_local_env(
        root,
        {
            "COMPANY_ID": company_id,
            "REPOSITORY_ID": repo_id,
            "MEMORY_LAYER_AWS_SECRET_NAME_PREFIX": prefix,
            "AWS_REGION": region,
        },
    )
    ensure_boto3()

    from .repo_enable import install_user_scope
    try:
        install_user_scope()
        user_scope_msg = "Installed user-level rules + subagents under ~/.cursor/"
    except Exception as exc:
        user_scope_msg = f"User-scope install skipped: {exc}"

    print("")
    print(f"Wrote machine env: {machine_env}")
    print(f"Wrote repo env:    {repo_env}")
    print(user_scope_msg)
    print("Credentials + config written. Installing Cursor hooks + subagents next...")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
