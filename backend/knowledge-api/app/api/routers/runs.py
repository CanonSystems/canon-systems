"""Run and run-event API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth import get_company_scope_id
from app.db.session import get_db_session
from app.models.run_api import (
    AdvanceRunLifecycleRequest,
    CreateRunEventRequest,
    CreateRunRequest,
    DispatchRunRequest,
    RunEventResponse,
    RunResponse,
    RunSummaryResponse,
    TransitionRunDispatchRequest,
)
from app.services.runs import (
    create_run,
    create_run_event,
    dispatch_run,
    get_run,
    advance_run_lifecycle,
    list_run_events,
    list_run_summaries,
    list_recent_scope_launch_summaries,
    list_runs,
    transition_run_dispatch,
)

router = APIRouter()


@router.get("", response_model=list[RunResponse])
def list_runs_endpoint(
    stage: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    dispatch_status: str | None = None,
    launch_mode: str | None = None,
    orchestration_runtime: str | None = None,
    task_queue: str | None = None,
    work_item_id: str | None = None,
    source_conversation_id: str | None = None,
    scope_artifact_id: str | None = None,
    execution_packet_artifact_id: str | None = None,
    company_scope_id: str | None = Depends(get_company_scope_id),
    session: Session = Depends(get_db_session),
) -> list[RunResponse]:
    """List orchestration runs."""
    return list_runs(
        session,
        company_scope_id=company_scope_id,
        stage=stage,
        status=status_filter,
        dispatch_status=dispatch_status,
        launch_mode=launch_mode,
        orchestration_runtime=orchestration_runtime,
        task_queue=task_queue,
        work_item_id=work_item_id,
        source_conversation_id=source_conversation_id,
        scope_artifact_id=scope_artifact_id,
        execution_packet_artifact_id=execution_packet_artifact_id,
    )


@router.get("/summaries", response_model=list[RunSummaryResponse])
def list_run_summaries_endpoint(
    stage: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    dispatch_status: str | None = None,
    launch_mode: str | None = None,
    orchestration_runtime: str | None = None,
    task_queue: str | None = None,
    work_item_id: str | None = None,
    source_conversation_id: str | None = None,
    scope_artifact_id: str | None = None,
    execution_packet_artifact_id: str | None = None,
    company_scope_id: str | None = Depends(get_company_scope_id),
    session: Session = Depends(get_db_session),
) -> list[RunSummaryResponse]:
    """List mission-control-oriented run summaries."""
    return list_run_summaries(
        session,
        company_scope_id=company_scope_id,
        stage=stage,
        status=status_filter,
        dispatch_status=dispatch_status,
        launch_mode=launch_mode,
        orchestration_runtime=orchestration_runtime,
        task_queue=task_queue,
        work_item_id=work_item_id,
        source_conversation_id=source_conversation_id,
        scope_artifact_id=scope_artifact_id,
        execution_packet_artifact_id=execution_packet_artifact_id,
    )


@router.get("/summaries/recent-scope-launches", response_model=list[RunSummaryResponse])
def list_recent_scope_launch_summaries_endpoint(
    scope_artifact_id: str | None = None,
    launch_mode: str = "initiative_launch",
    include_terminal: bool = False,
    limit: int = Query(default=20, ge=1, le=200),
    company_scope_id: str | None = Depends(get_company_scope_id),
    session: Session = Depends(get_db_session),
) -> list[RunSummaryResponse]:
    """Mission-control preset for recent scope-launch run summaries."""
    return list_recent_scope_launch_summaries(
        session,
        company_scope_id=company_scope_id,
        scope_artifact_id=scope_artifact_id,
        launch_mode=launch_mode,
        include_terminal=include_terminal,
        limit=limit,
    )


@router.get("/{run_id}", response_model=RunResponse)
def get_run_endpoint(
    run_id: str,
    company_scope_id: str | None = Depends(get_company_scope_id),
    session: Session = Depends(get_db_session),
) -> RunResponse:
    """Fetch a single run."""
    return get_run(session, run_id, company_scope_id=company_scope_id)


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run_endpoint(
    request: CreateRunRequest, session: Session = Depends(get_db_session)
) -> RunResponse:
    """Create a new orchestration run."""
    return create_run(session, request)


@router.post("/{run_id}/dispatch", response_model=RunResponse)
def dispatch_run_endpoint(
    run_id: str,
    request: DispatchRunRequest,
    session: Session = Depends(get_db_session),
) -> RunResponse:
    """Record durable workflow/task-queue dispatch metadata for a run."""
    return dispatch_run(session, run_id, request)


@router.post("/{run_id}/dispatch/transition", response_model=RunResponse)
def transition_run_dispatch_endpoint(
    run_id: str,
    request: TransitionRunDispatchRequest,
    session: Session = Depends(get_db_session),
) -> RunResponse:
    """Advance a run's dispatch state using optimistic status matching."""
    return transition_run_dispatch(session, run_id, request)


@router.post("/{run_id}/dispatch/lifecycle", response_model=RunResponse)
def advance_run_lifecycle_endpoint(
    run_id: str,
    request: AdvanceRunLifecycleRequest,
    session: Session = Depends(get_db_session),
) -> RunResponse:
    """Apply canonical lifecycle transitions for mission-control visibility."""
    return advance_run_lifecycle(session, run_id, request)


@router.post("/{run_id}/events", status_code=status.HTTP_204_NO_CONTENT)
def create_run_event_endpoint(
    run_id: str, request: CreateRunEventRequest, session: Session = Depends(get_db_session)
) -> Response:
    """Append an event to a run."""
    create_run_event(session, run_id, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{run_id}/events", response_model=list[RunEventResponse])
def list_run_events_endpoint(
    run_id: str,
    event_type_prefix: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=10000),
    company_scope_id: str | None = Depends(get_company_scope_id),
    session: Session = Depends(get_db_session),
) -> list[RunEventResponse]:
    """List run events ordered newest-first."""
    return list_run_events(
        session,
        run_id,
        company_scope_id=company_scope_id,
        event_type_prefix=event_type_prefix,
        limit=limit,
        offset=offset,
    )
