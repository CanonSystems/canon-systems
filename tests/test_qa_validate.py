from __future__ import annotations

import json
from pathlib import Path

from canon_systems.checkpoints import REQUIRED_PHASES
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
            "--require-checkpoints",
            "--handoff-id",
            "h1",
            "--task-id",
            "t1",
        ]
    )
    assert code == 0
