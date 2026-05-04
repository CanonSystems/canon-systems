"""Run-ledger-backed readiness evaluation (shared library for ``canon readiness check``).

Derives pass/fail from durable ledger rows and archive references only — no packet
body reads and no extra QA normalization beyond fields already on the ledger."""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping, Sequence
from datetime import datetime, timezone
from typing import Any

from canon_backend_shared.packet_archive import (
    PACKET_CURSOR_PILOT,
    PACKET_IMPLEMENTER,
    PACKET_IMPLEMENTER_SHARD,
    PACKET_QA_GATE,
    PACKET_RELEASE_STATUS,
    PACKET_SCOPER,
)
from canon_backend_shared.run_ledger import VALIDATION_OUTCOME_SLOTS

from canon_systems.run_ledger import (
    RunLedgerRecordNotFound,
    RunLedgerRequestFailed,
    RunLedgerServiceUnavailable,
    RunLedgerTransportError,
    get_run_ledger_from_state_api,
)

READINESS_SCHEMA_VERSION = 1


class RunLedgerQueryError(Exception):
    """Raised when state-api GET fails before a readiness snapshot can be built (CLI exit 2)."""

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.detail = detail

READINESS_REQUIRED_ARCHIVE_PHASES: tuple[str, ...] = (
    "scoper",
    "cursor-pilot",
    "qa-gate",
    "release-status",
)

_ARTIFACT_KIND_TO_PHASE: dict[str, str] = {
    PACKET_SCOPER: "scoper",
    PACKET_CURSOR_PILOT: "cursor-pilot",
    PACKET_IMPLEMENTER: "implementer",
    PACKET_IMPLEMENTER_SHARD: "implementer",
    PACKET_QA_GATE: "qa-gate",
    PACKET_RELEASE_STATUS: "release-status",
}

_ARCHIVE_STATUS_OK: frozenset[str] = frozenset(
    {"ok", "completed", "archived", "success", "stored", "pass", "passed"}
)

_SNAPSHOT_BODY_KEYS: frozenset[str] = frozenset({"body", "body_base64", "content"})


def archive_ref_phase(ref: Mapping[str, Any]) -> str | None:
    """Resolve canonical phase slug from ``phase`` or ``artifact_kind`` only."""
    ph = ref.get("phase")
    if isinstance(ph, str):
        s = ph.strip()
        if s:
            return s
    kind = ref.get("artifact_kind")
    if isinstance(kind, str) and kind in _ARTIFACT_KIND_TO_PHASE:
        return _ARTIFACT_KIND_TO_PHASE[kind]
    return None


def phases_present_in_archive_refs(record: Mapping[str, Any]) -> set[str]:
    out: set[str] = set()
    for ref in record.get("archive_refs") or []:
        if not isinstance(ref, Mapping):
            continue
        p = archive_ref_phase(ref)
        if p:
            out.add(p)
    return out


def _implementer_satisfied(record: Mapping[str, Any], phases: set[str]) -> bool:
    if "implementer" in phases:
        return True
    for ev in record.get("evidence_refs") or []:
        if not isinstance(ev, Mapping):
            continue
        blob = " ".join(
            str(ev.get(k) or "")
            for k in ("ref_kind", "label", "evidence_kind", "uri")
        ).lower()
        if "implementer" in blob or "implementer_shard" in blob.replace("-", "_"):
            return True
        if "shard" in blob and "implementer" in blob:
            return True
    return False


def _archive_ref_status_warning(ref: Mapping[str, Any]) -> str | None:
    status = ref.get("status") or ref.get("outcome")
    if status is None or status == "":
        return None
    if str(status).strip().lower() in _ARCHIVE_STATUS_OK:
        return None
    phase = archive_ref_phase(ref) or "unknown"
    return f"archive_ref phase={phase!r} has non-pass status/outcome={status!r}"


def _ledger_sort_key(rec: Mapping[str, Any]) -> tuple[str, str]:
    updated = str(rec.get("updated_at") or "")
    created = str(rec.get("created_at") or "")
    return (updated, created)


def _snapshot_safe(value: Any) -> Any:
    """Copy ledger metadata for local snapshots while stripping packet body fields."""
    if isinstance(value, Mapping):
        return {
            str(k): _snapshot_safe(v)
            for k, v in value.items()
            if str(k) not in _SNAPSHOT_BODY_KEYS
        }
    if isinstance(value, list):
        return [_snapshot_safe(v) for v in value]
    return value


