"""API router for memory-adapter."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models import MemorySearchRequest, MemorySearchResponse
from ..service import MemoryAdapterService, get_memory_adapter_service

health_router = APIRouter(tags=["memory-adapter"])


@health_router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


search_router = APIRouter(tags=["memory-adapter"])


@search_router.post("/memory/search", response_model=MemorySearchResponse)
def search_memory(
    request: MemorySearchRequest,
    service: MemoryAdapterService = Depends(get_memory_adapter_service),
) -> MemorySearchResponse:
    return service.search(request)


# Standalone service: same HTTP surface as before (health + search).
router = APIRouter()
router.include_router(health_router)
router.include_router(search_router)
