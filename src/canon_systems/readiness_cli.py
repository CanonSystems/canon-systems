"""``canon readiness check`` — run-ledger-backed readiness snapshot + exit codes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .packet_archive import default_state_api_base
from .readiness import evaluate_readiness
from .run_ledger import RunLedgerGetError

EXIT_OK = 0
EXIT_NOT_READY = 1
EXIT_USAGE_OR_QUERY = 2


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="canon readiness",
        description=(
            "Operator readiness over durable run-ledger rows (GET /state/run-ledger). "
            "Emits a JSON snapshot; exit 0 when ready, 1 when evaluated not ready, 2 on usage/query errors."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser(
        "check",
        help="Query run-ledger for the task scope and emit a readiness snapshot.",
        description=(
            "GET /state/run-ledger (scoped list or single ledger_run_id) and build a JSON readiness snapshot. "
            "See docs/SYSTEM-WORKFLOW.md persistence contract."
        ),
    )
    check.add_argument("--company-id", required=True)
    check.add_argument("--repository-id", required=True)
    check.add_argument("--plan-id", required=True)
    check.add_argument("--task-id", required=True)
    check.add_argument("--workstream-id", required=True)
    check.add_argument("--handoff-id", required=True)
    check.add_argument(
        "--ledger-run-id",
        default="",
        help="Optional explicit ledger_run_id (single-record GET). Omit for latest scoped query.",
    )
    check.add_argument(
        "--state-api-url",
        default="",
        help="state-api base URL (default CANON_STATE_API_URL or dev default).",
    )
    check.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max rows for scoped list query (1–200; forwarded to state-api).",
    )
    check.add_argument(
        "--output",
        default="",
        metavar="PATH",
        help="Write the same JSON snapshot as stdout to this path (e.g. .cursor/handoffs/<handoff_id>/<task_id>/readiness.json).",
    )
    check.add_argument("--timeout-seconds", type=float, default=60.0)
    check.add_argument(
        "--quiet",
        action="store_true",
        help="Print compact JSON on stdout (and still write --output when set).",
    )

    args = parser.parse_args(argv)
    if args.command != "check":
        print("readiness: only subcommand 'check' is supported", file=sys.stderr)
        return EXIT_USAGE_OR_QUERY

    if args.limit < 1 or args.limit > 200:
        print("readiness: --limit must be between 1 and 200", file=sys.stderr)
        return EXIT_USAGE_OR_QUERY

    rid = args.ledger_run_id.strip() or None
    base = args.state_api_url.strip() or default_state_api_base()

    try:
        snapshot = evaluate_readiness(
            base_url=base,
            company_id=args.company_id,
            repository_id=args.repository_id,
            plan_id=args.plan_id,
            task_id=args.task_id,
            workstream_id=args.workstream_id,
            handoff_id=args.handoff_id,
            ledger_run_id=rid,
            limit=args.limit,
            timeout_seconds=args.timeout_seconds,
        )
    except RunLedgerGetError as e:
        payload = {
            "error": "run_ledger_query_failed",
            "exception": e.__class__.__name__,
            "message": str(e),
        }
        print(json.dumps(payload, indent=2), file=sys.stderr)
        return EXIT_USAGE_OR_QUERY

    out = json.dumps(snapshot, indent=None if args.quiet else 2)
    print(out)
    op = args.output.strip()
    if op:
        path = Path(op)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(out + "\n", encoding="utf-8")

    return EXIT_OK if snapshot.get("ready") else EXIT_NOT_READY
