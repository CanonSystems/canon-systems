"""canon synth publish: idempotent diff-only driver for SynthesisPublisher.

Reads canonical events from a JSONL file, renders a deterministic VaultBundle
via backend/synthesis generate_vault, and publishes to S3 with content-hash
diff-only writes. Safe to invoke repeatedly.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_TRANSPORT = 2
EXIT_USAGE = 4

_REQUIRED_EVENT_FIELDS = (
    "schema_version",
    "event_id",
    "parent_event_id",
    "event_type",
    "company_id",
    "repository_id",
    "plan_id",
    "task_id",
    "handoff_id",
    "agent_name",
    "agent_run_id",
    "actor_id",
    "model",
    "timestamp",
    "state_version",
    "payload",
)


def _ensure_repo_backend_import_path() -> None:
    """Make `canon_backend_shared` + `synthesis` importable in monorepo dev/test."""
    root = Path(os.environ.get("CANON_SYSTEMS_REPO_ROOT", str(Path.cwd()))).resolve()
    for sub in ("backend/shared", "backend/synthesis"):
        p = root / sub
        if p.is_dir():
            s = str(p)
            if s not in sys.path:
                sys.path.insert(0, s)


def _s3_client_factory(aws_region: str, aws_profile: str) -> Any:
    """Return a boto3 S3 client. Monkeypatched in tests to return a dict-fake."""
    import boto3  # lazy import to keep --help cheap and avoid hard dep at import-time

    session = boto3.Session(
        profile_name=aws_profile or None,
        region_name=aws_region or None,
    )
    return session.client("s3")


def _load_events(path: Path) -> list[Any]:
    from canon_backend_shared.events import CanonicalEvent

    raw = path.read_text(encoding="utf-8")
    out: list[Any] = []
    for ln_no, ln in enumerate(raw.splitlines(), start=1):
        s = ln.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {ln_no}: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"line {ln_no}: expected JSON object")
        for k in _REQUIRED_EVENT_FIELDS:
            if k not in obj:
                raise ValueError(f"line {ln_no}: missing field '{k}'")
        if obj["schema_version"] != 1:
            raise ValueError(f"line {ln_no}: schema_version must be 1")
        ev = CanonicalEvent(
            schema_version=int(obj["schema_version"]),
            event_id=str(obj["event_id"]),
            parent_event_id=str(obj["parent_event_id"]),
            event_type=str(obj["event_type"]),
            company_id=str(obj["company_id"]),
            repository_id=str(obj["repository_id"]),
            plan_id=str(obj["plan_id"]),
            task_id=str(obj["task_id"]),
            handoff_id=str(obj["handoff_id"]),
            agent_name=str(obj["agent_name"]),
            agent_run_id=str(obj["agent_run_id"]),
            actor_id=str(obj["actor_id"]),
            model=str(obj["model"]),
            timestamp=str(obj["timestamp"]),
            state_version=int(obj["state_version"]),
            payload=dict(obj["payload"]),
        )
        out.append(ev)
    return out


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon synth",
        description="Synthesis vault publishing driver (internal).",
    )
    sub = p.add_subparsers(dest="subcommand", required=True)

    pub = sub.add_parser("publish", help="Publish vault bundle to S3 (idempotent, diff-only).")
    pub.add_argument("--events-file", required=True)
    pub.add_argument("--plan-id", required=True)
    pub.add_argument("--company-id", required=True)
    pub.add_argument("--repository-id", required=True)
    pub.add_argument("--cutoff-timestamp", required=True, help="ISO-8601 Z; only events strictly after are included.")
    pub.add_argument("--bucket", required=True)
    pub.add_argument("--prefix", required=True, help="S3 key prefix (e.g. 'vaults/c1/r1').")
    pub.add_argument("--task-id", default=None)
    pub.add_argument("--dry-run", action="store_true")
    pub.add_argument("--aws-region", default="")
    pub.add_argument("--aws-profile", default="")
    return p


def _print_envelope(envelope: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(envelope, sort_keys=True) + "\n")
    sys.stdout.flush()


def _print_error(payload: dict[str, Any]) -> None:
    sys.stderr.write(json.dumps(payload, sort_keys=True) + "\n")
    sys.stderr.flush()


def _publish(args: argparse.Namespace) -> int:
    from synthesis.generator import generate_vault
    from synthesis.publisher import SynthesisPublisher
    from synthesis.sources import InMemoryEventSource

    events_path = Path(args.events_file)
    try:
        events = _load_events(events_path)
    except FileNotFoundError:
        _print_error({"error": "usage", "detail": f"events-file not found: {events_path}"})
        return EXIT_USAGE
    except ValueError as exc:
        _print_error({"error": "usage", "detail": str(exc)})
        return EXIT_USAGE
    except OSError as exc:
        _print_error({"error": "usage", "detail": f"io: {exc}"})
        return EXIT_USAGE

    src = InMemoryEventSource(events)
    filtered = list(
        src.iter_events(
            plan_id=args.plan_id,
            task_id=args.task_id,
            cutoff_timestamp=args.cutoff_timestamp,
        )
    )
    bundle = generate_vault(
        filtered,
        company_id=args.company_id,
        repository_id=args.repository_id,
        cutoff_timestamp=args.cutoff_timestamp,
    )
    pages_rendered = len(bundle.pages)

    base_envelope: dict[str, Any] = {
        "bucket": args.bucket,
        "prefix": args.prefix,
        "plan_id": args.plan_id,
        "company_id": args.company_id,
        "repository_id": args.repository_id,
        "task_id": args.task_id,
        "cutoff_timestamp": args.cutoff_timestamp,
        "dry_run": bool(args.dry_run),
        "events_read": len(events),
        "pages_rendered": pages_rendered,
        "written": 0,
        "skipped": 0,
        "keys_written": [],
    }

    if args.dry_run:
        _print_envelope(base_envelope)
        return EXIT_OK

    try:
        client = _s3_client_factory(args.aws_region, args.aws_profile)
    except Exception as exc:  # noqa: BLE001 — boundary mapping
        _print_error({"error": "transport", "detail": f"s3_factory: {exc!r}"})
        return EXIT_TRANSPORT

    publisher = SynthesisPublisher(bucket=args.bucket, s3_client=client, prefix=args.prefix)
    try:
        result = publisher.publish(bundle)
    except Exception as exc:  # noqa: BLE001 — boundary mapping of ClientError/Boto3Error/OSError
        _print_error({"error": "transport", "detail": f"{type(exc).__name__}: {exc}"})
        return EXIT_TRANSPORT

    base_envelope["written"] = int(result.written)
    base_envelope["skipped"] = int(result.skipped)
    base_envelope["keys_written"] = list(result.keys_written)
    _print_envelope(base_envelope)
    return EXIT_OK


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    av = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parser.parse_args(av)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return EXIT_OK
        return EXIT_USAGE

    # Inject repo-root into environment for peer modules that honor it.
    os.environ.setdefault("CANON_SYSTEMS_REPO_ROOT", str(Path.cwd()))
    _ensure_repo_backend_import_path()

    if args.subcommand == "publish":
        return _publish(args)
    return EXIT_USAGE


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
