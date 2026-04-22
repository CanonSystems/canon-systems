"""Artifact-specific policy helpers."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.auth.models import ActorContext
from app.models.artifact_api import ArtifactResponse
from knowledge_policy import PolicyRequest, RequestedAction, can_access


def ensure_artifact_access(
    actor: ActorContext,
    artifact: ArtifactResponse,
    requested_action: RequestedAction = RequestedAction.VIEW,
) -> None:
    request = PolicyRequest(
        actor=actor.actor_id,
        artifact_type=artifact.artifact_type,
        visibility=artifact.visibility,
        owners=tuple(artifact.owners),
        groups=tuple(artifact.groups),
        requested_action=requested_action,
        actor_groups=tuple(actor.group_ids),
    )
    if not can_access(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def ensure_artifact_company_scope(
    artifact: ArtifactResponse,
    company_scope_id: str | None,
) -> None:
    if company_scope_id is None:
        return
    if company_scope_id not in (artifact.scope_ids or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