def pick_latest_ledger_record(items: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """Prefer newest by ``updated_at``, then ``created_at``, lexicographically (RFC3339 strings)."""
    maps = [x for x in items if isinstance(x, Mapping)]
    if not maps:
        return None
    return max(maps, key=_ledger_sort_key)


def summarize_validation_outcomes(record: Mapping[str, Any]) -> dict[str, Any]:
    """Pass through existing ledger validation slots only (no new normalization)."""
    raw = record.get("validation_outcomes")
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, Any] = {}
    for slot in VALIDATION_OUTCOME_SLOTS:
        if slot not in raw:
            continue
        val = raw[slot]
        if val is None:
            continue
        out[slot] = val
    return out


def build_readiness_report_for_record(
    *,
    record: Mapping[str, Any],
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    handoff_id: str,
    ledger_run_id_resolved: str | None,
    query_mode: str,
    limit_hit_warning: bool,
) -> dict[str, Any]:
    """Build AC5-shaped readiness JSON from a single ledger row (metadata-only)."""
    checks: list[dict[str, Any]] = []
    missing: list[str] = []
    failures: list[dict[str, str]] = []
    warnings: list[str] = []

    phases = phases_present_in_archive_refs(record)
    for req in READINESS_REQUIRED_ARCHIVE_PHASES:
        cid = f"archive_ref.required_phase.{req}"
        if req in phases:
            checks.append({"id": cid, "status": "pass", "detail": f"archive ref present for phase {req!r}"})
        else:
            missing.append(req)
            checks.append({"id": cid, "status": "fail", "detail": f"missing archive ref for phase {req!r}"})
            failures.append({"code": "missing_archive_phase", "message": f"missing packet archive ref for {req}"})

    impl_ok = _implementer_satisfied(record, phases)
    checks.append(
        {
            "id": "archive_ref.implementer_or_shard",
            "status": "pass" if impl_ok else "fail",
            "detail": "implementer packet/shard or implementer-linked evidence_ref present"
            if impl_ok
            else "missing implementer primary packet or shard/evidence marker",
        }
    )
    if not impl_ok:
        failures.append(
            {
                "code": "missing_implementer_evidence",
                "message": "need implementer archive ref or implementer/implementer-shard evidence_ref",
            }
        )

    for ref in record.get("archive_refs") or []:
        if not isinstance(ref, Mapping):
            continue
        warn = _archive_ref_status_warning(ref)
        if warn:
            warnings.append(warn)

    if limit_hit_warning:
        warnings.append(f"latest query returned at least `limit` rows; newer rows may exist outside the window")

    failure_level = bool(failures)
    warn_level = bool(warnings) and not failure_level
    if failure_level:
        overall = "fail"
        ready = False
    elif warn_level:
        overall = "warn"
        ready = False
    else:
        overall = "pass"
        ready = True

    validation_summary = summarize_validation_outcomes(record)
    commits = record.get("commits") if isinstance(record.get("commits"), list) else []
    pull_request = record.get("pull_request") if isinstance(record.get("pull_request"), Mapping) else None
    deployment = record.get("deployment") if isinstance(record.get("deployment"), Mapping) else None

    rid = ledger_run_id_resolved or str(record.get("ledger_run_id") or "")

    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "company_id": company_id,
        "repository_id": repository_id,
        "plan_id": plan_id,
        "task_id": task_id,
        "workstream_id": workstream_id,
        "handoff_id": handoff_id,
        "ledger_run_id": rid or None,
        "query_mode": query_mode,
        "overall_status": overall,
        "ready": ready,
        "checks": checks,
        "records": [_snapshot_safe(record)],
        "missing": missing,
        "failures": failures,
        "warnings": warnings,
        "validation_summary": validation_summary,
        "commits": commits,
        "pull_request": pull_request,
        "deployment": deployment,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _empty_report_not_found(
    *,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    handoff_id: str,
    ledger_run_id: str | None,
    query_mode: str,
    message: str,
) -> dict[str, Any]:
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "company_id": company_id,
        "repository_id": repository_id,
        "plan_id": plan_id,
        "task_id": task_id,
        "workstream_id": workstream_id,
        "handoff_id": handoff_id,
        "ledger_run_id": ledger_run_id,
        "query_mode": query_mode,
        "overall_status": "fail",
        "ready": False,
        "checks": [
            {
                "id": "run_ledger.record_presence",
                "status": "fail",
                "detail": message,
            }
        ],
        "records": [],
        "missing": list(READINESS_REQUIRED_ARCHIVE_PHASES) + ["implementer"],
        "failures": [{"code": "ledger_record_missing", "message": message}],
        "warnings": [],
        "validation_summary": {},
        "commits": [],
        "pull_request": None,
        "deployment": None,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


FetchFn = Callable[..., dict[str, Any]]


