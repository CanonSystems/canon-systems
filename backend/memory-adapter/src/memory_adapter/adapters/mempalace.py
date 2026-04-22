"""MemPalace backend adapter."""

from __future__ import annotations

from importlib import import_module

from ..models import MemorySearchRequest, MemorySearchResponse


class MempalaceSearchBackend:
    """Adapter around ``mempalace.searcher.search_memories``."""

    def __init__(self, palace_path: str) -> None:
        self.palace_path = palace_path

    def search(self, request: MemorySearchRequest) -> MemorySearchResponse:
        search_memories = self._load_search_memories()
        if search_memories is None:
            return MemorySearchResponse.unavailable(
                query=request.query,
                filters=request.filters(),
                error="mempalace.searcher.search_memories is not available.",
                hint="Install or expose MemPalace on PYTHONPATH, then set MEMPALACE_PATH.",
            )

        payload = search_memories(
            query=request.query,
            palace_path=request.palace_path or self.palace_path,
            wing=request.wing,
            room=request.room,
            n_results=request.limit,
        )
        return MemorySearchResponse.from_mempalace_payload(payload, request=request)

    @staticmethod
    def _load_search_memories():
        try:
            module = import_module("mempalace.searcher")
        except Exception:
            return None
        return getattr(module, "search_memories", None)
