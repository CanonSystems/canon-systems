"""API router for memory-adapter."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models import MemorySearchRequest, MemorySearchResponse
from ..service import MemoryAdapterService, get_memory_adapter_service

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/memory/search", response_model=MemorySearchResponse)
def search_memory(
    request: MemorySearchRequest,
    service: MemoryAdapterService = Depends(get_memory_adapter_service),
) -> MemorySearchResponse:
    return service.search(request)
