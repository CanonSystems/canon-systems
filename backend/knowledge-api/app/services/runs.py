"""Run service operations."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

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
from app.models.artifact_db import ArtifactORM
from app.models.run_db import RunEventORM, RunORM
from app.models.work_item_db import WorkItemORM


def _ensure_run_company_scope(row: RunORM | None, company_scope_id: str | None) -> None:
    if company_scope_id is None or row is None:
        return
    if row.scope_id != company_scope_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _to_run_response(row: RunORM) -> RunResponse:
    return RunResponse(
        id=row.id,
        stage=row.stage,
        status=row.status,
        dispatch_status=row.dispatch_status,
        launch_mode=row.launch_mode,
        initiated_by=row.initiated_by,
        orchestration_runtime=row.orchestration_runtime,
        workflow_type=row.workflow_type,
        task_queue=row.task_queue,
        capability_class=row.capability_class,
        provider_lane=row.provider_lane,
        fallback_lane=row.fallback_lane,
        parent_run_id=row.parent_run_id,
        dispatch_payload_json=row.dispatch_payload_json,
        claimed_by=row.claimed_by,
        claimed_at=row.claimed_at.isoformat() if row.claimed_at else None,
        source_conversation_id=row.source_conversation_id,
        scope_artifact_id=row.scope_artifact_id,
        plan_packet_artifact_id=row.plan_packet_artifact_id,
        scaffold_blueprint_artifact_id=row.scaffold_blueprint_artifact_id,
        execution_packet_artifact_id=row.execution_packet_artifact_id,
        work_item_id=row.work_item_id,
        jira_issue_key=row.jira_issue_key,
        canon_task_id=row.canon_task_id,
        task_title=row.task_title,
        repository_id=row.repository_id,
        scope_id=row.scope_id,
        started_at=row.started_at.isoformat(),
        ended_at=row.ended_at.isoformat() if row.ended_at else None,
    )


def _to_run_summary(row: RunORM) -> RunSummaryResponse:
    waiting_for_human = row.stage == "human_blocked" or row.status in {
        "waiting_for_human",
        "awaiting_human",
    }
    is_blocked = waiting_for_human or row.status in {"blocked", "failed"} or row.dispatch_status in {
        "blocked",
        "failed",
    }
    is_terminal = row.stage in {"completed", "failed"} or row.status in {"completed", "failed"}
    return RunSummaryResponse(
        id=row.id,
        stage=row.stage,
        status=row.status,
        dispatch_status=row.dispatch_status,
        launch_mode=row.launch_mode,
        workflow_type=row.workflow_type,
        task_queue=row.task_queue,
        provider_lane=row.provider_lane,
        initiated_by=row.initiated_by,
        work_item_id=row.work_item_id,
        jira_issue_key=row.jira_issue_key,
        canon_task_id=row.canon_task_id,
        task_title=row.task_title,
        scope_id=row.scope_id,
        source_conversation_id=row.source_conversation_id,
        scope_artifact_id=row.scope_artifact_id,
        plan_packet_artifact_id=row.plan_packet_artifact_id,
        scaffold_blueprint_artifact_id=row.scaffold_blueprint_artifact_id,
        execution_packet_artifact_id=row.execution_packet_artifact_id,
        waiting_for_human=waiting_for_human,
        is_blocked=is_blocked,
        is_terminal=is_terminal,
        started_at=row.started_at.isoformat(),
        ended_at=row.ended_at.isoformat() if row.ended_at else None,
    )


def _to_run_event_response(row: RunEventORM) -> RunEventResponse:
    return RunEventResponse(
        id=row.id,
        run_id=row.run_id,
        event_type=row.event_type,
        payload_json=row.payload_json,
        created_at=row.created_at.isoformat(),
    )


def _validate_run_linkages(
    session: Session,
    *,
    scope_artifact_id: str | None = None,
    plan_packet_artifact_id: str | None = None,
    scaffold_blueprint_artifact_id: str | None = None,
    execution_packet_artifact_id: str | None = None,
    work_item_id: str | None = None,
) -> None:
    artifact_links = {
        "scope_artifact_id": scope_artifact_id,
        "plan_packet_artifact_id": plan_packet_artifact_id,
        "scaffold_blueprint_artifact_id": scaffold_blueprint_artifact_id,
        "execution_packet_artifact_id": execution_packet_artifact_id,
    }
    for field_name, artifact_id in artifact_links.items():
        if artifact_id is None:
            continue
        if session.get(ArtifactORM, artifact_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{field_name} not found: {artifact_id}",
            )
    if work_item_id is not None and session.get(WorkItemORM, work_item_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"work_item_id not found: {work_item_id}",
        )


def list_runs(
    session: Session,
    *,
    company_scope_id: str | None = None,
    stage: str | None = None,
    status: str | None = None,
    dispatch_status: str | None = None,
    launch_mode: str | None = None,
    orchestration_runtime: str | None = None,
    task_queue: str | None = None,
    work_item_id: str | None = None,
    source_conversation_id: str | None = None,
    scope_artifact_id: str | None = None,
    execution_packet_artifact_id: str | None = None,
) -> list[RunResponse]:
    stmt = select(RunORM).order_by(RunORM.started_at.desc())
    if company_scope_id is not None:
        stmt = stmt.where(RunORM.scope_id == company_scope_id)
    if stage is not None:
        stmt = stmt.where(RunORM.stage == stage)
    if status is not None:
        stmt = stmt.where(RunORM.status == status)
    if dispatch_status is not None:
        stmt = stmt.where(RunORM.dispatch_status == dispatch_status)
    if launch_mode is not None:
        stmt = stmt.where(RunORM.launch_mode == launch_mode)
    if orchestration_runtime is not None:
        stmt = stmt.where(RunORM.orchestration_runtime == orchestration_runtime)
    if task_queue is not None:
        stmt = stmt.where(RunORM.task_queue == task_queue)
    if work_item_id is not None:
        stmt = stmt.where(RunORM.work_item_id == work_item_id)
    if source_conversation_id is not None:
        stmt = stmt.where(RunORM.source_conversation_id == source_conversation_id)
    if scope_artifact_id is not None:
        stmt = stmt.where(RunORM.scope_artifact_id == scope_artifact_id)
    if execution_packet_artifact_id is not None:
        stmt = stmt.where(RunORM.execution_packet_artifact_id == execution_packet_artifact_id)
    rows = session.scalars(stmt).all()
    return [_to_run_response(row) for row in rows]


def list_run_summaries(
    session: Session,
    *,
    company_scope_id: str | None = None,
    stage: str | None = None,
    status: str | None = None,
    dispatch_status: str | None = None,
    launch_mode: str | None = None,
    orchestration_runtime: str | None = None,
    task_queue: str | None = None,
    work_item_id: str | None = None,
    source_conversation_id: str | None = None,
    scope_artifact_id: str | None = None,
    execution_packet_artifact_id: str | None = None,
) -> list[RunSummaryResponse]:
    stmt = select(RunORM).order_by(RunORM.started_at.desc())
    if company_scope_id is not None:
        stmt = stmt.where(RunORM.scope_id == company_scope_id)
    if stage is not None:
        stmt = stmt.where(RunORM.stage == stage)
    if status is not None:
        stmt = stmt.where(RunORM.status == status)
    if dispatch_status is not None:
        stmt = stmt.where(RunORM.dispatch_status == dispatch_status)
    if launch_mode is not None:
        stmt = stmt.where(RunORM.launch_mode == launch_mode)
    if orchestration_runtime is not None:
        stmt = stmt.where(RunORM.orchestration_runtime == orchestration_runtime)
    if task_queue is not None:
        stmt = stmt.where(RunORM.task_queue == task_queue)
    if work_item_id is not None:
        stmt = stmt.where(RunORM.work_item_id == work_item_id)
    if source_conversation_id is not None:
        stmt = stmt.where(RunORM.source_conversation_id == source_conversation_id)
    if scope_artifact_id is not None:
        stmt = stmt.where(RunORM.scope_artifact_id == scope_artifact_id)
    if execution_packet_artifact_id is not None:
        stmt = stmt.where(RunORM.execution_packet_artifact_id == execution_packet_artifact_id)
    rows = session.scalars(stmt).all()
    return [_to_run_summary(row) for row in rows]


def list_recent_scope_launch_summaries(
    session: Session,
    *,
    company_scope_id: str | None = None,
    scope_artifact_id: str | None = None,
    launch_mode: str = "initiative_launch",
    include_terminal: bool = False,
    limit: int = 20,
) -> list[RunSummaryResponse]:
    stmt = select(RunORM).order_by(RunORM.started_at.desc())
    if company_scope_id is not None:
        stmt = stmt.where(RunORM.scope_id == company_scope_id)
    if launch_mode:
        stmt = stmt.where(RunORM.launch_mode == launch_mode)
    if scope_artifact_id is not None:
        stmt = stmt.where(RunORM.scope_artifact_id == scope_artifact_id)
    rows = session.scalars(stmt).all()
    summaries = [_to_run_summary(row) for row in rows]
    if not include_terminal:
        summaries = [item for item in summaries if not item.is_terminal]
    return summaries[: max(1, limit)]


def get_run(
    session: Session, run_id: str, *, company_scope_id: str | None = None
) -> RunResponse:
    row = session.get(RunORM, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    _ensure_run_company_scope(row, company_scope_id)
    return _to_run_response(row)


def create_run(session: Session, request: CreateRunRequest) -> RunResponse:
    if session.get(RunORM, request.run_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="run already exists")
    _validate_run_linkages(
        session,
        scope_artifact_id=request.scope_artifact_id,
        plan_packet_artifact_id=request.plan_packet_artifact_id,
        scaffold_blueprint_artifact_id=request.scaffold_blueprint_artifact_id,
        execution_packet_artifact_id=request.execution_packet_artifact_id,
        work_item_id=request.work_item_id,
    )

    row = RunORM(
        id=request.run_id,
        stage=request.stage.value,
        status=request.status,
        dispatch_status="pending",
        launch_mode=request.launch_mode.value if request.launch_mode else None,
        initiated_by=request.initiated_by,
        source_conversation_id=request.source_conversation_id,
        scope_artifact_id=request.scope_artifact_id,
        plan_packet_artifact_id=request.plan_packet_artifact_id,
        scaffold_blueprint_artifact_id=request.scaffold_blueprint_artifact_id,
        execution_packet_artifact_id=request.execution_packet_artifact_id,
        work_item_id=request.work_item_id,
        jira_issue_key=request.jira_issue_key,
        canon_task_id=request.canon_task_id,
        task_title=request.task_title,
        repository_id=request.repository_id,
        scope_id=request.scope_id,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return get_run(session, row.id)


def dispatch_run(session: Session, run_id: str, request: DispatchRunRequest) -> RunResponse:
    row = session.get(RunORM, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    if request.parent_run_id is not None and session.get(RunORM, request.parent_run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="parent run not found",
        )
    _validate_run_linkages(
        session,
        scope_artifact_id=request.scope_artifact_id,
        plan_packet_artifact_id=request.plan_packet_artifact_id,
        scaffold_blueprint_artifact_id=request.scaffold_blueprint_artifact_id,
        execution_packet_artifact_id=request.execution_packet_artifact_id,
    )

    row.dispatch_status = request.dispatch_status
    row.orchestration_runtime = request.orchestration_runtime
    row.workflow_type = request.workflow_type
    row.task_queue = request.task_queue
    row.capability_class = request.capability_class
    row.provider_lane = request.provider_lane
    row.fallback_lane = request.fallback_lane
    row.parent_run_id = request.parent_run_id
    row.dispatch_payload_json = request.dispatch_payload_json
    if request.launch_mode is not None:
        row.launch_mode = request.launch_mode.value
    if request.source_conversation_id is not None:
        row.source_conversation_id = request.source_conversation_id
    if request.scope_artifact_id is not None:
        row.scope_artifact_id = request.scope_artifact_id
    if request.plan_packet_artifact_id is not None:
        row.plan_packet_artifact_id = request.plan_packet_artifact_id
    if request.scaffold_blueprint_artifact_id is not None:
        row.scaffold_blueprint_artifact_id = request.scaffold_blueprint_artifact_id
    if request.execution_packet_artifact_id is not None:
        row.execution_packet_artifact_id = request.execution_packet_artifact_id
    if request.jira_issue_key is not None:
        row.jira_issue_key = request.jira_issue_key
    if request.canon_task_id is not None:
        row.canon_task_id = request.canon_task_id
    if request.task_title is not None:
        row.task_title = request.task_title
    session.add(row)
    session.commit()
    session.refresh(row)
    return get_run(session, row.id)


def transition_run_dispatch(
    session: Session,
    run_id: str,
    request: TransitionRunDispatchRequest,
) -> RunResponse:
    row = session.get(RunORM, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    values: dict[str, object] = {"dispatch_status": request.next_dispatch_status}
    if request.next_dispatch_status == "claimed":
        values["claimed_by"] = request.transition_actor_id
        values["claimed_at"] = datetime.now(timezone.utc)

    stmt = (
        update(RunORM)
        .where(
            RunORM.id == run_id,
            RunORM.dispatch_status == request.expected_dispatch_status,
        )
        .values(**values)
    )
    result = session.execute(stmt)
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="run dispatch state changed",
        )

    session.commit()
    return get_run(session, run_id)


def advance_run_lifecycle(
    session: Session,
    run_id: str,
    request: AdvanceRunLifecycleRequest,
) -> RunResponse:
    row = session.get(RunORM, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    if (
        request.expected_dispatch_status is not None
        and row.dispatch_status != request.expected_dispatch_status
    ):
        if request.next_dispatch_status == "started" and row.dispatch_status == "started":
            return get_run(session, row.id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="run dispatch state changed",
        )

    row.dispatch_status = request.next_dispatch_status
    if request.stage_override is not None:
        row.stage = request.stage_override.value
    if request.status_override is not None:
        row.status = request.status_override
    elif request.next_dispatch_status == "started":
        row.status = "started"
        if row.stage == "human_blocked":
            row.stage = "execution_packet"
    elif request.next_dispatch_status == "waiting_for_human":
        row.status = "waiting_for_human"
        row.stage = "human_blocked"
    elif request.next_dispatch_status == "completed":
        row.status = "completed"
        row.stage = "completed"
        row.ended_at = datetime.now(timezone.utc)
    elif request.next_dispatch_status == "failed":
        row.status = "failed"
        row.stage = "failed"
        row.ended_at = datetime.now(timezone.utc)

    session.add(row)
    session.commit()
    session.refresh(row)
    return get_run(session, row.id)


def create_run_event(session: Session, run_id: str, request: CreateRunEventRequest) -> None:
    if session.get(RunORM, run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    row = RunEventORM(
        id=request.event_id,
        run_id=run_id,
        event_type=request.event_type,
        payload_json=request.payload_json,
    )
    session.add(row)
    session.commit()


def list_run_events(
    session: Session,
    run_id: str,
    *,
    company_scope_id: str | None = None,
    event_type_prefix: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[RunEventResponse]:
    run = session.get(RunORM, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    _ensure_run_company_scope(run, company_scope_id)
    stmt = (
        select(RunEventORM)
        .where(RunEventORM.run_id == run_id)
        .order_by(RunEventORM.created_at.desc(), RunEventORM.id.desc())
        .offset(max(0, offset))
        .limit(max(1, limit))
    )
    if event_type_prefix:
        stmt = stmt.where(RunEventORM.event_type.like(f"{event_type_prefix}%"))
    rows = session.scalars(stmt).all()
    return [_to_run_event_response(row) for row in rows]
