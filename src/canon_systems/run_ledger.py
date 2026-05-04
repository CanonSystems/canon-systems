"""Operator-facing run ledger helpers (normalization, re-exports).

Shared schema, keys, and ingest rules live in ``canon_backend_shared.run_ledger``.
State-api persistence is implemented in ``state_api`` (separate shard)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any

from canon_backend_shared.run_ledger import (
    ARCHIVE_REFERENCE_ALLOWED_KEYS,
    FORBIDDEN_VALUE_KEYS,
    RUN_LEDGER_PK_TAIL,
    RUN_LEDGER_RECORD_SCHEMA_VERSION,
    VALIDATION_OUTCOME_SLOTS,
    RunLedgerValidationError,
    archive_record_to_ledger_reference,
    assert_ledger_key_isolation_against_checkpoint,
    build_run_ledger_pk,
    build_run_ledger_sk,
    ledger_keys_for_record,
    parse_ledger_run_id,
    sanitize_ledger_segment,
    validate_run_ledger_record,
)

RUN_LEDGER_STATE_PATH = "/state/run-ledger"


class RunLedgerGetError(Exception):
    """GET ``/state/run-ledger`` failed before a usable JSON body was returned."""

    exit_code = 2

    def __init__(self, message: str = "", *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status


class RunLedgerRecordNotFound(Exception):
    """Returned HTTP 404 for a single-row lookup by ``ledger_run_id``.

    Does not subclass :class:`RunLedgerGetError` so callers can treat durable
    \"no row\" separately from transport/query faults (readiness → not ready).
    """

    exit_code = 1


class RunLedgerRequestFailed(RunLedgerGetError):
    """HTTP 400 or malformed client request."""

    exit_code = 2

    def __init__(self, message: str = "", *, http_status: int | None = None) -> None:
        super().__init__(message, http_status=http_status)


class RunLedgerServiceUnavailable(RunLedgerGetError):
    """HTTP 503 or run-ledger table not configured."""

    exit_code = 2

    def __init__(self, message: str = "", *, http_status: int | None = 503) -> None:
        super().__init__(message, http_status=http_status)


class RunLedgerTransportError(RunLedgerGetError):
    """Network or transport failure talking to state-api."""

    exit_code = 2

    def __init__(self, message: str = "", *, http_status: int | None = None) -> None:
        super().__init__(message, http_status=http_status)


def _parse_run_ledger_error_payload(raw: str) -> tuple[str | None, str | None, dict[str, Any]]:
    """Return ``(error_code, message, detail_dict)`` from a JSON error body."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None, None, {}
    if not isinstance(parsed, dict):
        return None, None, {}
    detail = parsed.get("detail")
    if isinstance(detail, dict):
        err = detail.get("error")
        msg = detail.get("message")
        if isinstance(err, str):
            return err, msg if isinstance(msg, str) else None, detail
        # Some errors use FastAPI shape detail -> list
        return None, None, detail
    return None, None, parsed


__all__ = [
    "ARCHIVE_REFERENCE_ALLOWED_KEYS",
    "FORBIDDEN_VALUE_KEYS",
    "RUN_LEDGER_PK_TAIL",
    "RUN_LEDGER_RECORD_SCHEMA_VERSION",
    "VALIDATION_OUTCOME_SLOTS",
    "RunLedgerValidationError",
    "archive_record_to_ledger_reference",
    "assert_ledger_key_isolation_against_checkpoint",
    "build_run_ledger_pk",
    "build_run_ledger_sk",
    "ledger_keys_for_record",
    "merge_archive_snapshots_into_record",
    "parse_ledger_run_id",
    "sanitize_ledger_segment",
    "validate_run_ledger_record",
    "RUN_LEDGER_STATE_PATH",
    "RunLedgerGetError",
    "RunLedgerRecordNotFound",
    "RunLedgerRequestFailed",
    "RunLedgerServiceUnavailable",
    "RunLedgerTransportError",
    "get_run_ledger_from_state_api",
    "post_run_ledger_to_state_api",
    "prepare_cli_run_ledger_record",
]


