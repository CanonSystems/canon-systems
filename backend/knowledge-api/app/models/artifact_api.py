"""Pydantic API models for artifact operations."""

from __future__ import annotations

from pydantic import BaseModel, Field

from knowledge_schema import ArtifactEnvelope, ArtifactStatus, ArtifactType, BodyRef, Visibility


class CreateArtifactRequest(BaseModel):
    artifact_id: str
    version_id: str
    artifact_type: ArtifactType
    title: str
    visibility: Visibility
    source_system: str
    created_by: str
    body_ref: BodyRef
    body_text: str | None = None
    summary: str | None = None
    owners: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    scope_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    work_item_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)


class CreateArtifactVersionRequest(BaseModel):
    version_id: str
    body_ref: BodyRef
    created_by: str
    body_text: str | None = None
    summary: str | None = None
    schema_version: str = "1"


class PublishArtifactRequest(BaseModel):
    published_by: str


class SupersedeArtifactRequest(BaseModel):
    supersedes_artifact_id: str


class ArtifactListItem(BaseModel):
    artifact_id: str
    artifact_type: ArtifactType
    title: str
    status: ArtifactStatus
    visibility: Visibility
    current_version_id: str | None
    updated_at: str | None = None


class ArtifactResponse(ArtifactEnvelope):
    pass


class ArtifactVersionResponse(BaseModel):
    version_id: str
    artifact_id: str
    version_number: int
    body_ref: BodyRef
    body_checksum: str
    summary: str | None = None
    schema_version: str
    created_by: str
    created_at: str


class ArtifactBodyResponse(BaseModel):
    artifact_id: str
    version_id: str
    body_ref: BodyRef
    content_type: str
    body_text: str
