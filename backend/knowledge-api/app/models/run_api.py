"""Pydantic API models for orchestration runs."""

from __future__ import annotations

from pydantic import BaseModel

from knowledge_schema import RunLaunchMode, RunStage


class CreateRunRequest(BaseModel):
    run_id: str
    stage: RunStage
    status: str
    initiated_by: str
    launch_mode: RunLaunchMode | None = None
    source_conversation_id: str | None = None
    scope_artifact_id: str | None = None
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    execution_packet_artifact_id: str | None = None
    work_item_id: str | None = None
    jira_issue_key: str | None = None
    canon_task_id: str | None = None
    task_title: str | None = None
    repository_id: str | None = None
    scope_id: str | None = None


class DispatchRunRequest(BaseModel):
    orchestration_runtime: str
    workflow_type: str
    task_queue: str
    capability_class: str
    provider_lane: str
    fallback_lane: str | None = None
    parent_run_id: str | None = None
    dispatch_payload_json: str | None = None
    dispatch_status: str = "dispatched"
    launch_mode: RunLaunchMode | None = None
    source_conversation_id: str | None = None
    scope_artifact_id: str | None = None
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    execution_packet_artifact_id: str | None = None
    jira_issue_key: str | None = None
    canon_task_id: str | None = None
    task_title: str | None = None


class TransitionRunDispatchRequest(BaseModel):
    expected_dispatch_status: str
    next_dispatch_status: str
    transition_actor_id: str


class AdvanceRunLifecycleRequest(BaseModel):
    next_dispatch_status: str
    transition_actor_id: str
    expected_dispatch_status: str | None = None
    status_override: str | None = None
    stage_override: RunStage | None = None


class CreateRunEventRequest(BaseModel):
    event_id: str
    event_type: str
    payload_json: str | None = None


class RunEventResponse(BaseModel):
    id: str
    run_id: str
    event_type: str
    payload_json: str | None = None
    created_at: str


class RunResponse(BaseModel):
    id: str
    stage: RunStage
    status: str
    dispatch_status: str
    launch_mode: RunLaunchMode | None = None
    initiated_by: str
    orchestration_runtime: str | None = None
    workflow_type: str | None = None
    task_queue: str | None = None
    capability_class: str | None = None
    provider_lane: str | None = None
    fallback_lane: str | None = None
    parent_run_id: str | None = None
    dispatch_payload_json: str | None = None
    claimed_by: str | None = None
    claimed_at: str | None = None
    source_conversation_id: str | None = None
    scope_artifact_id: str | None = None
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    execution_packet_artifact_id: str | None = None
    work_item_id: str | None = None
    jira_issue_key: str | None = None
    canon_task_id: str | None = None
    task_title: str | None = None
    repository_id: str | None = None
    scope_id: str | None = None
    started_at: str
    ended_at: str | None = None


class RunSummaryResponse(BaseModel):
    id: str
    stage: RunStage
    status: str
    dispatch_status: str
    launch_mode: RunLaunchMode | None = None
    workflow_type: str | None = None
    task_queue: str | None = None
    provider_lane: str | None = None
    initiated_by: str
    work_item_id: str | None = None
    jira_issue_key: str | None = None
    canon_task_id: str | None = None
    task_title: str | None = None
    scope_id: str | None = None
    source_conversation_id: str | None = None
    scope_artifact_id: str | None = None
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    execution_packet_artifact_id: str | None = None
    waiting_for_human: bool
    is_blocked: bool
    is_terminal: bool
    started_at: str
    ended_at: str | None = None
