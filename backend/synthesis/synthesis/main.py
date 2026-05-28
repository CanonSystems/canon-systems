"""FastAPI entrypoint: healthz + /synth/vault/changes + /synth/show."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import Response

from synthesis.generator import (
    generate_vault,
    primary_vault_key,
)
from synthesis.sources import EventSource, InMemoryEventSource

app = FastAPI(title="synthesis", version="0.1.0")

MAX_CUTOFF = "9999-12-31T23:59:59Z"
MIN_SINCE = "0001-01-01T00:00:00Z"


def get_event_source() -> EventSource:
    return InMemoryEventSource(events=[])


def _env_company() -> str:
    return os.environ.get("SYNTHESIS_COMPANY_ID", "MJC")


def _env_repository() -> str:
    return os.environ.get("SYNTHESIS_REPOSITORY_ID", "marrow")


def _parse_iso8601(value: str) -> str:
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def _resolve_company_repo(
    evs: list[Any], fallback_company: str, fallback_repo: str
) -> tuple[str, str]:
    if not evs:
        return fallback_company, fallback_repo
    return evs[0].company_id, evs[0].repository_id


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "synthesis"}


@app.get("/synth/vault/changes")
def synth_vault_changes(
    since: str = Query(...),
    source: EventSource = Depends(get_event_source),
) -> dict[str, Any]:
    try:
        cutoff_lower = _parse_iso8601(since)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"invalid since: {exc}"
        ) from exc
    evs = list(
        source.iter_events(
            plan_id=None, task_id=None, cutoff_timestamp=cutoff_lower
        )
    )
    comp, rep = _resolve_company_repo(
        evs, _env_company(), _env_repository()
    )
    as_of: str
    if evs:
        as_of = max((e.timestamp for e in evs), default=since)
    else:
        as_of = MAX_CUTOFF
    _ = generate_vault(
        evs,
        company_id=comp,
        repository_id=rep,
        cutoff_timestamp=as_of,
    )
    out: list[dict[str, str]] = []
    for e in sorted(evs, key=lambda x: (x.timestamp, x.event_id)):
        out.append(
            {
                "vault_key": primary_vault_key(e),
                "event_id": e.event_id,
                "timestamp": e.timestamp,
            }
        )
    return {
        "since": since,
        "schema_version": 1,
        "changes": out,
        "count": len(out),
    }


@app.get("/synth/show")
def synth_show(
    plan_id: str = Query(...),
    task_id: str | None = Query(default=None),
    format: str = Query(
        default="json",
        pattern="^(json|markdown)$",
    ),
    source: EventSource = Depends(get_event_source),
) -> Any:
    evs = list(
        source.iter_events(
            plan_id=plan_id,
            task_id=task_id,
            cutoff_timestamp=MIN_SINCE,
        )
    )
    if not evs:
        raise HTTPException(status_code=404, detail="no events for scope")
    comp, rep = _resolve_company_repo(
        evs, _env_company(), _env_repository()
    )
    as_of = max((e.timestamp for e in evs), default=MAX_CUTOFF)
    bundle = generate_vault(
        evs,
        company_id=comp,
        repository_id=rep,
        cutoff_timestamp=as_of,
    )
    if task_id is None:
        vkey = f"plans/{plan_id}/index.md"
    else:
        vkey = f"plans/{plan_id}/tasks/{task_id}/index.md"
    if vkey not in bundle.pages:
        raise HTTPException(status_code=404, detail="page not in vault")
    body = bundle.pages[vkey]
    if not body.strip():
        raise HTTPException(status_code=404, detail="empty page")
    md = body.decode("utf-8")
    if format == "markdown":
        return Response(
            content=md, media_type="text/markdown; charset=utf-8"
        )
    return {
        "vault_key": vkey,
        "schema_version": 1,
        "markdown": md,
    }
