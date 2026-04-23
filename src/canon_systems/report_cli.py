"""`canon report` CLI.

Read NDJSON canonical event streams and emit either:

- a narrow ``{by, groups}`` rollup grouped by ``source``, ``phase``, or
  ``agent`` (E3-T5-compatible, still the default), or
- the full E6-T1 ``metrics_rollup`` schema when ``--full`` is passed.

Both modes support scope (``--company-id`` / ``--repository-id`` /
``--plan-id`` / ``--task-id``) and window (``--since`` / ``--until``)
filters and optional CSV export via ``--format csv``.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import metrics_rollup

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FILE_NOT_FOUND = 3
EXIT_MALFORMED = 4

_GROUPBY_CHOICES = ("phase", "agent", "source")
_FORMAT_CHOICES = ("json", "csv")


class _Malformed(Exception):
    pass


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


def _parse_iso_z(ts: str) -> datetime | None:
    s = (ts or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _filter_events(
    events: list[dict[str, Any]],
    *,
    scope: dict[str, str],
    since: datetime | None,
    until: datetime | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in events:
        if scope.get("company_id") and str(ev.get("company_id", "")) != scope["company_id"]:
            continue
        if scope.get("repository_id") and str(ev.get("repository_id", "")) != scope["repository_id"]:
            continue
        if scope.get("plan_id") and str(ev.get("plan_id", "")) != scope["plan_id"]:
            continue
        if scope.get("task_id") and str(ev.get("task_id", "")) != scope["task_id"]:
            continue
        if since is not None or until is not None:
            ts = _parse_iso_z(str(ev.get("timestamp", "")))
            if ts is None:
                continue
            if since is not None and ts < since:
                continue
            if until is not None and ts > until:
                continue
        out.append(ev)
    return out


def _aggregate_groupby(
    events: list[dict[str, Any]],
    *,
    by: str,
) -> dict[str, dict[str, int]]:
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"tokens_in": 0, "tokens_out": 0})
    for ev in events:
        if ev.get("event_type") != "retrieval_breakdown":
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


def _render_groupby_csv(by: str, groups: dict[str, dict[str, int]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([by, "tokens_in", "tokens_out"])
    for key in sorted(groups.keys()):
        writer.writerow([key, groups[key]["tokens_in"], groups[key]["tokens_out"]])
    return buf.getvalue()


def _render_full_csv(rollup: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["section", "key", "tokens_in", "tokens_out", "count"])
    for section_name in ("by_phase", "by_agent", "by_source"):
        for key, counts in sorted((rollup.get("token_cost", {}) or {}).get(section_name, {}).items()):
            writer.writerow([
                section_name,
                key,
                counts.get("tokens_in", 0),
                counts.get("tokens_out", 0),
                "",
            ])
    for phase, counts in sorted((rollup.get("cycle_time_by_phase", {}) or {}).items()):
        writer.writerow([
            "cycle_time_by_phase",
            phase,
            "",
            "",
            counts.get("total_seconds", 0),
        ])
    for task_id, info in sorted((rollup.get("lead_time_by_task", {}) or {}).items()):
        writer.writerow(["lead_time_by_task", task_id, "", "", info.get("seconds", 0)])
    for stage, count in sorted((rollup.get("dor_causes", {}) or {}).items()):
        writer.writerow(["dor_causes", stage, "", "", count])
    stalls = rollup.get("stalls", {}) or {}
    writer.writerow(["stalls", "total", "", "", stalls.get("total", 0)])
    for task_id, count in sorted((stalls.get("by_task", {}) or {}).items()):
        writer.writerow(["stalls_by_task", task_id, "", "", count])
    sp = rollup.get("synth_publish", {}) or {}
    for key in ("ok", "failed", "notifier_ok"):
        writer.writerow(["synth_publish", key, "", "", sp.get(key, 0)])
    return buf.getvalue()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon report",
        description=(
            "Aggregate canonical events (retrieval_breakdown, synth_publish, "
            "lease_stall_detected, dor_failure, ...) into a stable JSON/CSV rollup."
        ),
    )
    p.add_argument("--events", required=True, help="Path to NDJSON file of canonical events.")
    p.add_argument("--by", choices=_GROUPBY_CHOICES, default="source")
    p.add_argument("--format", choices=_FORMAT_CHOICES, default="json")
    p.add_argument(
        "--full",
        action="store_true",
        help="Emit the complete E6-T1 metrics_rollup schema instead of the --by groups envelope.",
    )
    p.add_argument("--plan-id", default=None)
    p.add_argument("--task-id", default=None)
    p.add_argument("--company-id", default=None)
    p.add_argument("--repository-id", default=None)
    p.add_argument("--since", default=None, help="ISO-8601 Z lower bound (inclusive).")
    p.add_argument("--until", default=None, help="ISO-8601 Z upper bound (inclusive).")
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

    scope = {
        "company_id": str(args.company_id or "").strip(),
        "repository_id": str(args.repository_id or "").strip(),
        "plan_id": str(args.plan_id or "").strip(),
        "task_id": str(args.task_id or "").strip(),
    }
    since = _parse_iso_z(args.since or "") if args.since else None
    until = _parse_iso_z(args.until or "") if args.until else None

    filtered = _filter_events(events, scope=scope, since=since, until=until)

    if args.full:
        rollup_scope = {k: v for k, v in scope.items() if v and k != "task_id"}
        window: dict[str, str] = {}
        if args.since:
            window["since"] = args.since
        if args.until:
            window["until"] = args.until
        rollup = metrics_rollup.aggregate(filtered, scope=rollup_scope, window=window)
        if args.format == "csv":
            sys.stdout.write(_render_full_csv(rollup))
        else:
            sys.stdout.write(json.dumps(rollup, sort_keys=True) + "\n")
        return EXIT_OK

    groups = _aggregate_groupby(filtered, by=args.by)
    if args.format == "csv":
        sys.stdout.write(_render_groupby_csv(args.by, groups))
        return EXIT_OK
    out = {"by": args.by, "groups": groups}
    print(json.dumps(out, sort_keys=True))
    return EXIT_OK


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
