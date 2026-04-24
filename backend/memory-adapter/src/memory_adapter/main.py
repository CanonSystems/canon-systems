"""FastAPI entrypoint for memory-adapter."""

from __future__ import annotations

from fastapi import FastAPI

from .api.router import health_router, search_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="memory-adapter",
        version="0.1.0",
        description="Permissions-aware memory adapter for Canon Systems v2.",
    )
    app.include_router(health_router)
    app.include_router(search_router)
    return app


app = create_app()
