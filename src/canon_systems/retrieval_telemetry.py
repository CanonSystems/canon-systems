"""retrieval_breakdown canonical event emitter (4-bucket: graph/state/canonical/file)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from canon_backend_shared.events import CanonicalEvent

RETRIEVAL_SOURCES: tuple[str, ...] = ("graph", "state", "canonical", "file")


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
