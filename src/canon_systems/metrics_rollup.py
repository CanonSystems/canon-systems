"""E6-T1: canonical-event metrics aggregator.

Consumes a stream of canonical events (see backend/shared
``CanonicalEvent``) and emits a stable JSON rollup covering lead/cycle
time per task, retries, DoR causes, stalls, token cost, and
``synth_publish`` health. The returned dict is deterministic under
``json.dumps(..., sort_keys=True)``.

Pure-Python, stdlib-only. No filesystem I/O, no canonical event
emission, no boto3/pandas/numpy imports.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from .retrieval_telemetry import comparison_from_payload

SCHEMA_VERSION = 1
_COMPARE_BY: frozenset[str] = frozenset({"memory_mode", "experiment_id"})

_PHASE_NAMES: tuple[str, ...] = (
    "scoper",
    "cursor-pilot",
    "implementer",
    "qa-gate",
    "release-orchestrator",
)


@dataclass(frozen=True)
class _Window:
    since: datetime | None
    until: datetime | None


def _parse_iso_z(ts: Any) -> datetime | None:
    if not isinstance(ts, str) or not ts.strip():
        return None
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _in_window(ts: datetime | None, window: _Window) -> bool:
    if ts is None:
        return False
    if window.since is not None and ts < window.since:
        return False
    if window.until is not None and ts > window.until:
        return False
    return True


def _in_scope(ev: Mapping[str, Any], scope: Mapping[str, str]) -> bool:
    for key in ("company_id", "repository_id", "plan_id"):
        wanted = scope.get(key)
        if wanted and str(ev.get(key, "")) != str(wanted):
            return False
    return True


def _event_matches_experiment_filters(
    ev: Mapping[str, Any],
    *,
    experiment_id: str,
    memory_mode: str,
) -> bool:
    c = comparison_from_payload(ev.get("payload"))
    if c is None:
        return False
    if experiment_id and c["experiment_id"] != experiment_id:
        return False
    if memory_mode and c["memory_mode"] != memory_mode:
        return False
    return True


def _coerce_int(val: Any) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _sort_nested(obj: Any) -> Any:
    """Return a structurally sorted copy so nested dicts serialize deterministically."""
    if isinstance(obj, dict):
        return {k: _sort_nested(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_sort_nested(x) for x in obj]
    return obj


def _compare_bucket_key(
    comparison: dict[str, str] | None,
    compare_by: str,
) -> str:
    if not comparison or compare_by not in comparison:
        return "unlabeled"
    return str(comparison[compare_by])


@dataclass
class _CompareBucket:
    tokens_in: int = 0
    tokens_out: int = 0
    task_outcomes_seen: int = 0
    status_completed_or_ready: int = 0
    qa_pass: int = 0
    qa_fail: int = 0
    elapsed_sum: int = 0
    retry_total: int = 0
    reopen_total: int = 0
    rework_total: int = 0


def _finalize_compare_buckets(
    by: str, raw: dict[str, _CompareBucket]
) -> dict[str, Any]:
    buckets: dict[str, Any] = {}
    for key in sorted(raw.keys()):
        b = raw[key]
        n = b.task_outcomes_seen
        avg_elapsed = (b.elapsed_sum + n // 2) // n if n else 0
        buckets[key] = {
            "tokens": {
                "tokens_in": b.tokens_in,
                "tokens_out": b.tokens_out,
            },
            "outcomes": {
                "task_outcomes_seen": b.task_outcomes_seen,
                "status_completed_or_ready": b.status_completed_or_ready,
                "qa_pass": b.qa_pass,
                "qa_fail": b.qa_fail,
                "avg_elapsed_seconds": int(avg_elapsed),
                "retry_total": b.retry_total,
                "reopen_total": b.reopen_total,
                "rework_total": b.rework_total,
            },
        }
    return {"by": by, "buckets": _sort_nested(buckets)}


def aggregate(
    events: Iterable[Mapping[str, Any]],
    *,
    scope: Mapping[str, str] | None = None,
    window: Mapping[str, str] | None = None,
    experiment_id: str | None = None,
    memory_mode: str | None = None,
    compare_by: str | None = None,
) -> dict[str, Any]:
    """Aggregate canonical events into a stable rollup dict.

    Parameters
    ----------
    events:
        Iterable of canonical-event-envelope dicts.
    scope:
        Optional filter on ``company_id``, ``repository_id``, ``plan_id``.
    window:
        Optional filter on ``since`` / ``until`` (ISO-8601 Z strings;
        events whose ``timestamp`` parses outside the window are
        dropped).
    experiment_id / memory_mode:
        Optional filters on ``payload.comparison`` (events without a
        valid comparison block are excluded when either is set).
    compare_by:
        When ``memory_mode`` or ``experiment_id``, adds a deterministic
        ``compare`` section with per-bucket token totals and task
        ``task_outcome`` summaries. Unlabeled events use the
        ``unlabeled`` bucket.

    Returns
    -------
    dict
        Rollup with the AC1 schema. Never raises on malformed event
        fields (missing/garbled data silently skipped or coerced to 0).
    """
    scope = dict(scope or {})
    window = dict(window or {})
    eid_f = (experiment_id or "").strip()
    mm_f = (memory_mode or "").strip().lower()
    cby: str | None = None
    if compare_by is not None and str(compare_by).strip():
        cby = str(compare_by).strip()
        if cby not in _COMPARE_BY:
            raise ValueError("compare_by must be 'memory_mode' or 'experiment_id'")

    win = _Window(
        since=_parse_iso_z(window.get("since")) if window.get("since") else None,
        until=_parse_iso_z(window.get("until")) if window.get("until") else None,
    )

    filtered: list[tuple[Mapping[str, Any], datetime]] = []
    events_total = 0
    for ev in events:
        if not isinstance(ev, Mapping):
            continue
        if not _in_scope(ev, scope):
            continue
        ts = _parse_iso_z(ev.get("timestamp"))
        if win.since is not None or win.until is not None:
            if not _in_window(ts, win):
                continue
        if eid_f or mm_f:
            if not _event_matches_experiment_filters(ev, experiment_id=eid_f, memory_mode=mm_f):
                continue
        events_total += 1
        if ts is not None:
            filtered.append((ev, ts))
        else:
            filtered.append((ev, datetime.min.replace(tzinfo=timezone.utc)))

    compare_raw: dict[str, _CompareBucket] | None = (
        defaultdict(_CompareBucket) if cby is not None else None
    )

    lead_time_by_task: dict[str, dict[str, Any]] = {}
    per_phase_ts: dict[str, dict[str, list[datetime]]] = defaultdict(lambda: defaultdict(list))
    retries: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    dor_causes: dict[str, int] = defaultdict(int)
    stalls_by_task: dict[str, int] = defaultdict(int)
    stalls_total = 0
    token_by_phase: dict[str, dict[str, int]] = defaultdict(lambda: {"tokens_in": 0, "tokens_out": 0})
    token_by_agent: dict[str, dict[str, int]] = defaultdict(lambda: {"tokens_in": 0, "tokens_out": 0})
    token_by_source: dict[str, dict[str, int]] = defaultdict(lambda: {"tokens_in": 0, "tokens_out": 0})
    tokens_in_total = 0
    tokens_out_total = 0
    publish_ok = 0
    publish_failed = 0
    notifier_ok = 0

    for ev, ts in filtered:
        task_id = str(ev.get("task_id", "") or "")
        agent_name = str(ev.get("agent_name", "") or "")
        etype = str(ev.get("event_type", "") or "")
        payload = ev.get("payload") or {}
        if not isinstance(payload, Mapping):
            payload = {}
        event_id = str(ev.get("event_id", "") or "")
        run_id = str(ev.get("agent_run_id", "") or "")

        if task_id and ts.tzinfo is not None and ts != datetime.min.replace(tzinfo=timezone.utc):
            bucket = lead_time_by_task.setdefault(task_id, {"first_ts": ts, "last_ts": ts})
            if ts < bucket["first_ts"]:
                bucket["first_ts"] = ts
            if ts > bucket["last_ts"]:
                bucket["last_ts"] = ts

        if task_id and agent_name in _PHASE_NAMES:
            per_phase_ts[agent_name][task_id].append(ts)
            if run_id and event_id:
                retries[task_id][agent_name].add(run_id)

        if etype == "dor_failure":
            stage = str(payload.get("stage", "") or "unknown")
            dor_causes[stage] += 1

        if etype == "lease_stall_detected":
            stalls_total += 1
            if task_id:
                stalls_by_task[task_id] += 1

        if etype == "retrieval_breakdown":
            totals = payload.get("totals") or {}
            if isinstance(totals, Mapping):
                tin = _coerce_int(totals.get("tokens_in"))
                tout = _coerce_int(totals.get("tokens_out"))
                tokens_in_total += tin
                tokens_out_total += tout
                if agent_name:
                    token_by_agent[agent_name]["tokens_in"] += tin
                    token_by_agent[agent_name]["tokens_out"] += tout
                    if agent_name in _PHASE_NAMES:
                        token_by_phase[agent_name]["tokens_in"] += tin
                        token_by_phase[agent_name]["tokens_out"] += tout
            if compare_raw is not None:
                c = comparison_from_payload(payload)
                bkey = _compare_bucket_key(c, cby or "")
                bk = compare_raw[bkey]
                if isinstance(totals, Mapping):
                    bk.tokens_in += _coerce_int(totals.get("tokens_in"))
                    bk.tokens_out += _coerce_int(totals.get("tokens_out"))
            sources = payload.get("sources") or {}
            if isinstance(sources, Mapping):
                for src, counts in sources.items():
                    if not isinstance(counts, Mapping):
                        continue
                    token_by_source[str(src)]["tokens_in"] += _coerce_int(counts.get("tokens_in"))
                    token_by_source[str(src)]["tokens_out"] += _coerce_int(counts.get("tokens_out"))

        if etype == "synth_publish":
            status = str(payload.get("status", "") or "")
            if status == "ok":
                publish_ok += 1
            elif status == "failed":
                publish_failed += 1
        if etype == "vault_sync_notified":
            notifier_ok += 1

        if etype == "task_outcome":
            if compare_raw is not None:
                c = comparison_from_payload(payload)
                bkey = _compare_bucket_key(c, cby or "")
                bk = compare_raw[bkey]
                bk.task_outcomes_seen += 1
                st = str(payload.get("status", "") or "").strip().lower()
                if st in ("completed", "ready"):
                    bk.status_completed_or_ready += 1
                qg = str(payload.get("qa_gate", "") or "").strip().upper()
                if qg == "PASS":
                    bk.qa_pass += 1
                elif qg == "FAIL":
                    bk.qa_fail += 1
                bk.elapsed_sum += _coerce_int(payload.get("elapsed_seconds"))
                bk.retry_total += _coerce_int(payload.get("retry_count"))
                bk.reopen_total += _coerce_int(payload.get("reopen_count"))
                bk.rework_total += _coerce_int(payload.get("rework_count"))

    lead_time_out: dict[str, dict[str, Any]] = {}
    for task_id, bucket in lead_time_by_task.items():
        first = bucket["first_ts"]
        last = bucket["last_ts"]
        seconds = int(max(0.0, (last - first).total_seconds()))
        lead_time_out[task_id] = {
            "first_ts": first.isoformat().replace("+00:00", "Z"),
            "last_ts": last.isoformat().replace("+00:00", "Z"),
            "seconds": seconds,
        }

    cycle_time_out: dict[str, dict[str, int]] = {}
    for phase in _PHASE_NAMES:
        task_map = per_phase_ts.get(phase, {})
        task_count = len(task_map)
        total_seconds = 0
        for task_id, stamps in task_map.items():
            valid = [s for s in stamps if s != datetime.min.replace(tzinfo=timezone.utc)]
            if len(valid) >= 2:
                total_seconds += int((max(valid) - min(valid)).total_seconds())
        avg_seconds = int(round(total_seconds / task_count)) if task_count else 0
        cycle_time_out[phase] = {
            "task_count": task_count,
            "total_seconds": total_seconds,
            "avg_seconds": avg_seconds,
        }

    retries_out: dict[str, dict[str, int]] = {}
    retries_total = 0
    for task_id, phases in retries.items():
        phase_retries: dict[str, int] = {}
        for phase, runs in phases.items():
            count = max(0, len(runs) - 1)
            if count > 0:
                phase_retries[phase] = count
                retries_total += count
        if phase_retries:
            retries_out[task_id] = phase_retries

    stalls_out = {
        "total": stalls_total,
        "by_task": {k: v for k, v in stalls_by_task.items() if v > 0},
    }

    token_cost_out = {
        "by_phase": {k: dict(v) for k, v in token_by_phase.items()},
        "by_agent": {k: dict(v) for k, v in token_by_agent.items()},
        "by_source": {k: dict(v) for k, v in token_by_source.items()},
    }

    totals_out = {
        "events": events_total,
        "tasks_seen": len(lead_time_out),
        "stalls_detected": stalls_total,
        "dor_failures": sum(dor_causes.values()),
        "retries": retries_total,
        "tokens_in": tokens_in_total,
        "tokens_out": tokens_out_total,
    }

    synth_publish_out = {
        "ok": publish_ok,
        "failed": publish_failed,
        "notifier_ok": notifier_ok,
    }

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "scope": {
            "company_id": scope.get("company_id", ""),
            "repository_id": scope.get("repository_id", ""),
            "plan_id": scope.get("plan_id", ""),
        },
        "window": {
            "since": window.get("since", ""),
            "until": window.get("until", ""),
        },
        "totals": totals_out,
        "lead_time_by_task": lead_time_out,
        "cycle_time_by_phase": cycle_time_out,
        "retries_by_task_phase": retries_out,
        "dor_causes": dict(dor_causes),
        "stalls": stalls_out,
        "token_cost": token_cost_out,
        "synth_publish": synth_publish_out,
    }
    if compare_raw is not None and cby is not None:
        result["compare"] = _finalize_compare_buckets(cby, dict(compare_raw))
    return _sort_nested(result)
