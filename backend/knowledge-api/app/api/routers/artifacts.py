"""Artifact API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import ActorContext, get_actor_context, get_company_scope_id
from app.db.session import get_db_session
from app.models.artifact_api import (
    ArtifactBodyResponse,
    ArtifactListItem,
    ArtifactResponse,
    ArtifactVersionResponse,
    CreateArtifactRequest,
    CreateArtifactVersionRequest,
    PublishArtifactRequest,
    SupersedeArtifactRequest,
)
from app.services.artifacts import (
    create_artifact,
    create_artifact_version,
    get_artifact,
    get_artifact_body,
    get_artifact_version,
    list_artifacts_filtered as list_artifacts,
    list_artifact_versions,
    publish_artifact,
    supersede_artifact,
)
from app.storage import ObjectStore, get_object_store
from knowledge_policy import RequestedAction
from app.policies import ensure_artifact_access, ensure_artifact_company_scope

router = APIRouter()


@router.get("", response_model=list[ArtifactListItem])
def list_artifacts_endpoint(
    artifact_type: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    visibility_filter: str | None = Query(default=None, alias="visibility"),
    scope_id: str | None = None,
    repo_id: str | None = None,
    work_item_id: str | None = None,
    company_scope_id: str | None = Depends(get_company_scope_id),
    actor: ActorContext = Depends(get_actor_context),
    session: Session = Depends(get_db_session),
) -> list[ArtifactListItem]:
    """List known artifacts."""
    visible_items: list[ArtifactListItem] = []
    for item in list_artifacts(
        session,
        artifact_type=artifact_type,
        status=status_filter,
        visibility=visibility_filter,
        scope_id=scope_id,
        repo_id=repo_id,
        work_item_id=work_item_id,
        company_scope_id=company_scope_id,
    ):
        artifact = get_artifact(session, item.artifact_id)
        try:
            ensure_artifact_access(actor, artifact, RequestedAction.VIEW)
            ensure_artifact_company_scope(artifact, company_scope_id)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_403_FORBIDDEN:
                raise
            continue
        visible_items.append(item)
    return visible_items


@router.post("", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
def create_artifact_endpoint(
    request: CreateArtifactRequest,
    actor: ActorContext = Depends(get_actor_context),
    object_store: ObjectStore = Depends(get_object_store),
    session: Session = Depends(get_db_session),
) -> ArtifactResponse:
    """Create a new artifact with its first version."""
    if actor.actor_id != request.created_by:
        request.owners = sorted(set(request.owners + [request.created_by]))
    if request.body_text is not None:
        object_store.put_text(
            bucket=request.body_ref.bucket,
            key=request.body_ref.key,
            text=request.body_text,
            content_type=request.body_ref.content_type,
        )
    return create_artifact(session, request)


@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact_endpoint(
    artifact_id: str,
    company_scope_id: str | None = Depends(get_company_scope_id),
    actor: ActorContext = Depends(get_actor_context),
    session: Session = Depends(get_db_session),
) -> ArtifactResponse:
    """Fetch the current version of an artifact."""
    artifact = get_artifact(session, artifact_id)
    ensure_artifact_access(actor, artifact, RequestedAction.VIEW)
    ensure_artifact_company_scope(artifact, company_scope_id)
    return artifact


@router.post(
    "/{artifact_id}/versions",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_artifact_version_endpoint(
    artifact_id: str,
    request: CreateArtifactVersionRequest,
    actor: ActorContext = Depends(get_actor_context),
    object_store: ObjectStore = Depends(get_object_store),
    session: Session = Depends(get_db_session),
) -> ArtifactResponse:
    """Create a new immutable artifact version and make it current."""
    artifact = get_artifact(session, artifact_id)
    ensure_artifact_access(actor, artifact, RequestedAction.EDIT)
    if request.body_text is not None:
        object_store.put_text(
            bucket=request.body_ref.bucket,
            key=request.body_ref.key,
            text=request.body_text,
            content_type=request.body_ref.content_type,
        )
    return create_artifact_version(session, artifact_id, request)


@router.get("/{artifact_id}/versions", response_model=list[ArtifactVersionResponse])
def list_artifact_versions_endpoint(
    artifact_id: str,
    company_scope_id: str | None = Depends(get_company_scope_id),
    actor: ActorContext = Depends(get_actor_context),
    session: Session = Depends(get_db_session),
) -> list[ArtifactVersionResponse]:
    """List immutable versions for an artifact."""
    artifact = get_artifact(session, artifact_id)
    ensure_artifact_access(actor, artifact, RequestedAction.VIEW)
    ensure_artifact_company_scope(artifact, company_scope_id)
    return list_artifact_versions(session, artifact_id)


@router.get("/{artifact_id}/versions/{version_id}", response_model=ArtifactVersionResponse)
def get_artifact_version_endpoint(
    artifact_id: str,
    version_id: str,
    company_scope_id: str | None = Depends(get_company_scope_id),
    actor: ActorContext = Depends(get_actor_context),
    session: Session = Depends(get_db_session),
) -> ArtifactVersionResponse:
    """Fetch a specific artifact version."""
    artifact = get_artifact(session, artifact_id)
    ensure_artifact_access(actor, artifact, RequestedAction.VIEW)
    ensure_artifact_company_scope(artifact, company_scope_id)
    return get_artifact_version(session, artifact_id, version_id)


@router.get("/{artifact_id}/body", response_model=ArtifactBodyResponse)
def get_artifact_body_endpoint(
    artifact_id: str,
    company_scope_id: str | None = Depends(get_company_scope_id),
    actor: ActorContext = Depends(get_actor_context),
    object_store: ObjectStore = Depends(get_object_store),
    session: Session = Depends(get_db_session),
) -> ArtifactBodyResponse:
    """Fetch the current artifact body text."""
    artifact = get_artifact(session, artifact_id)
    ensure_artifact_access(actor, artifact, RequestedAction.VIEW)
    ensure_artifact_company_scope(artifact, company_scope_id)
    return get_artifact_body(session, artifact_id, object_store=object_store)


@router.get("/{artifact_id}/versions/{version_id}/body", response_model=ArtifactBodyResponse)
def get_artifact_version_body_endpoint(
    artifact_id: str,
    version_id: str,
    company_scope_id: str | None = Depends(get_company_scope_id),
    actor: ActorContext = Depends(get_actor_context),
    object_store: ObjectStore = Depends(get_object_store),
    session: Session = Depends(get_db_session),
) -> ArtifactBodyResponse:
    """Fetch a specific artifact version body text."""
    artifact = get_artifact(session, artifact_id)
    ensure_artifact_access(actor, artifact, RequestedAction.VIEW)
    ensure_artifact_company_scope(artifact, company_scope_id)
    return get_artifact_body(
        session,
        artifact_id,
        version_id=version_id,
        object_store=object_store,
    )


@router.post("/{artifact_id}/publish", response_model=ArtifactResponse)
def publish_artifact_endpoint(
    artifact_id: str,
    request: PublishArtifactRequest,
    actor: ActorContext = Depends(get_actor_context),
    session: Session = Depends(get_db_session),
) -> ArtifactResponse:
    """Publish an artifact."""
    artifact = get_artifact(session, artifact_id)
    ensure_artifact_access(actor, artifact, RequestedAction.PUBLISH)
    return publish_artifact(session, artifact_id, request)


@router.post("/{artifact_id}/supersede", response_model=ArtifactResponse)
def supersede_artifact_endpoint(
    artifact_id: str,
    request: SupersedeArtifactRequest,
    actor: ActorContext = Depends(get_actor_context),
    session: Session = Depends(get_db_session),
) -> ArtifactResponse:
    """Mark an artifact as superseded by linkage."""
    artifact = get_artifact(session, artifact_id)
    ensure_artifact_access(actor, artifact, RequestedAction.RECLASSIFY)
    return supersede_artifact(session, artifact_id, request)
