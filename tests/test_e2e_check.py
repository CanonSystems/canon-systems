"""Tests for `canon e2e-check` plug-and-play validation."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import canon_systems.e2e_check as e2e
import canon_systems.memory_health as mh
from canon_systems import __version__ as pkg_version


def _ok_200() -> dict:
    return {
        "http_status": 200,
        "body_text": '{"status":"ok","version":"1"}',
        "body_json": {"status": "ok", "version": "1"},
        "error": None,
        "latency_ms": 1,
    }


def _write_wired_repo(tmp: Path, *, pin: str) -> Path:
    (tmp / ".cursor" / "hooks").mkdir(parents=True)
    for name in ("memory-preflight.sh", "memory-capture.sh"):
        p = tmp / ".cursor" / "hooks" / name
        p.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
        p.chmod(0o755)
    (tmp / ".cursor" / "rules").mkdir(parents=True)
    (tmp / ".cursor" / "rules" / "memory-platform-build-discipline.mdc").write_text(
        "---\nalwaysApply: true\n---\n", encoding="utf-8"
    )
    (tmp / ".cursor" / "rules" / "memory-layer-defaults.mdc").write_text(
        "---\nalwaysApply: true\n---\n", encoding="utf-8"
    )
    (tmp / ".canon").mkdir(parents=True)
    (tmp / ".canon" / "memory-layer.local.env").write_text(
        f"CANON_SYSTEMS_VERSION={pin}\n"
        "KNOWLEDGE_API_URL=http://k.t\n"
        "MEMORY_ADAPTER_URL=http://m.t\n",
        encoding="utf-8",
    )
    return tmp


def test_e2e_check_passes_for_minimal_wired_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_wired_repo(tmp_path / "r", pin=pkg_version)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(root))
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    buf = io.StringIO()
    monkeypatch.setattr(e2e.sys, "stdout", buf)
    code = e2e.run([])
    assert code == 0
    payload = json.loads(buf.getvalue())
    assert payload["verdict"] == "PASS"
    assert payload["canon_version"] == pkg_version


def test_e2e_check_wraps_with_agent_delimiters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_wired_repo(tmp_path / "r", pin=pkg_version)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(root))
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    buf = io.StringIO()
    monkeypatch.setattr(e2e.sys, "stdout", buf)
    assert e2e.run(["--agent"]) == 0
    text = buf.getvalue()
    assert "<<<CANON_E2E_VERDICT_START>>>" in text
    assert "<<<CANON_E2E_VERDICT_END>>>" in text


def test_e2e_check_fails_when_hooks_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "bad"
    (root / ".canon").mkdir(parents=True)
    (root / ".canon" / "memory-layer.local.env").write_text(
        f"CANON_SYSTEMS_VERSION={pkg_version}\n"
        "KNOWLEDGE_API_URL=http://k.t\n"
        "MEMORY_ADAPTER_URL=http://m.t\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(root))
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    buf = io.StringIO()
    monkeypatch.setattr(e2e.sys, "stdout", buf)
    assert e2e.run([]) == 1
    payload = json.loads(buf.getvalue())
    assert payload["verdict"] == "FAIL"


def test_cli_dispatches_e2e_check(monkeypatch: pytest.MonkeyPatch) -> None:
    from canon_systems import cli

    captured: list[list[str]] = []

    def fake_run(argv: list[str] | None = None) -> int:
        captured.append(list(argv or []))
        return 0

    monkeypatch.setattr("canon_systems.e2e_check.run", fake_run)
    assert cli.main(["e2e-check", "--agent"]) == 0
    assert captured == [["--agent"]]
