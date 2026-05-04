"""Run ledger record schema (v1): DynamoDB-ready keys, validation, archive refs only.

Checkpoint / lease mutable state lives on keys ``company#repository`` /
``plan#task#workstream``. Run ledger rows use a disjoint partition key suffix
(``...#run_ledger``) and a four-part sort key ending in ``ledger_run_id`` so WS2
stores never collide with checkpoint items in a shared table.

Full packet bodies MUST NOT appear on ledger payloads. Ingest paths must use
:class:`archive_record_to_ledger_reference` and reject ``body``, ``body_base64``,
and ``content`` fields."""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from typing import Any

from canon_backend_shared.packet_archive import (
    sanitize_key_segment as _sanitize_archive_segment,
)
from canon_backend_shared.packet_archive import normalize_sha256_hex as _normalize_sha256

RUN_LEDGER_RECORD_SCHEMA_VERSION = 1

RUN_LEDGER_PK_TAIL = "run_ledger"

# Checkpoint keys (existing state-api convention) use pk = company/repo, sk = plan/task/workstream.
_LEDGER_SEGMENT_FORBIDDEN = re.compile(r"[#|\\/]")


class RunLedgerValidationError(ValueError):
    """Raised when a run ledger record or archive ingest payload is unsafe or invalid."""


# Keys whose values may carry megabyte-scale packet text — never persist on ledger.
FORBIDDEN_VALUE_KEYS = frozenset({"body_base64", "body", "content"})

# Subset copied from archived packet/evidence rows (reference only — no bodies).
ARCHIVE_REFERENCE_ALLOWED_KEYS = frozenset(
    {
        "s3_uri",
        "s3_key",
        "s3_bucket",
        "content_sha256",
        "artifact_kind",
        "phase",
        "status",
        "outcome",
        "evidence_subtype",
        "source_label",
        "created_at",
        "byte_length",
        "content_type",
        "schema_version",
        "archive_event_id",
        "agent_run_id",
        "actor_id",
        "s3_version_id",
        "company_id",
        "repository_id",
        "plan_id",
        "task_id",
        "workstream_id",
        "handoff_id",
    }
)

# Readiness-oriented validation slots (AC5); each value is a small dict (status, verdict, etc.).
VALIDATION_OUTCOME_SLOTS = frozenset(
    {
        "qa_validate",
        "flow_audit",
        "memory_health",
        "ci",
        "deployment_smoke",
        "merge_readiness",
    }
)

_MAX_ARCHIVE_REFS = 512
_MAX_EVIDENCE_REFS = 256
_MAX_SOURCE_EVENT_IDS = 256
_MAX_COMMITS = 64


def sanitize_ledger_segment(raw: str, *, label: str) -> str:
    """Segment safe for ``#``-delimited DynamoDB keys and SK paths."""
    s = _sanitize_archive_segment(raw, label=label)
    if _LEDGER_SEGMENT_FORBIDDEN.search(s):
        raise RunLedgerValidationError(f"{label} must not contain '#', '/', or '\\\\'")
    return s


def build_run_ledger_pk(*, company_id: str, repository_id: str) -> str:
    """Partition key for ledger rows; disjoint from checkpoint ``pk`` (no ``#run_ledger`` tail)."""
    c = sanitize_ledger_segment(company_id, label="company_id")
    r = sanitize_ledger_segment(repository_id, label="repository_id")
    return f"{c}#{r}#{RUN_LEDGER_PK_TAIL}"


def build_run_ledger_sk(
    *,
    plan_id: str,
    task_id: str,
    workstream_id: str,
    ledger_run_id: str,
) -> str:
    """Sort key: ``plan#task#workstream#ledger_run_id`` (four segments — never matches checkpoint sk)."""
    p = sanitize_ledger_segment(plan_id, label="plan_id")
    t = sanitize_ledger_segment(task_id, label="task_id")
    w = sanitize_ledger_segment(workstream_id, label="workstream_id")
    rid = sanitize_ledger_segment(ledger_run_id, label="ledger_run_id")
    return f"{p}#{t}#{w}#{rid}"


def parse_ledger_run_id(value: str) -> str:
    """Require a non-empty run id (UUID recommended for idempotent writes in WS2)."""
    s = str(value).strip()
    if not s:
        raise RunLedgerValidationError("ledger_run_id is required")
    if len(s) > 256:
        raise RunLedgerValidationError("ledger_run_id exceeds maximum length (256)")
    try:
        return str(uuid.UUID(s))
    except ValueError as e:
        raise RunLedgerValidationError("ledger_run_id must be a UUID") from e


