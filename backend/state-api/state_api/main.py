"""FastAPI entrypoint for state-api."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from state_api.checkpoints import router as checkpoint_router
from state_api.config import Settings, get_settings
from state_api.leases import router as lease_router
from state_api.packet_archive import router as archive_router
from state_api.run_ledger import router as run_ledger_router

app = FastAPI(title="state-api", version="1.0.0")
app.include_router(checkpoint_router)
app.include_router(lease_router)
app.include_router(archive_router)
# Run-ledger GET is read-only for readiness queries; ledger rows are written via PUT only.
app.include_router(run_ledger_router)


@app.get("/healthz", response_model=None)
def healthz(settings: Settings = Depends(get_settings)) -> JSONResponse | dict[str, str]:
    if not settings.state_table_name:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "reason": "state_table_name_unset",
            },
        )
    return {
        "status": "ok",
        "service": "state-api",
        "table": settings.state_table_name,
    }
