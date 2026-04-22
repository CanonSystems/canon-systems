"""HTTP clients for Canon Systems v2 internal services."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Self
from urllib.parse import urlencode

import httpx

from .errors import KnowledgeClientResponseError
from .models import (
    ClaimAndStartRequest,
    ClaimAndStartResponse,
    AdvanceRunLifecycleRequest,
    ArtifactBodyResponse,
    ArtifactEnvelope,
    ArtifactListItem,
    BatchVaultProjectionRequest,
    BatchVaultProjectionResult,
    CodeGraphQueryRequest,
    CodeGraphQueryResult,
    CreateArtifactRequest,
    CreateRunEventRequest,
    CreateRunRequest,
    DogfoodOpsReportResponse,
    DogfoodOpsSnapshotRequest,
    DogfoodOpsSnapshotListResponse,
    DogfoodOpsSnapshotResponse,
    DogfoodContinuityReportResponse,
    DogfoodLaunchRecoveryReportResponse,
    DogfoodLaunchRecoveryRemediationRequest,
    DogfoodLaunchRecoveryRemediationResponse,
    DogfoodLaneDrilldownResponse,
    DogfoodMissionControlPresetResponse,
    DogfoodSnapshotCompareResponse,
    DogfoodSlackDeliveryRequest,
    DogfoodSlackDeliveryResponse,
    DogfoodSlackMessageResponse,
    DeliveryLaunchRequest,
    DeliveryLaunchResponse,
    DeliveryRunIntentRequest,
    DeliveryRunIntentResponse,
    DispatchRunRequest,
    JiraConnectivityListResponse,
    JiraConnectivityHealthResponse,
    JiraConnectivityPruneResponse,
    JiraProvisioningStatsResponse,
    JiraProjectResolutionRequest,
    JiraProjectResolutionResponse,
    JiraOAuthExchangeRequest,
    JiraOAuthExchangeResponse,
    JiraOAuthStartRequest,
    JiraOAuthStartResponse,
    JiraConnectivitySetupRequest,
    JiraConnectivitySetupResponse,
    MemoryCaptureRequest,
    MemoryCaptureResult,
    MemoryProjectionRequest,
    MemoryProjectionResult,
    RepoComprehensionIngestRequest,
    RepoComprehensionIngestResult,
    MemorySearchRequest,
    MemorySearchResponse,
    RunResponse,
    RunEventResponse,
    RunSummaryResponse,
    ScopeToJiraScaffoldRequest,
    ScopeToJiraScaffoldResolvedRequest,
    ScopeToJiraScaffoldResponse,
    ScopeDeliveryLaunchRequest,
    ScopeDeliveryLaunchResponse,
    TaskPacketGenerationRequest,
    TaskPacketGenerationResponse,
    TransitionRunDispatchRequest,
    WorkflowIntentBatch,
    WorkflowIntentQuery,
    VaultProjectionRequest,
    VaultProjectionResult,
)


@dataclass(slots=True)
class ClientConfig:
    """Common client configuration."""

    base_url: str
    timeout: float = 10.0
    headers: Mapping[str, str] | None = None
    actor_id: str | None = None
    actor_groups: tuple[str, ...] = ()


class _HttpServiceClient(AbstractContextManager["_HttpServiceClient"]):
    """Small wrapper around httpx for a single service."""

    service_name: str = "service"

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout, headers=headers)
        self._base_headers = dict(headers or {})

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _request(self, method: str, path: str, *, json: Any | None = None, headers: Mapping[str, str] | None = None) -> Any:
        merged_headers = dict(self._base_headers)
        if headers:
            merged_headers.update(headers)
        response = self._client.request(method, path, json=json, headers=merged_headers or None)
        if response.is_success:
            if response.content:
                return response.json()
            return None

        raise KnowledgeClientResponseError(
            service=self.service_name,
            method=method,
            url=str(response.request.url),
            status_code=response.status_code,
            body=response.text,
        )


class KnowledgeApiClient(_HttpServiceClient):
    """Client for the knowledge-api artifact surface."""

    service_name = "knowledge-api"

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        actor_id: str | None = None,
        actor_groups: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        request_headers = dict(headers or {})
        if actor_id:
            request_headers["x-actor-id"] = actor_id
        if actor_groups:
            request_headers["x-actor-groups"] = ",".join(actor_groups)
        super().__init__(base_url=base_url, client=client, timeout=timeout, headers=request_headers)

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        status: str | None = None,
        visibility: str | None = None,
        scope_id: str | None = None,
        repo_id: str | None = None,
        work_item_id: str | None = None,
    ) -> list[ArtifactListItem]:
        params = {
            key: value
            for key, value in {
                "artifact_type": artifact_type,
                "status": status,
                "visibility": visibility,
                "scope_id": scope_id,
                "repo_id": repo_id,
                "work_item_id": work_item_id,
            }.items()
            if value is not None
        }
        path = "/api/v1/artifacts"
        if params:
            path = f"{path}?{urlencode(params)}"
        payload = self._request("GET", path)
        return [ArtifactListItem.model_validate(item) for item in payload or []]

    def get_artifact(self, artifact_id: str) -> ArtifactEnvelope:
        payload = self._request("GET", f"/api/v1/artifacts/{artifact_id}")
        return ArtifactEnvelope.model_validate(payload)

    def get_artifact_body(self, artifact_id: str) -> ArtifactBodyResponse:
        payload = self._request("GET", f"/api/v1/artifacts/{artifact_id}/body")
        return ArtifactBodyResponse.model_validate(payload)

    def get_artifact_version_body(
        self,
        artifact_id: str,
        version_id: str,
    ) -> ArtifactBodyResponse:
        payload = self._request(
            "GET",
            f"/api/v1/artifacts/{artifact_id}/versions/{version_id}/body",
        )
        return ArtifactBodyResponse.model_validate(payload)

    def create_artifact(self, request: CreateArtifactRequest) -> ArtifactEnvelope:
        payload = self._request(
            "POST",
            "/api/v1/artifacts",
            json=request.model_dump(mode="json"),
        )
        return ArtifactEnvelope.model_validate(payload)

    def list_runs(
        self,
        *,
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
        params = {
            key: value
            for key, value in {
                "stage": stage,
                "status": status,
                "dispatch_status": dispatch_status,
                "launch_mode": launch_mode,
                "orchestration_runtime": orchestration_runtime,
                "task_queue": task_queue,
                "work_item_id": work_item_id,
                "source_conversation_id": source_conversation_id,
                "scope_artifact_id": scope_artifact_id,
                "execution_packet_artifact_id": execution_packet_artifact_id,
            }.items()
            if value is not None
        }
        path = "/api/v1/runs"
        if params:
            path = f"{path}?{urlencode(params)}"
        payload = self._request("GET", path)
        return [RunResponse.model_validate(item) for item in payload or []]

    def get_run(self, run_id: str) -> RunResponse:
        payload = self._request("GET", f"/api/v1/runs/{run_id}")
        return RunResponse.model_validate(payload)

    def list_run_summaries(
        self,
        *,
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
        params = {
            key: value
            for key, value in {
                "stage": stage,
                "status": status,
                "dispatch_status": dispatch_status,
                "launch_mode": launch_mode,
                "orchestration_runtime": orchestration_runtime,
                "task_queue": task_queue,
                "work_item_id": work_item_id,
                "source_conversation_id": source_conversation_id,
                "scope_artifact_id": scope_artifact_id,
                "execution_packet_artifact_id": execution_packet_artifact_id,
            }.items()
            if value is not None
        }
        path = "/api/v1/runs/summaries"
        if params:
            path = f"{path}?{urlencode(params)}"
        payload = self._request("GET", path)
        return [RunSummaryResponse.model_validate(item) for item in payload or []]

    def list_recent_scope_launch_summaries(
        self,
        *,
        scope_artifact_id: str | None = None,
        launch_mode: str = "initiative_launch",
        include_terminal: bool = False,
        limit: int = 20,
    ) -> list[RunSummaryResponse]:
        params = {
            "launch_mode": launch_mode,
            "include_terminal": str(include_terminal).lower(),
            "limit": str(limit),
        }
        if scope_artifact_id is not None:
            params["scope_artifact_id"] = scope_artifact_id
        path = f"/api/v1/runs/summaries/recent-scope-launches?{urlencode(params)}"
        payload = self._request("GET", path)
        return [RunSummaryResponse.model_validate(item) for item in payload or []]

    def create_run(self, request: CreateRunRequest) -> RunResponse:
        payload = self._request(
            "POST",
            "/api/v1/runs",
            json=request.model_dump(mode="json"),
        )
        return RunResponse.model_validate(payload)

    def dispatch_run(self, run_id: str, request: DispatchRunRequest) -> RunResponse:
        payload = self._request(
            "POST",
            f"/api/v1/runs/{run_id}/dispatch",
            json=request.model_dump(mode="json"),
        )
        return RunResponse.model_validate(payload)

    def transition_run_dispatch(
        self,
        run_id: str,
        request: TransitionRunDispatchRequest,
    ) -> RunResponse:
        payload = self._request(
            "POST",
            f"/api/v1/runs/{run_id}/dispatch/transition",
            json=request.model_dump(mode="json"),
        )
        return RunResponse.model_validate(payload)

    def advance_run_lifecycle(
        self,
        run_id: str,
        request: AdvanceRunLifecycleRequest,
    ) -> RunResponse:
        payload = self._request(
            "POST",
            f"/api/v1/runs/{run_id}/dispatch/lifecycle",
            json=request.model_dump(mode="json"),
        )
        return RunResponse.model_validate(payload)

    def create_run_event(self, run_id: str, request: CreateRunEventRequest) -> None:
        self._request(
            "POST",
            f"/api/v1/runs/{run_id}/events",
            json=request.model_dump(mode="json"),
        )

    def list_run_events(
        self,
        run_id: str,
        *,
        event_type_prefix: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[RunEventResponse]:
        params = {"limit": str(limit), "offset": str(offset)}
        if event_type_prefix is not None:
            params["event_type_prefix"] = event_type_prefix
        payload = self._request(
            "GET",
            f"/api/v1/runs/{run_id}/events?{urlencode(params)}",
        )
        return [RunEventResponse.model_validate(item) for item in payload or []]


class MemoryAdapterClient(_HttpServiceClient):
    """Client for the memory-adapter search surface."""

    service_name = "memory-adapter"

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        actor_id: str | None = None,
        actor_groups: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        request_headers = dict(headers or {})
        if actor_id:
            request_headers["x-actor-id"] = actor_id
        if actor_groups:
            request_headers["x-actor-groups"] = ",".join(actor_groups)
        super().__init__(base_url=base_url, client=client, timeout=timeout, headers=request_headers)

    def search(self, request: MemorySearchRequest) -> MemorySearchResponse:
        payload = self._request("POST", "/memory/search", json=request.model_dump(mode="json"))
        return MemorySearchResponse.model_validate(payload)


class KnowledgeWorkerClient(_HttpServiceClient):
    """Client for the knowledge-worker job surface."""

    service_name = "knowledge-worker"

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        actor_id: str | None = None,
        actor_groups: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        request_headers = dict(headers or {})
        if actor_id:
            request_headers["x-actor-id"] = actor_id
        if actor_groups:
            request_headers["x-actor-groups"] = ",".join(actor_groups)
        super().__init__(base_url=base_url, client=client, timeout=timeout, headers=request_headers)

    def project_memory(self, request: MemoryProjectionRequest) -> MemoryProjectionResult:
        payload = self._request(
            "POST",
            "/jobs/project-memory",
            json=request.model_dump(mode="json"),
        )
        return MemoryProjectionResult.model_validate(payload)

    def capture_memory(self, request: MemoryCaptureRequest) -> MemoryCaptureResult:
        payload = self._request(
            "POST",
            "/jobs/capture-memory",
            json=request.model_dump(mode="json"),
        )
        return MemoryCaptureResult.model_validate(payload)

    def ingest_repo_comprehension(
        self, request: RepoComprehensionIngestRequest
    ) -> RepoComprehensionIngestResult:
        payload = self._request(
            "POST",
            "/jobs/ingest-repo-comprehension",
            json=request.model_dump(mode="json"),
        )
        return RepoComprehensionIngestResult.model_validate(payload)


class VaultSyncClient(_HttpServiceClient):
    """Client for the vault-sync projection surface."""

    service_name = "vault-sync"

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        actor_id: str | None = None,
        actor_groups: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        request_headers = dict(headers or {})
        if actor_id:
            request_headers["x-actor-id"] = actor_id
        if actor_groups:
            request_headers["x-actor-groups"] = ",".join(actor_groups)
        super().__init__(base_url=base_url, client=client, timeout=timeout, headers=request_headers)

    def project_artifact(self, request: VaultProjectionRequest) -> VaultProjectionResult:
        payload = self._request(
            "POST",
            "/jobs/project-artifact",
            json=request.model_dump(mode="json"),
        )
        return VaultProjectionResult.model_validate(payload)

    def project_current_truth(
        self,
        request: BatchVaultProjectionRequest,
    ) -> BatchVaultProjectionResult:
        payload = self._request(
            "POST",
            "/jobs/project-current-truth",
            json=request.model_dump(mode="json"),
        )
        return BatchVaultProjectionResult.model_validate(payload)


class CodeGraphAdapterClient(_HttpServiceClient):
    """HTTP client for the optional codegraph-adapter query surface."""

    service_name = "codegraph-adapter"

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        actor_id: str | None = None,
        actor_groups: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        request_headers = dict(headers or {})
        if actor_id:
            request_headers["x-actor-id"] = actor_id
        if actor_groups:
            request_headers["x-actor-groups"] = ",".join(actor_groups)
        super().__init__(base_url=base_url, client=client, timeout=timeout, headers=request_headers)

    def query_codegraph(self, request: CodeGraphQueryRequest) -> CodeGraphQueryResult:
        payload = self._request(
            "POST",
            "/jobs/query-codegraph",
            json=request.model_dump(mode="json", exclude_none=True),
        )
        return CodeGraphQueryResult.model_validate(payload)


class TemporalRuntimeClient(_HttpServiceClient):
    """Client for the Temporal-ready starter surface."""

    service_name = "temporal-runtime"

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        actor_id: str | None = None,
        actor_groups: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        request_headers = dict(headers or {})
        if actor_id:
            request_headers["x-actor-id"] = actor_id
        if actor_groups:
            request_headers["x-actor-groups"] = ",".join(actor_groups)
        super().__init__(base_url=base_url, client=client, timeout=timeout, headers=request_headers)

    def list_start_intents(self, request: WorkflowIntentQuery) -> WorkflowIntentBatch:
        payload = self._request(
            "POST",
            "/starter/intents",
            json=request.model_dump(mode="json"),
        )
        return WorkflowIntentBatch.model_validate(payload)

    def claim_and_start_workflows(self, request: ClaimAndStartRequest) -> ClaimAndStartResponse:
        payload = self._request(
            "POST",
            "/starter/claim-and-start",
            json=request.model_dump(mode="json"),
        )
        return ClaimAndStartResponse.model_validate(payload)

    def launch_delivery_intents(
        self,
        request: DeliveryLaunchRequest,
    ) -> DeliveryLaunchResponse:
        payload = self._request(
            "POST",
            "/starter/delivery-launch",
            json=request.model_dump(mode="json"),
        )
        return DeliveryLaunchResponse.model_validate(payload)

    def launch_from_scope(
        self,
        request: ScopeDeliveryLaunchRequest,
    ) -> ScopeDeliveryLaunchResponse:
        payload = self._request(
            "POST",
            "/starter/launch-from-scope",
            json=request.model_dump(mode="json"),
        )
        return ScopeDeliveryLaunchResponse.model_validate(payload)

    def dogfood_ops_report(
        self,
        *,
        scope_artifact_id: str | None = None,
        include_terminal: bool = False,
        limit: int = 10,
    ) -> DogfoodOpsReportResponse:
        params = {
            "include_terminal": str(include_terminal).lower(),
            "limit": str(limit),
        }
        if scope_artifact_id is not None:
            params["scope_artifact_id"] = scope_artifact_id
        path = f"/starter/ops/dogfood-report?{urlencode(params)}"
        payload = self._request("GET", path)
        return DogfoodOpsReportResponse.model_validate(payload)

    def dogfood_ops_slack_message(
        self,
        *,
        scope_artifact_id: str | None = None,
        include_terminal: bool = False,
        limit: int = 10,
    ) -> DogfoodSlackMessageResponse:
        params = {
            "include_terminal": str(include_terminal).lower(),
            "limit": str(limit),
        }
        if scope_artifact_id is not None:
            params["scope_artifact_id"] = scope_artifact_id
        path = f"/starter/ops/dogfood-report/slack-message?{urlencode(params)}"
        payload = self._request("GET", path)
        return DogfoodSlackMessageResponse.model_validate(payload)

    def dogfood_ops_slack_delivery(
        self,
        request: DogfoodSlackDeliveryRequest,
    ) -> DogfoodSlackDeliveryResponse:
        payload = self._request(
            "POST",
            "/starter/ops/dogfood-report/slack-delivery",
            json=request.model_dump(mode="json"),
        )
        return DogfoodSlackDeliveryResponse.model_validate(payload)

    def dogfood_ops_snapshot(
        self,
        request: DogfoodOpsSnapshotRequest,
    ) -> DogfoodOpsSnapshotResponse:
        payload = self._request(
            "POST",
            "/starter/ops/dogfood-report/snapshot",
            json=request.model_dump(mode="json"),
        )
        return DogfoodOpsSnapshotResponse.model_validate(payload)

    def dogfood_ops_snapshots(
        self,
        *,
        scope_artifact_id: str | None = None,
        limit: int = 10,
    ) -> DogfoodOpsSnapshotListResponse:
        params = {"limit": str(limit)}
        if scope_artifact_id is not None:
            params["scope_artifact_id"] = scope_artifact_id
        path = f"/starter/ops/dogfood-report/snapshots?{urlencode(params)}"
        payload = self._request("GET", path)
        return DogfoodOpsSnapshotListResponse.model_validate(payload)

    def dogfood_run_continuity_report(
        self,
        *,
        scope_artifact_id: str | None = None,
        include_terminal: bool = False,
        limit: int = 20,
    ) -> DogfoodContinuityReportResponse:
        params = {
            "include_terminal": str(include_terminal).lower(),
            "limit": str(limit),
        }
        if scope_artifact_id is not None:
            params["scope_artifact_id"] = scope_artifact_id
        path = f"/starter/ops/dogfood-report/continuity?{urlencode(params)}"
        payload = self._request("GET", path)
        return DogfoodContinuityReportResponse.model_validate(payload)

    def dogfood_mission_control_preset(
        self,
        *,
        scope_artifact_id: str | None = None,
        include_terminal: bool = False,
        limit: int = 10,
    ) -> DogfoodMissionControlPresetResponse:
        params = {
            "include_terminal": str(include_terminal).lower(),
            "limit": str(limit),
        }
        if scope_artifact_id is not None:
            params["scope_artifact_id"] = scope_artifact_id
        path = f"/starter/ops/dogfood-report/mission-control?{urlencode(params)}"
        payload = self._request("GET", path)
        return DogfoodMissionControlPresetResponse.model_validate(payload)

    def dogfood_launch_recovery_report(
        self,
        *,
        scope_artifact_id: str | None = None,
        limit: int = 200,
    ) -> DogfoodLaunchRecoveryReportResponse:
        params = {"limit": str(limit)}
        if scope_artifact_id is not None:
            params["scope_artifact_id"] = scope_artifact_id
        path = f"/starter/ops/dogfood-report/launch-recovery?{urlencode(params)}"
        payload = self._request("GET", path)
        return DogfoodLaunchRecoveryReportResponse.model_validate(payload)

    def dogfood_launch_recovery_remediate(
        self,
        request: DogfoodLaunchRecoveryRemediationRequest,
    ) -> DogfoodLaunchRecoveryRemediationResponse:
        payload = self._request(
            "POST",
            "/starter/ops/dogfood-report/launch-recovery/remediate",
            json=request.model_dump(mode="json"),
        )
        return DogfoodLaunchRecoveryRemediationResponse.model_validate(payload)

    def dogfood_lane_drilldown_preset(
        self,
        *,
        scope_artifact_id: str | None = None,
        include_terminal: bool = False,
        limit: int = 10,
    ) -> DogfoodLaneDrilldownResponse:
        params = {
            "include_terminal": str(include_terminal).lower(),
            "limit": str(limit),
        }
        if scope_artifact_id is not None:
            params["scope_artifact_id"] = scope_artifact_id
        path = f"/starter/ops/dogfood-report/lane-drilldown?{urlencode(params)}"
        payload = self._request("GET", path)
        return DogfoodLaneDrilldownResponse.model_validate(payload)

    def dogfood_ops_snapshot_compare(
        self,
        *,
        scope_artifact_id: str | None = None,
    ) -> DogfoodSnapshotCompareResponse:
        params: dict[str, str] = {}
        if scope_artifact_id is not None:
            params["scope_artifact_id"] = scope_artifact_id
        query = f"?{urlencode(params)}" if params else ""
        payload = self._request(
            "GET",
            f"/starter/ops/dogfood-report/snapshots/compare{query}",
        )
        return DogfoodSnapshotCompareResponse.model_validate(payload)


class JiraBridgeClient(_HttpServiceClient):
    """Client for Jira scaffolding bridge surface."""

    service_name = "jira-bridge"

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        actor_id: str | None = None,
        actor_groups: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        request_headers = dict(headers or {})
        if actor_id:
            request_headers["x-actor-id"] = actor_id
        if actor_groups:
            request_headers["x-actor-groups"] = ",".join(actor_groups)
        super().__init__(base_url=base_url, client=client, timeout=timeout, headers=request_headers)

    def scaffold_from_scope(
        self,
        request: ScopeToJiraScaffoldRequest,
    ) -> ScopeToJiraScaffoldResponse:
        payload = self._request(
            "POST",
            "/jobs/scope-to-jira-scaffold",
            json=request.model_dump(mode="json"),
        )
        return ScopeToJiraScaffoldResponse.model_validate(payload)

    def scaffold_from_scope_with_resolution(
        self,
        request: ScopeToJiraScaffoldResolvedRequest,
    ) -> ScopeToJiraScaffoldResponse:
        payload = self._request(
            "POST",
            "/jobs/scope-to-jira-scaffold/resolve-project",
            json=request.model_dump(mode="json"),
        )
        return ScopeToJiraScaffoldResponse.model_validate(payload)

    def setup_connectivity(
        self,
        request: JiraConnectivitySetupRequest,
    ) -> JiraConnectivitySetupResponse:
        payload = self._request(
            "POST",
            "/setup/connectivity",
            json=request.model_dump(mode="json"),
        )
        return JiraConnectivitySetupResponse.model_validate(payload)

    def oauth_start(
        self,
        request: JiraOAuthStartRequest,
    ) -> JiraOAuthStartResponse:
        payload = self._request(
            "POST",
            "/setup/oauth/start",
            json=request.model_dump(mode="json"),
        )
        return JiraOAuthStartResponse.model_validate(payload)

    def oauth_exchange(
        self,
        request: JiraOAuthExchangeRequest,
    ) -> JiraOAuthExchangeResponse:
        payload = self._request(
            "POST",
            "/setup/oauth/exchange",
            json=request.model_dump(mode="json"),
        )
        return JiraOAuthExchangeResponse.model_validate(payload)

    def oauth_exchange_callback(
        self,
        *,
        code: str,
        state: str,
    ) -> JiraOAuthExchangeResponse:
        payload = self._request(
            "GET",
            f"/setup/oauth/callback?{urlencode({'code': code, 'state': state})}",
        )
        return JiraOAuthExchangeResponse.model_validate(payload)

    def list_connectivity(self) -> JiraConnectivityListResponse:
        payload = self._request("GET", "/setup/connectivity")
        return JiraConnectivityListResponse.model_validate(payload)

    def connectivity_health(self) -> JiraConnectivityHealthResponse:
        payload = self._request("GET", "/setup/connectivity/health")
        return JiraConnectivityHealthResponse.model_validate(payload)

    def prune_connectivity(self) -> JiraConnectivityPruneResponse:
        payload = self._request("POST", "/setup/connectivity/prune")
        return JiraConnectivityPruneResponse.model_validate(payload)

    def provisioning_stats(self) -> JiraProvisioningStatsResponse:
        payload = self._request("GET", "/setup/provisioning-stats")
        return JiraProvisioningStatsResponse.model_validate(payload)

    def refresh_connectivity(self, jira_project_key: str) -> JiraConnectivitySetupResponse:
        payload = self._request("POST", f"/setup/connectivity/{jira_project_key}/refresh")
        return JiraConnectivitySetupResponse.model_validate(payload)

    def resolve_project(
        self,
        request: JiraProjectResolutionRequest,
    ) -> JiraProjectResolutionResponse:
        payload = self._request(
            "POST",
            "/setup/connectivity/resolve-project",
            json=request.model_dump(mode="json"),
        )
        return JiraProjectResolutionResponse.model_validate(payload)

    def generate_task_packets(
        self,
        request: TaskPacketGenerationRequest,
    ) -> TaskPacketGenerationResponse:
        payload = self._request(
            "POST",
            "/jobs/generate-task-packets",
            json=request.model_dump(mode="json"),
        )
        return TaskPacketGenerationResponse.model_validate(payload)

    def build_delivery_run_intents(
        self,
        request: DeliveryRunIntentRequest,
    ) -> DeliveryRunIntentResponse:
        payload = self._request(
            "POST",
            "/jobs/build-delivery-run-intents",
            json=request.model_dump(mode="json"),
        )
        return DeliveryRunIntentResponse.model_validate(payload)


class CanonSystemsClient:
    """Convenience wrapper that bundles the two known internal clients."""

    def __init__(
        self,
        *,
        knowledge_api_url: str,
        memory_adapter_url: str,
        knowledge_worker_url: str | None = None,
        vault_sync_url: str | None = None,
        temporal_runtime_url: str | None = None,
        jira_bridge_url: str | None = None,
        knowledge_client: httpx.Client | None = None,
        memory_client: httpx.Client | None = None,
        worker_client: httpx.Client | None = None,
        vault_client: httpx.Client | None = None,
        temporal_client: httpx.Client | None = None,
        jira_client: httpx.Client | None = None,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        actor_id: str | None = None,
        actor_groups: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self.knowledge_api = KnowledgeApiClient(
            base_url=knowledge_api_url,
            client=knowledge_client,
            timeout=timeout,
            headers=headers,
            actor_id=actor_id,
            actor_groups=actor_groups,
        )
        self.memory_adapter = MemoryAdapterClient(
            base_url=memory_adapter_url,
            client=memory_client,
            timeout=timeout,
            headers=headers,
            actor_id=actor_id,
            actor_groups=actor_groups,
        )
        self.knowledge_worker = (
            KnowledgeWorkerClient(
                base_url=knowledge_worker_url,
                client=worker_client,
                timeout=timeout,
                headers=headers,
                actor_id=actor_id,
                actor_groups=actor_groups,
            )
            if knowledge_worker_url
            else None
        )
        self.vault_sync = (
            VaultSyncClient(
                base_url=vault_sync_url,
                client=vault_client,
                timeout=timeout,
                headers=headers,
                actor_id=actor_id,
                actor_groups=actor_groups,
            )
            if vault_sync_url
            else None
        )
        self.temporal_runtime = (
            TemporalRuntimeClient(
                base_url=temporal_runtime_url,
                client=temporal_client,
                timeout=timeout,
                headers=headers,
                actor_id=actor_id,
                actor_groups=actor_groups,
            )
            if temporal_runtime_url
            else None
        )
        self.jira_bridge = (
            JiraBridgeClient(
                base_url=jira_bridge_url,
                client=jira_client,
                timeout=timeout,
                headers=headers,
                actor_id=actor_id,
                actor_groups=actor_groups,
            )
            if jira_bridge_url
            else None
        )

    def close(self) -> None:
        self.knowledge_api.close()
        if self.memory_adapter is not self.knowledge_api:
            self.memory_adapter.close()
        if self.knowledge_worker and self.knowledge_worker not in {
            self.knowledge_api,
            self.memory_adapter,
        }:
            self.knowledge_worker.close()
        if self.vault_sync and self.vault_sync not in {
            self.knowledge_api,
            self.memory_adapter,
            self.knowledge_worker,
        }:
            self.vault_sync.close()
        if self.temporal_runtime and self.temporal_runtime not in {
            self.knowledge_api,
            self.memory_adapter,
            self.knowledge_worker,
            self.vault_sync,
        }:
            self.temporal_runtime.close()
        if self.jira_bridge and self.jira_bridge not in {
            self.knowledge_api,
            self.memory_adapter,
            self.knowledge_worker,
            self.vault_sync,
            self.temporal_runtime,
        }:
            self.jira_bridge.close()