def merge_archive_snapshots_into_record(
    base: Mapping[str, Any],
    archive_snapshots: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Attach :func:`archive_record_to_ledger_reference` entries to ``archive_refs`` (WS3 dry-run)."""
    rec = dict(base)
    existing = list(rec.get("archive_refs") or [])
    for snap in archive_snapshots:
        existing.append(archive_record_to_ledger_reference(snap))
    rec["archive_refs"] = existing
    return validate_run_ledger_record(rec)


def prepare_cli_run_ledger_record(
    base: Mapping[str, Any],
    archive_snapshots: list[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Validate a ledger record from CLI JSON, optionally merging archive metadata by reference."""
    if archive_snapshots:
        return merge_archive_snapshots_into_record(base, list(archive_snapshots))
    return validate_run_ledger_record(base)


def post_run_ledger_to_state_api(
    *,
    base_url: str,
    record: Mapping[str, Any],
    timeout_seconds: float = 60.0,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    """Send a validated ledger record with HTTP PUT to ``{base}/state/run-ledger`` (state-api)."""
    from .packet_archive import default_state_api_base

    root = (base_url or default_state_api_base()).rstrip("/")
    url = f"{root}{RUN_LEDGER_STATE_PATH}"
    data = json.dumps(record, separators=(",", ":"), sort_keys=True).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            headers = {k: v for k, v in resp.headers.items()}
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed if isinstance(parsed, dict) else {}, headers
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
        except Exception:
            detail = {"detail": e.reason}
        if isinstance(detail, dict) and "detail" in detail and isinstance(detail["detail"], dict):
            return e.code, dict(detail["detail"]), {}
        return e.code, detail if isinstance(detail, dict) else {}, {}


def get_run_ledger_from_state_api(
    *,
    base_url: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    ledger_run_id: str | None = None,
    handoff_id: str | None = None,
    limit: int = 50,
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    """GET ``{base}/state/run-ledger`` — latest scoped rows or one row by ``ledger_run_id``.

    Raises:
        RunLedgerRecordNotFound: explicit ``ledger_run_id`` and HTTP 404.
        RunLedgerRequestFailed: HTTP 400 (invalid scope/limit).
        RunLedgerServiceUnavailable: HTTP 503 (table unset / unavailable).
        RunLedgerTransportError: DNS, TLS, timeout, or non-HTTP errors.
    """
    from .packet_archive import default_state_api_base

    root = (base_url or default_state_api_base()).rstrip("/")
    params: dict[str, str | int] = {
        "company_id": company_id,
        "repository_id": repository_id,
        "plan_id": plan_id,
        "task_id": task_id,
        "workstream_id": workstream_id,
        "limit": limit,
    }
    if ledger_run_id:
        params["ledger_run_id"] = ledger_run_id
    if handoff_id:
        params["handoff_id"] = handoff_id
    qs = urllib.parse.urlencode(params)
    url = f"{root}{RUN_LEDGER_STATE_PATH}?{qs}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            if not isinstance(parsed, dict):
                raise RunLedgerRequestFailed("run_ledger GET returned non-object JSON", http_status=None)
            return parsed
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        err_code, msg, detail = _parse_run_ledger_error_payload(body)
        if e.code == 404 and ledger_run_id:
            raise RunLedgerRecordNotFound(
                msg or err_code or "run ledger row not found",
            ) from e
        if e.code == 400:
            raise RunLedgerRequestFailed(
                msg or err_code or "run_ledger GET rejected (400)",
                http_status=e.code,
            ) from e
        if e.code == 503:
            raise RunLedgerServiceUnavailable(
                msg or err_code or "run_ledger GET unavailable (503)",
                http_status=e.code,
            ) from e
        extras = f" ({err_code})" if err_code else ""
        raise RunLedgerRequestFailed(
            f"run_ledger GET HTTP {e.code}{extras}",
            http_status=e.code,
        ) from e
    except urllib.error.URLError as e:
        raise RunLedgerTransportError(f"run_ledger GET transport failure: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise RunLedgerRequestFailed("run_ledger GET returned invalid JSON", http_status=None) from e
