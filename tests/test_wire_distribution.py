"""E7-T1 — canon wire distribution of the hard-lock rule.

Asserts that the workspace's `.cursor/rules/memory-platform-build-discipline.mdc`
is packaged as a canon-systems template and installed byte-identically into
every wired repo by `enable_repo`.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from canon_systems.repo_enable import enable_repo, install_user_scope


_RULE_BASENAME = "memory-platform-build-discipline.mdc"
_WORKSPACE_RULE = Path(".cursor/rules") / _RULE_BASENAME


def _template_rule_bytes() -> bytes:
    with resources.files("canon_systems.templates.rules").joinpath(_RULE_BASENAME).open("rb") as src:
        return src.read()


def test_template_rule_is_packaged() -> None:
    assert _template_rule_bytes(), "hard-lock rule template must not be empty"


def test_hard_lock_includes_experimental_multilane_opt_in_section() -> None:
    text = _template_rule_bytes().decode("utf-8")
    assert "## 11. Experimental parent-session multilane orchestration (opt-in only)" in text
    assert "CANON_EXPERIMENTAL_MULTILANE_ORCHESTRATION" in text
    assert "canon resume --tasks-file <path> --lanes" in text


def test_template_rule_byte_identical_to_workspace() -> None:
    ws = Path(_WORKSPACE_RULE).read_bytes()
    tpl = _template_rule_bytes()
    assert ws == tpl, (
        "src/canon_systems/templates/rules/memory-platform-build-discipline.mdc "
        "must be byte-identical to the workspace rule so canon wire distributes "
        "the exact same hard-lock rule to every repo."
    )


def test_enable_repo_installs_hard_lock_rule(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    enable_repo(repo)
    installed = repo / ".cursor" / "rules" / _RULE_BASENAME
    assert installed.exists(), "hard-lock rule must be installed into .cursor/rules/"
    assert installed.read_bytes() == _template_rule_bytes(), (
        "installed rule must be byte-identical to the packaged template"
    )


def test_enable_repo_install_is_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    enable_repo(repo)
    first = (repo / ".cursor" / "rules" / _RULE_BASENAME).read_bytes()
    enable_repo(repo)
    second = (repo / ".cursor" / "rules" / _RULE_BASENAME).read_bytes()
    assert first == second, "repeated enable_repo must leave the rule byte-identical"


def test_install_user_scope_installs_hard_lock_rule(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))  # type: ignore[arg-type]
    install_user_scope()
    installed = home / ".cursor" / "rules" / _RULE_BASENAME
    assert installed.exists(), "user-scope install must include the hard-lock rule"
    assert installed.read_bytes() == _template_rule_bytes()
