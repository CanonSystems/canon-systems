from __future__ import annotations
from fastapi import APIRouter, Depends
from ..auth import bearer_auth
from ..config import Settings, get_settings
from ..events import EventEmitter, get_event_emitter, make_graph_event
from ..models import IndexRequest, IndexResponse
from ..storage import AxonStore

router = APIRouter(dependencies=[Depends(bearer_auth)])


def _get_store(settings: Settings = Depends(get_settings)) -> AxonStore:
    return AxonStore(
        s3_bucket=settings.s3_bucket,
        meta_table_name=settings.meta_table_name,
        region=settings.aws_region,
    )


@router.post(
    "/axon/{company_id}/{repository_id}/index",
    response_model=IndexResponse,
)
def post_index(
    company_id: str,
    repository_id: str,
    body: IndexRequest,
    store: AxonStore = Depends(_get_store),
    emit: EventEmitter = Depends(get_event_emitter),
) -> IndexResponse:
    result = store.put_snapshot(
        company_id=company_id,
        repository_id=repository_id,
        commit_sha=body.commit_sha,
        nodes=body.nodes,
        edges=body.edges,
        metadata=body.metadata,
    )
    emit(
        make_graph_event(
            event_type="retrieval.graph.index",
            company_id=company_id,
            repository_id=repository_id,
            payload={
                "commit_sha": body.commit_sha,
                "node_count": result["node_count"],
                "edge_count": result["edge_count"],
            },
        )
    )
    return IndexResponse(
        company_id=company_id,
        repository_id=repository_id,
        commit_sha=body.commit_sha,
        **result,
    )
