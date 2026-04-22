"""Validate agent-flow artifacts for a task without code review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .shared import repo_root


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

    # If any HANDOFF_NOT_READY packets were persisted, require matching
    # telemetry artifacts from parent orchestration.
    rejection_dir = base / "handoff-not-ready"
    telemetry_dir = base / "dor-failure"
    rejection_packets = sorted(rejection_dir.glob("*.md")) if rejection_dir.exists() else []
    telemetry_json = sorted(telemetry_dir.glob("*.json")) if telemetry_dir.exists() else []
    telemetry_status = sorted(telemetry_dir.glob("*.status")) if telemetry_dir.exists() else []

    if rejection_packets and not telemetry_json:
        errors.append(
            "HANDOFF_NOT_READY packets exist but no DoR telemetry JSON files found under "
            f"{telemetry_dir}"
        )

    for packet in rejection_packets:
        stem = packet.stem
        json_path = telemetry_dir / f"{stem}.json"
        status_path = telemetry_dir / f"{stem}.status"
        if not json_path.exists():
            errors.append(f"missing DoR telemetry JSON for rejection packet: {packet}")
            continue
        if not status_path.exists():
            errors.append(f"missing DoR telemetry status file for rejection packet: {packet}")
            continue
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"invalid JSON in telemetry file: {json_path}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"telemetry payload must be object: {json_path}")
            continue
        if str(payload.get("handoff_id", "")).strip() != args.handoff_id:
            errors.append(f"telemetry handoff_id mismatch in: {json_path}")
        if not str(payload.get("stage", "")).strip():
            errors.append(f"telemetry stage missing in: {json_path}")
        status_text = status_path.read_text(encoding="utf-8")
        if "exit_code:" not in status_text:
            errors.append(f"telemetry status missing exit_code marker: {status_path}")

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
