"""Validate persisted QA gate packets for merge governance."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .shared import repo_root


def _extract_gate_block(text: str) -> str:
    start = text.find("GATE_RESULTS")
    end = text.find("END_GATE_RESULTS")
    if start < 0 or end < 0 or end <= start:
        return ""
    return text[start : end + len("END_GATE_RESULTS")]


def _collect_errors(block: str, *, root: Path, require_pass: bool) -> list[str]:
    errors: list[str] = []
    required_tokens = ("handoff_id:", "verdict:", "acceptance_criteria:", "regression_checked:")
    for token in required_tokens:
        if token not in block:
            errors.append(f"missing required field token: {token}")

    verdict_match = re.search(r"^\s*verdict:\s*(\S+)", block, flags=re.M)
    verdict = verdict_match.group(1).strip() if verdict_match else ""
    if require_pass and verdict != "PASS":
        errors.append(f"verdict must be PASS for merge gate (found: {verdict or 'missing'})")

    test_refs = re.findall(r'^\s*-\s*"([^"]+::[^"]+)"\s*$', block, flags=re.M)
    test_refs += re.findall(r"^\s*-\s*([^\"\n]+::[^\n]+)\s*$", block, flags=re.M)
    normalized: list[str] = []
    for ref in test_refs:
        cleaned = ref.strip().strip('"').strip("'")
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    if not normalized:
        errors.append("no covering_tests references found")
    for ref in normalized:
        path_part = ref.split("::", 1)[0].strip()
        if not path_part:
            errors.append(f"invalid test ref path in {ref}")
            continue
        if not (root / path_part).exists():
            errors.append(f"test file referenced but missing: {path_part}")
    return errors


def _collect_rejection_telemetry_errors(*, root: Path, handoff_id: str, task_id: str) -> list[str]:
    errors: list[str] = []
    base = root / ".cursor" / "handoffs" / handoff_id / task_id
    rejection_dir = base / "handoff-not-ready"
    telemetry_dir = base / "dor-failure"
    rejection_packets = sorted(rejection_dir.glob("*.md")) if rejection_dir.exists() else []
    if not rejection_packets:
        return errors

    for packet in rejection_packets:
        stem = packet.stem
        payload_file = telemetry_dir / f"{stem}.json"
        status_file = telemetry_dir / f"{stem}.status"
        if not payload_file.exists():
            errors.append(f"missing DoR telemetry JSON for rejection packet: {packet}")
            continue
        if not status_file.exists():
            errors.append(f"missing DoR telemetry status file for rejection packet: {packet}")
            continue
        try:
            payload = json.loads(payload_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"invalid JSON in DoR telemetry file: {payload_file}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"DoR telemetry payload must be object: {payload_file}")
            continue
        if str(payload.get("handoff_id", "")).strip() != handoff_id:
            errors.append(f"DoR telemetry handoff_id mismatch in: {payload_file}")
        if not str(payload.get("stage", "")).strip():
            errors.append(f"DoR telemetry stage missing in: {payload_file}")
        if "exit_code:" not in status_file.read_text(encoding="utf-8"):
            errors.append(f"DoR telemetry status missing exit_code marker: {status_file}")
    return errors


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="canon qa-validate", description="Validate QA gate packet artifacts.")
    parser.add_argument("--file", required=True, help="Path to qa-gate packet file.")
    parser.add_argument("--require-pass", action="store_true", help="Fail unless verdict is PASS.")
    parser.add_argument("--handoff-id", default="", help="Handoff id for rejection telemetry checks.")
    parser.add_argument("--task-id", default="", help="Task id for rejection telemetry checks.")
    parser.add_argument(
        "--require-dor-telemetry",
        action="store_true",
        help="If HANDOFF_NOT_READY packets exist for this task, require matching DoR telemetry artifacts.",
    )
    args = parser.parse_args(argv)

    root = repo_root()
    packet = Path(args.file)
    if not packet.is_absolute():
        packet = (root / packet).resolve()
    if not packet.exists():
        print(f"qa-validate: packet file not found: {packet}")
        return 2
    text = packet.read_text(encoding="utf-8")
    block = _extract_gate_block(text)
    if not block:
        print("qa-validate: missing GATE_RESULTS block")
        return 2
    errors = _collect_errors(block, root=root, require_pass=bool(args.require_pass))
    if args.require_dor_telemetry:
        if not args.handoff_id or not args.task_id:
            print("qa-validate: --require-dor-telemetry requires --handoff-id and --task-id")
            return 2
        errors.extend(
            _collect_rejection_telemetry_errors(
                root=root,
                handoff_id=args.handoff_id.strip(),
                task_id=args.task_id.strip(),
            )
        )
    if errors:
        print("qa-validate: FAILED")
        for err in errors:
            print(f"- {err}")
        return 1
    print("qa-validate: PASS")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
