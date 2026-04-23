"""Structured submission of canon runtime secrets to AWS Secrets Manager."""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
from typing import Any

from .aws_secrets import DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX, parse_secret_string, slug_canon_systems_segment
from .shared import load_env_file, repo_root

_DEFAULT_REQUIRED_KEYS = (
    "COMPANY_ID",
    "REPOSITORY_ID",
    "AWS_REGION",
    "MEMORY_LAYER_AWS_SECRET_NAME_PREFIX",
    "KNOWLEDGE_API_URL",
    "KNOWLEDGE_WORKER_URL",
    "MEMORY_ADAPTER_URL",
    "SCOPE_ARTIFACT_BUCKET",
)

_SENSITIVE_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "KEY")


def _load_payload_file(path: str) -> dict[str, str]:
    content = Path(path).read_text(encoding="utf-8")
    return parse_secret_string(content)


def _parse_set_pairs(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in items:
        if "=" not in raw:
            raise ValueError(f"invalid --set '{raw}' (expected KEY=VALUE)")
        key, value = raw.split("=", 1)
        k = key.strip()
        if not k:
            raise ValueError(f"invalid --set '{raw}' (empty key)")
        out[k] = value
    return out


def _scope_defaults() -> dict[str, str]:
    root = repo_root()
    env = load_env_file(root / ".canon" / "memory-layer.local.env")
    return {
        "COMPANY_ID": env.get("COMPANY_ID", "").strip(),
        "REPOSITORY_ID": env.get("REPOSITORY_ID", "").strip(),
        "MEMORY_LAYER_AWS_SECRET_NAME_PREFIX": env.get("MEMORY_LAYER_AWS_SECRET_NAME_PREFIX", "").strip(),
        "AWS_REGION": (
            env.get("AWS_REGION", "").strip()
            or os.environ.get("AWS_REGION", "").strip()
            or os.environ.get("AWS_DEFAULT_REGION", "").strip()
            or "us-east-1"
        ),
    }


def _resolve_secret_id(*, explicit_secret_id: str, company_id: str, repository_id: str, prefix: str) -> str:
    if explicit_secret_id.strip():
        return explicit_secret_id.strip()
    if not (company_id.strip() and repository_id.strip() and prefix.strip()):
        return ""
    return (
        f"{prefix.strip()}/memory-layer__{slug_canon_systems_segment(company_id)}__"
        f"{slug_canon_systems_segment(repository_id)}"
    )


def _resolve_source_secret_id(
    *,
    source_secret_id: str,
    source_company_id: str,
    source_repository_id: str,
    source_prefix: str,
) -> str:
    return _resolve_secret_id(
        explicit_secret_id=source_secret_id,
        company_id=source_company_id,
        repository_id=source_repository_id,
        prefix=source_prefix or DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX,
    )


def _secrets_client(*, profile: str, region: str):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is not installed; reinstall canon-systems with [aws] extra") from exc

    if profile.strip():
        session = boto3.session.Session(profile_name=profile.strip(), region_name=region.strip() or None)
        return session.client("secretsmanager")
    if region.strip():
        return boto3.client("secretsmanager", region_name=region.strip())
    return boto3.client("secretsmanager")


def _secret_exists(client: Any, secret_id: str) -> bool:
    try:
        client.describe_secret(SecretId=secret_id)
        return True
    except Exception as exc:
        code = ""
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            code = str(response.get("Error", {}).get("Code", ""))
        if code == "ResourceNotFoundException":
            return False
        raise


def _validate_payload(
    payload: dict[str, str],
    *,
    required_keys: tuple[str, ...],
    expected_company_id: str,
    expected_repository_id: str,
) -> list[str]:
    errors: list[str] = []
    missing = [k for k in required_keys if not payload.get(k, "").strip()]
    if missing:
        errors.append(f"missing required keys: {', '.join(missing)}")

    company = payload.get("COMPANY_ID", "").strip()
    repo = payload.get("REPOSITORY_ID", "").strip()
    if expected_company_id and company and company != expected_company_id:
        errors.append(f"COMPANY_ID mismatch (payload={company}, expected={expected_company_id})")
    if expected_repository_id and repo and repo != expected_repository_id:
        errors.append(f"REPOSITORY_ID mismatch (payload={repo}, expected={expected_repository_id})")
    return errors


def _redacted_keys(payload: dict[str, str]) -> list[str]:
    out: list[str] = []
    for key in sorted(payload.keys()):
        marker_hit = any(marker in key.upper() for marker in _SENSITIVE_MARKERS)
        out.append(f"{key}=<redacted>" if marker_hit else key)
    return out


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    entered = input(f"{label}{suffix}: ").strip()
    return entered or default


def _prompt_secret(label: str, default_present: bool) -> str:
    suffix = " [press Enter to keep existing]" if default_present else ""
    entered = getpass.getpass(f"{label}{suffix}: ").strip()
    return entered


def _read_existing_payload(client: Any, secret_id: str) -> dict[str, str]:
    try:
        resp = client.get_secret_value(SecretId=secret_id)
    except Exception:
        return {}
    raw = resp.get("SecretString")
    if not isinstance(raw, str) or not raw.strip():
        return {}
    return parse_secret_string(raw)


def _build_template_payload(*, company_id: str, repository_id: str, prefix: str, aws_region: str) -> dict[str, str]:
    base = "https://memory.canon-systems.com"
    return {
        "COMPANY_ID": company_id or "<COMPANY_ID>",
        "REPOSITORY_ID": repository_id or "<REPOSITORY_ID>",
        "MEMORY_LAYER_AWS_SECRET_NAME_PREFIX": prefix or DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX,
        "AWS_REGION": aws_region or "us-east-1",
        "KNOWLEDGE_API_URL": base,
        "KNOWLEDGE_WORKER_URL": base,
        "MEMORY_ADAPTER_URL": base,
        "CANON_STATE_API_URL": base,
        "SCOPE_ARTIFACT_BUCKET": "<artifact-bucket>",
        "CANON_HTTP_BEARER_TOKEN": "<token>",
    }


def _coerce_state_api_url(payload: dict[str, str]) -> None:
    """Persist state plane URL: default to knowledge base when not set (shared gateway or legacy secrets)."""
    if (payload.get("CANON_STATE_API_URL") or "").strip() or (payload.get("STATE_API_URL") or "").strip():
        return
    k = (payload.get("KNOWLEDGE_API_URL") or "").strip().rstrip("/")
    if k:
        payload["CANON_STATE_API_URL"] = k


def _submit_payload(
    *,
    payload: dict[str, str],
    company_id: str,
    repository_id: str,
    prefix: str,
    aws_region: str,
    aws_profile: str,
    secret_id_override: str,
    create_if_missing: bool,
    allow_partial: bool,
    dry_run: bool,
) -> int:
    _coerce_state_api_url(payload)

    required_keys = tuple() if allow_partial else _DEFAULT_REQUIRED_KEYS
    validation_errors = _validate_payload(
        payload,
        required_keys=required_keys,
        expected_company_id=company_id,
        expected_repository_id=repository_id,
    )
    if validation_errors:
        for err in validation_errors:
            print(f"canon secrets submit: {err}")
        print("canon secrets submit: use --allow-partial only for intentional incremental updates.")
        return 2

    secret_id = _resolve_secret_id(
        explicit_secret_id=secret_id_override,
        company_id=company_id,
        repository_id=repository_id,
        prefix=prefix,
    )
    if not secret_id:
        print("canon secrets submit: could not resolve secret id (set scope fields or pass --secret-id).")
        return 2

    print("canon secrets submit plan:")
    print(f"- secret_id: {secret_id}")
    print(f"- aws_region: {aws_region}")
    if aws_profile:
        print(f"- aws_profile: {aws_profile.strip()}")
    print(f"- create_if_missing: {bool(create_if_missing)}")
    print(f"- payload_keys: {', '.join(_redacted_keys(payload))}")

    if dry_run:
        return 0

    try:
        client = _secrets_client(profile=aws_profile, region=aws_region)
    except RuntimeError as exc:
        print(f"canon secrets submit: {exc}")
        return 2
    except Exception as exc:
        print(f"canon secrets submit: failed to create AWS client: {exc}")
        return 1

    secret_string = json.dumps(payload, sort_keys=True)
    try:
        if _secret_exists(client, secret_id):
            resp = client.put_secret_value(SecretId=secret_id, SecretString=secret_string)
            op = "put_secret_value"
        elif create_if_missing:
            resp = client.create_secret(Name=secret_id, SecretString=secret_string)
            op = "create_secret"
        else:
            print("canon secrets submit: secret does not exist (use --create-if-missing).")
            return 2
    except Exception as exc:
        print(f"canon secrets submit: AWS write failed: {exc}")
        return 1

    version = ""
    if isinstance(resp, dict):
        version = str(resp.get("VersionId", "")).strip()
    print(f"canon secrets submit: success via {op} ({secret_id})")
    if version:
        print(f"canon secrets submit: version_id={version}")
    return 0


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Structured Canon secret submission workflow.")
    sub = parser.add_subparsers(dest="secrets_command", required=False)

    submit = sub.add_parser("submit", help="Validate and submit repo-scoped secret payload to AWS Secrets Manager.")
    submit.add_argument("--payload-file", default="", help="JSON or dotenv file containing secret key/value pairs.")
    submit.add_argument("--set", action="append", default=[], help="Override/add KEY=VALUE (repeatable).")
    submit.add_argument("--secret-id", default="", help="Explicit AWS secret id to write.")
    submit.add_argument("--company-id", default="", help="Override COMPANY_ID scope.")
    submit.add_argument("--repository-id", default="", help="Override REPOSITORY_ID scope.")
    submit.add_argument(
        "--prefix",
        default="",
        help="Override MEMORY_LAYER_AWS_SECRET_NAME_PREFIX (ignored if --secret-id is set).",
    )
    submit.add_argument("--aws-profile", default="", help="AWS profile to use.")
    submit.add_argument("--aws-region", default="", help="AWS region to use.")
    submit.add_argument("--create-if-missing", action="store_true", help="Create secret when id does not exist.")
    submit.add_argument("--allow-partial", action="store_true", help="Skip required-key validation.")
    submit.add_argument("--dry-run", action="store_true", help="Validate and print plan; do not write AWS.")

    template = sub.add_parser("template", help="Print canonical JSON template for secret submission.")
    template.add_argument("--company-id", default="")
    template.add_argument("--repository-id", default="")
    template.add_argument("--prefix", default="")
    template.add_argument("--aws-region", default="")

    wizard = sub.add_parser("wizard", help="Interactive guided secret setup/write flow.")
    wizard.add_argument("--company-id", default="")
    wizard.add_argument("--repository-id", default="")
    wizard.add_argument("--prefix", default="")
    wizard.add_argument("--aws-profile", default="")
    wizard.add_argument("--aws-region", default="")
    wizard.add_argument("--secret-id", default="")
    wizard.add_argument("--copy-from-secret-id", default="")
    wizard.add_argument("--copy-from-company-id", default="")
    wizard.add_argument("--copy-from-repository-id", default="")
    wizard.add_argument("--copy-from-prefix", default="")
    wizard.add_argument("--allow-partial", action="store_true")
    wizard.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    scope = _scope_defaults()
    company_id = (getattr(args, "company_id", "") or scope["COMPANY_ID"]).strip()
    repository_id = (getattr(args, "repository_id", "") or scope["REPOSITORY_ID"]).strip()
    prefix = (
        getattr(args, "prefix", "")
        or scope["MEMORY_LAYER_AWS_SECRET_NAME_PREFIX"]
        or DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX
    ).strip()
    aws_region = (getattr(args, "aws_region", "") or scope["AWS_REGION"]).strip()

    command = args.secrets_command or "wizard"

    if command == "template":
        payload = _build_template_payload(
            company_id=company_id,
            repository_id=repository_id,
            prefix=prefix,
            aws_region=aws_region,
        )
        print(json.dumps(payload, indent=2))
        return 0

    if command == "wizard":
        print("Canon secrets wizard")
        print(f"Target repo: {repo_root()}")
        company_id = _prompt("Company ID", company_id or "IMC")
        repository_id = _prompt("Repository ID", repository_id or repo_root().name)
        prefix = _prompt(
            "Secret prefix",
            prefix or DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX,
        )
        aws_region = _prompt("AWS region", aws_region or "us-east-1")
        aws_profile = _prompt("AWS profile (optional)", getattr(args, "aws_profile", ""))
        secret_id_override = _prompt("Explicit secret id (optional)", getattr(args, "secret_id", ""))

        secret_id_preview = _resolve_secret_id(
            explicit_secret_id=secret_id_override,
            company_id=company_id,
            repository_id=repository_id,
            prefix=prefix,
        )
        print(f"Resolved secret id: {secret_id_preview}")

        existing_payload: dict[str, str] = {}
        if secret_id_preview:
            try:
                client = _secrets_client(profile=aws_profile, region=aws_region)
                existing_payload = _read_existing_payload(client, secret_id_preview)
            except Exception:
                existing_payload = {}
        if existing_payload:
            print("Loaded existing secret values (sensitive values remain hidden).")

        source_secret_id = getattr(args, "copy_from_secret_id", "").strip()
        source_company_id = getattr(args, "copy_from_company_id", "").strip()
        source_repository_id = getattr(args, "copy_from_repository_id", "").strip()
        source_prefix = getattr(args, "copy_from_prefix", "").strip()
        source_payload: dict[str, str] = {}
        if source_secret_id or (source_company_id and source_repository_id):
            resolved_source = _resolve_source_secret_id(
                source_secret_id=source_secret_id,
                source_company_id=source_company_id,
                source_repository_id=source_repository_id,
                source_prefix=source_prefix,
            )
            if resolved_source:
                try:
                    client = _secrets_client(profile=aws_profile, region=aws_region)
                    source_payload = _read_existing_payload(client, resolved_source)
                    if source_payload:
                        print(f"Imported values from source secret: {resolved_source}")
                except Exception:
                    source_payload = {}
        else:
            reuse = _prompt("Reuse credentials from another secret/repo? (y/n)", "n").strip().lower()
            if reuse in ("y", "yes"):
                source_secret_id = _prompt("Source secret id (optional)", "")
                if not source_secret_id:
                    source_company_id = _prompt("Source company ID", company_id)
                    source_repository_id = _prompt("Source repository ID", repository_id)
                    source_prefix = _prompt("Source prefix", prefix or DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX)
                resolved_source = _resolve_source_secret_id(
                    source_secret_id=source_secret_id,
                    source_company_id=source_company_id,
                    source_repository_id=source_repository_id,
                    source_prefix=source_prefix,
                )
                if resolved_source:
                    try:
                        client = _secrets_client(profile=aws_profile, region=aws_region)
                        source_payload = _read_existing_payload(client, resolved_source)
                        if source_payload:
                            print(f"Imported values from source secret: {resolved_source}")
                        else:
                            print(f"No readable source payload found at: {resolved_source}")
                    except Exception:
                        print(f"Could not load source secret: {resolved_source}")

        payload = _build_template_payload(
            company_id=company_id,
            repository_id=repository_id,
            prefix=prefix,
            aws_region=aws_region,
        )
        payload.update(source_payload)
        payload.update(existing_payload)
        payload["COMPANY_ID"] = company_id
        payload["REPOSITORY_ID"] = repository_id
        payload["MEMORY_LAYER_AWS_SECRET_NAME_PREFIX"] = prefix
        payload["AWS_REGION"] = aws_region

        payload["KNOWLEDGE_API_URL"] = _prompt("KNOWLEDGE_API_URL", payload.get("KNOWLEDGE_API_URL", ""))
        payload["KNOWLEDGE_WORKER_URL"] = _prompt("KNOWLEDGE_WORKER_URL", payload.get("KNOWLEDGE_WORKER_URL", ""))
        payload["MEMORY_ADAPTER_URL"] = _prompt("MEMORY_ADAPTER_URL", payload.get("MEMORY_ADAPTER_URL", ""))
        _coerce_state_api_url(payload)
        payload["SCOPE_ARTIFACT_BUCKET"] = _prompt("SCOPE_ARTIFACT_BUCKET", payload.get("SCOPE_ARTIFACT_BUCKET", ""))
        token_entered = _prompt_secret(
            "CANON_HTTP_BEARER_TOKEN",
            default_present=bool(payload.get("CANON_HTTP_BEARER_TOKEN", "").strip()),
        )
        if token_entered:
            payload["CANON_HTTP_BEARER_TOKEN"] = token_entered

        create_default = "y" if existing_payload else "n"
        create_answer = _prompt("Create secret if missing? (y/n)", create_default).strip().lower()
        create_if_missing = create_answer in ("y", "yes")

        print("")
        print("Review plan:")
        print(f"- secret_id: {secret_id_preview}")
        print(f"- aws_region: {aws_region}")
        if aws_profile:
            print(f"- aws_profile: {aws_profile}")
        print(f"- create_if_missing: {create_if_missing}")
        print(f"- payload_keys: {', '.join(_redacted_keys(payload))}")
        confirm = _prompt("Submit now? (y/n)", "y").strip().lower()
        if confirm not in ("y", "yes"):
            print("canon secrets submit: cancelled.")
            return 0

        return _submit_payload(
            payload=payload,
            company_id=company_id,
            repository_id=repository_id,
            prefix=prefix,
            aws_region=aws_region,
            aws_profile=aws_profile,
            secret_id_override=secret_id_override,
            create_if_missing=create_if_missing,
            allow_partial=bool(getattr(args, "allow_partial", False)),
            dry_run=bool(getattr(args, "dry_run", False)),
        )

    payload: dict[str, str] = {}
    if args.payload_file:
        payload.update(_load_payload_file(args.payload_file))
    payload.update(
        {
            "COMPANY_ID": company_id,
            "REPOSITORY_ID": repository_id,
            "MEMORY_LAYER_AWS_SECRET_NAME_PREFIX": prefix,
            "AWS_REGION": aws_region,
        }
    )
    try:
        payload.update(_parse_set_pairs(args.set))
    except ValueError as exc:
        print(f"canon secrets submit: {exc}")
        return 2
    return _submit_payload(
        payload=payload,
        company_id=company_id,
        repository_id=repository_id,
        prefix=prefix,
        aws_region=aws_region,
        aws_profile=args.aws_profile,
        secret_id_override=args.secret_id,
        create_if_missing=bool(args.create_if_missing),
        allow_partial=bool(args.allow_partial),
        dry_run=bool(args.dry_run),
    )


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
