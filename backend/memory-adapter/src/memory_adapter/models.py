"""Typed request and response models for memory-adapter."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MemoryAdapterStatus(StrEnum):
    """High-level adapter outcome."""

    ok = "ok"
    unavailable = "unavailable"
    error = "error"


class MemorySearchFilters(BaseModel):
    """Search filters supported by the adapter layer."""

    palace_path: str | None = None
    wing: str | None = None
    room: str | None = None


class MemorySearchRequest(BaseModel):
    """Search request accepted by the adapter."""

    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=100)
    palace_path: str | None = None
    wing: str | None = None
    room: str | None = None
    allowed_wings: list[str] = Field(default_factory=list)

    def filters(self) -> MemorySearchFilters:
        return MemorySearchFilters(
            palace_path=self.palace_path,
            wing=self.wing,
            room=self.room,
        )


class MemoryHit(BaseModel):
    """Single verbatim memory hit returned by the adapter."""

    text: str
    wing: str
    room: str
    source_file: str
    similarity: float = Field(ge=0.0, le=1.0)
    raw: dict[str, Any] | None = None


class MemorySearchResponse(BaseModel):
    """Structured search result for orchestration and downstream services."""

    status: MemoryAdapterStatus = MemoryAdapterStatus.ok
    query: str
    filters: MemorySearchFilters
    results: list[MemoryHit] = Field(default_factory=list)
    source: str = "mempalace"
    error: str | None = None
    hint: str | None = None

    @classmethod
    def unavailable(
        cls,
        *,
        query: str,
        filters: MemorySearchFilters,
        error: str,
        hint: str | None = None,
    ) -> "MemorySearchResponse":
        return cls(
            status=MemoryAdapterStatus.unavailable,
            query=query,
            filters=filters,
            results=[],
            source="mempalace",
            error=error,
            hint=hint,
        )

    @classmethod
    def from_mempalace_payload(
        cls,
        payload: dict[str, Any],
        *,
        request: MemorySearchRequest,
    ) -> "MemorySearchResponse":
        if payload.get("error"):
            return cls.unavailable(
                query=request.query,
                filters=request.filters(),
                error=str(payload["error"]),
                hint=payload.get("hint"),
            )

        hits: list[MemoryHit] = []
        for item in payload.get("results", []):
            hits.append(
                MemoryHit(
                    text=str(item.get("text", "")),
                    wing=str(item.get("wing", "unknown")),
                    room=str(item.get("room", "unknown")),
                    source_file=str(item.get("source_file", "?")),
                    similarity=float(item.get("similarity", 0.0)),
                    raw=item,
                )
            )

        return cls(
            status=MemoryAdapterStatus.ok,
            query=payload.get("query", request.query),
            filters=MemorySearchFilters(
                palace_path=request.palace_path,
                wing=payload.get("filters", {}).get("wing", request.wing),
                room=payload.get("filters", {}).get("room", request.room),
            ),
            results=hits,
            source="mempalace",
        )
