"""Event acquisition seam: InMemoryEventSource + Wave-5-waived StateApiEventSource stub."""
from __future__ import annotations

from typing import Iterable, Protocol, cast

from canon_backend_shared.events import CanonicalEvent


class SourceError(RuntimeError):
    """Event source misconfiguration (e.g. unimplemented state-api path)."""


class EventSource(Protocol):
    def iter_events(
        self,
        *,
        plan_id: str | None,
        task_id: str | None,
        cutoff_timestamp: str,
    ) -> Iterable[CanonicalEvent]: ...


def _is_after_cutoff(*, event_ts: str, cutoff: str) -> bool:
    """Lower-bound filter: event strictly after *cutoff* (since semantics for ISO-8601 Z)."""
    return event_ts > cutoff


def _in_scope(
    e: CanonicalEvent, *, plan_id: str | None, task_id: str | None
) -> bool:
    if plan_id is not None and e.plan_id != plan_id:
        return False
    if task_id is not None and e.task_id != task_id:
        return False
    return True


class InMemoryEventSource:
    def __init__(self, events: list[CanonicalEvent]) -> None:
        self._events = list(events)

    def iter_events(
        self,
        *,
        plan_id: str | None,
        task_id: str | None,
        cutoff_timestamp: str,
    ) -> Iterable[CanonicalEvent]:
        for e in self._events:
            if not _in_scope(e, plan_id=plan_id, task_id=task_id):
                continue
            if not _is_after_cutoff(event_ts=e.timestamp, cutoff=cutoff_timestamp):
                continue
            yield e


class StateApiEventSource:
    def __init__(self, *, base_url: str, fetch_fn=None) -> None:
        _ = base_url
        self._fetch_fn = fetch_fn

    def iter_events(
        self,
        *,
        plan_id: str | None,
        task_id: str | None,
        cutoff_timestamp: str,
    ) -> Iterable[CanonicalEvent]:
        if self._fetch_fn is None:
            raise SourceError(
                "wave-5 waiver: state-api event query endpoint pending; "
                "use InMemoryEventSource or CLI-fed JSONL for now"
            )
        out = self._fetch_fn(
            plan_id=plan_id,
            task_id=task_id,
            cutoff_timestamp=cutoff_timestamp,
        )
        return cast(Iterable[CanonicalEvent], out)
