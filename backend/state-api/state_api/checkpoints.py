"""Checkpoint read (GET) and conditional write (PUT)."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Response, status

from canon_backend_shared.events import CanonicalEvent

from state_api.events import EventEmitter, get_event_emitter
from state_api.leases import get_state_store
from state_api.models import (
    CheckpointBody,
    CheckpointPutRequest,
    ConflictError,
    NotFoundError,
    checkpoint_from_item,
    pk_sk_from_parts,
)
from state_api.storage import StateStore

router = APIRouter(prefix="/state/checkpoint", tags=["checkpoint"])


def _now_epoch() -> int:
    return int(time.time())


def _rfc3339z_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _classify_put_failure(
    item: dict[str, Any] | None,
    *,
    expected_state_version: int,
    lease_token: str,
    now: int,
) -> tuple[str, int | None]:
    if item is None:
        return ("not_found", None)
    actual_sv = int(item.get("state_version", 0))
    if actual_sv != expected_state_version:
        return ("state_version_conflict", actual_sv)

    db_tok = item.get("lease_token")
    exp_raw = item.get("lease_expires_at")
    try:
        exp_i = int(exp_raw) if exp_raw is not None else 0
    except (TypeError, ValueError):
        exp_i = 0
    live = bool(db_tok) and exp_i > now

    if not live:
        if db_tok is not None and str(db_tok) == lease_token:
            return ("lease_expired", None)
        return ("lease_required", None)
    if str(db_tok) != lease_token:
        return ("lease_token_mismatch", None)
    return ("lease_required", None)


@router.get("", response_model=CheckpointBody)
def get_checkpoint(
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    store: Annotated[StateStore, Depends(get_state_store)],
) -> CheckpointBody:
    pk, sk = pk_sk_from_parts(company_id, repository_id, plan_id, task_id, workstream_id)
    item = store.get_item(pk, sk)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NotFoundError(pk=pk, sk=sk).model_dump(),
        )
    return checkpoint_from_item(item)


@router.put("", response_model=CheckpointBody)
def put_checkpoint(
    body: CheckpointPutRequest,
    response: Response,
    store: Annotated[StateStore, Depends(get_state_store)],
    emit: Annotated[EventEmitter, Depends(get_event_emitter)],
) -> CheckpointBody:
    pk, sk = pk_sk_from_parts(
        body.company_id,
        body.repository_id,
        body.plan_id,
        body.task_id,
        body.workstream_id,
    )
    existing = store.get_item(pk, sk)
    prior_last = str(existing.get("last_event_id", "")) if existing else ""

    now = _now_epoch()
    updated_at = _rfc3339z_now()
    event_id = str(uuid.uuid4())

    optional_sets: dict[str, Any] = {}
    if body.inputs is not None:
        optional_sets["inputs"] = body.inputs
    if body.outputs is not None:
        optional_sets["outputs"] = body.outputs
    if body.decisions is not None:
        optional_sets["decisions"] = body.decisions
    if body.open_questions is not None:
        optional_sets["open_questions"] = body.open_questions

    try:
        attrs = store.put_checkpoint(
            pk,
            sk,
            expected_state_version=body.state_version,
            lease_token=body.lease_token,
            now_epoch=now,
            phase=body.phase,
            phase_status=body.phase_status,
            updated_at=updated_at,
            new_last_event_id=event_id,
            handoff_id=body.handoff_id,
            optional_sets=optional_sets or None,
        )
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        item = store.get_item(pk, sk)
        code, actual_sv = _classify_put_failure(
            item,
            expected_state_version=body.state_version,
            lease_token=body.lease_token,
            now=now,
        )
        if code == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=NotFoundError(pk=pk, sk=sk).model_dump(),
            ) from e
        if code == "state_version_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ConflictError(
                    error=code,
                    expected=body.state_version,
                    actual=actual_sv,
                ).model_dump(),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictError(error=code).model_dump(),
        ) from e

    # Emit after successful write
    item_for_meta = attrs
    agent_run = str(item_for_meta.get("lease_owner_agent_run_id", ""))
    actor = str(item_for_meta.get("lease_owner_actor_id", ""))
    new_sv = int(attrs["state_version"])

    event = CanonicalEvent(
        schema_version=1,
        event_id=event_id,
        parent_event_id=prior_last,
        event_type="checkpoint_write",
        company_id=body.company_id,
        repository_id=body.repository_id,
        plan_id=body.plan_id,
        task_id=body.task_id,
        handoff_id=body.handoff_id,
        agent_name="state-api",
        agent_run_id=agent_run,
        actor_id=actor,
        model="",
        timestamp=updated_at,
        state_version=new_sv,
        payload={
            "phase": body.phase,
            "phase_status": body.phase_status,
            "updated_at": updated_at,
        },
    )
    emit(event)
    response.headers["X-Canon-Event-Id"] = event_id

    return checkpoint_from_item(attrs)
