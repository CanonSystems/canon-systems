from __future__ import annotations

from canon_systems.resume_engine import PHASE_ORDER
from canon_systems.task_thread_scheduler import compute_lane_state


def test_lane_state_runnable_and_dependency_blocked() -> None:
    tasks = [
        {
            "task_id": "A",
            "workstream_id": "w",
            "depends_on": [],
            "parallel_group": "",
            "can_run_parallel": False,
        },
        {
            "task_id": "B",
            "workstream_id": "w",
            "depends_on": ["A"],
            "parallel_group": "",
            "can_run_parallel": False,
        },
    ]
    scans = [
        (None, None, None),
        (None, None, None),
    ]
    out = compute_lane_state(tasks, scans, phase_order=PHASE_ORDER)
    assert out["runnable_targets"] == [{"task_id": "A", "workstream_id": "w", "phase": "scoper"}]
    assert out["active_targets"] == []
    assert len(out["blocked_targets"]) == 1
    assert out["blocked_targets"][0]["task_id"] == "B"
    assert out["blocked_targets"][0]["reason"] == "dependency"


def test_lane_state_active_vs_runnable() -> None:
    tasks = [
        {
            "task_id": "A",
            "workstream_id": "w",
            "depends_on": [],
            "parallel_group": "g1",
            "can_run_parallel": True,
        },
        {
            "task_id": "B",
            "workstream_id": "w",
            "depends_on": [],
            "parallel_group": "g1",
            "can_run_parallel": True,
        },
    ]
    scans = [
        ("implementer", "in_progress", None),
        (None, None, None),
    ]
    out = compute_lane_state(tasks, scans, phase_order=PHASE_ORDER)
    assert out["active_targets"] == [{"task_id": "A", "phase": "implementer", "workstream_id": "w"}]
    assert out["runnable_targets"] == [{"task_id": "B", "phase": "scoper", "workstream_id": "w"}]


def test_lane_state_transport_blocked() -> None:
    tasks = [
        {
            "task_id": "A",
            "workstream_id": "w",
            "depends_on": [],
            "parallel_group": "",
            "can_run_parallel": False,
        },
    ]
    scans = [(None, None, "transport")]
    out = compute_lane_state(tasks, scans, phase_order=PHASE_ORDER)
    assert out["runnable_targets"] == []
    assert out["active_targets"] == []
    assert out["blocked_targets"][0]["reason"] == "transport"


def test_lane_state_task_threads_sorted() -> None:
    tasks = [
        {
            "task_id": "Z",
            "workstream_id": "w",
            "depends_on": [],
            "parallel_group": "b",
            "can_run_parallel": True,
        },
        {
            "task_id": "Y",
            "workstream_id": "w",
            "depends_on": [],
            "parallel_group": "",
            "can_run_parallel": False,
        },
    ]
    scans = [
        ("release-orchestrator", "completed", None),
        ("release-orchestrator", "completed", None),
    ]
    out = compute_lane_state(tasks, scans, phase_order=PHASE_ORDER)
    assert out["runnable_targets"] == []
    threads = out["task_threads"]
    assert [t["parallel_group"] for t in threads] == ["", "b"]
