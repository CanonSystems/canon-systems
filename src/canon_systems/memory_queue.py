"""JSONL retry queue for failed MemPalace /memory/search calls (stdlib-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .shared import repo_root


def queue_path() -> Path:
    path = repo_root() / ".canon" / "memory" / "mempalace-retry-queue.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def classify_mempalace_response(
    *,
    status: int,
    payload: Any,
    endpoint_ref: str,
    latency_ms: int,
    configured: bool,
) -> dict[str, Any]:
    """
    Return {status, latency_ms, last_error, endpoint_ref}.
    status: ok | degraded | unreachable | not_configured
    """
    base = {
        "latency_ms": latency_ms,
        "endpoint_ref": endpoint_ref,
    }
    if not configured:
        return {**base, "status": "not_configured", "last_error": ""}
    if status == 0:
        if isinstance(payload, str) and payload.strip():
            err = f"url error: {payload.strip()}"
        else:
            err = "url error: request failed"
        if len(err) > 200:
            err = err[:199] + "…"
        return {**base, "status": "unreachable", "last_error": err}
    if 200 <= status < 300 and isinstance(payload, dict):
        return {**base, "status": "ok", "last_error": ""}
    last_error = f"http {status}"
    if isinstance(payload, str) and payload.strip():
        extra = " ".join(payload.split())
        if len(extra) > 120:
            extra = extra[:119] + "…"
        last_error = f"http {status}: {extra}"
    if len(last_error) > 200:
        last_error = last_error[:199] + "…"
    return {**base, "status": "degraded", "last_error": last_error}


def enqueue_mempalace_retry(record: dict[str, Any]) -> None:
    path = queue_path()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(
        existing + json.dumps(record, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def is_degraded(block: dict[str, Any]) -> bool:
    s = str(block.get("status", "")).strip()
    return s in {"degraded", "unreachable"}
