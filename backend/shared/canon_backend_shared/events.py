"""Canonical event envelope for the historical plane (backlog §C)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, MutableMapping


@dataclass
class CanonicalEvent:
    """
    In-memory representation of the §C canonical event envelope.
    ``schema_version`` is fixed at ``1`` for this revision.
    """

    schema_version: int
    event_id: str
    parent_event_id: str
    event_type: str
    company_id: str
    repository_id: str
    plan_id: str
    task_id: str
    handoff_id: str
    agent_name: str
    agent_run_id: str
    actor_id: str
    model: str
    timestamp: str
    state_version: int
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1 for this envelope revision")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["payload"] = dict(self.payload)
        return d

    @classmethod
    def from_dict(cls, data: MutableMapping[str, Any]) -> CanonicalEvent:
        payload = data.get("payload", {})
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dict")
        return cls(
            schema_version=int(data["schema_version"]),
            event_id=str(data["event_id"]),
            parent_event_id=str(data["parent_event_id"]),
            event_type=str(data["event_type"]),
            company_id=str(data["company_id"]),
            repository_id=str(data["repository_id"]),
            plan_id=str(data["plan_id"]),
            task_id=str(data["task_id"]),
            handoff_id=str(data["handoff_id"]),
            agent_name=str(data["agent_name"]),
            agent_run_id=str(data["agent_run_id"]),
            actor_id=str(data["actor_id"]),
            model=str(data["model"]),
            timestamp=str(data["timestamp"]),
            state_version=int(data["state_version"]),
            payload=dict(payload),
        )
