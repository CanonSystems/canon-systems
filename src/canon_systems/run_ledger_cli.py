"""``canon run-ledger`` — validate ledger JSON, optional archive-ref merge, dry-run or PUT to state-api."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from canon_backend_shared.run_ledger import RunLedgerValidationError

from .packet_archive import default_state_api_base
from .run_ledger import (
    post_run_ledger_to_state_api,
    prepare_cli_run_ledger_record,
)


def _load_json(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="canon run-ledger",
        description=(
            "Prepare a versioned run-ledger record from JSON, optionally merge packet-archive "
            "metadata into ``archive_refs`` by reference only, then either print the normalized "
            "record (``--dry-run``) or PUT it to state-api (``PUT /state/run-ledger``)."
        ),
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--record-file",
        metavar="PATH",
        default="",
        help="Path to a JSON object: the run ledger record (before optional archive merge).",
    )
    src.add_argument(
        "--record-json",
        metavar="JSON",
        default="",
        help="Inline JSON object for the ledger record (shell-quoted).",
    )
    parser.add_argument(
        "--merge-archive-json",
        metavar="PATH",
        default="",
        help=(
            "Optional path to a JSON array of archive-record metadata objects; each is passed "
            "through ``archive_record_to_ledger_reference`` (no bodies on the ledger)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate + normalize and print JSON; no HTTP.",
    )
    parser.add_argument(
        "--state-api-url",
        default="",
        help=f"state-api base URL (default ``CANON_STATE_API_URL`` or {default_state_api_base()}).",
    )
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--quiet", action="store_true", help="Dry-run: single-line JSON on stdout.")

    args = parser.parse_args(argv)

    try:
        if args.record_file:
            record_raw = _load_json(Path(args.record_file))
        else:
            record_raw = json.loads(args.record_json)
    except json.JSONDecodeError as e:
        print(f"run-ledger: invalid JSON: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"run-ledger: failed to read file: {e}", file=sys.stderr)
        return 2

    if not isinstance(record_raw, dict):
        print("run-ledger: record must be a JSON object", file=sys.stderr)
        return 2

    snaps: list[dict[str, Any]] | None = None
    if args.merge_archive_json.strip():
        ap = Path(args.merge_archive_json.strip())
        try:
            merged = _load_json(ap)
        except (json.JSONDecodeError, OSError) as e:
            print(f"run-ledger: merge-archive-json: {e}", file=sys.stderr)
            return 2
        if not isinstance(merged, list):
            print("run-ledger: merge-archive-json must be a JSON array", file=sys.stderr)
            return 2
        bad = [i for i, x in enumerate(merged) if not isinstance(x, dict)]
        if bad:
            print(
                "run-ledger: merge-archive-json entries must all be JSON objects "
                f"(bad indices: {bad[:8]}{'…' if len(bad) > 8 else ''})",
                file=sys.stderr,
            )
            return 2
        snaps = merged

    try:
        normalized = prepare_cli_run_ledger_record(record_raw, snaps)
    except RunLedgerValidationError as e:
        print(f"run-ledger: validation error: {e}", file=sys.stderr)
        return 2

    if args.dry_run:
        indent = None if args.quiet else 2
        print(json.dumps(normalized, indent=indent))
        return 0

    base = args.state_api_url.strip() or default_state_api_base()
    status, parsed, headers = post_run_ledger_to_state_api(
        base_url=base,
        record=normalized,
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
