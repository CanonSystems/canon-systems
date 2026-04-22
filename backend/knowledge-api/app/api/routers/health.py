"""Service health endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Return a simple liveness response."""
    return {"status": "ok"}

