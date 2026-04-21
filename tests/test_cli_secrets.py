from pathlib import Path

from canon_systems import cli


def test_secrets_defaults_to_wizard_without_subcommand(monkeypatch, tmp_path: Path) -> None:
    captured: list[list[str]] = []
    monkeypatch.delenv("CANON_SYSTEMS_REPO_ROOT", raising=False)
    monkeypatch.delenv("CANON_MEMORY_LAYER_REPO_ROOT", raising=False)
    monkeypatch.setattr(cli, "detect_repo_root", lambda explicit="": tmp_path)
    monkeypatch.setattr(cli, "_maybe_auto_rewire", lambda root, command: None)
    monkeypatch.setattr(cli, "_maybe_auto_rewire_all", lambda command: None)
    monkeypatch.setattr(cli, "run_secrets_submit", lambda argv: captured.append(argv) or 0)

    code = cli.main(["secrets"])
    assert code == 0
    assert captured == [["wizard"]]
