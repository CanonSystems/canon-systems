from __future__ import annotations
from fastapi import FastAPI
from .api import router as api_router
from .routers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="axon-service", version="0.0.0")
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
