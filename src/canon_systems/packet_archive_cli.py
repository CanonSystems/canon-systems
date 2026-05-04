"""``canon packet-archive`` — upload a local packet/evidence file via state-api."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .packet_archive import (
    ArchiveValidationError,
    build_archive_request_payload,
    default_state_api_base,
    dry_run_archive_record,
    post_archive_to_state_api,
)


def _rfc3339z_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="canon packet-archive",
        description=(
            "Archive a packet or evidence file to the tenant S3 artifact bucket via state-api "
            "(``POST /state/archive``). Local ``.cursor/handoffs/...`` files remain required "
            "working-copy artifacts; this command adds a durable server-side copy."
        ),
    )
    parser.add_argument("--file", default="", help="Path to the packet or evidence file.")
    parser.add_argument(
        "--body-file",
        default="",
        help="Alias of --file (explicit body path).",
    )
    parser.add_argument("--company-id", required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--workstream-id", required=True)
    parser.add_argument("--handoff-id", required=True)
    parser.add_argument("--phase", required=True, help="Agent phase label (e.g. scoper, implementer).")
    parser.add_argument(
        "--artifact-kind",
        required=True,
        help=(
            "Built-in kind (e.g. packet_scoper, dor_telemetry, evidence_memory_health) "
            "or extension evidence_<slug>."
        ),
    )
    parser.add_argument(
        "--source-label",
        default="",
        help="Logical source path or label stored on the archive record (defaults to --file).",
    )
    parser.add_argument("--content-type", default="", help="MIME type (guessed from filename if omitted).")
    parser.add_argument("--evidence-subtype", default="", help="Shard id / QA subtype segment when required.")
    parser.add_argument("--agent-run-id", default="")
    parser.add_argument("--actor-id", default="")
    parser.add_argument("--outcome", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--dry-run", action="store_true", help="Resolve metadata + print JSON; no network I/O.")
    parser.add_argument(
        "--dry-run-bucket",
        default="",
        help="Bucket name printed on dry-run records (default CANON_STATE_ARTIFACT_BUCKET or placeholder).",
    )
    parser.add_argument(
        "--dry-run-prefix",
        default="",
        help="Key prefix for dry-run resolution (default CANON_STATE_ARCHIVE_KEY_PREFIX or canon/packets).",
    )
    parser.add_argument(
        "--state-api-url",
        default="",
        help=f"state-api base URL (default env CANON_STATE_API_URL or {default_state_api_base()}).",
    )
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--quiet", action="store_true", help="Emit only JSON on stdout (no banners).")

    args = parser.parse_args(argv)
    path_s = (args.file or args.body_file or "").strip()
    if not path_s:
        print("packet-archive: --file is required unless using tests that inject body separately", file=sys.stderr)
        return 2
    path = Path(path_s)
    if not path.is_file():
        print(f"packet-archive: not a file: {path}", file=sys.stderr)
        return 2

    body = path.read_bytes()
    source_label = args.source_label.strip() or str(path)
    ctype = args.content_type.strip()
    if not ctype:
        guessed, _enc = mimetypes.guess_type(path.name)
        ctype = guessed or "application/octet-stream"

    evidence_subtype = args.evidence_subtype.strip() or None

    if args.dry_run:
        bucket = (
            args.dry_run_bucket.strip()
            or os.environ.get("STATE_ARTIFACT_BUCKET", "").strip()
            or os.environ.get("CANON_STATE_ARTIFACT_BUCKET", "").strip()
            or "dry-run-bucket"
        )
        prefix = (
            args.dry_run_prefix.strip()
            or os.environ.get("STATE_ARCHIVE_KEY_PREFIX", "").strip()
            or os.environ.get("CANON_STATE_ARCHIVE_KEY_PREFIX", "").strip()
            or "canon/packets"
        )
        try:
            record = dry_run_archive_record(
                bucket=bucket,
                key_prefix=prefix,
                body=body,
                company_id=args.company_id,
                repository_id=args.repository_id,
                plan_id=args.plan_id,
                task_id=args.task_id,
                workstream_id=args.workstream_id,
                handoff_id=args.handoff_id,
                phase=args.phase,
                artifact_kind=args.artifact_kind,
                source_label=source_label,
                content_type=ctype,
                created_at=_rfc3339z_now(),
                agent_run_id=args.agent_run_id,
                actor_id=args.actor_id,
                outcome=args.outcome,
                status=args.status,
                evidence_subtype=evidence_subtype,
            )
        except ArchiveValidationError as e:
            print(f"packet-archive: validation error: {e}", file=sys.stderr)
            return 2
        print(json.dumps(record, indent=2 if not args.quiet else None))
        return 0

    base = args.state_api_url.strip() or default_state_api_base()
    try:
        payload = build_archive_request_payload(
            body=body,
            company_id=args.company_id,
            repository_id=args.repository_id,
            plan_id=args.plan_id,
            task_id=args.task_id,
            workstream_id=args.workstream_id,
            handoff_id=args.handoff_id,
            phase=args.phase,
            artifact_kind=args.artifact_kind,
            source_label=source_label,
            content_type=ctype,
            agent_run_id=args.agent_run_id,
            actor_id=args.actor_id,
            outcome=args.outcome,
            status=args.status,
            evidence_subtype=evidence_subtype,
        )
    except ArchiveValidationError as e:
        print(f"packet-archive: validation error: {e}", file=sys.stderr)
        return 2

    status, parsed, headers = post_archive_to_state_api(
        base_url=base,
        payload=payload,
        timeout_seconds=args.timeout_seconds,
    )
    event_id = headers.get("X-Canon-Event-Id", headers.get("x-canon-event-id", ""))
    if status >= 400:
        print(
            json.dumps({"http_status": status, "detail": parsed}, indent=2 if not args.quiet else None),
            file=sys.stderr,
        )
        return 1
    out = dict(parsed)
    if event_id:
        out["_event_id"] = event_id
    print(json.dumps(out, indent=2 if not args.quiet else None))
    return 0
