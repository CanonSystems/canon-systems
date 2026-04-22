"""Work item API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.work_item_api import CreateWorkItemRequest, WorkItemResponse
from app.services.work_items import create_work_item, get_work_item_by_external_key, list_work_items

router = APIRouter()


@router.get("", response_model=list[WorkItemResponse])
def list_work_items_endpoint(session: Session = Depends(get_db_session)) -> list[WorkItemResponse]:
    """List known work items."""
    return list_work_items(session)


@router.get("/{external_key}", response_model=WorkItemResponse)
def get_work_item_endpoint(
    external_key: str, session: Session = Depends(get_db_session)
) -> WorkItemResponse:
    """Fetch a work item by external key."""
    return get_work_item_by_external_key(session, external_key)


@router.post("", response_model=WorkItemResponse, status_code=status.HTTP_201_CREATED)
def create_work_item_endpoint(
    request: CreateWorkItemRequest, session: Session = Depends(get_db_session)
) -> WorkItemResponse:
    """Create a new work item identity."""
    return create_work_item(session, request)
