"""Run ledger REST surface: durable rows separate from checkpoint/lease items.

Readiness and other callers must use ``GET /state/run-ledger`` as the only
ledger read path supported for diagnosis. That handler is read-only: it must
never perform DynamoDB writes or touch checkpoint lease rows, packet-archive
writes, or S3 objects. Ledger inserts remain ``PUT``-only on this router.
"""

from __future__ import annotations

from typing import Annotated, Any, Protocol, runtime_checkable

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status

from canon_backend_shared.run_ledger import (
    RunLedgerValidationError,
    build_run_ledger_pk,
    build_run_ledger_sk,
    ledger_keys_for_record,
    sanitize_ledger_segment,
    validate_run_ledger_record,
)

from state_api.config import Settings, get_settings
from state_api.models import ConflictError, NotFoundError
from state_api.storage import RunLedgerStore, ledger_record_from_item, run_ledger_items_equivalent

router = APIRouter(prefix="/state/run-ledger", tags=["run-ledger"])


@runtime_checkable
class RunLedgerReadAccessor(Protocol):
    """Narrow surface used by GET handlers — reads only (no puts / mutations)."""

    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None: ...

    def query_sk_prefix(self, pk: str, sk_prefix: str, *, limit: int) -> list[dict[str, Any]]: ...


def get_run_ledger_store(settings: Annotated[Settings, Depends(get_settings)]) -> RunLedgerStore:
    if not settings.state_run_ledger_table_name.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "run_ledger_table_unset",
                "message": "STATE_RUN_LEDGER_TABLE_NAME is required for run-ledger routes",
            },
        )
    return RunLedgerStore(settings.state_run_ledger_table_name.strip(), settings.aws_region)


def _item_for_write(record: dict[str, Any]) -> dict[str, Any]:
    pk, sk = ledger_keys_for_record(record)
    item = dict(record)
    item["pk"] = pk
    item["sk"] = sk
    return item


@router.put("", response_model=None)
def put_run_ledger(
    body: dict[str, Any],
    store: Annotated[RunLedgerStore, Depends(get_run_ledger_store)],
) -> dict[str, Any]:
    try:
        record = validate_run_ledger_record(body)
    except RunLedgerValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "run_ledger_validation_error", "message": str(e)},
        ) from e

    item = _item_for_write(record)
    try:
        store.put_if_absent(item)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        pk, sk = item["pk"], item["sk"]
        existing = store.get_item(pk, sk)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "run_ledger_race", "message": "conditional failed but item missing"},
            ) from e
        if run_ledger_items_equivalent(existing, item):
            return ledger_record_from_item(existing)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictError(error="run_ledger_id_conflict").model_dump(),
        ) from e

    return ledger_record_from_item(item)


@router.get("", response_model=None)
def get_run_ledger(
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    store: Annotated[RunLedgerReadAccessor, Depends(get_run_ledger_store)],
    ledger_run_id: str | None = None,
    handoff_id: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_limit", "message": "limit must be between 1 and 200"},
        )
    try:
        pk = build_run_ledger_pk(company_id=company_id, repository_id=repository_id)
    except RunLedgerValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "run_ledger_validation_error", "message": str(e)},
        ) from e

    if ledger_run_id:
        try:
            sk = build_run_ledger_sk(
                plan_id=plan_id,
                task_id=task_id,
                workstream_id=workstream_id,
                ledger_run_id=ledger_run_id,
            )
        except RunLedgerValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "run_ledger_validation_error", "message": str(e)},
            ) from e
        row = store.get_item(pk, sk)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=NotFoundError(pk=pk, sk=sk).model_dump(),
            )
        rec = ledger_record_from_item(row)
        if handoff_id and rec.get("handoff_id") != handoff_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=NotFoundError(pk=pk, sk=sk).model_dump(),
            )
        return {"ledger_run_id": ledger_run_id, "record": rec}

    try:
        p = sanitize_ledger_segment(plan_id, label="plan_id")
        t = sanitize_ledger_segment(task_id, label="task_id")
        w = sanitize_ledger_segment(workstream_id, label="workstream_id")
    except RunLedgerValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "run_ledger_validation_error", "message": str(e)},
        ) from e
    sk_prefix = f"{p}#{t}#{w}#"

    rows = store.query_sk_prefix(pk, sk_prefix, limit=limit)
    records: list[dict[str, Any]] = []
    for row in rows:
        rec = ledger_record_from_item(row)
        if handoff_id is not None and rec.get("handoff_id") != handoff_id:
            continue
        records.append(rec)
    return {"items": records, "count": len(records)}

