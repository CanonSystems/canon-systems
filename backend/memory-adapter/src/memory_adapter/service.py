"""Service layer for memory-adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

from .config import Settings, get_settings
from .models import MemoryAdapterStatus, MemorySearchRequest, MemorySearchResponse


class MemorySearchBackend(Protocol):
    """Backend protocol for memory search implementations."""

    def search(self, request: MemorySearchRequest) -> MemorySearchResponse:
        """Search for memories matching the request."""


@dataclass(slots=True)
class MemoryAdapterService:
    """Facade used by orchestration to search memory safely."""

    backend: MemorySearchBackend | None = None
    settings: Settings = field(default_factory=get_settings)

    def search(self, request: MemorySearchRequest) -> MemorySearchResponse:
        """Search using the configured backend or return a structured failure."""

        backend = self.backend or self._build_default_backend()
        if backend is None:
            return MemorySearchResponse.unavailable(
                query=request.query,
                filters=request.filters(),
                error="No memory backend is configured.",
                hint="Install mempalace or inject a backend implementation.",
            )
        if request.allowed_wings:
            if request.wing is not None and request.wing not in request.allowed_wings:
                return MemorySearchResponse.unavailable(
                    query=request.query,
                    filters=request.filters(),
                    error="Requested wing is outside the allowed scope.",
                    hint="Retry with an allowed wing or let the adapter fan out across allowed wings.",
                )
            if request.wing is None:
                return self._search_across_allowed_wings(backend=backend, request=request)
        return backend.search(request)

    def _build_default_backend(self) -> MemorySearchBackend | None:
        if not self.settings.mempalace_enabled:
            return None
        if not self.settings.mempalace_path:
            return None

        from .adapters.mempalace import MempalaceSearchBackend

        return MempalaceSearchBackend(palace_path=self.settings.mempalace_path)

    def _search_across_allowed_wings(
        self, *, backend: MemorySearchBackend, request: MemorySearchRequest
    ) -> MemorySearchResponse:
        merged = []

        for wing in request.allowed_wings:
            wing_request = request.model_copy(update={"wing": wing})
            response = backend.search(wing_request)
            if response.status != MemoryAdapterStatus.ok:
                continue
            merged.extend(response.results)

        merged.sort(key=lambda hit: hit.similarity, reverse=True)
        return MemorySearchResponse(
            query=request.query,
            filters=request.filters(),
            results=merged[: request.limit],
            source="mempalace",
        )


@lru_cache(maxsize=1)
def get_memory_adapter_service() -> MemoryAdapterService:
    return MemoryAdapterService()