def evaluate_readiness(
    *,
    base_url: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    handoff_id: str,
    ledger_run_id: str | None = None,
    limit: int = 50,
    timeout_seconds: float = 60.0,
    fetcher: FetchFn | None = None,
) -> dict[str, Any]:
    """Load ledger row(s) via GET ``/state/run-ledger`` and emit readiness JSON.

    Raises:
        RunLedgerRequestFailed, RunLedgerServiceUnavailable, RunLedgerTransportError:
            query or infrastructure faults (maps to CLI exit 2 in ws2).

    ``RunLedgerRecordNotFound`` is swallowed for explicit ``ledger_run_id`` and
    turned into ``ready: false`` with failures (CLI exit 1 when ws2 evaluates).
    """
    fetch = fetcher or get_run_ledger_from_state_api
    try:
        payload = fetch(
            base_url=base_url,
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            task_id=task_id,
            workstream_id=workstream_id,
            ledger_run_id=ledger_run_id,
            handoff_id=handoff_id,
            limit=limit,
            timeout_seconds=timeout_seconds,
        )
    except RunLedgerRecordNotFound as e:
        return _empty_report_not_found(
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            task_id=task_id,
            workstream_id=workstream_id,
            handoff_id=handoff_id,
            ledger_run_id=ledger_run_id,
            query_mode="by_run_id",
            message=str(e),
        )

    if ledger_run_id:
        rec = payload.get("record")
        if not isinstance(rec, Mapping):
            return _empty_report_not_found(
                company_id=company_id,
                repository_id=repository_id,
                plan_id=plan_id,
                task_id=task_id,
                workstream_id=workstream_id,
                handoff_id=handoff_id,
                ledger_run_id=ledger_run_id,
                query_mode="by_run_id",
                message="run ledger GET returned no record object",
            )
        return build_readiness_report_for_record(
            record=rec,
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            task_id=task_id,
            workstream_id=workstream_id,
            handoff_id=handoff_id,
            ledger_run_id_resolved=str(rec.get("ledger_run_id") or ledger_run_id),
            query_mode="by_run_id",
            limit_hit_warning=False,
        )

    items_raw = payload.get("items")
    if not isinstance(items_raw, list):
        return _empty_report_not_found(
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            task_id=task_id,
            workstream_id=workstream_id,
            handoff_id=handoff_id,
            ledger_run_id=None,
            query_mode="latest_scoped",
            message="run ledger GET returned no items list",
        )

    latest = pick_latest_ledger_record(items_raw)
    if latest is None:
        return _empty_report_not_found(
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            task_id=task_id,
            workstream_id=workstream_id,
            handoff_id=handoff_id,
            ledger_run_id=None,
            query_mode="latest_scoped",
            message="no run ledger rows for scope/handoff filter",
        )

    count = int(payload.get("count") if isinstance(payload.get("count"), int) else len(items_raw))
    limit_hit_warning = limit >= 1 and count >= limit

    return build_readiness_report_for_record(
        record=latest,
        company_id=company_id,
        repository_id=repository_id,
        plan_id=plan_id,
        task_id=task_id,
        workstream_id=workstream_id,
        handoff_id=handoff_id,
        ledger_run_id_resolved=str(latest.get("ledger_run_id") or ""),
        query_mode="latest_scoped",
        limit_hit_warning=limit_hit_warning,
    )


def merge_readiness_summaries(target: MutableMapping[str, Any], extra: Mapping[str, Any]) -> None:
    """Hook for ws2 multi-record merges — mutates ``target`` with additive summary keys."""
    for k, v in extra.items():
        if k not in target or target[k] in (None, {}, []):
            target[k] = v


def run_readiness_pipeline(
    *,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    handoff_id: str,
    ledger_run_id: str | None = None,
    limit: int = 50,
    state_api_url: str,
    timeout_seconds: float = 60.0,
    fetcher: FetchFn | None = None,
) -> dict[str, Any]:
    """CLI-facing facade: return readiness JSON or raise :class:`RunLedgerQueryError`."""
    try:
        return evaluate_readiness(
            base_url=state_api_url,
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            task_id=task_id,
            workstream_id=workstream_id,
            handoff_id=handoff_id,
            ledger_run_id=ledger_run_id,
            limit=limit,
            timeout_seconds=timeout_seconds,
            fetcher=fetcher,
        )
    except RunLedgerRequestFailed as e:
        raise RunLedgerQueryError(str(e), http_status=getattr(e, "http_status", None)) from e
    except RunLedgerServiceUnavailable as e:
        raise RunLedgerQueryError(str(e), http_status=getattr(e, "http_status", None)) from e
    except RunLedgerTransportError as e:
        raise RunLedgerQueryError(str(e)) from e
