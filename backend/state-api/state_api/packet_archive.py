"""POST /state/archive — durable S3 packet/evidence bodies (no DynamoDB run ledger)."""

from __future__ import annotations

import base64
import binascii
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Response, status

from canon_backend_shared.events import CanonicalEvent
from canon_backend_shared.packet_archive import (
    ArchiveValidationError,
    build_archive_object_key,
    build_archive_record_payload,
    normalize_archive_prefix,
    normalize_sha256_hex,
    packet_archived_event_payload,
    sha256_hex_digest,
    validate_artifact_kind,
)

from state_api.config import Settings, get_settings
from state_api.events import EventEmitter, get_event_emitter
from state_api.models import ArchiveRecordResponse, ArchiveUploadRequest

router = APIRouter(prefix="/state/archive", tags=["archive"])


def _rfc3339z_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_s3_client(settings: Annotated[Settings, Depends(get_settings)]) -> Any:
    return boto3.client("s3", region_name=settings.aws_region)


def _decode_body(body_b64: str) -> bytes:
    try:
        return base64.b64decode(body_b64, validate=True)
    except binascii.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "archive_body_decode_failed", "message": str(e)},
        ) from e


@router.post("", response_model=ArchiveRecordResponse)
def post_archive(
    body: ArchiveUploadRequest,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    s3: Annotated[Any, Depends(get_s3_client)],
    emit: Annotated[EventEmitter, Depends(get_event_emitter)],
) -> ArchiveRecordResponse:
    bucket = settings.state_artifact_bucket.strip()
    if not bucket:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "artifact_bucket_unset",
                "message": "STATE_ARTIFACT_BUCKET is required for archive uploads",
            },
        )

    raw = _decode_body(body.body_base64)
    digest = sha256_hex_digest(raw)
    try:
        declared = normalize_sha256_hex(body.content_sha256)
    except ArchiveValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "archive_validation_error", "message": str(e)},
        ) from e

    if digest != declared:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "archive_sha256_mismatch",
                "expected": declared,
                "actual": digest,
            },
        )

    try:
        validate_artifact_kind(body.artifact_kind, evidence_subtype=body.evidence_subtype)
        prefix = normalize_archive_prefix(settings.state_archive_key_prefix)
        key = build_archive_object_key(
            prefix=prefix,
            company_id=body.company_id,
            repository_id=body.repository_id,
            plan_id=body.plan_id,
            task_id=body.task_id,
            workstream_id=body.workstream_id,
            handoff_id=body.handoff_id,
            phase=body.phase,
            artifact_kind=body.artifact_kind,
            content_sha256_hex=digest,
            evidence_subtype=body.evidence_subtype,
        )
    except ArchiveValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "archive_validation_error", "message": str(e)},
        ) from e

    created_at = _rfc3339z_now()
    ctype = body.content_type.strip() or "application/octet-stream"

    try:
        s3_resp = s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=raw,
            ContentType=ctype,
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "s3_put_failed",
                "message": str(e),
                "code": e.response.get("Error", {}).get("Code", ""),
            },
        ) from e

    version_id = s3_resp.get("VersionId")
    version_str = str(version_id) if version_id else None

    record = build_archive_record_payload(
        bucket=bucket,
        key=key,
        content_sha256_hex=digest,
        byte_length=len(raw),
        content_type=ctype,
        created_at=created_at,
        company_id=body.company_id,
        repository_id=body.repository_id,
        plan_id=body.plan_id,
        task_id=body.task_id,
        workstream_id=body.workstream_id,
        handoff_id=body.handoff_id,
        phase=body.phase,
        artifact_kind=body.artifact_kind,
        source_label=body.source_label,
        agent_run_id=body.agent_run_id,
        actor_id=body.actor_id,
        outcome=body.outcome,
        status=body.status,
        evidence_subtype=body.evidence_subtype,
        s3_version_id=version_str,
    )

    event_id = str(uuid.uuid4())
    ev_payload = packet_archived_event_payload(record)
    event = CanonicalEvent(
        schema_version=1,
        event_id=event_id,
        parent_event_id="",
        event_type="packet_archived",
        company_id=body.company_id,
        repository_id=body.repository_id,
        plan_id=body.plan_id,
        task_id=body.task_id,
        handoff_id=body.handoff_id,
        agent_name="state-api",
        agent_run_id=body.agent_run_id or "",
        actor_id=body.actor_id or "",
        model="",
        timestamp=created_at,
        state_version=0,
        payload=ev_payload,
    )
    emit(event)
    response.headers["X-Canon-Event-Id"] = event_id

    return ArchiveRecordResponse.model_validate(record)
