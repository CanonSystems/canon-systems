"""Multilane task visibility: checkpoint scans + manifest metadata (read-only, no state writes)."""

from __future__ import annotations

from typing import Any, Mapping


def _first_incomplete_phase(
    phase: str | None, phase_status: str | None, phase_order: tuple[str, ...]
) -> str | None:
    if phase is None:
        return phase_order[0]
    if phase not in phase_order:
        return phase_order[0]
    idx = phase_order.index(phase)
    if phase_status == "completed":
        if idx + 1 >= len(phase_order):
            return None
        return phase_order[idx + 1]
    return phase


def _is_fully_complete(
    phase: str | None, phase_status: str | None, phase_order: tuple[str, ...]
) -> bool:
    return (
        phase == phase_order[-1]
        and phase_status == "completed"
        and phase is not None
    )


def _deps_satisfied(
    depends_on: list[str], complete_ids: set[str], known_ids: set[str]
) -> tuple[bool, list[str]]:
    """Return (satisfied, missing_ids) where missing are deps not yet complete."""
    missing: list[str] = []
    for dep in depends_on:
        if dep not in known_ids:
            missing.append(dep)
        elif dep not in complete_ids:
            missing.append(dep)
    return (len(missing) == 0, sorted(missing))


def compute_lane_state(
    tasks: list[Mapping[str, Any]],
    scans: list[tuple[str | None, str | None, str | None]],
    *,
    phase_order: tuple[str, ...],
) -> dict[str, Any]:
    """
    Derive runnable / active / blocked targets and thread groupings.

    Uses only per-task checkpoint (phase, phase_status, degrade) plus manifest
    fields: depends_on, parallel_group, can_run_parallel.
    """
    if len(tasks) != len(scans):
        raise ValueError("tasks and scans length mismatch")

    known_ids = {str(t["task_id"]) for t in tasks}
    complete_ids: set[str] = set()
    for task, scan in zip(tasks, scans, strict=True):
        phase, status, degrade = scan
        if degrade is None and _is_fully_complete(phase, status, phase_order):
            complete_ids.add(str(task["task_id"]))

    runnable: list[dict[str, str]] = []
    active: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []

    for task, scan in zip(tasks, scans, strict=True):
        tid = str(task["task_id"])
        ws = str(task["workstream_id"])
        phase, status, degrade = scan

        if degrade is not None:
            blocked.append(
                {
                    "task_id": tid,
                    "workstream_id": ws,
                    "reason": "transport",
                    "detail": str(degrade),
                }
            )
            continue

        if _is_fully_complete(phase, status, phase_order):
            continue

        next_phase = _first_incomplete_phase(phase, status, phase_order)
        if next_phase is None:
            continue

        if status == "in_progress":
            active.append({"task_id": tid, "workstream_id": ws, "phase": str(next_phase)})
            continue

        depends_on = [str(d) for d in (task.get("depends_on") or [])]
        ok, missing = _deps_satisfied(depends_on, complete_ids, known_ids)
        if not ok:
            blocked.append(
                {
                    "task_id": tid,
                    "workstream_id": ws,
                    "reason": "dependency",
                    "detail": ",".join(missing),
                }
            )
            continue

        runnable.append({"task_id": tid, "workstream_id": ws, "phase": str(next_phase)})

    # Deterministic ordering: lexicographic by task_id, then workstream_id, then phase.
    def _sort_key(d: Mapping[str, str]) -> tuple[str, str, str]:
        return (d["task_id"], d.get("workstream_id", ""), d.get("phase", ""))

    runnable.sort(key=_sort_key)
    active.sort(key=_sort_key)
    blocked.sort(key=lambda b: (b["task_id"], b["workstream_id"], b["reason"], b.get("detail", "")))

    # task_threads: group by parallel_group (empty string when absent)
    group_map: dict[str, list[dict[str, str]]] = {}
    for task in tasks:
        tid = str(task["task_id"])
        ws = str(task["workstream_id"])
        pg = str(task.get("parallel_group") or "")
        group_map.setdefault(pg, []).append({"task_id": tid, "workstream_id": ws})

    for members in group_map.values():
        members.sort(key=lambda m: (m["task_id"], m["workstream_id"]))

    task_threads = [
        {"parallel_group": pg, "tasks": group_map[pg]}
        for pg in sorted(group_map.keys(), key=lambda x: (0 if x == "" else 1, x))
    ]

    return {
        "runnable_targets": runnable,
        "active_targets": active,
        "blocked_targets": blocked,
        "task_threads": task_threads,
    }
