from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QueryParam
from ..auth import bearer_auth
from ..config import Settings, get_settings
from ..events import EventEmitter, get_event_emitter, make_graph_event
from ..models import QueryResponse
from ..storage import AxonStore

router = APIRouter(dependencies=[Depends(bearer_auth)])


def _get_store(settings: Settings = Depends(get_settings)) -> AxonStore:
    return AxonStore(
        s3_bucket=settings.s3_bucket,
        meta_table_name=settings.meta_table_name,
        region=settings.aws_region,
    )


@router.get(
    "/axon/{company_id}/{repository_id}/query",
    response_model=QueryResponse,
)
def get_query(
    company_id: str,
    repository_id: str,
    commit_sha: str,
    q: str = "",
    limit: int = QueryParam(default=50, ge=1, le=5000),
    store: AxonStore = Depends(_get_store),
    emit: EventEmitter = Depends(get_event_emitter),
) -> QueryResponse:
    if not commit_sha:
        raise HTTPException(status_code=422, detail="commit_sha required")
    meta = store.get_snapshot_meta(
        company_id=company_id, repository_id=repository_id, commit_sha=commit_sha
    )
    if meta is None:
        emit(
            make_graph_event(
                event_type="retrieval.graph.query",
                company_id=company_id,
                repository_id=repository_id,
                payload={"commit_sha": commit_sha, "q": q, "limit": limit, "match_count": 0},
            )
        )
        return QueryResponse(
            nodes=[],
            edges=[],
            scores=[],
            source_spans=[],
            commit_sha=commit_sha,
            query=q,
        )
    key = meta.get("snapshot_key")
    if not key or not isinstance(key, str):
        emit(
            make_graph_event(
                event_type="retrieval.graph.query",
                company_id=company_id,
                repository_id=repository_id,
                payload={"commit_sha": commit_sha, "q": q, "limit": limit, "match_count": 0},
            )
        )
        return QueryResponse(
            nodes=[],
            edges=[],
            scores=[],
            source_spans=[],
            commit_sha=commit_sha,
            query=q,
        )
    payload = store.get_snapshot_payload(key)
    if not payload:
        emit(
            make_graph_event(
                event_type="retrieval.graph.query",
                company_id=company_id,
                repository_id=repository_id,
                payload={"commit_sha": commit_sha, "q": q, "limit": limit, "match_count": 0},
            )
        )
        return QueryResponse(
            nodes=[],
            edges=[],
            scores=[],
            source_spans=[],
            commit_sha=commit_sha,
            query=q,
        )
    nodes: list[dict] = list(payload.get("nodes") or [])
    edges: list[dict] = list(payload.get("edges") or [])
    if q:
        ql = q.lower()
        nodes = [n for n in nodes if ql in json.dumps(n, default=str).lower()][:limit]
    else:
        nodes = nodes[:limit]
    scores = [1.0] * len(nodes)
    emit(
        make_graph_event(
            event_type="retrieval.graph.query",
            company_id=company_id,
            repository_id=repository_id,
            payload={
                "commit_sha": commit_sha,
                "q": q,
                "limit": limit,
                "match_count": len(nodes),
            },
        )
    )
    return QueryResponse(
        nodes=nodes,
        edges=edges,
        scores=scores,
        source_spans=[],
        commit_sha=commit_sha,
        query=q,
    )
