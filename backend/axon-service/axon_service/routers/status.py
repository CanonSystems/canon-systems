from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..auth import bearer_auth
from ..config import Settings, get_settings
from ..storage import AxonStore

router = APIRouter(dependencies=[Depends(bearer_auth)])


def _get_store(settings: Settings = Depends(get_settings)) -> AxonStore:
    return AxonStore(s3_bucket=settings.s3_bucket, meta_table_name=settings.meta_table_name, region=settings.aws_region)


@router.get("/axon/{company_id}/{repository_id}/reindex-status")
def reindex_status(
    company_id: str,
    repository_id: str,
    commit_sha: str = Query(..., min_length=1),
    store: AxonStore = Depends(_get_store),
) -> dict:
    try:
        meta = store.get_snapshot_meta(company_id=company_id, repository_id=repository_id, commit_sha=commit_sha)
    except Exception:
        return {
            "company_id": company_id,
            "repository_id": repository_id,
            "commit_sha": commit_sha,
            "status": "error",
            "uploaded_at": None,
            "node_count": 0,
            "edge_count": 0,
            "size_bytes": 0,
        }
    if meta is None:
        return {
            "company_id": company_id,
            "repository_id": repository_id,
            "commit_sha": commit_sha,
            "status": "missing",
            "uploaded_at": None,
            "node_count": 0,
            "edge_count": 0,
            "size_bytes": 0,
        }
    return {
        "company_id": company_id,
        "repository_id": repository_id,
        "commit_sha": commit_sha,
        "status": "ready",
        "uploaded_at": meta.get("uploaded_at"),
        "node_count": int(meta.get("node_count", 0)),
        "edge_count": int(meta.get("edge_count", 0)),
        "size_bytes": int(meta.get("size_bytes", 0)),
    }