def _reject_forbidden_keys(m: Mapping[str, Any], *, ctx: str) -> None:
    bad = FORBIDDEN_VALUE_KEYS.intersection(m.keys())
    if bad:
        raise RunLedgerValidationError(f"{ctx} must not contain body fields: {sorted(bad)}")


def archive_record_to_ledger_reference(record: Mapping[str, Any]) -> dict[str, Any]:
    """Map an archive record (or upload response metadata) to ledger storage by reference only."""
    if not isinstance(record, Mapping):
        raise RunLedgerValidationError("archive record must be a mapping")
    _reject_forbidden_keys(record, ctx="archive record")
    out: dict[str, Any] = {}
    for k, v in record.items():
        if k not in ARCHIVE_REFERENCE_ALLOWED_KEYS:
            continue
        if v is None:
            continue
        if isinstance(v, str) and k == "content_sha256":
            out[k] = _normalize_sha256(v)
            continue
        out[k] = v
    if "content_sha256" not in out:
        raise RunLedgerValidationError("archive reference requires content_sha256")
    if "artifact_kind" not in out:
        raise RunLedgerValidationError("archive reference requires artifact_kind")
    _reject_forbidden_keys(out, ctx="normalized archive reference")
    return out


def _normalize_timestamp(value: Any, *, label: str, required: bool) -> str:
    if value is None or value == "":
        if required:
            raise RunLedgerValidationError(f"{label} is required")
        return ""
    s = str(value).strip()
    if len(s) > 64:
        raise RunLedgerValidationError(f"{label} exceeds maximum length (64)")
    if not re.match(r"^\d{4}-\d{2}-\d{2}T", s):
        raise RunLedgerValidationError(f"{label} must start with RFC3339-style YYYY-MM-DDThh:mm:ss...")
    return s


def _normalize_optional_str(value: Any, *, label: str, max_len: int) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if len(s) > max_len:
        raise RunLedgerValidationError(f"{label} exceeds maximum length ({max_len})")
    return s


_GIT_SHA_RE = re.compile(r"^[a-f0-9]{7,40}$")


def _normalize_commit_sha(raw: str) -> str:
    s = raw.strip().lower()
    if _GIT_SHA_RE.match(s) is None:
        raise RunLedgerValidationError("commit.sha must be 7–40 lowercase hex characters")
    return s


def _normalize_commits(entries: Any) -> list[dict[str, Any]]:
    if entries is None or entries == []:
        return []
    if not isinstance(entries, list):
        raise RunLedgerValidationError("commits must be a list")
    out: list[dict[str, Any]] = []
    if len(entries) > _MAX_COMMITS:
        raise RunLedgerValidationError(f"commits list exceeds {_MAX_COMMITS}")
    for i, ent in enumerate(entries):
        if not isinstance(ent, Mapping):
            raise RunLedgerValidationError(f"commits[{i}] must be an object")
        if "sha" not in ent:
            raise RunLedgerValidationError(f"commits[{i}].sha is required")
        item = {"sha": _normalize_commit_sha(str(ent["sha"]))}
        if "label" in ent and ent["label"] is not None:
            lbl = _normalize_optional_str(ent["label"], label=f"commits[{i}].label", max_len=256)
            if lbl:
                item["label"] = lbl
        out.append(item)
    return out


