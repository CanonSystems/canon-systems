from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QueryParam
from ..auth import bearer_auth
from ..config import Settings, get_settings
from ..events import EventEmitter, get_event_emitter, make_graph_event
from ..models import ImpactResponse
from ..storage import AxonStore

router = APIRouter(dependencies=[Depends(bearer_auth)])


def _get_store(settings: Settings = Depends(get_settings)) -> AxonStore:
    return AxonStore(
        s3_bucket=settings.s3_bucket,
        meta_table_name=settings.meta_table_name,
        region=settings.aws_region,
    )


@router.get(
    "/axon/{company_id}/{repository_id}/impact",
    response_model=ImpactResponse,
)
def get_impact(
    company_id: str,
    repository_id: str,
    symbol: str,
    commit_sha: str,
    depth: int = QueryParam(default=1, ge=0, le=32),
    store: AxonStore = Depends(_get_store),
    emit: EventEmitter = Depends(get_event_emitter),
) -> ImpactResponse:
    if not commit_sha or not symbol:
        raise HTTPException(status_code=422, detail="commit_sha and symbol required")
    meta = store.get_snapshot_meta(
        company_id=company_id, repository_id=repository_id, commit_sha=commit_sha
    )
    if meta is None:
        emit(
            make_graph_event(
                event_type="retrieval.graph.impact",
                company_id=company_id,
                repository_id=repository_id,
                payload={
                    "commit_sha": commit_sha,
                    "symbol": symbol,
                    "depth": depth,
                    "found": False,
                },
            )
        )
        return ImpactResponse(
            symbol=symbol,
            commit_sha=commit_sha,
            depth=depth,
            upstream=[],
            downstream=[],
        )
    key = meta.get("snapshot_key")
    payload = store.get_snapshot_payload(key) if key else None
    if not payload:
        emit(
            make_graph_event(
                event_type="retrieval.graph.impact",
                company_id=company_id,
                repository_id=repository_id,
                payload={
                    "commit_sha": commit_sha,
                    "symbol": symbol,
                    "depth": depth,
                    "found": False,
                },
            )
        )
        return ImpactResponse(
            symbol=symbol,
            commit_sha=commit_sha,
            depth=depth,
            upstream=[],
            downstream=[],
        )
    nodes: list[dict] = list(payload.get("nodes") or [])
    found = any(symbol in json.dumps(n, default=str) for n in nodes)
    emit(
        make_graph_event(
            event_type="retrieval.graph.impact",
            company_id=company_id,
            repository_id=repository_id,
            payload={
                "commit_sha": commit_sha,
                "symbol": symbol,
                "depth": depth,
                "found": found,
            },
        )
    )
    return ImpactResponse(
        symbol=symbol,
        commit_sha=commit_sha,
        depth=depth,
        upstream=[],
        downstream=[],
    )
