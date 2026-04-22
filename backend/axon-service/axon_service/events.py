from __future__ import annotations
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from canon_backend_shared.events import CanonicalEvent

EventEmitter = Callable[[CanonicalEvent], None]
_logger = logging.getLogger("axon_service.events")


def make_graph_event(
    *,
    event_type: str,
    company_id: str,
    repository_id: str,
    payload: dict[str, Any],
) -> CanonicalEvent:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    eid = str(uuid.uuid4())
    return CanonicalEvent(
        schema_version=1,
        event_id=eid,
        parent_event_id="",
        event_type=event_type,
        company_id=company_id,
        repository_id=repository_id,
        plan_id="",
        task_id="",
        handoff_id="",
        agent_name="axon-service",
        agent_run_id="",
        actor_id="",
        model="",
        timestamp=ts,
        state_version=0,
        payload=payload,
    )


def _default_emitter(event: CanonicalEvent) -> None:
    line = json.dumps(asdict(event), default=str)
    _logger.info("%s", line)


def get_event_emitter() -> EventEmitter:
    return _default_emitter
