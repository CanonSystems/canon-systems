"""Validate persisted QA gate packets for merge governance."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .checkpoints import _collect_checkpoint_errors
from .dor_telemetry import DorTelemetryLabels, collect_dor_telemetry_errors_for_task
from .shared import repo_root


def _extract_gate_block(text: str) -> str:
    start = text.find("GATE_RESULTS")
    end = text.find("END_GATE_RESULTS")
    if start < 0 or end < 0 or end <= start:
        return ""
    return text[start : end + len("END_GATE_RESULTS")]


def _leading_space_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


_ALLOWED_COVERING_TEST_KINDS: frozenset[str] = frozenset({"pytest", "manual", "shell", "browser"})
_ALLOWED_KINDS_DISPLAY = "pytest, manual, shell, browser"

_ITEM_BODY_RE = re.compile(r"^\s*-\s+(.*)$")
_LABELED_KIND_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$")


def _head_looks_like_unprefixed_pytest_path(head: str) -> bool:
    if not head or head in _ALLOWED_COVERING_TEST_KINDS:
        return False
    return "/" in head or head.endswith(".py") or head.startswith("tests/")


def _strip_yaml_scalar_quotes(raw: str) -> str:
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1].strip()
    return s


@dataclass(frozen=True)
class _CoveringTestEntry:
    """Evidence entry parsed from a criterion covering_tests list (ws1 schema)."""

    line_no: int
    kind: str
    text: str


def _parse_covering_tests_item_line(*, line_no: int, line: str) -> _CoveringTestEntry | str:
    """
    Parse one list item line under covering_tests.

    Supports unprefixed pytest node ids (``tests/a.py::test_x``), ``kind::…`` prefixes,
    and single-colon labeled entries (``manual: …``).

    Returns ``_CoveringTestEntry`` on success, or an error message string.
    """
    m = _ITEM_BODY_RE.match(line)
    if not m:
        return f"line {line_no}: malformed covering_tests list item (expected leading '- ')"
    body = m.group(1).strip()

    raw = _strip_yaml_scalar_quotes(body)
    if not raw.strip():
        return f"line {line_no}: empty covering_tests entry"
    if raw.startswith(":"):
        return (
            f"line {line_no}: empty evidence kind in covering_tests "
            f"(allowed kinds: {_ALLOWED_KINDS_DISPLAY})"
        )

    # Explicit ``kind::`` labels (preserve unprefixed ``path::node`` by trying these first).
    for kind in ("pytest", "manual", "shell", "browser"):
        prefix = f"{kind}::"
        if raw.startswith(prefix):
            return _CoveringTestEntry(line_no=line_no, kind=kind, text=raw[len(prefix) :])

    # Single-colon YAML-style ``kind: value`` (only when the key is a known kind).
    labeled = _LABELED_KIND_RE.match(body)
    if labeled:
        kind_raw = labeled.group(1).strip()
        rest = labeled.group(2)
        if not kind_raw:
            return (
                f"line {line_no}: empty evidence kind in covering_tests "
                f"(allowed kinds: {_ALLOWED_KINDS_DISPLAY})"
            )
        kind_l = kind_raw.lower()
        if kind_l not in _ALLOWED_COVERING_TEST_KINDS:
            return (
                f"line {line_no}: unknown evidence kind {kind_raw!r} in covering_tests "
                f"(allowed kinds: {_ALLOWED_KINDS_DISPLAY})"
            )
        text = _strip_yaml_scalar_quotes(rest)
        return _CoveringTestEntry(line_no=line_no, kind=kind_l, text=text)

    # Unprefixed ``path::node`` vs ``unknownLabel::…``.
    if "::" in raw:
        head, tail = raw.split("::", 1)
        if head == "":
            return (
                f"line {line_no}: empty evidence kind in covering_tests "
                f"(allowed kinds: {_ALLOWED_KINDS_DISPLAY})"
            )
        if head in _ALLOWED_COVERING_TEST_KINDS:
            return _CoveringTestEntry(line_no=line_no, kind=head, text=tail)
        if _head_looks_like_unprefixed_pytest_path(head):
            return _CoveringTestEntry(line_no=line_no, kind="pytest", text=raw)
        return (
            f"line {line_no}: unknown evidence kind {head!r} in covering_tests "
            f"(allowed kinds: {_ALLOWED_KINDS_DISPLAY})"
        )

    return _CoveringTestEntry(line_no=line_no, kind="pytest", text=raw)


def _finalize_criterion_covering_tests_structure(
    *,
    crit_line: int,
    has_covering_tests_key: bool,
    covering_tests_key_line: int | None,
    list_item_count: int,
    list_marker_lines: int,
) -> list[str]:
    """Emit structure errors for a single ``- criterion:`` block (ws2)."""
    errs: list[str] = []
    if not has_covering_tests_key:
        errs.append(f"line {crit_line}: acceptance criterion missing covering_tests")
        return errs
    if (
        list_item_count == 0
        and list_marker_lines == 0
        and covering_tests_key_line is not None
    ):
        errs.append(f"line {covering_tests_key_line}: covering_tests has no list items")
    return errs


def _extract_covering_tests_entries(
    lines: list[str], gate_start_idx: int, gate_end_idx: int
) -> tuple[list[_CoveringTestEntry], list[str], list[str]]:
    """
    Collect covering_tests list items only from ``acceptance_criteria`` / ``- criterion`` blocks.

    Line indices are 0-based into ``lines``; ``gate_*`` bound the GATE_RESULTS region inclusive.

    Returns ``(entries, parse_errors, structure_errors)``.
    """
    entries: list[_CoveringTestEntry] = []
    parse_errors: list[str] = []
    structure_errors: list[str] = []
    ac_indent: int | None = None
    i = gate_start_idx

    while i <= gate_end_idx:
        line = lines[i]
        stripped = line.strip()
        ind = _leading_space_indent(line)

        if ac_indent is None:
            if stripped.startswith("acceptance_criteria:"):
                ac_indent = ind
            i += 1
            continue

        assert ac_indent is not None

        if stripped and ind <= ac_indent and not stripped.startswith("- criterion"):
            ac_indent = None
            i += 1
            continue

        crit_marker = ac_indent + 2
        if ind == crit_marker and stripped.startswith("- criterion:"):
            crit_line = i + 1
            has_covering_tests_key = False
            covering_tests_key_line: int | None = None
            list_item_count = 0
            list_marker_lines = 0
            i += 1
            while i <= gate_end_idx:
                line_inner = lines[i]
                stripped_inner = line_inner.strip()
                ind_inner = _leading_space_indent(line_inner)

                if ind_inner == crit_marker and stripped_inner.startswith("- criterion:"):
                    structure_errors.extend(
                        _finalize_criterion_covering_tests_structure(
                            crit_line=crit_line,
                            has_covering_tests_key=has_covering_tests_key,
                            covering_tests_key_line=covering_tests_key_line,
                            list_item_count=list_item_count,
                            list_marker_lines=list_marker_lines,
                        )
                    )
                    break
                if stripped_inner and ind_inner <= ac_indent:
                    structure_errors.extend(
                        _finalize_criterion_covering_tests_structure(
                            crit_line=crit_line,
                            has_covering_tests_key=has_covering_tests_key,
                            covering_tests_key_line=covering_tests_key_line,
                            list_item_count=list_item_count,
                            list_marker_lines=list_marker_lines,
                        )
                    )
                    break

                if stripped_inner.startswith("covering_tests:"):
                    has_covering_tests_key = True
                    covering_tests_key_line = i + 1
                    ct_key_indent = ind_inner
                    list_marker_lines = 0
                    i += 1
                    while i <= gate_end_idx:
                        ln = lines[i]
                        ind_ln = _leading_space_indent(ln)
                        st_ln = ln.strip()
                        if not st_ln:
                            i += 1
                            continue
                        if ind_ln <= ct_key_indent:
                            break
                        if _ITEM_BODY_RE.match(ln):
                            list_marker_lines += 1
                        abs_ln = i + 1
                        parsed = _parse_covering_tests_item_line(line_no=abs_ln, line=ln)
                        if isinstance(parsed, str):
                            parse_errors.append(parsed)
                        else:
                            entries.append(parsed)
                            list_item_count += 1
                        i += 1
                    continue

                i += 1

            if i > gate_end_idx:
                structure_errors.extend(
                    _finalize_criterion_covering_tests_structure(
                        crit_line=crit_line,
                        has_covering_tests_key=has_covering_tests_key,
                        covering_tests_key_line=covering_tests_key_line,
                        list_item_count=list_item_count,
                        list_marker_lines=list_marker_lines,
                    )
                )
            continue

        i += 1

    return entries, parse_errors, structure_errors


def _covering_tests_entries_from_packet(packet_text: str) -> tuple[list[_CoveringTestEntry], list[str], list[str]]:
    """
    Parse covering_tests entries scoped to criterion blocks.

    Returns ``(entries, parse_errors, structure_errors)`` for malformed lines, invalid kinds, and
    missing/empty ``covering_tests`` keys per criterion.
    """
    lines = packet_text.splitlines()
    gate_start = gate_end = None
    for idx, line in enumerate(lines):
        st = line.strip()
        if st == "GATE_RESULTS" or st.startswith("GATE_RESULTS "):
            gate_start = idx
            break
    if gate_start is None:
        return [], [], []

    for j in range(gate_start, len(lines)):
        if "END_GATE_RESULTS" in lines[j]:
            gate_end = j
            break
    if gate_end is None:
        return [], [], []

    return _extract_covering_tests_entries(lines, gate_start, gate_end)


def _acceptance_criteria_line_no(lines: list[str], gate_start_idx: int, gate_end_idx: int) -> int | None:
    for idx in range(gate_start_idx, gate_end_idx + 1):
        if lines[idx].strip().startswith("acceptance_criteria:"):
            return idx + 1
    return None


def _collect_errors(block: str, *, packet_text: str, root: Path, require_pass: bool) -> list[str]:
    errors: list[str] = []
    required_tokens = ("handoff_id:", "verdict:", "acceptance_criteria:", "regression_checked:")
    for token in required_tokens:
        if token not in block:
            errors.append(f"missing required field token: {token}")

    verdict_match = re.search(r"^\s*verdict:\s*(\S+)", block, flags=re.M)
    verdict = verdict_match.group(1).strip() if verdict_match else ""
    if require_pass and verdict != "PASS":
        errors.append(f"verdict must be PASS for merge gate (found: {verdict or 'missing'})")

    entries, parse_errors, structure_errors = _covering_tests_entries_from_packet(packet_text)
    errors.extend(parse_errors)
    errors.extend(structure_errors)

    lines = packet_text.splitlines()
    gate_start = gate_end = None
    for idx, line in enumerate(lines):
        st = line.strip()
        if st == "GATE_RESULTS" or st.startswith("GATE_RESULTS "):
            gate_start = idx
            break
    if gate_start is not None:
        for j in range(gate_start, len(lines)):
            if "END_GATE_RESULTS" in lines[j]:
                gate_end = j
                break

    for ent in entries:
        if ent.kind in ("manual", "shell", "browser"):
            if not ent.text.strip():
                errors.append(
                    f"line {ent.line_no}: empty evidence text for {ent.kind} covering_tests entry "
                    f"(non-pytest kinds require a description)"
                )
            continue
        if ent.kind != "pytest":
            continue
        ref = ent.text.strip().strip('"').strip("'")
        if not ref:
            errors.append(f"line {ent.line_no}: empty pytest reference in covering_tests entry")
            continue
        path_part = ref.split("::", 1)[0].strip()
        if not path_part:
            errors.append(f"line {ent.line_no}: invalid test ref path in {ref!r}")
            continue
        if not (root / path_part).exists():
            errors.append(
                f"line {ent.line_no}: test file referenced by pytest evidence but missing: {path_part}"
            )

    if (
        not entries
        and not parse_errors
        and not structure_errors
        and gate_start is not None
        and gate_end is not None
    ):
        ac_ln = _acceptance_criteria_line_no(lines, gate_start, gate_end)
        loc = f"line {ac_ln}" if ac_ln is not None else "qa-gate packet"
        errors.append(f"{loc}: no covering_tests entries found under acceptance_criteria")
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
    parser.add_argument(
        "--require-checkpoints",
        action="store_true",
        help="Require valid per-phase checkpoint artifacts.",
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
    errors = _collect_errors(block, packet_text=text, root=root, require_pass=bool(args.require_pass))
    if args.require_dor_telemetry:
        if not args.handoff_id or not args.task_id:
            print("qa-validate: --require-dor-telemetry requires --handoff-id and --task-id")
            return 2
        errors.extend(
            collect_dor_telemetry_errors_for_task(
                root=root,
                handoff_id=args.handoff_id.strip(),
                task_id=args.task_id.strip(),
                labels=DorTelemetryLabels.qa_validate(),
                require_task_identity=False,
                bulk_error_if_no_json=False,
            )
        )
    if args.require_checkpoints:
        if not args.handoff_id or not args.task_id:
            print("qa-validate: --require-checkpoints requires --handoff-id and --task-id")
            return 2
        errors.extend(
            _collect_checkpoint_errors(
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
