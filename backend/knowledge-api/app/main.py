"""FastAPI application entrypoint for knowledge-api."""

from app.bootstrap import ensure_workspace_paths

ensure_workspace_paths()

from fastapi import FastAPI

from app.api.router import api_router
from app.api.routers.health import router as health_router
from memory_adapter.api.router import search_router as memory_search_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="knowledge-api",
        version="0.1.0",
        description="Canonical API service for artifacts, work items, and runs.",
    )
    app.include_router(health_router)
    # MemPalace search (memory-adapter) shares the same base URL as knowledge-api when
    # memory-adapter is not deployed as its own ECS service (see infra/terraform README).
    app.include_router(memory_search_router)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
