"""Validate persisted QA gate packets for merge governance."""

from __future__ import annotations

import argparse
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


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="canon qa-validate", description="Validate QA gate packet artifacts.")
    parser.add_argument("--file", required=True, help="Path to qa-gate packet file.")
    parser.add_argument("--require-pass", action="store_true", help="Fail unless verdict is PASS.")
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
