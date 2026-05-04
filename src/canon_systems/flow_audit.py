"""Validate agent-flow artifacts for a task without code review.

Deploy smoke attestation (``deployment-smoke.json``) schema ``schema_version`` ``1`` —
non-secret fields only:

- ``handoff_id``, ``task_id``: identity; must match ``flow-audit`` CLI scope.
- ``environment``: deployment slice label (for example ``dev``, ``staging``).
- ``base_url``: HTTPS origin of the environment that was smoke-tested.
- ``expected_branch``: Git branch whose tip defines the intended deployment head.
- ``expected_head_sha``: full or abbreviated Git commit SHA expected at branch head.
- Proof of deploy — supply **either**:

  - ``deployed_commit_sha`` matching ``expected_head_sha`` (ASCII hex, compared case-insensitively), **or**
  - ``deployed_build_id`` together with ``expected_build_id`` (same opaque string).

  Omitting both ``deployed_commit_sha`` (non-empty) and ``deployed_build_id`` (non-empty)
  is invalid.

- ``smoke_verdict``: operator verdict string; ``environment_smoke_not_proof_of_branch``
  fails attestation (stale or unverifiable branch/deploy proof).
- ``verdict_reason``: optional; equal to ``environment_smoke_not_proof_of_branch`` also fails.
- ``checked_at``: RFC3339 / ISO-8601 timestamp string when smoke ran.
- ``evidence_refs``: JSON array of opaque refs (strings or objects); may be empty.

File path: ``.cursor/handoffs/<handoff_id>/<task_id>/deployment-smoke.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .checkpoints import _collect_checkpoint_errors
from .dor_telemetry import DorTelemetryLabels, collect_dor_telemetry_errors_for_task
from .shared import repo_root

DEPLOY_ATTESTATION_FILENAME = "deployment-smoke.json"
DEPLOY_ATTESTATION_SCHEMA_VERSION = "1"
STALE_DEPLOY_VERDICT = "environment_smoke_not_proof_of_branch"


def _collect_memory_health_errors(base: Path) -> list[str]:
    path = base / "memory-health.json"
    if not path.exists():
        return [f"missing memory-health evidence: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"invalid JSON in memory-health evidence: {path}"]
    if not isinstance(payload, dict):
        return [f"memory-health evidence payload must be object: {path}"]
    if payload.get("schema_version") != "1":
        v = payload.get("schema_version")
        return [f"memory-health evidence schema_version mismatch (got {v!r}, expected '1'): {path}"]
    if payload.get("overall_status") != "ok":
        s = payload.get("overall_status")
        return [f"memory-health evidence overall_status='{s}' (expected 'ok'): {path}"]
    return []


def _deploy_str_field(payload: dict, key: str, *, path: Path) -> tuple[str | None, list[str]]:
    raw = payload.get(key)
    if raw is None:
        return None, [f"deploy attestation missing required field {key!r}: {path}"]
    if not isinstance(raw, str):
        return None, [f"deploy attestation field {key!r} must be a string: {path}"]
    s = raw.strip()
    if not s:
        return None, [f"deploy attestation field {key!r} must be non-empty: {path}"]
    return s, []


def _deploy_str_field_any(
    payload: dict,
    canonical_key: str,
    aliases: tuple[str, ...],
    *,
    path: Path,
) -> tuple[str | None, list[str]]:
    """Read a canonical deploy-attestation field, accepting pre-schema aliases."""
    keys = (canonical_key, *aliases)
    for key in keys:
        if key in payload:
            return _deploy_str_field(payload, key, path=path)
    alias_note = f" (aliases: {', '.join(aliases)})" if aliases else ""
    return None, [f"deploy attestation missing required field {canonical_key!r}{alias_note}: {path}"]


def _normalize_git_sha(value: str) -> str:
    return value.strip().lower()


def _collect_deploy_attestation_errors(base: Path, *, handoff_id: str, task_id: str) -> list[str]:
    """Validate ``deployment-smoke.json`` when ``--require-deploy-attestation`` is set."""
    path = base / DEPLOY_ATTESTATION_FILENAME
    if not path.exists():
        return [f"missing deploy attestation evidence: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON in deploy attestation evidence {path}: {exc}"]
    if not isinstance(payload, dict):
        return [f"deploy attestation payload must be JSON object: {path}"]

    errors: list[str] = []
    ver = payload.get("schema_version")
    if ver != DEPLOY_ATTESTATION_SCHEMA_VERSION:
        errors.append(
            "deploy attestation schema_version mismatch "
            f"(got {ver!r}, expected {DEPLOY_ATTESTATION_SCHEMA_VERSION!r}): {path}"
        )

    hid = payload.get("handoff_id")
    tid = payload.get("task_id")
    if not isinstance(hid, str) or not hid.strip():
        errors.append(f"deploy attestation missing or invalid handoff_id: {path}")
    elif hid.strip() != handoff_id:
        errors.append(
            f"deploy attestation handoff_id mismatch (got {hid.strip()!r}, "
            f"expected {handoff_id!r}): {path}"
        )
    if not isinstance(tid, str) or not tid.strip():
        errors.append(f"deploy attestation missing or invalid task_id: {path}")
    elif tid.strip() != task_id:
        errors.append(
            f"deploy attestation task_id mismatch (got {tid.strip()!r}, expected {task_id!r}): {path}"
        )

    for key in ("environment", "expected_branch", "smoke_verdict", "checked_at"):
        _val, errs = _deploy_str_field(payload, key, path=path)
        errors.extend(errs)
    _base_url, errs = _deploy_str_field_any(payload, "base_url", ("deployment_url",), path=path)
    errors.extend(errs)
    expected_sha, errs = _deploy_str_field_any(payload, "expected_head_sha", ("expected_git_sha",), path=path)
    errors.extend(errs)

    refs = payload.get("evidence_refs")
    if refs is None:
        errors.append(f"deploy attestation missing required field 'evidence_refs': {path}")
    elif not isinstance(refs, list):
        errors.append(f"deploy attestation evidence_refs must be a JSON array: {path}")

    if errors:
        return errors

    smoke_verdict = str(payload.get("smoke_verdict", "")).strip()
    verdict_reason = payload.get("verdict_reason")
    reason_str = str(verdict_reason).strip() if isinstance(verdict_reason, str) else ""
    if smoke_verdict == STALE_DEPLOY_VERDICT:
        errors.append(
            f"deploy attestation smoke_verdict={STALE_DEPLOY_VERDICT!r} "
            f"(not acceptable branch/deploy proof): {path}"
        )
    if reason_str == STALE_DEPLOY_VERDICT:
        errors.append(
            f"deploy attestation verdict_reason={STALE_DEPLOY_VERDICT!r} "
            f"(not acceptable branch/deploy proof): {path}"
        )
    if errors:
        return errors

    expected_head_sha_raw = str(expected_sha).strip()

    deployed_sha_raw = payload.get("deployed_commit_sha")
    if deployed_sha_raw is None:
        deployed_sha_raw = payload.get("deployed_git_sha")
    deployed_sha = deployed_sha_raw.strip() if isinstance(deployed_sha_raw, str) else ""
    deployed_build_raw = payload.get("deployed_build_id")
    deployed_build = deployed_build_raw.strip() if isinstance(deployed_build_raw, str) else ""

    have_sha = bool(deployed_sha)
    have_build = bool(deployed_build)

    if not have_sha and not have_build:
        errors.append(
            "deploy attestation must include non-empty deployed_commit_sha "
            f"and/or deployed_build_id (with expected_build_id when using build proof): {path}"
        )
        return errors

    if have_sha:
        exp_norm = _normalize_git_sha(expected_head_sha_raw)
        dep_norm = _normalize_git_sha(deployed_sha)
        if exp_norm != dep_norm:
            errors.append(
                "deploy attestation deployed_commit_sha does not match expected_head_sha "
                f"(deployed={deployed_sha!r}, expected={expected_head_sha_raw!r}): {path}"
            )
        return errors

    # Build-ID proof path
    eb_raw = payload.get("expected_build_id")
    expected_build = eb_raw.strip() if isinstance(eb_raw, str) else ""
    if not expected_build:
        errors.append(
            "deploy attestation uses deployed_build_id but expected_build_id "
            f"is missing or empty (cannot verify branch/build alignment): {path}"
        )
        return errors
    if deployed_build != expected_build:
        errors.append(
            "deploy attestation deployed_build_id does not match expected_build_id "
            f"({deployed_build!r} vs {expected_build!r}): {path}"
        )
    return errors


def _sample_selected(*, handoff_id: str, task_id: str, sample_rate: float) -> bool:
    if sample_rate <= 0:
        return False
    if sample_rate >= 1:
        return True
    seed = f"{handoff_id}::{task_id}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()
    value = int(digest[:8], 16) / 0xFFFFFFFF
    return value < sample_rate


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="canon flow-audit", description="Audit task-level agent flow artifacts.")
    parser.add_argument("--handoff-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--plan-file", default="")
    parser.add_argument("--sample-rate", type=float, default=1.0)
    parser.add_argument("--require-release-status", action="store_true")
    parser.add_argument("--require-memory-health", action="store_true")
    parser.add_argument(
        "--require-checkpoints",
        action="store_true",
        help="Require valid per-phase checkpoint artifacts under checkpoints/.",
    )
    parser.add_argument("--require-deploy-attestation", action="store_true")
    args = parser.parse_args(argv)

    sample_rate = max(0.0, min(1.0, float(args.sample_rate)))
    if not _sample_selected(handoff_id=args.handoff_id, task_id=args.task_id, sample_rate=sample_rate):
        print("flow-audit: SKIPPED (not selected by sample)")
        return 0

    root = repo_root()
    base = root / ".cursor" / "handoffs" / args.handoff_id / args.task_id
    required = {
        "scoper.md": "HANDOFF_TO_CURSOR_PILOT",
        "cursor-pilot.md": "CURSOR_PILOT_PROMPT",
        "qa-gate.md": "GATE_RESULTS",
    }
    if args.require_release_status:
        required["release-status.md"] = "RELEASE_STATUS"

    errors: list[str] = []
    for name, token in required.items():
        path = base / name
        if not path.exists():
            errors.append(f"missing artifact file: {path}")
            continue
        body = path.read_text(encoding="utf-8")
        if token not in body:
            errors.append(f"artifact missing required token '{token}': {path}")

    errors.extend(
        collect_dor_telemetry_errors_for_task(
            root=root,
            handoff_id=args.handoff_id,
            task_id=args.task_id,
            labels=DorTelemetryLabels.flow_audit(),
            require_task_identity=True,
            bulk_error_if_no_json=True,
        )
    )

    if args.require_memory_health:
        errors.extend(_collect_memory_health_errors(base))

    if args.plan_file:
        plan = Path(args.plan_file)
        if not plan.is_absolute():
            plan = (root / plan).resolve()
        if not plan.exists():
            errors.append(f"plan file not found: {plan}")
        else:
            content = plan.read_text(encoding="utf-8")
            if args.task_id not in content:
                errors.append(f"task_id not referenced in plan file: {args.task_id}")

    if args.require_checkpoints:
        errors.extend(
            _collect_checkpoint_errors(
                root=root,
                handoff_id=args.handoff_id,
                task_id=args.task_id,
            )
        )

    if args.require_deploy_attestation:
        errors.extend(
            _collect_deploy_attestation_errors(
                base,
                handoff_id=args.handoff_id,
                task_id=args.task_id,
            )
        )

    if errors:
        print("flow-audit: FAILED")
        for err in errors:
            print(f"- {err}")
        return 1

    print("flow-audit: PASS")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
