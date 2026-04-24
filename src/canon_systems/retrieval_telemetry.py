"""retrieval_breakdown canonical event emitter (4-bucket: graph/state/canonical/file)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping

from canon_backend_shared.events import CanonicalEvent

RETRIEVAL_SOURCES: tuple[str, ...] = ("graph", "state", "canonical", "file")

COMPARISON_KEYS: tuple[str, ...] = (
    "experiment_id",
    "memory_mode",
    "run_id",
    "task_attempt_id",
)


@dataclass(frozen=True)
class SourceCounts:
    tokens_in: int = 0
    tokens_out: int = 0

    def __post_init__(self) -> None:
        if self.tokens_in < 0 or self.tokens_out < 0:
            raise ValueError("tokens_in and tokens_out must be non-negative")


@dataclass
class RetrievalBreakdown:
    graph: SourceCounts = field(default_factory=SourceCounts)
    state: SourceCounts = field(default_factory=SourceCounts)
    canonical: SourceCounts = field(default_factory=SourceCounts)
    file: SourceCounts = field(default_factory=SourceCounts)


def comparison_from_payload(payload: Any) -> dict[str, str] | None:
    """
    Return a validated ``comparison`` object from a canonical payload, or
    ``None`` if the block is missing or incomplete.
    """
    if not isinstance(payload, Mapping):
        return None
    comp = payload.get("comparison")
    if not isinstance(comp, Mapping):
        return None
    try:
        return build_comparison_block(
            experiment_id=str(comp.get("experiment_id", "")),
            memory_mode=str(comp.get("memory_mode", "")),
            run_id=str(comp.get("run_id", "")),
            task_attempt_id=str(comp.get("task_attempt_id", "")),
        )
    except ValueError:
        return None


def build_comparison_block(
    *,
    experiment_id: str,
    memory_mode: str,
    run_id: str,
    task_attempt_id: str,
) -> dict[str, str]:
    """Return the additive shared ``payload.comparison`` object (opaque slugs, stable keys)."""
    eid = str(experiment_id).strip()
    mm = str(memory_mode).strip().lower()
    rid = str(run_id).strip()
    tid = str(task_attempt_id).strip()
    for label, v in (("experiment_id", eid), ("memory_mode", mm), ("run_id", rid), ("task_attempt_id", tid)):
        if not v:
            raise ValueError(f"{label} is required and must be non-empty for experiment comparison")
    return {
        "experiment_id": eid,
        "memory_mode": mm,
        "run_id": rid,
        "task_attempt_id": tid,
    }


def sum_breakdown(breakdown: RetrievalBreakdown) -> SourceCounts:
    total_in = 0
    total_out = 0
    for src in RETRIEVAL_SOURCES:
        sc: SourceCounts = getattr(breakdown, src)
        total_in += sc.tokens_in
        total_out += sc.tokens_out
    return SourceCounts(tokens_in=total_in, tokens_out=total_out)


def build_retrieval_breakdown_event(
    *,
    event_id: str,
    parent_event_id: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    handoff_id: str,
    agent_name: str,
    agent_run_id: str,
    actor_id: str,
    model: str,
    timestamp: str,
    state_version: int,
    breakdown: RetrievalBreakdown,
    comparison: Mapping[str, str] | None = None,
) -> CanonicalEvent:
    sources_payload: dict[str, dict[str, int]] = {}
    for src in RETRIEVAL_SOURCES:
        sc: SourceCounts = getattr(breakdown, src)
        sources_payload[src] = {"tokens_in": sc.tokens_in, "tokens_out": sc.tokens_out}
    totals = sum_breakdown(breakdown)
    payload: dict[str, Any] = {
        "sources": sources_payload,
        "totals": {"tokens_in": totals.tokens_in, "tokens_out": totals.tokens_out},
    }
    if comparison is not None:
        comp = build_comparison_block(
            experiment_id=str(comparison.get("experiment_id", "")),
            memory_mode=str(comparison.get("memory_mode", "")),
            run_id=str(comparison.get("run_id", "")),
            task_attempt_id=str(comparison.get("task_attempt_id", "")),
        )
        payload["comparison"] = comp
    return CanonicalEvent(
        schema_version=1,
        event_id=event_id,
        parent_event_id=parent_event_id,
        event_type="retrieval_breakdown",
        company_id=company_id,
        repository_id=repository_id,
        plan_id=plan_id,
        task_id=task_id,
        handoff_id=handoff_id,
        agent_name=agent_name,
        agent_run_id=agent_run_id,
        actor_id=actor_id,
        model=model,
        timestamp=timestamp,
        state_version=state_version,
        payload=payload,
    )


def build_task_outcome_event(
    *,
    event_id: str,
    parent_event_id: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    handoff_id: str,
    agent_name: str,
    agent_run_id: str,
    actor_id: str,
    model: str,
    timestamp: str,
    state_version: int,
    comparison: Mapping[str, str],
    status: str,
    qa_gate: str,
    elapsed_seconds: int,
    retry_count: int,
    reopen_count: int,
    rework_count: int,
) -> CanonicalEvent:
    """
    One ``task_outcome`` per task attempt. ``agent_run_id`` is the process run;
    ``payload.comparison.run_id`` is the experiment run identifier and stays distinct.
    """
    comp = build_comparison_block(
        experiment_id=str(comparison.get("experiment_id", "")),
        memory_mode=str(comparison.get("memory_mode", "")),
        run_id=str(comparison.get("run_id", "")),
        task_attempt_id=str(comparison.get("task_attempt_id", "")),
    )
    for name, v in (
        ("qa_gate", qa_gate),
        ("status", status),
    ):
        if not str(v).strip():
            raise ValueError(f"{name} is required and must be non-empty")
    es = int(elapsed_seconds)
    if es < 0:
        raise ValueError("elapsed_seconds must be non-negative")
    for label, c in (
        ("retry_count", retry_count),
        ("reopen_count", reopen_count),
        ("rework_count", rework_count),
    ):
        n = int(c)
        if n < 0:
            raise ValueError(f"{label} must be non-negative")
    payload: MutableMapping[str, Any] = {
        "comparison": comp,
        "status": str(status).strip(),
        "qa_gate": str(qa_gate).strip().upper(),
        "elapsed_seconds": es,
        "retry_count": int(retry_count),
        "reopen_count": int(reopen_count),
        "rework_count": int(rework_count),
    }
    return CanonicalEvent(
        schema_version=1,
        event_id=event_id,
        parent_event_id=parent_event_id,
        event_type="task_outcome",
        company_id=company_id,
        repository_id=repository_id,
        plan_id=plan_id,
        task_id=task_id,
        handoff_id=handoff_id,
        agent_name=agent_name,
        agent_run_id=agent_run_id,
        actor_id=actor_id,
        model=model,
        timestamp=timestamp,
        state_version=state_version,
        payload=dict(payload),
    )
