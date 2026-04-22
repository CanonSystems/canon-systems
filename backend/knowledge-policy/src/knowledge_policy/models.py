"""Small policy and action model for access control and routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence

from knowledge_schema import ArtifactType, RunStage, Visibility


class PolicyActionKind(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"
    REQUEST_CLARIFICATION = "request_clarification"
    REDACT = "redact"
    PUBLISH = "publish"
    SYNC = "sync"


class RequestedAction(str, Enum):
    VIEW = "view"
    EDIT = "edit"
    PUBLISH = "publish"
    RECLASSIFY = "reclassify"
    QUERY_MEMORY = "query_memory"
    RECEIVE_ESCALATION = "receive_escalation"


@dataclass(frozen=True, slots=True)
class PolicyAction:
    kind: PolicyActionKind
    reason: str | None = None
    target_visibility: Visibility | None = None
    target_stage: RunStage | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PolicyRequest:
    actor: str
    artifact_type: ArtifactType
    visibility: Visibility
    owners: tuple[str, ...] = ()
    groups: tuple[str, ...] = ()
    stage: RunStage | None = None
    requested_action: RequestedAction = RequestedAction.VIEW
    actor_groups: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    actions: tuple[PolicyAction, ...] = ()
    reason: str | None = None

    @classmethod
    def allow(cls, reason: str | None = None, *actions: PolicyAction) -> "PolicyDecision":
        return cls(allowed=True, actions=actions, reason=reason)

    @classmethod
    def deny(cls, reason: str, *actions: PolicyAction) -> "PolicyDecision":
        return cls(allowed=False, actions=actions, reason=reason)


def can_access(request: PolicyRequest) -> bool:
    """Return True when the actor is allowed to perform the requested action."""

    is_owner = request.actor in request.owners
    in_allowed_group = bool(set(request.actor_groups).intersection(request.groups))

    if request.requested_action in {
        RequestedAction.EDIT,
        RequestedAction.PUBLISH,
        RequestedAction.RECLASSIFY,
    }:
        if request.visibility == Visibility.PRIVATE:
            return is_owner
        if request.visibility == Visibility.TEAM:
            return is_owner or in_allowed_group
        if request.visibility == Visibility.PROJECT:
            return is_owner or in_allowed_group
        if request.visibility == Visibility.RESTRICTED:
            return is_owner or in_allowed_group
        return False

    if request.requested_action in {
        RequestedAction.VIEW,
        RequestedAction.QUERY_MEMORY,
        RequestedAction.RECEIVE_ESCALATION,
    }:
        if request.visibility == Visibility.TEAM:
            return True
        if request.visibility == Visibility.PRIVATE:
            return is_owner
        if request.visibility == Visibility.PROJECT:
            return in_allowed_group
        if request.visibility == Visibility.RESTRICTED:
            return is_owner or in_allowed_group
        return False

    return False


def classify_visibility_routing(
    visibility: Visibility,
    allowed_groups: Sequence[str] | None = None,
) -> str:
    """Map a visibility scope to a coarse routing lane."""

    if visibility == Visibility.TEAM:
        return "team"
    if visibility == Visibility.PROJECT:
        return "project"
    if visibility == Visibility.PRIVATE:
        return "private"
    if allowed_groups:
        return "restricted-group"
    return "restricted"
