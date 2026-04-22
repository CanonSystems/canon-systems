"""canon report CLI (Wave-3 stub per backlog §E3-T5; Wave 6 will polish)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FILE_NOT_FOUND = 3
EXIT_MALFORMED = 4

_GROUPBY_CHOICES = ("phase", "agent", "source")


def _load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise _Malformed(f"line {lineno}: {exc}") from exc
    return events


class _Malformed(Exception):
    pass


def _aggregate(
    events: list[dict[str, Any]],
    *,
    by: str,
    plan_id: str | None,
    task_id: str | None,
) -> dict[str, dict[str, int]]:
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"tokens_in": 0, "tokens_out": 0})
    for ev in events:
        if ev.get("event_type") != "retrieval_breakdown":
            continue
        if plan_id is not None and ev.get("plan_id") != plan_id:
            continue
        if task_id is not None and ev.get("task_id") != task_id:
            continue
        payload = ev.get("payload", {}) or {}
        sources = payload.get("sources", {}) or {}
        if by == "source":
            for src, counts in sources.items():
                buckets[src]["tokens_in"] += int(counts.get("tokens_in", 0))
                buckets[src]["tokens_out"] += int(counts.get("tokens_out", 0))
        elif by in ("phase", "agent"):
            key = str(ev.get("agent_name", "unknown"))
            totals = payload.get("totals", {}) or {}
            buckets[key]["tokens_in"] += int(totals.get("tokens_in", 0))
            buckets[key]["tokens_out"] += int(totals.get("tokens_out", 0))
        else:
            raise ValueError(f"unknown --by: {by}")
    return dict(sorted(buckets.items()))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon report",
        description="Aggregate retrieval_breakdown canonical events (stub; Wave 6 polishes).",
    )
    p.add_argument("--events", required=True, help="Path to NDJSON file of canonical events.")
    p.add_argument("--by", choices=_GROUPBY_CHOICES, default="source")
    p.add_argument("--plan-id", default=None)
    p.add_argument("--task-id", default=None)
    return p


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
    path = Path(args.events)
    if not path.is_file():
        print(f"error: --events file not found: {path}", file=sys.stderr)
        return EXIT_FILE_NOT_FOUND
    try:
        events = _load_events(path)
    except _Malformed as exc:
        print(f"error: malformed NDJSON: {exc}", file=sys.stderr)
        return EXIT_MALFORMED
    agg = _aggregate(events, by=args.by, plan_id=args.plan_id, task_id=args.task_id)
    out = {"by": args.by, "groups": agg}
    print(json.dumps(out, sort_keys=True))
    return EXIT_OK


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
