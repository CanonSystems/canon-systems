from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from canon_systems.checkpoints import REQUIRED_PHASES
from canon_systems.dor_telemetry import DorTelemetryLabels, collect_dor_telemetry_errors
from canon_systems import cli as canon_cli
from canon_systems.qa_validate import run


def test_qa_validate_passes_for_valid_gate_packet(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "tests/test_sample.py::test_ok"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    assert code == 0


def test_covering_tests_parser_ignores_non_covering_double_colon_list_items(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC1: only ``covering_tests:`` list items count; notes lists must not."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "tests/test_sample.py::test_ok"',
                "      run_result: pass",
                "  notes:",
                '    - "decoy::ignored_outside_covering_tests"',
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "decoy" not in out


def test_qa_validate_accepts_explicit_evidence_kinds(tmp_path: Path, monkeypatch) -> None:
    """AC2: explicit pytest / manual / shell / browser labels parse and validate."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "pytest::tests/test_sample.py::test_ok"',
                '        - "manual::Reviewed the flow"',
                '        - "shell::pytest -q tests/test_sample.py"',
                '        - "browser::https://example.com/run"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert run(["--file", str(packet), "--require-pass"]) == 0


def test_qa_validate_rejects_unknown_evidence_kind_with_allowed_kinds(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC2: unknown or empty kind must fail and list allowed kinds."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "boguskind::not_valid"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    out = capsys.readouterr().out
    assert code == 1
    assert "unknown evidence kind" in out
    assert "boguskind" in out
    assert "allowed kinds" in out

    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "::orphan"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    code2 = run(["--file", str(packet), "--require-pass"])
    out2 = capsys.readouterr().out
    assert code2 == 1
    assert "empty evidence kind" in out2
    assert "allowed kinds" in out2


def test_qa_validate_fails_when_test_file_missing(tmp_path: Path, monkeypatch) -> None:
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "tests/missing_test.py::test_nope"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    assert code == 1


def test_qa_validate_fails_without_gate_block(tmp_path: Path, monkeypatch) -> None:
    packet = tmp_path / "qa-gate.md"
    packet.write_text("no structured packet here\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    assert code == 2


def test_qa_validate_require_dor_telemetry_delegates_to_shared_helper(
    tmp_path: Path, monkeypatch
) -> None:
    """AC1: DoR validation routes through ``collect_dor_telemetry_errors_for_task``."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "tests/test_sample.py::test_ok"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    with patch(
        "canon_systems.qa_validate.collect_dor_telemetry_errors_for_task",
        autospec=True,
    ) as mock_collect:
        mock_collect.return_value = []
        code = run(
            [
                "--file",
                str(packet),
                "--require-pass",
                "--require-dor-telemetry",
                "--handoff-id",
                "h1",
                "--task-id",
                "t1",
            ]
        )
    assert code == 0
    mock_collect.assert_called_once()
    kwargs = mock_collect.call_args.kwargs
    assert kwargs["handoff_id"] == "h1"
    assert kwargs["task_id"] == "t1"
    assert kwargs["require_task_identity"] is False
    assert kwargs["bulk_error_if_no_json"] is False


def test_qa_validate_require_dor_telemetry_exits_2_without_handoff_or_task_id(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC4: missing --handoff-id / --task-id with --require-dor-telemetry exits 2."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--task-id",
            "t1",
        ]
    )
    assert code == 2
    assert "--require-dor-telemetry requires --handoff-id and --task-id" in capsys.readouterr().out
    code2 = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--handoff-id",
            "h1",
        ]
    )
    assert code2 == 2
    assert "--require-dor-telemetry requires --handoff-id and --task-id" in capsys.readouterr().out


