"""FastAPI entrypoint (scaffold)."""

from fastapi import FastAPI

app = FastAPI(title="memory-adapter", version="0.0.0-scaffold")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "scaffold", "service": "memory-adapter"}
