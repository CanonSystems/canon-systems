from __future__ import annotations
from fastapi import APIRouter, Depends
from ..config import Settings, get_settings
from ..models import HealthResponse
from ..storage import AxonStore

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
def healthz(settings: Settings = Depends(get_settings)) -> HealthResponse:
    try:
        store = AxonStore(
            s3_bucket=settings.s3_bucket,
            meta_table_name=settings.meta_table_name,
            region=settings.aws_region,
        )
        count = store.list_snapshots_count()
        return HealthResponse(status="ok", snapshots=count)
    except Exception:
        return HealthResponse(status="degraded", snapshots=None)
