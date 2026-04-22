"""Lease acquire / renew / release routes."""

from __future__ import annotations

import time
import uuid
from typing import Annotated

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status

from state_api.config import Settings, get_settings
from state_api.models import (
    ConflictError,
    LeaseAcquireRequest,
    LeaseAcquireResponse,
    LeaseReleaseRequest,
    LeaseReleaseResponse,
    LeaseRenewRequest,
    LeaseRenewResponse,
    ScopeIds,
    item_has_live_lease,
    pk_sk,
)
from state_api.storage import StateStore

router = APIRouter(prefix="/state/lease", tags=["lease"])


def get_state_store(settings: Annotated[Settings, Depends(get_settings)]) -> StateStore:
    if not settings.state_table_name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="state_table_name_unset",
        )
    return StateStore(settings.state_table_name, settings.aws_region)


def _now() -> int:
    return int(time.time())


@router.post("/acquire", response_model=LeaseAcquireResponse)
def lease_acquire(
    body: LeaseAcquireRequest,
    store: Annotated[StateStore, Depends(get_state_store)],
) -> LeaseAcquireResponse:
    scope = ScopeIds(
        company_id=body.company_id,
        repository_id=body.repository_id,
        plan_id=body.plan_id,
        task_id=body.task_id,
        workstream_id=body.workstream_id,
    )
    pk, sk = pk_sk(scope)
    now = _now()
    expires_at = now + body.ttl_seconds
    item = store.get_item(pk, sk)

    if item is not None and item_has_live_lease(item, now):
        owner = str(item.get("lease_owner_agent_run_id", ""))
        if owner != body.owner_agent_run_id:
            exp = int(item["lease_expires_at"])
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ConflictError(
                    error="lease_held",
                    owner_agent_run_id=owner,
                    expires_at=exp,
                ).model_dump(),
            )
        # Same owner: extend lease, keep token
        token = str(item["lease_token"])
        try:
            store.acquire_lease(
                pk,
                sk,
                token=token,
                owner_agent_run_id=body.owner_agent_run_id,
                owner_actor_id=body.owner_actor_id,
                acquired_at=int(item["lease_acquired_at"]),
                expires_at=expires_at,
                now_epoch=now,
                base_item={},
                extend_same_owner=True,
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ConflictError(error="lease_held").model_dump(),
            ) from e
        return LeaseAcquireResponse(
            lease_token=token,
            expires_at=expires_at,
            acquired_at=int(item["lease_acquired_at"]),
            owner_agent_run_id=body.owner_agent_run_id,
            owner_actor_id=body.owner_actor_id,
        )

    token = str(uuid.uuid4())
    base_item = {
        "company_id": body.company_id,
        "repository_id": body.repository_id,
        "plan_id": body.plan_id,
        "task_id": body.task_id,
        "workstream_id": body.workstream_id,
    }
    try:
        store.acquire_lease(
            pk,
            sk,
            token=token,
            owner_agent_run_id=body.owner_agent_run_id,
            owner_actor_id=body.owner_actor_id,
            acquired_at=now,
            expires_at=expires_at,
            now_epoch=now,
            base_item=base_item,
            extend_same_owner=False,
        )
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        # Race: another holder claimed a live lease
        fresh = store.get_item(pk, sk)
        if fresh and item_has_live_lease(fresh, _now()):
            owner = str(fresh.get("lease_owner_agent_run_id", ""))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ConflictError(
                    error="lease_held",
                    owner_agent_run_id=owner,
                    expires_at=int(fresh["lease_expires_at"]),
                ).model_dump(),
            ) from e
        raise

    return LeaseAcquireResponse(
        lease_token=token,
        expires_at=expires_at,
        acquired_at=now,
        owner_agent_run_id=body.owner_agent_run_id,
        owner_actor_id=body.owner_actor_id,
    )


@router.post("/renew", response_model=LeaseRenewResponse)
def lease_renew(
    body: LeaseRenewRequest,
    store: Annotated[StateStore, Depends(get_state_store)],
) -> LeaseRenewResponse:
    pk, sk = pk_sk(body.scope_ids)
    now = _now()
    new_exp = now + body.ttl_seconds
    try:
        store.renew_lease(
            pk,
            sk,
            lease_token=body.lease_token,
            expires_at=new_exp,
            now_epoch=now,
        )
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        item = store.get_item(pk, sk)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ConflictError(error="lease_expired").model_dump(),
            ) from e
        db_tok = item.get("lease_token")
        if db_tok is None or str(db_tok) != body.lease_token:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ConflictError(error="lease_token_mismatch").model_dump(),
            ) from e
        try:
            exp_i = int(item["lease_expires_at"])
        except (KeyError, TypeError, ValueError):
            exp_i = 0
        if exp_i <= now:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ConflictError(error="lease_expired").model_dump(),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictError(error="lease_token_mismatch").model_dump(),
        ) from e

    return LeaseRenewResponse(lease_token=body.lease_token, expires_at=new_exp)


@router.post("/release", response_model=LeaseReleaseResponse)
def lease_release(
    body: LeaseReleaseRequest,
    store: Annotated[StateStore, Depends(get_state_store)],
) -> LeaseReleaseResponse:
    """Release does not emit canonical events in v1."""
    pk, sk = pk_sk(body.scope_ids)
    ok = store.release_lease(pk, sk, lease_token=body.lease_token)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictError(error="lease_token_mismatch").model_dump(),
        )
    return LeaseReleaseResponse(released=True)
