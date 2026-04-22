"""FastAPI router for knowledge-worker job surfaces."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from ..models import (
    MemoryCaptureRequest,
    MemoryCaptureResult,
    MemoryProjectionRequest,
    MemoryProjectionResult,
    RepoComprehensionIngestRequest,
    RepoComprehensionIngestResult,
)
from ..service import KnowledgeWorkerService

router = APIRouter()


def get_worker_service(
    x_actor_id: str | None = Header(default=None),
    x_actor_groups: str | None = Header(default=None),
) -> KnowledgeWorkerService:
    group_ids = tuple(
        part.strip() for part in (x_actor_groups or "").split(",") if part.strip()
    )
    return KnowledgeWorkerService(
        actor_id=x_actor_id or "usr_system",
        actor_groups=group_ids,
    )


@router.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "knowledge-worker"}


@router.post("/jobs/project-memory", response_model=MemoryProjectionResult)
def project_memory(
    request: MemoryProjectionRequest,
    service: KnowledgeWorkerService = Depends(get_worker_service),
) -> MemoryProjectionResult:
    return service.project_memory_to_artifact(request)


@router.post("/jobs/capture-memory", response_model=MemoryCaptureResult)
def capture_memory(
    request: MemoryCaptureRequest,
    service: KnowledgeWorkerService = Depends(get_worker_service),
) -> MemoryCaptureResult:
    return service.capture_memory_artifact(request)


@router.post("/jobs/ingest-repo-comprehension", response_model=RepoComprehensionIngestResult)
def ingest_repo_comprehension(
    request: RepoComprehensionIngestRequest,
    service: KnowledgeWorkerService = Depends(get_worker_service),
) -> RepoComprehensionIngestResult:
    return service.ingest_repo_comprehension(request)
