"""Root API router."""

from fastapi import APIRouter

from app.api.routers.artifacts import router as artifacts_router
from app.api.routers.runs import router as runs_router
from app.api.routers.work_items import router as work_items_router

api_router = APIRouter()
api_router.include_router(artifacts_router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(work_items_router, prefix="/work-items", tags=["work-items"])
api_router.include_router(runs_router, prefix="/runs", tags=["runs"])

