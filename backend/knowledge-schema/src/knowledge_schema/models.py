"""Shared data models for canonical artifact envelopes."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import ArtifactStatus, ArtifactType, Visibility


class BodyRef(BaseModel):
    storage: str = Field(..., examples=["s3"])
    bucket: str
    key: str
    content_type: str = Field(default="text/markdown", examples=["text/markdown"])


class ArtifactEnvelope(BaseModel):
    artifact_id: str
    version_id: str
    artifact_type: ArtifactType
    title: str
    status: ArtifactStatus
    visibility: Visibility
    owners: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    scope_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    work_item_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)
    source_system: str
    supersedes_artifact_id: str | None = None
    body_ref: BodyRef
    summary: str | None = None
    created_at: str
    created_by: str