def _normalize_pull_request(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise RunLedgerValidationError("pull_request must be an object")
    url = raw.get("url")
    if not url:
        raise RunLedgerValidationError("pull_request.url is required")
    s = str(url).strip()
    if not (s.startswith("https://") or s.startswith("http://")):
        raise RunLedgerValidationError("pull_request.url must be an http(s) URL")
    if len(s) > 4096:
        raise RunLedgerValidationError("pull_request.url is too long")
    pr_obj: dict[str, Any] = {"url": s}
    num = raw.get("number")
    if num is not None and num != "":
        try:
            n = int(num)
        except (TypeError, ValueError) as e:
            raise RunLedgerValidationError("pull_request.number must be an integer") from e
        if n < 1:
            raise RunLedgerValidationError("pull_request.number must be positive")
        pr_obj["number"] = n
    _reject_forbidden_keys(raw, ctx="pull_request")
    return pr_obj


def _normalize_deployment(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise RunLedgerValidationError("deployment must be an object")
    _reject_forbidden_keys(raw, ctx="deployment block")
    env = raw.get("environment")
    stat = raw.get("status")
    if not env or not str(env).strip():
        raise RunLedgerValidationError("deployment.environment is required when deployment is present")
    if not stat or not str(stat).strip():
        raise RunLedgerValidationError("deployment.status is required when deployment is present")
    out: dict[str, Any] = {
        "environment": sanitize_ledger_segment(str(env), label="deployment.environment"),
        "status": _normalize_optional_str(stat, label="deployment.status", max_len=128),
    }
    for opt_key in ("deployed_at", "endpoint_url", "detail_uri"):
        v = raw.get(opt_key)
        if v is None or v == "":
            continue
        s = _normalize_optional_str(v, label=f"deployment.{opt_key}", max_len=4096)
        if s:
            out[opt_key] = s
    return out


def _normalize_validation_outcomes(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise RunLedgerValidationError("validation_outcomes must be an object")
    out: dict[str, Any] = {}
    unknown = set(raw.keys()) - VALIDATION_OUTCOME_SLOTS
    if unknown:
        raise RunLedgerValidationError(f"validation_outcomes has unknown slots: {sorted(unknown)}")
    for slot in VALIDATION_OUTCOME_SLOTS:
        if slot not in raw:
            continue
        val = raw[slot]
        if val is None:
            continue
        if not isinstance(val, Mapping):
            raise RunLedgerValidationError(f"validation_outcomes.{slot} must be an object")
        _reject_forbidden_keys(val, ctx=f"validation_outcomes.{slot}")
        block: dict[str, Any] = {}
        for fk in ("status", "verdict", "summary", "checked_at", "job_url", "artifact_uri"):
            if fk not in val:
                continue
            if val[fk] is None or val[fk] == "":
                continue
            if fk == "exit_code":
                continue
            block[fk] = _normalize_optional_str(val[fk], label=f"{slot}.{fk}", max_len=2048)
        if "exit_code" in val and val["exit_code"] is not None:
            try:
                block["exit_code"] = int(val["exit_code"])
            except (TypeError, ValueError) as e:
                raise RunLedgerValidationError(f"validation_outcomes.{slot}.exit_code must be int") from e
        if block:
            out[slot] = block
    return out


def _normalize_ref_list(
    raw: Any,
    *,
    label: str,
    max_items: int,
    normalizer,
) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise RunLedgerValidationError(f"{label} must be a list")
    if len(raw) > max_items:
        raise RunLedgerValidationError(f"{label} exceeds {max_items} items")
    return [normalizer(x, i) for i, x in enumerate(raw)]


def _normalize_archive_ref_item(x: Any, index: int) -> dict[str, Any]:
    if not isinstance(x, Mapping):
        raise RunLedgerValidationError(f"archive_refs[{index}] must be an object")
    return archive_record_to_ledger_reference(x)


def _normalize_evidence_ref_item(x: Any, index: int) -> dict[str, Any]:
    if not isinstance(x, Mapping):
        raise RunLedgerValidationError(f"evidence_refs[{index}] must be an object")
    _reject_forbidden_keys(x, ctx=f"evidence_refs[{index}]")
    out: dict[str, Any] = {}
    for k in ("ref_kind", "uri", "label", "content_sha256", "s3_uri", "s3_key", "evidence_kind"):
        if k not in x or x[k] is None or x[k] == "":
            continue
        if k == "content_sha256":
            out[k] = _normalize_sha256(str(x[k]))
        else:
            out[k] = _normalize_optional_str(x[k], label=f"evidence_refs[{index}].{k}", max_len=4096)
    if not out:
        raise RunLedgerValidationError(f"evidence_refs[{index}] is empty")
    return out


def _normalize_source_event_ids(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise RunLedgerValidationError("source_event_ids must be a list")
    if len(raw) > _MAX_SOURCE_EVENT_IDS:
        raise RunLedgerValidationError(f"source_event_ids exceeds {_MAX_SOURCE_EVENT_IDS}")
    out: list[str] = []
    for i, x in enumerate(raw):
        s = _normalize_optional_str(x, label=f"source_event_ids[{i}]", max_len=256)
        if not s:
            raise RunLedgerValidationError(f"source_event_ids[{i}] must be non-empty")
        out.append(s)
    return out


def validate_run_ledger_record(data: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a JSON-serializable ledger record (v1)."""
    if not isinstance(data, Mapping):
        raise RunLedgerValidationError("record must be a mapping")
    _reject_forbidden_keys(data, ctx="run ledger record")

    ver = data.get("schema_version", RUN_LEDGER_RECORD_SCHEMA_VERSION)
    if int(ver) != RUN_LEDGER_RECORD_SCHEMA_VERSION:
        raise RunLedgerValidationError(f"unsupported schema_version (expected {RUN_LEDGER_RECORD_SCHEMA_VERSION})")

    ledger_run_id = parse_ledger_run_id(str(data.get("ledger_run_id", "")))

    company_id = sanitize_ledger_segment(str(data["company_id"]), label="company_id")
    repository_id = sanitize_ledger_segment(str(data["repository_id"]), label="repository_id")
    plan_id = sanitize_ledger_segment(str(data["plan_id"]), label="plan_id")
    task_id = sanitize_ledger_segment(str(data["task_id"]), label="task_id")
    workstream_id = sanitize_ledger_segment(str(data["workstream_id"]), label="workstream_id")
    handoff_id = sanitize_ledger_segment(str(data["handoff_id"]), label="handoff_id")
    phase = sanitize_ledger_segment(str(data["phase"]), label="phase")
    phase_status = _normalize_optional_str(data.get("phase_status"), label="phase_status", max_len=128)
    if not phase_status:
        raise RunLedgerValidationError("phase_status is required")

    created_at = _normalize_timestamp(data.get("created_at"), label="created_at", required=True)
    updated_at = _normalize_timestamp(data.get("updated_at"), label="updated_at", required=False)

    verdict = _normalize_optional_str(data.get("verdict"), label="verdict", max_len=128)

    archive_refs = _normalize_ref_list(
        data.get("archive_refs"),
        label="archive_refs",
        max_items=_MAX_ARCHIVE_REFS,
        normalizer=_normalize_archive_ref_item,
    )
    evidence_refs = _normalize_ref_list(
        data.get("evidence_refs"),
        label="evidence_refs",
        max_items=_MAX_EVIDENCE_REFS,
        normalizer=_normalize_evidence_ref_item,
    )

    validation_outcomes = _normalize_validation_outcomes(data.get("validation_outcomes"))
    commits = _normalize_commits(data.get("commits"))
    pull_request = _normalize_pull_request(data.get("pull_request"))
    deployment = _normalize_deployment(data.get("deployment"))
    source_event_ids = _normalize_source_event_ids(data.get("source_event_ids"))

    agent_run_id = _normalize_optional_str(data.get("agent_run_id"), label="agent_run_id", max_len=256)
    actor_id = _normalize_optional_str(data.get("actor_id"), label="actor_id", max_len=256)

    record: dict[str, Any] = {
        "schema_version": RUN_LEDGER_RECORD_SCHEMA_VERSION,
        "ledger_run_id": ledger_run_id,
        "company_id": company_id,
        "repository_id": repository_id,
        "plan_id": plan_id,
        "task_id": task_id,
        "workstream_id": workstream_id,
        "handoff_id": handoff_id,
        "phase": phase,
        "phase_status": phase_status,
        "created_at": created_at,
        "archive_refs": archive_refs,
        "evidence_refs": evidence_refs,
        "validation_outcomes": validation_outcomes,
        "commits": commits,
        "source_event_ids": source_event_ids,
    }
    if verdict:
        record["verdict"] = verdict
    if updated_at:
        record["updated_at"] = updated_at
    if pull_request is not None:
        record["pull_request"] = pull_request
    if deployment is not None:
        record["deployment"] = deployment
    if agent_run_id:
        record["agent_run_id"] = agent_run_id
    if actor_id:
        record["actor_id"] = actor_id

    _reject_forbidden_keys(record, ctx="normalized run ledger record")
    return record


def ledger_keys_for_record(record: Mapping[str, Any]) -> tuple[str, str]:
    """Return ``(pk, sk)`` for DynamoDB from a validated record mapping."""
    v = validate_run_ledger_record(record)
    pk = build_run_ledger_pk(company_id=v["company_id"], repository_id=v["repository_id"])
    sk = build_run_ledger_sk(
        plan_id=v["plan_id"],
        task_id=v["task_id"],
        workstream_id=v["workstream_id"],
        ledger_run_id=v["ledger_run_id"],
    )
    return pk, sk


def assert_ledger_key_isolation_against_checkpoint(*, ledger_pk: str, ledger_sk: str, checkpoint_pk: str, checkpoint_sk: str) -> None:
    """Debug helper: prove ledger and checkpoint keys are never equal (AC2/AC8 tests)."""
    if ledger_pk == checkpoint_pk and ledger_sk == checkpoint_sk:
        raise RunLedgerValidationError("ledger key collision with checkpoint key")
