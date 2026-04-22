"""Pydantic API models for work items."""

from __future__ import annotations

from pydantic import BaseModel


class CreateWorkItemRequest(BaseModel):
    work_item_id: str
    external_type: str
    external_key: str
    title: str
    status: str
    project_scope_id: str | None = None
    repository_id: str | None = None


class WorkItemResponse(BaseModel):
    id: str
    external_type: str
    external_key: str
    title: str
    status: str
    project_scope_id: str | None = None
    repository_id: str | None = None
