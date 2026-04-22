"""Typed request and response models for the client package."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CanonicalStrEnum(str, Enum):
    """String enum with stable lowercase values."""

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(member.value for member in cls)


class ArtifactType(CanonicalStrEnum):
    CONVERSATION_TRANSCRIPT = "conversation_transcript"
    MEMORY_CAPTURE = "memory_capture"
    CURRENT_STATE_NOTE = "current_state_note"
    DECISION_RECORD = "decision_record"
    ARCHITECTURE_NOTE = "architecture_note"
    REPO_NOTE = "repo_note"
    PROJECT_NOTE = "project_note"
    TASK_CONTEXT = "task_context"
    PLAN_PACKET = "plan_packet"
    SCAFFOLD_BLUEPRINT = "scaffold_blueprint"
    SCOPE_PACKET = "scope_packet"
    EXECUTION_PACKET = "execution_packet"
    QA_PACKET = "qa_packet"
    JIRA_COMMENT_SNAPSHOT = "jira_comment_snapshot"
    SYNC_EVENT = "sync_event"


class Visibility(CanonicalStrEnum):
    PRIVATE = "private"
    TEAM = "team"
    PROJECT = "project"
    RESTRICTED = "restricted"


class ArtifactStatus(CanonicalStrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class MemoryAdapterStatus(CanonicalStrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class RunStage(CanonicalStrEnum):
    INTAKE = "intake"
    CONTEXT_HYDRATION = "context_hydration"
    PATH_SELECTION = "path_selection"
    PROJECT_STRUCTURING = "project_structuring"
    STORY_SCOPING = "story_scoping"
    EXECUTION_PACKET = "execution_packet"
    IMPLEMENTATION = "implementation"
    PARALLEL_QA = "parallel_qa"
    PUBLISH_SYNC = "publish_sync"
    RECONCILIATION = "reconciliation"
    HUMAN_BLOCKED = "human_blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class RunLaunchMode(CanonicalStrEnum):
    INITIATIVE_LAUNCH = "initiative_launch"
    DELIVERY_LAUNCH = "delivery_launch"


class JiraAuthMode(CanonicalStrEnum):
    API_TOKEN = "api_token"
    OAUTH = "oauth"
    PAT = "pat"


class JiraConnectivityFailureCode(CanonicalStrEnum):
    AUTH_FAILED = "auth_failed"
    NETWORK_ERROR = "network_error"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


class BodyRef(BaseModel):
    storage: str = Field(default="s3")
    bucket: str
    key: str
    content_type: str = Field(default="text/markdown")


class CreateArtifactRequest(BaseModel):
    artifact_id: str
    version_id: str
    artifact_type: ArtifactType
    title: str
    visibility: Visibility
    source_system: str
    created_by: str
    body_ref: BodyRef
    body_text: str | None = None
    summary: str | None = None
    owners: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    scope_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    work_item_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)


class ArtifactListItem(BaseModel):
    artifact_id: str
    artifact_type: ArtifactType
    title: str
    status: ArtifactStatus
    visibility: Visibility
    current_version_id: str | None = None
    updated_at: str | None = None


class ArtifactEnvelope(BaseModel):
    artifact_id: str
    version_id: str
    artifact_type: ArtifactType
    title: str
    status: ArtifactStatus
    visibility: Visibility
    owners: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    scope_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    work_item_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)
    source_system: str
    supersedes_artifact_id: str | None = None
    body_ref: BodyRef
    summary: str | None = None
    created_at: str
    created_by: str


class ArtifactBodyResponse(BaseModel):
    artifact_id: str
    version_id: str
    body_ref: BodyRef
    content_type: str
    body_text: str


class MemorySearchFilters(BaseModel):
    palace_path: str | None = None
    wing: str | None = None
    room: str | None = None


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=100)
    palace_path: str | None = None
    wing: str | None = None
    room: str | None = None
    allowed_wings: list[str] = Field(default_factory=list)


class MemoryHit(BaseModel):
    text: str
    wing: str
    room: str
    source_file: str
    similarity: float = Field(ge=0.0, le=1.0)
    raw: dict[str, Any] | None = None


class MemorySearchResponse(BaseModel):
    status: MemoryAdapterStatus = MemoryAdapterStatus.OK
    query: str
    filters: MemorySearchFilters
    results: list[MemoryHit] = Field(default_factory=list)
    source: str = "mempalace"
    error: str | None = None
    hint: str | None = None


class MemoryProjectionRequest(BaseModel):
    query: str = Field(min_length=1)
    artifact_id: str
    version_id: str
    title: str
    artifact_type: ArtifactType = ArtifactType.TASK_CONTEXT
    visibility: Visibility = Visibility.PROJECT
    created_by: str
    source_system: str = "knowledge-worker"
    body_bucket: str | None = None
    body_key: str | None = None
    wing: str | None = None
    room: str | None = None
    allowed_wings: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=25)
    owners: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    scope_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    work_item_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)


class MemoryCaptureRequest(BaseModel):
    artifact_id: str
    version_id: str
    title: str
    transcript_text: str = Field(min_length=1)
    artifact_type: ArtifactType = ArtifactType.MEMORY_CAPTURE
    visibility: Visibility = Visibility.PROJECT
    created_by: str
    source_system: str = "knowledge-worker"
    body_bucket: str | None = None
    body_key: str | None = None
    summary: str | None = None
    decisions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    scope_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    work_item_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)


class MemoryProjectionResult(BaseModel):
    artifact_id: str
    version_id: str
    memory_hit_count: int
    body_ref: BodyRef
    markdown_preview: str
    memory_recall_source: str = "unknown"
    memory_search_status: str = "unknown"


class MemoryCaptureResult(BaseModel):
    artifact_id: str
    version_id: str
    body_ref: BodyRef
    markdown_preview: str


class RepoComprehensionIngestRequest(BaseModel):
    """Single memory search producing TASK_CONTEXT + REPO_NOTE artifacts."""

    query: str = Field(min_length=1)
    task_context_artifact_id: str
    task_context_version_id: str
    task_context_title: str
    repo_note_artifact_id: str
    repo_note_version_id: str
    repo_note_title: str
    visibility: Visibility = Visibility.PROJECT
    created_by: str
    source_system: str = "knowledge-worker"
    body_bucket: str | None = None
    task_context_body_key: str | None = None
    repo_note_body_key: str | None = None
    wing: str | None = None
    room: str | None = None
    allowed_wings: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=25)
    owners: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    scope_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    work_item_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)


class RepoComprehensionIngestResult(BaseModel):
    task_context_artifact_id: str
    task_context_version_id: str
    task_context_body_ref: BodyRef
    repo_note_artifact_id: str
    repo_note_version_id: str
    repo_note_body_ref: BodyRef
    memory_hit_count: int
    task_context_markdown_preview: str
    repo_note_markdown_preview: str
    memory_recall_source: str = "unknown"
    memory_search_status: str = "unknown"


class VaultProjectionRequest(BaseModel):
    artifact_id: str
    vault_root: str | None = None
    vault_name: str = "current"
    scope_id: str | None = None
    editable_class: str = "read_only_generated"


class VaultProjectionResult(BaseModel):
    artifact_id: str
    version_id: str
    artifact_type: ArtifactType
    visibility: Visibility
    output_path: str
    relative_path: str
    editable_class: str
    bytes_written: int = Field(ge=0)


class BatchVaultProjectionRequest(BaseModel):
    vault_root: str | None = None
    vault_name: str = "current"
    scope_id: str | None = None
    repo_id: str | None = None
    work_item_id: str | None = None
    visibility: Visibility | None = None
    status: str | None = None
    editable_class: str = "read_only_generated"
    artifact_types: list[ArtifactType] = Field(
        default_factory=lambda: [
            ArtifactType.CURRENT_STATE_NOTE,
            ArtifactType.DECISION_RECORD,
            ArtifactType.TASK_CONTEXT,
            ArtifactType.PROJECT_NOTE,
            ArtifactType.REPO_NOTE,
        ]
    )
    prune_missing: bool = True


class BatchVaultProjectionResult(BaseModel):
    vault_name: str
    manifest_path: str
    projected: list[VaultProjectionResult] = Field(default_factory=list)
    removed_paths: list[str] = Field(default_factory=list)


class CodeGraphQueryRequest(BaseModel):
    """Request for a bounded CodeGraph adapter query (adapter-local graph / index)."""

    query: str
    repo_id: str | None = None
    scope_id: str | None = None
    work_item_id: str | None = None
    commit_sha: str | None = None
    repo_root: str | None = None


class CodeGraphQueryResult(BaseModel):
    """Normalized CodeGraph query outcome for lane telemetry."""

    model_config = ConfigDict(extra="ignore")

    status: str
    summary: str | None = None
    record_count: int = 0
    sample_records: list[dict[str, Any]] = Field(default_factory=list)


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


class WorkflowIntentQuery(BaseModel):
    task_queue: str | None = None
    workflow_type: str | None = None
    work_item_id: str | None = None
    launch_mode: RunLaunchMode | None = None
    scope_artifact_id: str | None = None
    execution_packet_artifact_id: str | None = None
    dispatch_status: str = "dispatched"
    orchestration_runtime: str = "temporal"
    claim_dispatch: bool = False
    claimer_id: str | None = None


class WorkflowStartIntent(BaseModel):
    run_id: str
    workflow_type: str
    task_queue: str
    stage: str
    initiated_by: str
    dispatch_status: str
    launch_mode: RunLaunchMode | None = None
    capability_class: str | None = None
    provider_lane: str | None = None
    fallback_lane: str | None = None
    claimed_by: str | None = None
    claimed_at: str | None = None
    source_conversation_id: str | None = None
    scope_artifact_id: str | None = None
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    execution_packet_artifact_id: str | None = None
    parent_run_id: str | None = None
    work_item_id: str | None = None
    repository_id: str | None = None
    scope_id: str | None = None
    input_payload: dict = Field(default_factory=dict)


class WorkflowIntentBatch(BaseModel):
    query: WorkflowIntentQuery
    intents: list[WorkflowStartIntent] = Field(default_factory=list)


class ClaimAndStartRequest(BaseModel):
    task_queue: str
    workflow_type: str | None = None
    launch_mode: RunLaunchMode | None = None
    scope_artifact_id: str | None = None
    execution_packet_artifact_id: str | None = None
    dispatch_status: str = "dispatched"
    orchestration_runtime: str = "temporal"
    claimer_id: str | None = None


class ClaimAndStartFailure(BaseModel):
    run_id: str
    error: str


class ClaimAndStartResponse(BaseModel):
    claimed_count: int = 0
    started_count: int = 0
    started_run_ids: list[str] = Field(default_factory=list)
    failures: list[ClaimAndStartFailure] = Field(default_factory=list)


class ScopeTaskCandidate(BaseModel):
    task_id: str
    title: str
    summary: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    issue_type: str = "Story"
    labels: list[str] = Field(default_factory=list)


class JiraConnectivitySetupRequest(BaseModel):
    jira_project_key: str
    jira_base_url: str
    auth_mode: JiraAuthMode
    credential_ref: str
    oauth_cloud_id: str | None = None
    oauth_refresh_token_ref: str | None = None


class JiraProjectConnectivity(BaseModel):
    jira_project_key: str
    jira_base_url: str
    auth_mode: JiraAuthMode
    credential_ref: str
    oauth_cloud_id: str | None = None
    oauth_refresh_token_ref: str | None = None
    connected: bool
    last_verified_at: str
    expires_at: str
    failure_code: JiraConnectivityFailureCode | None = None
    failure_reason: str | None = None


class JiraConnectivitySetupResponse(BaseModel):
    connectivity: JiraProjectConnectivity


class JiraOAuthStartRequest(BaseModel):
    jira_project_key: str
    jira_base_url: str
    scopes: list[str] = Field(
        default_factory=lambda: [
            "read:jira-user",
            "read:jira-work",
            "write:jira-work",
            "offline_access",
        ]
    )
    state: str | None = None


class JiraOAuthStartResponse(BaseModel):
    authorization_url: str
    state: str


class JiraOAuthExchangeRequest(BaseModel):
    jira_project_key: str
    jira_base_url: str
    code: str
    state: str


class JiraOAuthExchangeResponse(BaseModel):
    connectivity: JiraProjectConnectivity


class JiraConnectivityListResponse(BaseModel):
    projects: list[JiraProjectConnectivity] = Field(default_factory=list)


class JiraConnectivityHealthResponse(BaseModel):
    healthy_project_keys: list[str] = Field(default_factory=list)
    stale_project_keys: list[str] = Field(default_factory=list)


class JiraConnectivityPruneResponse(BaseModel):
    removed_project_keys: list[str] = Field(default_factory=list)
    remaining_project_keys: list[str] = Field(default_factory=list)


class JiraProvisioningProjectStats(BaseModel):
    jira_project_key: str
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    last_error_code: JiraConnectivityFailureCode | None = None
    last_error_reason: str | None = None
    last_attempt_at: str | None = None
    last_success_at: str | None = None


class JiraProvisioningStatsResponse(BaseModel):
    projects: list[JiraProvisioningProjectStats] = Field(default_factory=list)


class JiraProjectResolutionRequest(BaseModel):
    preferred_project_key: str | None = None
    work_item_key: str | None = None
    scope_id: str | None = None
    repository_id: str | None = None


class JiraProjectResolutionResponse(BaseModel):
    jira_project_key: str
    reason: str


class ScopeToJiraScaffoldRequest(BaseModel):
    scope_artifact_id: str
    jira_project_key: str
    initiated_by: str
    launch_mode: RunLaunchMode
    tasks: list[ScopeTaskCandidate] = Field(min_length=1)
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    source_conversation_id: str | None = None


class PlannedJiraIssue(BaseModel):
    task_id: str
    title: str
    summary: str
    issue_type: str = "Story"
    proposed_issue_key: str
    scope_artifact_id: str
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    execution_packet_artifact_id: str
    metadata: dict[str, str | list[str]] = Field(default_factory=dict)


class ScopeToJiraScaffoldResponse(BaseModel):
    scope_artifact_id: str
    jira_project_key: str
    launch_mode: RunLaunchMode
    scaffold_artifact_id: str
    source_conversation_id: str | None = None
    planned_issues: list[PlannedJiraIssue] = Field(default_factory=list)


class ScopeToJiraScaffoldResolvedRequest(BaseModel):
    scope_artifact_id: str
    initiated_by: str
    launch_mode: RunLaunchMode
    tasks: list[ScopeTaskCandidate] = Field(min_length=1)
    preferred_project_key: str | None = None
    work_item_key: str | None = None
    scope_id: str | None = None
    repository_id: str | None = None
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    source_conversation_id: str | None = None


class TaskPacketGenerationRequest(BaseModel):
    scope_artifact_id: str
    scaffold_artifact_id: str
    initiated_by: str
    launch_mode: RunLaunchMode
    planned_issues: list[PlannedJiraIssue] = Field(min_length=1)
    repository_id: str | None = None


class ExecutionTaskPacket(BaseModel):
    execution_packet_artifact_id: str
    task_id: str
    title: str
    summary: str
    jira_issue_key: str
    scope_artifact_id: str
    launch_mode: RunLaunchMode
    repository_id: str | None = None
    verification_steps: list[str] = Field(default_factory=list)


class TaskPacketGenerationResponse(BaseModel):
    scope_artifact_id: str
    scaffold_artifact_id: str
    launch_mode: RunLaunchMode
    generated_count: int
    packets: list[ExecutionTaskPacket] = Field(default_factory=list)


class DeliveryRunIntent(BaseModel):
    run_id: str
    stage: str = "execution_packet"
    status: str = "started"
    initiated_by: str
    launch_mode: RunLaunchMode
    scope_artifact_id: str
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    source_conversation_id: str | None = None
    execution_packet_artifact_id: str
    jira_issue_key: str
    canon_task_id: str | None = None
    task_title: str | None = None
    workflow_type: str
    task_queue: str
    capability_class: str
    provider_lane: str
    dispatch_payload_json: str


class DeliveryRunIntentRequest(BaseModel):
    initiated_by: str
    launch_mode: RunLaunchMode = RunLaunchMode.DELIVERY_LAUNCH
    scope_artifact_id: str
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    source_conversation_id: str | None = None
    packets: list[ExecutionTaskPacket] = Field(min_length=1)
    workflow_type: str = "TaskExecutionWorkflow"
    task_queue: str = "tq_implementation_bulk"
    capability_class: str = "implementation"
    provider_lane: str = "cursor_bulk_worker"


class DeliveryRunIntentResponse(BaseModel):
    scope_artifact_id: str
    launch_mode: RunLaunchMode
    intent_count: int
    intents: list[DeliveryRunIntent] = Field(default_factory=list)


class DeliveryLaunchRequest(BaseModel):
    scope_artifact_id: str
    intents: list[DeliveryRunIntent] = Field(min_length=1)


class DeliveryLaunchFailure(BaseModel):
    run_id: str
    phase: str
    error: str
    compensated: bool = False


class DeliveryLaunchResponse(BaseModel):
    scope_artifact_id: str
    created_run_ids: list[str] = Field(default_factory=list)
    dispatched_run_ids: list[str] = Field(default_factory=list)
    failures: list[DeliveryLaunchFailure] = Field(default_factory=list)


class ScopeDeliveryLaunchRequest(BaseModel):
    scope_artifact_id: str
    initiated_by: str
    launch_mode: RunLaunchMode
    tasks: list[ScopeTaskCandidate] = Field(min_length=1)
    preferred_project_key: str | None = None
    work_item_key: str | None = None
    scope_id: str | None = None
    repository_id: str | None = None
    plan_packet_artifact_id: str | None = None
    scaffold_blueprint_artifact_id: str | None = None
    source_conversation_id: str | None = None


class ScopeDeliveryLaunchResponse(BaseModel):
    scope_artifact_id: str
    resolved_project_key: str
    scaffold_artifact_id: str
    packet_count: int
    run_intent_count: int
    created_run_ids: list[str] = Field(default_factory=list)
    dispatched_run_ids: list[str] = Field(default_factory=list)
    failures: list[DeliveryLaunchFailure] = Field(default_factory=list)


class DogfoodRunSummary(BaseModel):
    id: str
    stage: str
    status: str
    dispatch_status: str
    launch_mode: RunLaunchMode | None = None
    scope_artifact_id: str | None = None
    execution_packet_artifact_id: str | None = None
    waiting_for_human: bool
    is_blocked: bool
    is_terminal: bool
    publish_sync_state: str = "unknown"
    documentation_state: str = "unknown"
    started_at: str


class DogfoodLaneEventSummary(BaseModel):
    run_id: str
    event_id: str
    event_type: str
    artifact_id: str | None = None
    version_id: str | None = None
    created_at: datetime | None = None
    payload_json: str | None = None


class DogfoodRunLaneDrilldown(BaseModel):
    run: DogfoodRunSummary
    latest_lane_event: DogfoodLaneEventSummary | None = None


class DogfoodLaneDrilldownResponse(BaseModel):
    generated_at: datetime
    runs: list[DogfoodRunLaneDrilldown] = Field(default_factory=list)


class DogfoodProvisioningProject(BaseModel):
    jira_project_key: str
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    last_error_code: JiraConnectivityFailureCode | None = None
    last_error_reason: str | None = None


class DocValidationLiveSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str
    artifact_doc_path: str | None = None
    source_truth_path: str | None = None
    source_truth_kind: str | None = None
    expected_version: str | None = None
    declared_version: str | None = None
    finished_at: str | None = None
    detail: str | None = None


class DogfoodOpsReportResponse(BaseModel):
    generated_at: str
    recent_scope_launches: list[DogfoodRunSummary] = Field(default_factory=list)
    jira_provisioning_projects: list[DogfoodProvisioningProject] = Field(default_factory=list)
    launch_recovery_issue_count: int = 0
    launch_recovery_unresolved_count: int = 0
    launch_recovery_issue_codes: dict[str, int] = Field(default_factory=dict)
    launch_recovery_unresolved_issue_codes: dict[str, int] = Field(default_factory=dict)
    launch_success_count: int = 0
    launch_failure_count: int = 0
    launch_latency_buckets: dict[str, int] = Field(default_factory=dict)
    launch_latency_buckets_last_hour: dict[str, int] = Field(default_factory=dict)
    launch_latency_buckets_last_day: dict[str, int] = Field(default_factory=dict)
    launch_last_hour_total: int = 0
    launch_last_hour_success: int = 0
    launch_last_hour_failure: int = 0
    launch_last_day_total: int = 0
    launch_last_day_success: int = 0
    launch_last_day_failure: int = 0
    last_success_at: str | None = None
    last_failure_at: str | None = None
    doc_validation_live: DocValidationLiveSnapshot | None = None


class DogfoodSlackMessageResponse(BaseModel):
    generated_at: str
    text: str
    blocks: list[dict] = Field(default_factory=list)


class DogfoodSlackDeliveryRequest(BaseModel):
    scope_artifact_id: str | None = None
    include_terminal: bool = False
    limit: int = 10
    transport_mode: str | None = None
    webhook_url: str | None = None
    bot_token: str | None = None
    channel_id: str | None = None


class DogfoodSlackDeliveryResponse(BaseModel):
    delivered: bool
    attempts: int
    status_code: int | None = None
    error: str | None = None
    transport_mode: str | None = None
    attempt_details: list[dict] = Field(default_factory=list)


class DogfoodOpsSnapshotRequest(BaseModel):
    scope_artifact_id: str | None = None
    include_terminal: bool = False
    limit: int = 10
    created_by: str = "usr_system"
    artifact_id: str | None = None
    version_id: str | None = None
    title: str | None = None


class DogfoodOpsSnapshotResponse(BaseModel):
    artifact_id: str
    version_id: str
    scope_artifact_id: str | None = None
    generated_at: str


class DogfoodOpsSnapshotSummary(BaseModel):
    artifact_id: str
    version_id: str | None = None
    title: str
    scope_artifact_id: str | None = None
    updated_at: str | None = None


class DogfoodOpsSnapshotListResponse(BaseModel):
    snapshots: list[DogfoodOpsSnapshotSummary] = Field(default_factory=list)


class DogfoodContinuityIssue(BaseModel):
    run_id: str
    issue_code: str
    detail: str


class DogfoodContinuityReportResponse(BaseModel):
    generated_at: str
    checked_runs: int = 0
    issue_count: int = 0
    issues: list[DogfoodContinuityIssue] = Field(default_factory=list)


class DogfoodLaunchRecoveryIssue(BaseModel):
    run_id: str
    execution_packet_artifact_id: str | None = None
    issue_code: str
    detail: str
    needs_recovery: bool = True


class DogfoodLaunchRecoveryReportResponse(BaseModel):
    generated_at: str
    checked_runs: int = 0
    issue_count: int = 0
    issues: list[DogfoodLaunchRecoveryIssue] = Field(default_factory=list)


class DogfoodLaunchRecoveryRemediationRequest(BaseModel):
    scope_artifact_id: str | None = None
    limit: int = 200
    dry_run: bool = True
    max_actions: int = 50
    claimed_stale_after_minutes: int = 15
    issue_codes: list[str] = Field(
        default_factory=lambda: [
            "created_not_dispatched",
            "partial_failure_unrecovered",
            "claimed_not_started",
        ]
    )


class DogfoodLaunchRecoveryRemediationAction(BaseModel):
    run_id: str
    execution_packet_artifact_id: str | None = None
    issue_code: str
    action: str
    attempted: bool = False
    succeeded: bool = False
    detail: str


class DogfoodLaunchRecoveryRemediationResponse(BaseModel):
    generated_at: str
    dry_run: bool = True
    considered_issues: int = 0
    attempted_actions: int = 0
    successful_actions: int = 0
    actions: list[DogfoodLaunchRecoveryRemediationAction] = Field(default_factory=list)


class DogfoodMissionControlPresetResponse(BaseModel):
    generated_at: str
    ops_report: DogfoodOpsReportResponse
    continuity: DogfoodContinuityReportResponse
    snapshots: DogfoodOpsSnapshotListResponse
    lane_drilldown: DogfoodLaneDrilldownResponse
    launch_recovery: DogfoodLaunchRecoveryReportResponse


class DogfoodSnapshotCompareResponse(BaseModel):
    generated_at: str
    scope_artifact_id: str | None = None
    baseline_artifact_id: str | None = None
    candidate_artifact_id: str | None = None
    compared: bool
    diff_preview: list[str] = Field(default_factory=list)
