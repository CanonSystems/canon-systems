from __future__ import annotations
from fastapi import APIRouter
from .routers import index as index_r
from .routers import impact as impact_r
from .routers import query as query_r

router = APIRouter()
router.include_router(index_r.router)
router.include_router(query_r.router)
router.include_router(impact_r.router)
