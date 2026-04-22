"""FastAPI app entrypoint for knowledge-worker."""

from __future__ import annotations

from fastapi import FastAPI

from .api.router import router

app = FastAPI(title="knowledge-worker", version="0.1.0")
app.include_router(router)

