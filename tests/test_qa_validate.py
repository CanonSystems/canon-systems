from __future__ import annotations

from pathlib import Path

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
