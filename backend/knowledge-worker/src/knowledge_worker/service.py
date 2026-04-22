"""Worker service orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from memory_adapter.models import MemorySearchRequest, MemorySearchResponse
from knowledge_client.models import ArtifactType, CreateArtifactRequest
from knowledge_client.errors import KnowledgeClientResponseError

from .config import Settings, get_settings
from .models import (
    MemoryCaptureRequest,
    MemoryCaptureResult,
    MemoryProjectionRequest,
    MemoryProjectionResult,
    RepoComprehensionIngestRequest,
    RepoComprehensionIngestResult,
)
from .projections import (
    render_memory_capture,
    render_memory_projection,
    render_repo_comprehension_note,
)


class MemorySearchClient(Protocol):
    def search(self, request: MemorySearchRequest) -> MemorySearchResponse: ...


class ArtifactClient(Protocol):
    def create_artifact(self, request: CreateArtifactRequest): ...


@dataclass(slots=True)
class KnowledgeWorkerService:
    settings: Settings = field(default_factory=get_settings)
    memory_client: MemorySearchClient | None = None
    artifact_client: ArtifactClient | None = None
    actor_id: str = "usr_system"
    actor_groups: tuple[str, ...] = ()

    def project_memory_to_artifact(
        self, request: MemoryProjectionRequest
    ) -> MemoryProjectionResult:
        memory_client = self.memory_client or self._build_memory_client()
        artifact_client = self.artifact_client or self._build_artifact_client()

        if memory_client is None:
            raise RuntimeError("No memory client is configured.")
        if artifact_client is None:
            raise RuntimeError("No artifact client is configured.")

        search_response = memory_client.search(
            MemorySearchRequest(
                query=request.query,
                limit=request.limit,
                wing=request.wing,
                room=request.room,
                allowed_wings=request.allowed_wings,
            )
        )
        markdown = render_memory_projection(query=request.query, response=search_response)
        body_key = request.body_key or (
            f"artifacts/{request.artifact_id}/{request.version_id}/body.md"
        )
        body_bucket = request.body_bucket or self.settings.worker_default_bucket

        _create_artifact_replay_safe(
            artifact_client,
            CreateArtifactRequest(
                artifact_id=request.artifact_id,
                version_id=request.version_id,
                artifact_type=request.artifact_type,
                title=request.title,
                visibility=request.visibility,
                source_system=request.source_system,
                created_by=request.created_by,
                body_ref={
                    "storage": "s3",
                    "bucket": body_bucket,
                    "key": body_key,
                    "content_type": "text/markdown",
                },
                body_text=markdown,
                summary=f"Memory projection for query: {request.query}",
                owners=request.owners,
                groups=request.groups,
                scope_ids=request.scope_ids,
                repo_ids=request.repo_ids,
                work_item_ids=request.work_item_ids,
                conversation_ids=request.conversation_ids,
            ),
        )

        return MemoryProjectionResult(
            artifact_id=request.artifact_id,
            version_id=request.version_id,
            memory_hit_count=len(search_response.results),
            body_ref={
                "storage": "s3",
                "bucket": body_bucket,
                "key": body_key,
                "content_type": "text/markdown",
            },
            markdown_preview=markdown[:500],
            memory_recall_source=search_response.source,
            memory_search_status=search_response.status.value,
        )

    def capture_memory_artifact(self, request: MemoryCaptureRequest) -> MemoryCaptureResult:
        artifact_client = self.artifact_client or self._build_artifact_client()
        if artifact_client is None:
            raise RuntimeError("No artifact client is configured.")

        markdown = render_memory_capture(request)
        body_key = request.body_key or (
            f"artifacts/{request.artifact_id}/{request.version_id}/body.md"
        )
        body_bucket = request.body_bucket or self.settings.worker_default_bucket

        _create_artifact_replay_safe(
            artifact_client,
            CreateArtifactRequest(
                artifact_id=request.artifact_id,
                version_id=request.version_id,
                artifact_type=request.artifact_type,
                title=request.title,
                visibility=request.visibility,
                source_system=request.source_system,
                created_by=request.created_by,
                body_ref={
                    "storage": "s3",
                    "bucket": body_bucket,
                    "key": body_key,
                    "content_type": "text/markdown",
                },
                body_text=markdown,
                summary=request.summary,
                owners=request.owners,
                groups=request.groups,
                scope_ids=request.scope_ids,
                repo_ids=request.repo_ids,
                work_item_ids=request.work_item_ids,
                conversation_ids=request.conversation_ids,
            ),
        )

        return MemoryCaptureResult(
            artifact_id=request.artifact_id,
            version_id=request.version_id,
            body_ref={
                "storage": "s3",
                "bucket": body_bucket,
                "key": body_key,
                "content_type": "text/markdown",
            },
            markdown_preview=markdown[:500],
        )

    def ingest_repo_comprehension(
        self, request: RepoComprehensionIngestRequest
    ) -> RepoComprehensionIngestResult:
        memory_client = self.memory_client or self._build_memory_client()
        artifact_client = self.artifact_client or self._build_artifact_client()

        if memory_client is None:
            raise RuntimeError("No memory client is configured.")
        if artifact_client is None:
            raise RuntimeError("No artifact client is configured.")

        search_response = memory_client.search(
            MemorySearchRequest(
                query=request.query,
                limit=request.limit,
                wing=request.wing,
                room=request.room,
                allowed_wings=request.allowed_wings,
            )
        )
        task_markdown = render_memory_projection(query=request.query, response=search_response)
        repo_markdown = render_repo_comprehension_note(
            query=request.query,
            response=search_response,
            repo_ids=request.repo_ids,
        )
        body_bucket = request.body_bucket or self.settings.worker_default_bucket
        tc_key = request.task_context_body_key or (
            f"artifacts/{request.task_context_artifact_id}/"
            f"{request.task_context_version_id}/body.md"
        )
        rn_key = request.repo_note_body_key or (
            f"artifacts/{request.repo_note_artifact_id}/{request.repo_note_version_id}/body.md"
        )

        _create_artifact_replay_safe(
            artifact_client,
            CreateArtifactRequest(
                artifact_id=request.task_context_artifact_id,
                version_id=request.task_context_version_id,
                artifact_type=ArtifactType.TASK_CONTEXT,
                title=request.task_context_title,
                visibility=request.visibility,
                source_system=request.source_system,
                created_by=request.created_by,
                body_ref={
                    "storage": "s3",
                    "bucket": body_bucket,
                    "key": tc_key,
                    "content_type": "text/markdown",
                },
                body_text=task_markdown,
                summary=f"Memory projection for query: {request.query}",
                owners=request.owners,
                groups=request.groups,
                scope_ids=request.scope_ids,
                repo_ids=request.repo_ids,
                work_item_ids=request.work_item_ids,
                conversation_ids=request.conversation_ids,
            ),
        )
        _create_artifact_replay_safe(
            artifact_client,
            CreateArtifactRequest(
                artifact_id=request.repo_note_artifact_id,
                version_id=request.repo_note_version_id,
                artifact_type=ArtifactType.REPO_NOTE,
                title=request.repo_note_title,
                visibility=request.visibility,
                source_system=request.source_system,
                created_by=request.created_by,
                body_ref={
                    "storage": "s3",
                    "bucket": body_bucket,
                    "key": rn_key,
                    "content_type": "text/markdown",
                },
                body_text=repo_markdown,
                summary=f"Repository comprehension note for query: {request.query}",
                owners=request.owners,
                groups=request.groups,
                scope_ids=request.scope_ids,
                repo_ids=request.repo_ids,
                work_item_ids=request.work_item_ids,
                conversation_ids=request.conversation_ids,
            ),
        )

        return RepoComprehensionIngestResult(
            task_context_artifact_id=request.task_context_artifact_id,
            task_context_version_id=request.task_context_version_id,
            task_context_body_ref={
                "storage": "s3",
                "bucket": body_bucket,
                "key": tc_key,
                "content_type": "text/markdown",
            },
            repo_note_artifact_id=request.repo_note_artifact_id,
            repo_note_version_id=request.repo_note_version_id,
            repo_note_body_ref={
                "storage": "s3",
                "bucket": body_bucket,
                "key": rn_key,
                "content_type": "text/markdown",
            },
            memory_hit_count=len(search_response.results),
            task_context_markdown_preview=task_markdown[:500],
            repo_note_markdown_preview=repo_markdown[:500],
            memory_recall_source=search_response.source,
            memory_search_status=search_response.status.value,
        )

    def _build_memory_client(self) -> MemorySearchClient | None:
        try:
            from knowledge_client import MemoryAdapterClient
        except Exception:
            return None
        return MemoryAdapterClient(
            base_url=self.settings.memory_adapter_base_url,
            actor_id=self.actor_id,
            actor_groups=self.actor_groups,
        )

    def _build_artifact_client(self) -> ArtifactClient | None:
        try:
            from knowledge_client import KnowledgeApiClient
        except Exception:
            return None
        return KnowledgeApiClient(
            base_url=self.settings.knowledge_api_base_url,
            actor_id=self.actor_id,
            actor_groups=self.actor_groups,
        )


def _create_artifact_replay_safe(artifact_client: ArtifactClient, request: CreateArtifactRequest) -> None:
    try:
        artifact_client.create_artifact(request)
    except KnowledgeClientResponseError as exc:
        if exc.status_code == 409:
            return
        raise
