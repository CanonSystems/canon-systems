import os
import sys
import time
from pathlib import Path

import pytest

from canon_systems import self_update


def test_should_skip_when_env_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_SKIP_SELF_UPDATE", "1")
    assert self_update.should_skip_self_update() is True


def test_should_skip_when_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI", "true")
    assert self_update.should_skip_self_update() is True


def test_not_pipx_venv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    assert self_update._is_pipx_canon_systems() is False


def test_is_pipx_canon_systems(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_py = tmp_path / "venvs" / "canon-systems" / "bin" / "python3.13"
    fake_py.parent.mkdir(parents=True)
    fake_py.touch()
    monkeypatch.setattr(sys, "executable", str(fake_py))
    assert self_update._is_pipx_canon_systems() is True


def test_try_self_update_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_SKIP_SELF_UPDATE", "1")
    called: list[str] = []

    def boom() -> None:
        called.append("pipx")

    monkeypatch.setattr(self_update, "_run_pipx_upgrade", boom)
    self_update.try_self_update(["canon", "setup"])
    assert called == []


def test_try_self_update_reexec_when_version_bumps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("CANON_SYSTEMS_SKIP_SELF_UPDATE", raising=False)
    monkeypatch.delenv("CI", raising=False)
    fake_py = tmp_path / "venvs" / "canon-systems" / "bin" / "python3.13"
    fake_py.parent.mkdir(parents=True)
    fake_py.touch()
    monkeypatch.setattr(sys, "executable", str(fake_py))

    phase = {"n": 0}

    def fake_dist(_venv: Path) -> str:
        phase["n"] += 1
        return "3.0.1" if phase["n"] == 1 else "3.0.2"

    monkeypatch.setattr(self_update, "_installed_dist_version", fake_dist)
    monkeypatch.setattr(self_update, "_run_pipx_upgrade", lambda: (0, "ok"))

    execv_args: list[tuple[str, list[str]]] = []

    def fake_execv(path: str, args: list[str]) -> None:
        execv_args.append((path, args))
        raise SystemExit(0)

    monkeypatch.setattr(os, "execv", fake_execv)
    def fake_which(name: str) -> str | None:
        if name == "pipx":
            return "/opt/bin/pipx"
        if name == "canon":
            return "/fake/canon"
        return None

    monkeypatch.setattr(self_update.shutil, "which", fake_which)

    with pytest.raises(SystemExit) as exc:
        self_update.try_self_update(["canon", "setup", "--repo-root", "/tmp/r"], force=True)
    assert exc.value.code == 0
    assert execv_args == [("/fake/canon", ["/fake/canon", "setup", "--repo-root", "/tmp/r"])]


def test_try_self_update_throttled_without_force(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("CANON_SYSTEMS_SKIP_SELF_UPDATE", raising=False)
    monkeypatch.delenv("CI", raising=False)
    fake_py = tmp_path / "venvs" / "canon-systems" / "bin" / "python3.13"
    fake_py.parent.mkdir(parents=True)
    fake_py.touch()
    monkeypatch.setattr(sys, "executable", str(fake_py))
    monkeypatch.setenv("CANON_SYSTEMS_SELF_UPDATE_INTERVAL_SEC", "3600")
    monkeypatch.setattr(self_update, "_self_update_state_path", lambda: tmp_path / "state.txt")
    (tmp_path / "state.txt").write_text(str(time.time()), encoding="utf-8")

    called: list[str] = []
    monkeypatch.setattr(self_update, "_run_pipx_upgrade", lambda: (called.append("x") or (0, "ok")))
    monkeypatch.setattr(self_update.shutil, "which", lambda name: "/bin/ok" if name in ("pipx", "canon") else None)
    monkeypatch.setattr(self_update, "_installed_dist_version", lambda _p: "3.0.4")

    self_update.try_self_update(["canon", "ask", "x"])
    assert called == []
