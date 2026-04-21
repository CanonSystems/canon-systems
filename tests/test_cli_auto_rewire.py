from pathlib import Path

from canon_systems import cli


def _write_pin(root: Path, version: str, *, legacy: bool = False) -> None:
    env = root / ".canon" / "memory-layer.local.env"
    env.parent.mkdir(parents=True, exist_ok=True)
    key = "CANON_MEMORY_LAYER_VERSION" if legacy else "CANON_SYSTEMS_VERSION"
    env.write_text(f"{key}={version}\n", encoding="utf-8")


def test_auto_rewire_runs_when_installed_newer(monkeypatch, tmp_path: Path) -> None:
    _write_pin(tmp_path, "3.0.0")
    monkeypatch.setattr(cli, "__version__", "3.0.4")
    calls: list[Path] = []
    monkeypatch.setattr(cli, "enable_repo", lambda root: calls.append(root))
    monkeypatch.delenv("CANON_SYSTEMS_DISABLE_AUTO_REWIRE", raising=False)

    cli._maybe_auto_rewire(tmp_path, "capture")
    assert calls == [tmp_path]


def test_auto_rewire_skips_when_equal_or_older(monkeypatch, tmp_path: Path) -> None:
    _write_pin(tmp_path, "3.0.4")
    monkeypatch.setattr(cli, "__version__", "3.0.4")
    calls: list[Path] = []
    monkeypatch.setattr(cli, "enable_repo", lambda root: calls.append(root))

    cli._maybe_auto_rewire(tmp_path, "ask")
    assert calls == []


def test_auto_rewire_honors_disable_env(monkeypatch, tmp_path: Path) -> None:
    _write_pin(tmp_path, "3.0.0")
    monkeypatch.setattr(cli, "__version__", "3.0.4")
    calls: list[Path] = []
    monkeypatch.setattr(cli, "enable_repo", lambda root: calls.append(root))
    monkeypatch.setenv("CANON_SYSTEMS_DISABLE_AUTO_REWIRE", "1")

    cli._maybe_auto_rewire(tmp_path, "capture")
    assert calls == []


def test_auto_rewire_skips_setup_enable_repo(monkeypatch, tmp_path: Path) -> None:
    _write_pin(tmp_path, "3.0.0", legacy=True)
    monkeypatch.setattr(cli, "__version__", "3.0.4")
    calls: list[Path] = []
    monkeypatch.setattr(cli, "enable_repo", lambda root: calls.append(root))

    cli._maybe_auto_rewire(tmp_path, "setup")
    cli._maybe_auto_rewire(tmp_path, "enable-repo")
    assert calls == []


def test_auto_rewire_all_refreshes_multiple_repos_once(monkeypatch, tmp_path: Path) -> None:
    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    for repo in (repo_a, repo_b):
        (repo / ".git").mkdir(parents=True)
        _write_pin(repo, "3.0.0")
    monkeypatch.setattr(cli, "__version__", "3.1.0")
    monkeypatch.setenv("CANON_SYSTEMS_REWIRE_ROOTS", str(tmp_path))
    state_path = tmp_path / "rewire-state.json"
    monkeypatch.setattr(cli, "_global_rewire_state_path", lambda: state_path)
    touched: list[Path] = []
    monkeypatch.setattr(cli, "enable_repo", lambda root: touched.append(root))

    cli._maybe_auto_rewire_all("ask")
    assert sorted(touched) == sorted([repo_a, repo_b])
    # Second run on same version should no-op.
    cli._maybe_auto_rewire_all("ask")
    assert sorted(touched) == sorted([repo_a, repo_b])


def test_auto_rewire_all_honors_disable_flag(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    _write_pin(repo, "3.0.0")
    monkeypatch.setattr(cli, "__version__", "3.1.0")
    monkeypatch.setenv("CANON_SYSTEMS_REWIRE_ROOTS", str(tmp_path))
    monkeypatch.setenv("CANON_SYSTEMS_DISABLE_GLOBAL_REWIRE", "1")
    state_path = tmp_path / "rewire-state.json"
    monkeypatch.setattr(cli, "_global_rewire_state_path", lambda: state_path)
    touched: list[Path] = []
    monkeypatch.setattr(cli, "enable_repo", lambda root: touched.append(root))

    cli._maybe_auto_rewire_all("capture")
    assert touched == []
