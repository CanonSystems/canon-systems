"""Artifact service operations."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

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
from app.models.artifact_db import ArtifactORM, ArtifactVersionORM
from knowledge_schema import ArtifactStatus, BodyRef


def _checksum_for_ref(body_ref: BodyRef) -> str:
    payload = f"{body_ref.bucket}:{body_ref.key}:{body_ref.content_type}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _version_response(version: ArtifactVersionORM) -> ArtifactVersionResponse:
    return ArtifactVersionResponse(
        version_id=version.id,
        artifact_id=version.artifact_id,
        version_number=version.version_number,
        body_ref=BodyRef(
            storage=version.body_storage_provider,
            bucket=version.body_storage_bucket,
            key=version.body_storage_key,
            content_type=version.body_content_type,
        ),
        body_checksum=version.body_checksum,
        summary=version.summary,
        schema_version=version.schema_version,
        created_by=version.created_by,
        created_at=version.created_at.isoformat(),
    )


def list_artifacts(session: Session) -> list[ArtifactListItem]:
    rows = session.scalars(select(ArtifactORM).order_by(ArtifactORM.updated_at.desc())).all()
    return [
        ArtifactListItem(
            artifact_id=row.id,
            artifact_type=row.artifact_type,
            title=row.title,
            status=row.status,
            visibility=row.visibility,
            current_version_id=row.current_version_id,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )
        for row in rows
    ]


def list_artifacts_filtered(
    session: Session,
    *,
    artifact_type: str | None = None,
    status: str | None = None,
    visibility: str | None = None,
    scope_id: str | None = None,
    repo_id: str | None = None,
    work_item_id: str | None = None,
    company_scope_id: str | None = None,
) -> list[ArtifactListItem]:
    items = list_artifacts(session)

    def matches(item: ArtifactListItem) -> bool:
        if artifact_type and item.artifact_type.value != artifact_type:
            return False
        if status and item.status.value != status:
            return False
        if visibility and item.visibility.value != visibility:
            return False

        if not any([scope_id, repo_id, work_item_id, company_scope_id]):
            return True

        artifact = get_artifact(session, item.artifact_id)
        if company_scope_id and company_scope_id not in artifact.scope_ids:
            return False
        if scope_id and scope_id not in artifact.scope_ids:
            return False
        if repo_id and repo_id not in artifact.repo_ids:
            return False
        if work_item_id and work_item_id not in artifact.work_item_ids:
            return False
        return True

    return [item for item in items if matches(item)]


def get_artifact(session: Session, artifact_id: str) -> ArtifactResponse:
    artifact = session.get(ArtifactORM, artifact_id)
    if artifact is None or artifact.current_version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")

    current_version = artifact.current_version
    return ArtifactResponse(
        artifact_id=artifact.id,
        version_id=current_version.id,
        artifact_type=artifact.artifact_type,
        title=artifact.title,
        status=artifact.status,
        visibility=artifact.visibility,
        owners=artifact.owners or [],
        groups=artifact.groups or [],
        scope_ids=artifact.scope_ids or [],
        repo_ids=artifact.repo_ids or [],
        work_item_ids=artifact.work_item_ids or [],
        conversation_ids=artifact.conversation_ids or [],
        source_system=artifact.source_system,
        supersedes_artifact_id=artifact.supersedes_artifact_id,
        body_ref=BodyRef(
            storage=current_version.body_storage_provider,
            bucket=current_version.body_storage_bucket,
            key=current_version.body_storage_key,
            content_type=current_version.body_content_type,
        ),
        summary=current_version.summary,
        created_at=artifact.created_at.isoformat(),
        created_by=artifact.created_by,
    )


def list_artifact_versions(session: Session, artifact_id: str) -> list[ArtifactVersionResponse]:
    artifact = session.get(ArtifactORM, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")
    versions = session.scalars(
        select(ArtifactVersionORM)
        .where(ArtifactVersionORM.artifact_id == artifact_id)
        .order_by(ArtifactVersionORM.version_number.desc())
    ).all()
    return [_version_response(version) for version in versions]


def get_artifact_version(
    session: Session, artifact_id: str, version_id: str
) -> ArtifactVersionResponse:
    version = session.scalar(
        select(ArtifactVersionORM).where(
            ArtifactVersionORM.artifact_id == artifact_id,
            ArtifactVersionORM.id == version_id,
        )
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact version not found")
    return _version_response(version)


def get_artifact_body(
    session: Session,
    artifact_id: str,
    *,
    version_id: str | None = None,
    object_store,
) -> ArtifactBodyResponse:
    if version_id is None:
        artifact = get_artifact(session, artifact_id)
        resolved_version_id = artifact.version_id
        body_ref = artifact.body_ref
    else:
        version = get_artifact_version(session, artifact_id, version_id)
        resolved_version_id = version.version_id
        body_ref = version.body_ref

    body_text, content_type = object_store.get_text(
        bucket=body_ref.bucket,
        key=body_ref.key,
    )
    return ArtifactBodyResponse(
        artifact_id=artifact_id,
        version_id=resolved_version_id,
        body_ref=body_ref,
        content_type=content_type,
        body_text=body_text,
    )


def create_artifact(session: Session, request: CreateArtifactRequest) -> ArtifactResponse:
    if session.get(ArtifactORM, request.artifact_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="artifact already exists"
        )

    artifact = ArtifactORM(
        id=request.artifact_id,
        artifact_type=request.artifact_type.value,
        current_version_id=None,
        title=request.title,
        status=ArtifactStatus.DRAFT.value,
        visibility=request.visibility.value,
        owners=request.owners,
        groups=request.groups,
        scope_ids=request.scope_ids,
        repo_ids=request.repo_ids,
        work_item_ids=request.work_item_ids,
        conversation_ids=request.conversation_ids,
        source_system=request.source_system,
        supersedes_artifact_id=None,
        created_by=request.created_by,
    )
    version = ArtifactVersionORM(
        id=request.version_id,
        artifact_id=request.artifact_id,
        version_number=1,
        body_storage_provider=request.body_ref.storage,
        body_storage_bucket=request.body_ref.bucket,
        body_storage_key=request.body_ref.key,
        body_content_type=request.body_ref.content_type,
        body_checksum=_checksum_for_ref(request.body_ref),
        summary=request.summary,
        schema_version="1",
        created_by=request.created_by,
    )
    session.add(artifact)
    session.flush()
    session.add(version)
    session.flush()
    artifact.current_version_id = request.version_id
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return get_artifact(session, artifact.id)


def create_artifact_version(
    session: Session, artifact_id: str, request: CreateArtifactVersionRequest
) -> ArtifactResponse:
    artifact = session.get(ArtifactORM, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")

    next_version_number = len(artifact.versions) + 1
    version = ArtifactVersionORM(
        id=request.version_id,
        artifact_id=artifact_id,
        version_number=next_version_number,
        body_storage_provider=request.body_ref.storage,
        body_storage_bucket=request.body_ref.bucket,
        body_storage_key=request.body_ref.key,
        body_content_type=request.body_ref.content_type,
        body_checksum=_checksum_for_ref(request.body_ref),
        summary=request.summary,
        schema_version=request.schema_version,
        created_by=request.created_by,
    )
    artifact.current_version_id = request.version_id
    artifact.updated_at = datetime.now(UTC)
    session.add(version)
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return get_artifact(session, artifact_id)


def publish_artifact(
    session: Session, artifact_id: str, request: PublishArtifactRequest
) -> ArtifactResponse:
    artifact = session.get(ArtifactORM, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")
    artifact.status = ArtifactStatus.PUBLISHED.value
    artifact.updated_at = datetime.now(UTC)
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return get_artifact(session, artifact_id)


def supersede_artifact(
    session: Session, artifact_id: str, request: SupersedeArtifactRequest
) -> ArtifactResponse:
    artifact = session.get(ArtifactORM, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")
    artifact.supersedes_artifact_id = request.supersedes_artifact_id
    artifact.status = ArtifactStatus.SUPERSEDED.value
    artifact.updated_at = datetime.now(UTC)
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return get_artifact(session, artifact_id)
