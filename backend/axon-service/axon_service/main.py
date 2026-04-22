"""FastAPI entrypoint (scaffold)."""

from fastapi import FastAPI

app = FastAPI(title="axon-service", version="0.0.0-scaffold")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "scaffold", "service": "axon-service"}