def test_qa_validate_without_require_dor_telemetry_ignores_rejection_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    """AC5: qa-gate-only validation passes despite missing DoR telemetry when flag is off."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "tests/test_sample.py::test_ok"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rejection = tmp_path / ".cursor" / "handoffs" / "h1" / "t1" / "handoff-not-ready"
    rejection.mkdir(parents=True, exist_ok=True)
    (rejection / "scoper-20260424T010203Z.md").write_text(
        "HANDOFF_NOT_READY\nDOR_FAILURE_LOG:\n  stage: scoper\nEND_HANDOFF_NOT_READY\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert run(["--file", str(packet), "--require-pass"]) == 0


def test_qa_validate_rejects_missing_dor_telemetry_artifacts(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "tests/test_sample.py::test_ok"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rejection = tmp_path / ".cursor" / "handoffs" / "h1" / "t1" / "handoff-not-ready"
    rejection.mkdir(parents=True, exist_ok=True)
    (rejection / "scoper-20260424T010203Z.md").write_text(
        "HANDOFF_NOT_READY\nDOR_FAILURE_LOG:\n  stage: scoper\nEND_HANDOFF_NOT_READY\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    assert code == 1


def test_qa_validate_accepts_present_dor_telemetry_artifacts(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "tests/test_sample.py::test_ok"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    base = tmp_path / ".cursor" / "handoffs" / "h1" / "t1"
    rejection = base / "handoff-not-ready"
    telemetry = base / "dor-failure"
    rejection.mkdir(parents=True, exist_ok=True)
    telemetry.mkdir(parents=True, exist_ok=True)
    stem = "cursor-pilot-preflight-20260424T010203Z"
    (rejection / f"{stem}.md").write_text(
        "HANDOFF_NOT_READY\nDOR_FAILURE_LOG:\n  stage: cursor-pilot-preflight\nEND_HANDOFF_NOT_READY\n",
        encoding="utf-8",
    )
    (telemetry / f"{stem}.json").write_text(
        '{"handoff_id":"h1","stage":"cursor-pilot-preflight","task_id":"t1"}\n',
        encoding="utf-8",
    )
    (telemetry / f"{stem}.status").write_text("exit_code: 0\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    assert code == 0


def test_qa_validate_accepts_dor_telemetry_without_task_id(tmp_path: Path, monkeypatch) -> None:
    """AC3/AC5: existing DoR telemetry may omit task_id when it is otherwise scoped by path."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    base = tmp_path / ".cursor" / "handoffs" / "h1" / "t1"
    rejection = base / "handoff-not-ready"
    telemetry = base / "dor-failure"
    rejection.mkdir(parents=True, exist_ok=True)
    telemetry.mkdir(parents=True, exist_ok=True)
    stem = "cursor-pilot-preflight-20260424T010203Z"
    (rejection / f"{stem}.md").write_text(
        "HANDOFF_NOT_READY\nDOR_FAILURE_LOG:\n  stage: cursor-pilot-preflight\nEND_HANDOFF_NOT_READY\n",
        encoding="utf-8",
    )
    (telemetry / f"{stem}.json").write_text(
        '{"handoff_id":"h1","stage":"cursor-pilot-preflight"}\n',
        encoding="utf-8",
    )
    (telemetry / f"{stem}.status").write_text("exit_code: 0\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    assert code == 0


def _write_minimal_gate_packet(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "tests/test_sample.py::test_ok"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_valid_checkpoints(root: Path, *, handoff_id: str, task_id: str) -> None:
    base = root / ".cursor" / "handoffs" / handoff_id / task_id / "checkpoints"
    base.mkdir(parents=True, exist_ok=True)
    for phase in REQUIRED_PHASES:
        body = {
            "schema_version": "1",
            "phase": phase,
            "task_id": task_id,
            "handoff_id": handoff_id,
            "state_version": 1,
        }
        (base / f"{phase}.json").write_text(json.dumps(body) + "\n", encoding="utf-8")


def test_qa_validate_require_checkpoints_passes_on_valid_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    _write_valid_checkpoints(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-checkpoints",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    assert code == 0


def test_public_cli_qa_validate_forwards_require_checkpoints(
    tmp_path: Path, monkeypatch
) -> None:
    """ws2-cli-parity: top-level ``canon qa-validate`` forwards ``--require-checkpoints``."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    _write_valid_checkpoints(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.delenv("CANON_SYSTEMS_REPO_ROOT", raising=False)
    monkeypatch.delenv("CANON_MEMORY_LAYER_REPO_ROOT", raising=False)
    code = canon_cli.main(
        [
            "--repo-root",
            str(tmp_path),
            "qa-validate",
            "--file",
            str(packet),
            "--require-pass",
            "--require-checkpoints",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    assert code == 0


def test_top_level_help_lists_qa_validate_require_checkpoints(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC2/AC4: public parser documents checkpoint gate flag."""
    with pytest.raises(SystemExit) as ei:
        canon_cli.main(["--repo-root", str(tmp_path), "qa-validate", "--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "--require-checkpoints" in out
    assert "--require-dor-telemetry" in out


def test_qa_validate_require_checkpoints_fails_on_missing_checkpoint_file(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    _write_valid_checkpoints(tmp_path, handoff_id="h1", task_id="t1")
    (tmp_path / ".cursor" / "handoffs" / "h1" / "t1" / "checkpoints" / "scoper.json").unlink()
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-checkpoints",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert "qa-validate: FAILED" in out
    assert "missing checkpoint artifact" in out


def test_qa_validate_require_checkpoints_exits_2_without_handoff_or_task_id(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    _write_valid_checkpoints(tmp_path, handoff_id="h1", task_id="t1")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-checkpoints",
            "--task-id",
            "t1",
        ]
    )
    assert code == 2
    assert "--require-checkpoints requires --handoff-id and --task-id" in capsys.readouterr().out
    code2 = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-checkpoints",
            "--handoff-id",
            "h1",
        ]
    )
    assert code2 == 2
    assert "--require-checkpoints requires --handoff-id and --task-id" in capsys.readouterr().out


def test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    _write_valid_checkpoints(tmp_path, handoff_id="h1", task_id="t1")
    base = tmp_path / ".cursor" / "handoffs" / "h1" / "t1"
    rejection = base / "handoff-not-ready"
    telemetry = base / "dor-failure"
    rejection.mkdir(parents=True, exist_ok=True)
    telemetry.mkdir(parents=True, exist_ok=True)
    stem = "cursor-pilot-preflight-20260424T010203Z"
    (rejection / f"{stem}.md").write_text(
        "HANDOFF_NOT_READY\nDOR_FAILURE_LOG:\n  stage: cursor-pilot-preflight\nEND_HANDOFF_NOT_READY\n",
        encoding="utf-8",
    )
    (telemetry / f"{stem}.json").write_text(
        '{"handoff_id":"h1","stage":"cursor-pilot-preflight","task_id":"t1"}\n',
        encoding="utf-8",
    )
    (telemetry / f"{stem}.status").write_text("exit_code: 0\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--require-checkpoints",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    assert code == 0


def test_covering_tests_only_parsed_from_criterion_blocks(tmp_path: Path, monkeypatch) -> None:
    """AC1: stray list items outside acceptance_criterion covering_tests do not affect validation."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "tests/test_sample.py::test_ok"',
                "      run_result: pass",
                "  stray_section:",
                '    - "tests/missing_decoy.py::should_be_ignored"',
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    assert code == 0


def test_covering_tests_preserves_unprefixed_pytest_refs(tmp_path: Path, monkeypatch) -> None:
    """AC1: implicit pytest rows accept unprefixed ``path::node`` refs (no evidence kind label)."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                "        - tests/test_sample.py::test_ok",
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    assert code == 0


def test_unknown_covering_tests_kind_reports_allowed_kinds(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC2: unknown evidence kind fails with allowed kinds listed."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                "        - bogus_kind: whatever",
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    assert code == 1
    out = capsys.readouterr().out
    assert "unknown evidence kind" in out
    assert "pytest, manual, shell, browser" in out


def test_empty_manual_shell_browser_evidence_fails_with_line(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC3: manual/shell/browser require non-empty evidence text (no path check)."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    for kind in ("manual", "shell", "browser"):
        packet = tmp_path / "qa-gate.md"
        packet.write_text(
            "\n".join(
                [
                    "GATE_RESULTS",
                    '  handoff_id: "h1"',
                    "  verdict: PASS",
                    "  acceptance_criteria:",
                    '    - criterion: "c1"',
                    "      status: PASS",
                    "      covering_tests:",
                    f'        - "{kind}::"',
                    "      run_result: pass",
                    "  regression_checked: true",
                    "END_GATE_RESULTS",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
        assert run(["--file", str(packet), "--require-pass"]) == 1
        out = capsys.readouterr().out
        assert "empty evidence text" in out
        assert "line " in out
        assert kind in out


def test_pytest_missing_file_reports_packet_line(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC3/AC4: pytest evidence points to missing file with the covering_tests line number."""
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                '        - "tests/missing_test.py::test_nope"',
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    out = capsys.readouterr().out
    assert code == 1
    assert "line 8:" in out
    assert "test file referenced by pytest evidence but missing" in out


def test_criterion_missing_covering_tests_reports_line(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC4: missing covering_tests key includes criterion line number."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    out = capsys.readouterr().out
    assert code == 1
    assert "line 5:" in out
    assert "missing covering_tests" in out


def test_empty_covering_tests_list_reports_key_line(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC4: covering_tests with no list items reports the key line."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    out = capsys.readouterr().out
    assert code == 1
    assert "line 7:" in out
    assert "no list items" in out


def test_malformed_covering_tests_entry_reports_line(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC4: malformed rows inside covering_tests include the packet line number."""
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                "        tests/test_sample.py::test_ok",
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    out = capsys.readouterr().out
    assert code == 1
    assert "line 8:" in out
    assert "malformed covering_tests list item" in out


def test_no_covering_tests_anywhere_reports_acceptance_criteria_line(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC4: completely missing entries falls back to acceptance_criteria line hint."""
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    out = capsys.readouterr().out
    assert code == 1
    assert "line 4:" in out
    assert "no covering_tests entries found" in out


def test_empty_covering_tests_kind_reports_allowed_kinds(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC2: empty evidence kind fails with allowed kinds listed."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    packet.write_text(
        "\n".join(
            [
                "GATE_RESULTS",
                '  handoff_id: "h1"',
                "  verdict: PASS",
                "  acceptance_criteria:",
                '    - criterion: "c1"',
                "      status: PASS",
                "      covering_tests:",
                "        - : not-a-kind",
                "      run_result: pass",
                "  regression_checked: true",
                "END_GATE_RESULTS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(["--file", str(packet), "--require-pass"])
    assert code == 1
    out = capsys.readouterr().out
    assert "empty evidence kind" in out
    assert "pytest, manual, shell, browser" in out


def _dor_fixture_dirs(root: Path, *, stem: str) -> tuple[Path, Path]:
    base = root / ".cursor" / "handoffs" / "h1" / "t1"
    rejection = base / "handoff-not-ready"
    telemetry = base / "dor-failure"
    rejection.mkdir(parents=True, exist_ok=True)
    telemetry.mkdir(parents=True, exist_ok=True)
    (rejection / f"{stem}.md").write_text(
        "HANDOFF_NOT_READY\nDOR_FAILURE_LOG:\n  stage: x\nEND_HANDOFF_NOT_READY\n",
        encoding="utf-8",
    )
    return telemetry, rejection / f"{stem}.md"


def test_qa_validate_dor_telemetry_invalid_json_reports_payload_path(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC2: invalid/non-object telemetry JSON yields actionable file paths."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    telemetry, _rej = _dor_fixture_dirs(tmp_path, stem="e1")
    (telemetry / "e1.json").write_text("{not json\n", encoding="utf-8")
    (telemetry / "e1.status").write_text("exit_code: 0\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "invalid JSON in DoR telemetry file:" in out
    assert str(telemetry / "e1.json") in out

    (telemetry / "e1.json").write_text("[]\n", encoding="utf-8")
    code2 = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    out2 = capsys.readouterr().out
    assert code2 == 1
    assert "DoR telemetry payload must be object:" in out2


def test_qa_validate_dor_telemetry_missing_artifacts_reference_packet_path(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC2: missing JSON/status reference the rejection packet path."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    telemetry, rej_path = _dor_fixture_dirs(tmp_path, stem="n1")
    (telemetry / "n1.status").write_text("exit_code: 0\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "missing DoR telemetry JSON for rejection packet:" in out
    assert str(rej_path) in out

    (telemetry / "n1.json").write_text('{"handoff_id":"h1","stage":"s","task_id":"t1"}\n', encoding="utf-8")
    (telemetry / "n1.status").unlink()
    code2 = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    out2 = capsys.readouterr().out
    assert code2 == 1
    assert "missing DoR telemetry status file for rejection packet:" in out2
    assert str(rej_path) in out2


def test_qa_validate_dor_telemetry_identity_handoff_stage_task(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC3: handoff_id, stage, and task_id must align with CLI scope."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    telemetry, _rej = _dor_fixture_dirs(tmp_path, stem="id1")

    def run_case(payload: str, *, expect: str) -> None:
        (telemetry / "id1.json").write_text(payload + "\n", encoding="utf-8")
        (telemetry / "id1.status").write_text("exit_code: 0\n", encoding="utf-8")
        c = run(
            [
                "--file",
                str(packet),
                "--require-pass",
                "--require-dor-telemetry",
                "--handoff-id",
                "h1",
                "--task-id",
                "t1",
            ]
        )
        o = capsys.readouterr().out
        assert c == 1, o
        assert expect in o

    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    run_case(
        '{"handoff_id":"other","stage":"scoper","task_id":"t1"}',
        expect="DoR telemetry handoff_id mismatch",
    )
    run_case('{"handoff_id":"h1","stage":"","task_id":"t1"}', expect="DoR telemetry stage missing")
    run_case(
        '{"handoff_id":"h1","stage":"scoper","task_id":"wrong"}',
        expect="DoR telemetry task_id mismatch",
    )


def test_qa_validate_dor_telemetry_status_requires_exit_code_marker(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC4: status file must contain exit_code: marker."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    packet = tmp_path / "qa-gate.md"
    _write_minimal_gate_packet(packet)
    telemetry, _rej = _dor_fixture_dirs(tmp_path, stem="st1")
    (telemetry / "st1.json").write_text('{"handoff_id":"h1","stage":"scoper","task_id":"t1"}\n', encoding="utf-8")
    (telemetry / "st1.status").write_text("no marker here\n", encoding="utf-8")
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    code = run(
        [
            "--file",
            str(packet),
            "--require-pass",
            "--require-dor-telemetry",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "DoR telemetry status missing exit_code marker:" in out
    assert str(telemetry / "st1.status") in out


def test_collect_dor_telemetry_skips_task_id_when_absent_if_not_required(tmp_path: Path) -> None:
    """AC3: helper only enforces task_id when present unless require_task_identity."""
    base = tmp_path / ".cursor" / "handoffs" / "h1" / "t1"
    rej = base / "handoff-not-ready"
    tel = base / "dor-failure"
    rej.mkdir(parents=True, exist_ok=True)
    tel.mkdir(parents=True, exist_ok=True)
    stem = "x1"
    (rej / f"{stem}.md").write_text("HANDOFF_NOT_READY\n", encoding="utf-8")
    (tel / f"{stem}.json").write_text('{"handoff_id":"h1","stage":"scoper"}\n', encoding="utf-8")
    (tel / f"{stem}.status").write_text("exit_code: 0\n", encoding="utf-8")
    errs = collect_dor_telemetry_errors(
        rejection_packets=[rej / f"{stem}.md"],
        telemetry_dir=tel,
        handoff_id="h1",
        task_id="t1",
        labels=DorTelemetryLabels.qa_validate(),
        require_task_identity=False,
        bulk_error_if_no_json=False,
    )
    assert errs == []

    errs_req = collect_dor_telemetry_errors(
        rejection_packets=[rej / f"{stem}.md"],
        telemetry_dir=tel,
        handoff_id="h1",
        task_id="t1",
        labels=DorTelemetryLabels.qa_validate(),
        require_task_identity=True,
        bulk_error_if_no_json=False,
    )
    assert len(errs_req) == 1
    assert "task_id mismatch" in errs_req[0]
