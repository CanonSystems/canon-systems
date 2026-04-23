from __future__ import annotations

import json
from pathlib import Path

import pytest

import canon_systems.resume_engine as resume_engine
from canon_systems.resume_engine import run


def _base_argv(tmp_path: Path) -> list[str]:
    f = tmp_path / "t.json"
    f.write_text(
        json.dumps(
            [
                {"task_id": "A", "workstream_id": "ws1"},
            ]
        ),
        encoding="utf-8",
    )
    return [
        "--plan-id",
        "p1",
        "--company-id",
        "c1",
        "--repository-id",
        "r1",
        "--tasks-file",
        str(f),
    ]


def test_resume_cli_help_returns_0() -> None:
    assert run(["--help"]) == 0


def test_both_task_sources_is_usage_error(tmp_path: Path) -> None:
    tf = tmp_path / "a.json"
    tf.write_text("[]", encoding="utf-8")
    assert (
        run(
            [
                "--plan-id",
                "p",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--tasks-file",
                str(tf),
                "--handoffs-dir",
                str(tmp_path),
            ]
        )
        == 4
    )


def test_neither_task_source_is_usage_error() -> None:
    assert run(["--plan-id", "p", "--company-id", "c", "--repository-id", "r"]) == 4


def test_missing_tasks_file_is_not_found(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "nope.json"
    assert (
        run(
            [
                "--plan-id",
                "p",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--tasks-file",
                str(missing),
            ]
        )
        == 4
    )
    err = capsys.readouterr().err
    assert "not_found" in err


def test_resume_target_first_incomplete_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """B before A in task list: B implementer in progress is chosen over A qa-gate completed."""
    f = tmp_path / "t.json"
    f.write_text(
        json.dumps(
            [
                {"task_id": "B", "workstream_id": "ws-main"},
                {"task_id": "A", "workstream_id": "ws-main"},
            ]
        ),
        encoding="utf-8",
    )
    order = [
        (200, {"phase": "implementer", "phase_status": "in_progress"}, {}),
        (200, {"phase": "qa-gate", "phase_status": "completed"}, {}),
    ]
    i = 0

    def fake(url: str, *, timeout_ms: int) -> tuple:
        nonlocal i
        out = order[i]
        i += 1
        return out

    monkeypatch.setattr(resume_engine, "_http_request", fake)
    av = [
        "--plan-id",
        "p1",
        "--company-id",
        "c1",
        "--repository-id",
        "r1",
        "--tasks-file",
        str(f),
    ]
    assert run(av) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["resume_target"] == {
        "task_id": "B",
        "workstream_id": "ws-main",
        "phase": "implementer",
    }


def test_resume_target_none_when_all_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "t.json"
    f.write_text(
        json.dumps(
            [
                {"task_id": "x", "workstream_id": "ws1"},
            ]
        ),
        encoding="utf-8",
    )

    def fake(_url: str, *, timeout_ms: int) -> tuple:
        return (200, {"phase": "release-orchestrator", "phase_status": "completed"}, {})

    monkeypatch.setattr(resume_engine, "_http_request", fake)
    av = [
        "--plan-id",
        "p1",
        "--company-id",
        "c1",
        "--repository-id",
        "r1",
        "--tasks-file",
        str(f),
    ]
    assert run(av) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["resume_target"] is None
    assert out["resume_available"] is False


def test_resume_missing_checkpoint_points_to_scoper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "t.json"
    f.write_text(json.dumps([{"task_id": "t1", "workstream_id": "ws1"}]), encoding="utf-8")

    def fake(_url: str, *, timeout_ms: int) -> tuple:
        return (404, {"detail": {"error": "not_found"}}, {})

    monkeypatch.setattr(resume_engine, "_http_request", fake)
    av = _base_argv(tmp_path)
    assert run(av) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["resume_target"] == {
        "task_id": "A",
        "workstream_id": "ws1",
        "phase": "scoper",
    }


def test_crash_restart_scenario_task_b_cursor_pilot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "t.json"
    f.write_text(
        json.dumps(
            [
                {"task_id": "A", "workstream_id": "w"},
                {"task_id": "B", "workstream_id": "w"},
            ]
        ),
        encoding="utf-8",
    )
    order = [
        (200, {"phase": "release-orchestrator", "phase_status": "completed"}, {}),
        (200, {"phase": "cursor-pilot", "phase_status": "completed"}, {}),
    ]
    n = 0

    def fake(_url: str, *, timeout_ms: int) -> tuple:
        nonlocal n
        o = order[n]
        n += 1
        return o

    monkeypatch.setattr(resume_engine, "_http_request", fake)
    av = [
        "--plan-id",
        "p1",
        "--company-id",
        "c1",
        "--repository-id",
        "r1",
        "--tasks-file",
        str(f),
    ]
    assert run(av) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["resume_target"] == {
        "task_id": "B",
        "workstream_id": "w",
        "phase": "implementer",
    }


def test_idempotent_byte_equal_on_double_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "t.json"
    f.write_text(
        json.dumps(
            [
                {"task_id": "A", "workstream_id": "ws1"},
            ]
        ),
        encoding="utf-8",
    )

    def fake(_url: str, *, timeout_ms: int) -> tuple:
        return (404, None, {})

    monkeypatch.setattr(resume_engine, "_http_request", fake)
    av = _base_argv(tmp_path)
    run(av)
    first = capsys.readouterr().out
    run(av)
    second = capsys.readouterr().out
    assert first == second


def test_no_event_emission_in_module_source() -> None:
    src = Path(resume_engine.__file__).read_text(encoding="utf-8")
    for needle in ("CanonicalEvent", "event_type", "emit_event"):
        assert needle not in src


def test_transport_error_all_tasks_exit_5(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "t.json"
    f.write_text(
        json.dumps(
            [
                {"task_id": "a", "workstream_id": "w"},
                {"task_id": "b", "workstream_id": "w"},
            ]
        ),
        encoding="utf-8",
    )

    def fake(_url: str, *, timeout_ms: int) -> tuple:
        return (0, None, {"X-Canon-Transport-Error": "URLError"})

    monkeypatch.setattr(resume_engine, "_http_request", fake)
    av = [
        "--plan-id",
        "p",
        "--company-id",
        "c",
        "--repository-id",
        "r",
        "--tasks-file",
        str(f),
    ]
    assert run(av) == 5
    out = json.loads(capsys.readouterr().out)
    assert len(out["degraded_tasks"]) == 2


def test_transport_error_partial_degrade_resume_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "t.json"
    f.write_text(
        json.dumps(
            [
                {"task_id": "a", "workstream_id": "w"},
                {"task_id": "b", "workstream_id": "w"},
            ]
        ),
        encoding="utf-8",
    )
    order = [
        (0, None, {"X-Canon-Transport-Error": "x"}),
        (200, {"phase": "release-orchestrator", "phase_status": "completed"}, {}),
    ]
    n = 0

    def fake(_url: str, *, timeout_ms: int) -> tuple:
        nonlocal n
        o = order[n]
        n += 1
        return o

    monkeypatch.setattr(resume_engine, "_http_request", fake)
    av = [
        "--plan-id",
        "p",
        "--company-id",
        "c",
        "--repository-id",
        "r",
        "--tasks-file",
        str(f),
    ]
    assert run(av) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["resume_available"] is False


def test_output_envelope_keys_sorted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "t.json"
    f.write_text(json.dumps([{"task_id": "a", "workstream_id": "w"}]), encoding="utf-8")

    def fake(_url: str, *, timeout_ms: int) -> tuple:
        return (200, {"phase": "scoper", "phase_status": "in_progress"}, {})

    monkeypatch.setattr(resume_engine, "_http_request", fake)
    av = [
        "--plan-id",
        "p",
        "--company-id",
        "c",
        "--repository-id",
        "r",
        "--tasks-file",
        str(f),
    ]
    run(av)
    line = capsys.readouterr().out.strip()
    top_keys = list(json.loads(line).keys())
    assert top_keys == sorted(top_keys)


def test_handoffs_dir_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    d = tmp_path / "hand"
    d.mkdir()
    d.joinpath("E4-T1").mkdir()
    d.joinpath("E4-T2").mkdir()
    d.joinpath("other").mkdir()

    def fake(_url: str, *, timeout_ms: int) -> tuple:
        return (200, {"phase": "scoper", "phase_status": "in_progress"}, {})

    monkeypatch.setattr(resume_engine, "_http_request", fake)
    av = [
        "--plan-id",
        "p",
        "--company-id",
        "c",
        "--repository-id",
        "r",
        "--handoffs-dir",
        str(d),
    ]
    run(av)
    out = json.loads(capsys.readouterr().out)
    assert out["tasks_scanned"] == 2
    assert out["resume_target"] is not None
    assert out["resume_target"]["task_id"] == "E4-T1"
