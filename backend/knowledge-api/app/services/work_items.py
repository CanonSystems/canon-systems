"""Work item service operations."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.work_item_api import CreateWorkItemRequest, WorkItemResponse
from app.models.work_item_db import WorkItemORM


def list_work_items(session: Session) -> list[WorkItemResponse]:
    rows = session.scalars(select(WorkItemORM).order_by(WorkItemORM.updated_at.desc())).all()
    return [
        WorkItemResponse(
            id=row.id,
            external_type=row.external_type,
            external_key=row.external_key,
            title=row.title,
            status=row.status,
            project_scope_id=row.project_scope_id,
            repository_id=row.repository_id,
        )
        for row in rows
    ]


def get_work_item_by_external_key(session: Session, external_key: str) -> WorkItemResponse:
    row = session.scalar(select(WorkItemORM).where(WorkItemORM.external_key == external_key))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="work item not found")
    return WorkItemResponse(
        id=row.id,
        external_type=row.external_type,
        external_key=row.external_key,
        title=row.title,
        status=row.status,
        project_scope_id=row.project_scope_id,
        repository_id=row.repository_id,
    )


def create_work_item(session: Session, request: CreateWorkItemRequest) -> WorkItemResponse:
    existing = session.scalar(select(WorkItemORM).where(WorkItemORM.external_key == request.external_key))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="work item already exists")

    row = WorkItemORM(
        id=request.work_item_id,
        external_type=request.external_type,
        external_key=request.external_key,
        title=request.title,
        status=request.status,
        project_scope_id=request.project_scope_id,
        repository_id=request.repository_id,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return get_work_item_by_external_key(session, row.external_key)
