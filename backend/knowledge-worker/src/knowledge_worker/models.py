"""Typed job models for knowledge-worker."""

from __future__ import annotations

from pydantic import BaseModel, Field

from knowledge_schema import ArtifactType, BodyRef, Visibility


class MemoryProjectionRequest(BaseModel):
    query: str = Field(min_length=1)
    artifact_id: str
    version_id: str
    title: str
    artifact_type: ArtifactType = ArtifactType.TASK_CONTEXT
    visibility: Visibility = Visibility.PROJECT
    created_by: str
    source_system: str = "knowledge-worker"
    body_bucket: str | None = None
    body_key: str | None = None
    wing: str | None = None
    room: str | None = None
    allowed_wings: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=25)
    owners: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    scope_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    work_item_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)


class MemoryCaptureRequest(BaseModel):
    artifact_id: str
    version_id: str
    title: str
    transcript_text: str = Field(min_length=1)
    artifact_type: ArtifactType = ArtifactType.MEMORY_CAPTURE
    visibility: Visibility = Visibility.PROJECT
    created_by: str
    source_system: str = "knowledge-worker"
    body_bucket: str | None = None
    body_key: str | None = None
    summary: str | None = None
    decisions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    scope_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    work_item_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)


class MemoryProjectionResult(BaseModel):
    artifact_id: str
    version_id: str
    memory_hit_count: int
    body_ref: BodyRef
    markdown_preview: str
    memory_recall_source: str = "unknown"
    memory_search_status: str = "unknown"


class MemoryCaptureResult(BaseModel):
    artifact_id: str
    version_id: str
    body_ref: BodyRef
    markdown_preview: str


class RepoComprehensionIngestRequest(BaseModel):
    """Single memory search producing TASK_CONTEXT + REPO_NOTE artifacts."""

    query: str = Field(min_length=1)
    task_context_artifact_id: str
    task_context_version_id: str
    task_context_title: str
    repo_note_artifact_id: str
    repo_note_version_id: str
    repo_note_title: str
    visibility: Visibility = Visibility.PROJECT
    created_by: str
    source_system: str = "knowledge-worker"
    body_bucket: str | None = None
    task_context_body_key: str | None = None
    repo_note_body_key: str | None = None
    wing: str | None = None
    room: str | None = None
    allowed_wings: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=25)
    owners: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    scope_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    work_item_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)


class RepoComprehensionIngestResult(BaseModel):
    task_context_artifact_id: str
    task_context_version_id: str
    task_context_body_ref: BodyRef
    repo_note_artifact_id: str
    repo_note_version_id: str
    repo_note_body_ref: BodyRef
    memory_hit_count: int
    task_context_markdown_preview: str
    repo_note_markdown_preview: str
    memory_recall_source: str = "unknown"
    memory_search_status: str = "unknown"
