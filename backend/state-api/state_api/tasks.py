"""Assignable-task REST surface (server-authoritative task plane).

Tasks are event-sourced: clients POST normalized events here and GET the raw
event stream back to fold into materialized tasks. This makes "what's next",
status changes, progress/branch/deployment attribution, and reassignment work
from any machine independent of repo git state.

- ``POST /state/tasks/events`` — append one task event (idempotent by event_id).
- ``GET /state/tasks`` — return events for a company (optionally one task_ref).

This router never touches checkpoint/lease rows or S3.
"""

from __future__ import annotations

from typing import Annotated, Any

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status

from canon_backend_shared.tasks import (
    TaskValidationError,
    build_tasks_pk,
    event_keys,
    events_equivalent,
    task_event_sk_prefix,
    validate_task_event,
)

from state_api.config import Settings, get_settings
from state_api.storage import TasksStore, task_event_from_item

router = APIRouter(prefix="/state/tasks", tags=["tasks"])


def get_tasks_store(settings: Annotated[Settings, Depends(get_settings)]) -> TasksStore:
    if not settings.state_tasks_table_name.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "tasks_table_unset",
                "message": "STATE_TASKS_TABLE_NAME is required for task routes",
            },
        )
    return TasksStore(settings.state_tasks_table_name.strip(), settings.aws_region)


@router.post("/events", response_model=None)
def post_task_event(
    body: dict[str, Any],
    store: Annotated[TasksStore, Depends(get_tasks_store)],
) -> dict[str, Any]:
    try:
        record = validate_task_event(body)
        pk, sk = event_keys(record)
    except TaskValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "task_validation_error", "message": str(e)},
        ) from e

    item = dict(record)
    item["pk"] = pk
    item["sk"] = sk
    try:
        store.put_event_if_absent(item)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        existing = store.get_item(pk, sk)
        if existing is not None and events_equivalent(
            task_event_from_item(existing), task_event_from_item(item)
        ):
            return {"status": "idempotent", "event": task_event_from_item(existing)}
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "task_event_id_conflict", "message": "event_id already used with different body"},
        ) from e

    return {"status": "created", "event": task_event_from_item(item)}


@router.get("", response_model=None)
def get_tasks(
    company_id: str,
    store: Annotated[TasksStore, Depends(get_tasks_store)],
    task_ref: str | None = None,
    limit: int = 2000,
) -> dict[str, Any]:
    if limit < 1 or limit > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_limit", "message": "limit must be between 1 and 10000"},
        )
    try:
        pk = build_tasks_pk(company_id=company_id)
    except TaskValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "task_validation_error", "message": str(e)},
        ) from e

    if task_ref:
        try:
            prefix = task_event_sk_prefix(task_ref=task_ref)
        except TaskValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "task_validation_error", "message": str(e)},
            ) from e
        rows = store.query_task_events(pk, prefix, limit=limit)
    else:
        rows = store.query_company_events(pk, limit=limit)

    events = [task_event_from_item(r) for r in rows]
    return {"events": events, "count": len(events)}
