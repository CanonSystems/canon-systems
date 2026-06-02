"""Server-authoritative transport for `canon task` (state-api task plane).

When ``CANON_TASKS_API_URL`` (or the shared ``CANON_STATE_API_URL``) is set,
``canon task`` treats state-api as the source of truth: every mutation is pushed
as a task event and every read folds the server's event stream. The on-disk
NDJSON ledger becomes an offline cache + the canonical-memory mirror.

Everything here is **fail-open**: any network/transport error returns a sentinel
(``None`` for reads, ``(False, reason)`` for writes) so the CLI can fall back to
local-only behavior and tell the user the write is pending sync.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

ENV_TASKS_URL = "CANON_TASKS_API_URL"
ENV_STATE_URL = "CANON_STATE_API_URL"
_DEFAULT_TIMEOUT_MS = 10000


def remote_base() -> str | None:
    """Return the configured task-plane base URL, or None when local-only."""
    for env in (ENV_TASKS_URL, ENV_STATE_URL):
        val = (os.environ.get(env, "") or "").strip()
        if val:
            return val.rstrip("/")
    return None


def _timeout_seconds() -> float:
    raw = (os.environ.get("CANON_TASKS_TIMEOUT_MS", "") or "").strip()
    try:
        ms = int(raw) if raw else _DEFAULT_TIMEOUT_MS
    except ValueError:
        ms = _DEFAULT_TIMEOUT_MS
    return max(0.5, ms / 1000.0)


def _request(method: str, url: str, body: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    token = (os.environ.get("CANON_STATE_API_TOKEN", "") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=_timeout_seconds()) as resp:  # noqa: S310
        raw = resp.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
        return resp.getcode(), (parsed if isinstance(parsed, dict) else {"data": parsed})


def fetch_events(company_id: str, *, task_ref: str | None = None, limit: int = 2000) -> list[dict[str, Any]] | None:
    """GET the server's task event stream for a company. None on any failure."""
    base = remote_base()
    if not base or not company_id.strip():
        return None
    params: dict[str, str] = {"company_id": company_id.strip(), "limit": str(limit)}
    if task_ref:
        params["task_ref"] = task_ref
    url = f"{base}/state/tasks?{urlencode(params)}"
    try:
        code, payload = _request("GET", url, None)
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    if code != 200:
        return None
    events = payload.get("events")
    if not isinstance(events, list):
        return None
    return [e for e in events if isinstance(e, dict)]


def push_event(event: dict[str, Any]) -> tuple[bool, str]:
    """POST one task event to the server. Returns (ok, detail)."""
    base = remote_base()
    if not base:
        return False, "no_remote_configured"
    url = f"{base}/state/tasks/events"
    try:
        code, payload = _request("POST", url, event)
    except urllib.error.HTTPError as exc:  # 4xx/5xx
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except Exception:
            detail = {}
        return False, f"http_{exc.code}:{detail.get('detail', {}).get('error', '')}"
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        return False, f"transport:{exc}"
    if code not in (200, 201):
        return False, f"http_{code}"
    return True, str(payload.get("status", "ok"))
