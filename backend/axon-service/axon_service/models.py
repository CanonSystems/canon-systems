from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


class IndexRequest(BaseModel):
    commit_sha: str = Field(min_length=1)
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexResponse(BaseModel):
    company_id: str
    repository_id: str
    commit_sha: str
    snapshot_key: str
    uploaded_at: str
    node_count: int
    edge_count: int
    size_bytes: int


class QueryResponse(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    scores: list[float] = Field(default_factory=list)
    source_spans: list[dict[str, Any]] = Field(default_factory=list)
    commit_sha: str
    query: str


class ImpactResponse(BaseModel):
    symbol: str
    commit_sha: str
    depth: int
    upstream: list[dict[str, Any]] = Field(default_factory=list)
    downstream: list[dict[str, Any]] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    snapshots: Optional[int] = None
