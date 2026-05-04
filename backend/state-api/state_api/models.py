"""Pydantic models for checkpoints, leases, and errors."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- Keys & scope ---


class ScopeIds(BaseModel):
    company_id: str
    repository_id: str
    plan_id: str
    task_id: str
    workstream_id: str


# --- §B checkpoint (REST / nested lease) ---


class LeaseInfo(BaseModel):
    """Nested lease object in GET/PUT responses (no token)."""

    owner_agent_run_id: str
    owner_actor_id: str
    acquired_at: int
    expires_at: int


class CheckpointBody(BaseModel):
    """Checkpoint JSON aligned with backlog §B (lease nested when returned over REST)."""

    schema_version: int = 1
    company_id: str
    repository_id: str
    plan_id: str
    task_id: str
    workstream_id: str
    handoff_id: str
    phase: str
    phase_status: str
    state_version: int
    lease: LeaseInfo | None = None
    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    decisions: list[dict[str, Any]] | None = None
    open_questions: list[str] | None = None
    last_event_id: str = ""
    updated_at: str


class CheckpointPutRequest(BaseModel):
    """PUT body: §B fields plus optimistic version and lease proof."""

    company_id: str
    repository_id: str
    plan_id: str
    task_id: str
    workstream_id: str
    handoff_id: str
    phase: str
    phase_status: str
    state_version: int = Field(description="Expected current state_version (optimistic lock).")
    lease_token: str
    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    decisions: list[dict[str, Any]] | None = None
    open_questions: list[str] | None = None
    last_event_id: str | None = None


# --- Lease acquire / renew / release ---


class LeaseAcquireRequest(BaseModel):
    company_id: str
    repository_id: str
    plan_id: str
    task_id: str
    workstream_id: str
    owner_agent_run_id: str
    owner_actor_id: str
    ttl_seconds: int

    @field_validator("ttl_seconds")
    @classmethod
    def _ttl_bounds(cls, v: int) -> int:
        if not 1 <= v <= 3600:
            raise ValueError("ttl_seconds must be between 1 and 3600 inclusive")
        return v


class LeaseAcquireResponse(BaseModel):
    lease_token: str
    expires_at: int
    acquired_at: int
    owner_agent_run_id: str
    owner_actor_id: str


class LeaseRenewRequest(BaseModel):
    scope_ids: ScopeIds
    lease_token: str
    ttl_seconds: int

    @field_validator("ttl_seconds")
    @classmethod
    def _ttl_bounds(cls, v: int) -> int:
        if not 1 <= v <= 3600:
            raise ValueError("ttl_seconds must be between 1 and 3600 inclusive")
        return v


class LeaseRenewResponse(BaseModel):
    lease_token: str
    expires_at: int


class LeaseReleaseRequest(BaseModel):
    scope_ids: ScopeIds
    lease_token: str


class LeaseReleaseResponse(BaseModel):
    released: bool


# --- Error envelopes ---


class NotFoundError(BaseModel):
    error: str = "not_found"
    pk: str
    sk: str


class ConflictError(BaseModel):
    error: str
    expected: int | None = None
    actual: int | None = None
    owner_agent_run_id: str | None = None
    expires_at: int | None = None


# --- Flat <-> nested lease (DynamoDB stores flat attrs) ---

LEASE_ATTR_TOKEN = "lease_token"
LEASE_ATTR_OWNER_RUN = "lease_owner_agent_run_id"
LEASE_ATTR_OWNER_ACTOR = "lease_owner_actor_id"
LEASE_ATTR_ACQUIRED = "lease_acquired_at"
LEASE_ATTR_EXPIRES = "lease_expires_at"


def item_has_live_lease(item: dict[str, Any], now_epoch: int) -> bool:
    exp = item.get(LEASE_ATTR_EXPIRES)
    if exp is None:
        return False
    try:
        exp_i = int(exp)
    except (TypeError, ValueError):
        return False
    return exp_i > now_epoch and bool(item.get(LEASE_ATTR_TOKEN))


def lease_from_item(item: dict[str, Any]) -> LeaseInfo | None:
    """Build nested lease for REST from flat DynamoDB attributes."""
    if not item.get(LEASE_ATTR_TOKEN):
        return None
    try:
        return LeaseInfo(
            owner_agent_run_id=str(item.get(LEASE_ATTR_OWNER_RUN, "")),
            owner_actor_id=str(item.get(LEASE_ATTR_OWNER_ACTOR, "")),
            acquired_at=int(item[LEASE_ATTR_ACQUIRED]),
            expires_at=int(item[LEASE_ATTR_EXPIRES]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def flatten_lease_for_write(
    token: str,
    owner_agent_run_id: str,
    owner_actor_id: str,
    acquired_at: int,
    expires_at: int,
) -> dict[str, Any]:
    return {
        LEASE_ATTR_TOKEN: token,
        LEASE_ATTR_OWNER_RUN: owner_agent_run_id,
        LEASE_ATTR_OWNER_ACTOR: owner_actor_id,
        LEASE_ATTR_ACQUIRED: acquired_at,
        LEASE_ATTR_EXPIRES: expires_at,
    }


def checkpoint_from_item(item: dict[str, Any]) -> CheckpointBody:
    """Map raw DynamoDB item to §B checkpoint (nested lease, no token in lease block)."""
    lease = lease_from_item(item)
    return CheckpointBody(
        schema_version=int(item.get("schema_version", 1)),
        company_id=str(item["company_id"]),
        repository_id=str(item["repository_id"]),
        plan_id=str(item["plan_id"]),
        task_id=str(item["task_id"]),
        workstream_id=str(item["workstream_id"]),
        handoff_id=str(item.get("handoff_id", "")),
        phase=str(item.get("phase", "")),
        phase_status=str(item.get("phase_status", "")),
        state_version=int(item.get("state_version", 0)),
        lease=lease,
        inputs=item.get("inputs") if isinstance(item.get("inputs"), dict) else None,
        outputs=item.get("outputs") if isinstance(item.get("outputs"), dict) else None,
        decisions=item.get("decisions") if isinstance(item.get("decisions"), list) else None,
        open_questions=item.get("open_questions")
        if isinstance(item.get("open_questions"), list)
        else None,
        last_event_id=str(item.get("last_event_id", "")),
        updated_at=str(item.get("updated_at", "")),
    )


def pk_sk(scope: ScopeIds) -> tuple[str, str]:
    pk = f"{scope.company_id}#{scope.repository_id}"
    sk = f"{scope.plan_id}#{scope.task_id}#{scope.workstream_id}"
    return pk, sk


def pk_sk_from_parts(
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
) -> tuple[str, str]:
    return pk_sk(
        ScopeIds(
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            task_id=task_id,
            workstream_id=workstream_id,
        )
    )


# --- Packet / evidence archive (S3 historical plane; no DynamoDB run ledger) ---


class ArchiveUploadRequest(BaseModel):
    """Upload metadata + base64 body for ``POST /state/archive``."""

    schema_version: int = 1
    company_id: str
    repository_id: str
    plan_id: str
    task_id: str
    workstream_id: str
    handoff_id: str
    phase: str
    artifact_kind: str
    source_label: str
    content_type: str = "application/octet-stream"
    body_base64: str
    content_sha256: str
    agent_run_id: str = ""
    actor_id: str = ""
    outcome: str = ""
    status: str = ""
    evidence_subtype: str | None = None

    @field_validator("source_label")
    @classmethod
    def _source_label_bounds(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("source_label is required")
        if len(s) > 4096:
            raise ValueError("source_label exceeds 4096 characters")
        if "\x00" in s:
            raise ValueError("source_label contains NUL")
        return s


class ArchiveRecordResponse(BaseModel):
    """Structured archive row returned after a successful S3 write."""

    model_config = ConfigDict(extra="ignore")

    schema_version: int
    company_id: str
    repository_id: str
    plan_id: str
    task_id: str
    workstream_id: str
    handoff_id: str
    phase: str
    artifact_kind: str
    source_label: str
    s3_bucket: str
    s3_key: str
    s3_uri: str
    content_sha256: str
    byte_length: int
    content_type: str
    created_at: str
    agent_run_id: str = ""
    actor_id: str = ""
    outcome: str = ""
    status: str = ""
    evidence_subtype: str | None = None
    s3_version_id: str | None = None
