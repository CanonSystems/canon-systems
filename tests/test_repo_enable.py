import json
from pathlib import Path

from canon_systems import __version__
from canon_systems.repo_enable import enable_repo


def test_enable_repo_writes_hooks_rule_agents_and_version(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    enable_repo(repo)

    # Hooks
    assert (repo / ".cursor" / "hooks" / "memory-preflight.sh").exists()
    assert (repo / ".cursor" / "hooks" / "memory-capture.sh").exists()

    hooks_json = repo / ".cursor" / "hooks.json"
    assert hooks_json.exists()
    payload = json.loads(hooks_json.read_text(encoding="utf-8"))
    before = payload["hooks"]["beforeSubmitPrompt"]
    after = payload["hooks"]["afterAgentResponse"]
    assert any(item.get("command") == "bash .cursor/hooks/memory-preflight.sh" for item in before)
    assert any(item.get("command") == "bash .cursor/hooks/memory-capture.sh" for item in after)

    # Rule
    assert (repo / ".cursor" / "rules" / "memory-layer-defaults.mdc").exists()

    # Subagents
    for name in ("scoper.md", "cursor-pilot.md", "implementer.md", "qa-gate.md"):
        assert (repo / ".cursor" / "agents" / name).exists(), f"missing subagent {name}"

    # Version pin (new key)
    env_path = repo / ".canon" / "memory-layer.local.env"
    assert env_path.exists()
    body = env_path.read_text(encoding="utf-8")
    assert f"CANON_SYSTEMS_VERSION={__version__}" in body
    # Legacy key should not be re-emitted when pinning.
    assert "CANON_MEMORY_LAYER_VERSION=" not in body


def test_enable_repo_strips_legacy_version_pin(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    env_path = repo / ".canon" / "memory-layer.local.env"
    env_path.parent.mkdir(parents=True)
    env_path.write_text(
        "CANON_MEMORY_LAYER_VERSION=0.1.0\nCOMPANY_ID=FMO\n",
        encoding="utf-8",
    )

    enable_repo(repo)
    body = env_path.read_text(encoding="utf-8")
    assert f"CANON_SYSTEMS_VERSION={__version__}" in body
    assert "CANON_MEMORY_LAYER_VERSION" not in body
    assert "COMPANY_ID=FMO" in body, "unrelated keys preserved"


def test_enable_repo_merges_existing_hooks_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".cursor").mkdir(parents=True)
    (repo / ".cursor" / "hooks.json").write_text(
        json.dumps(
            {
                "version": 1,
                "hooks": {
                    "beforeSubmitPrompt": [
                        {"command": "bash .cursor/hooks/custom.sh", "timeout": 10}
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    enable_repo(repo)
    parsed = json.loads((repo / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    commands = [h.get("command") for h in parsed["hooks"]["beforeSubmitPrompt"]]
    assert "bash .cursor/hooks/custom.sh" in commands, "pre-existing hook preserved"
    assert "bash .cursor/hooks/memory-preflight.sh" in commands, "memory-layer hook added"
