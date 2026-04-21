from __future__ import annotations

from pathlib import Path

from canon_systems.auth_migration import run
from canon_systems.shared import load_env_file


def test_status_phase_reports_without_writing_env(tmp_path: Path) -> None:
    code = run(["status", "--repo-root", str(tmp_path)])
    assert code == 0
    assert not (tmp_path / ".canon" / "memory-layer.local.env").exists()


def test_prepare_phase_writes_domain_urls(tmp_path: Path) -> None:
    code = run([
        "prepare",
        "--repo-root",
        str(tmp_path),
        "--domain",
        "memory.canon-systems.com",
    ])
    assert code == 0
    env = load_env_file(tmp_path / ".canon" / "memory-layer.local.env")
    assert env["CANON_AUTH_PHASE"] == "prepare"
    assert env["CANON_AUTH_MODE"] == "dual"
    assert env["KNOWLEDGE_API_URL"] == "https://memory.canon-systems.com"
    assert env["KNOWLEDGE_WORKER_URL"] == "https://memory.canon-systems.com"
    assert env["MEMORY_ADAPTER_URL"] == "https://memory.canon-systems.com"


def test_dry_run_does_not_write_env(tmp_path: Path) -> None:
    code = run(["enforce", "--repo-root", str(tmp_path), "--dry-run"])
    assert code == 0
    assert not (tmp_path / ".canon" / "memory-layer.local.env").exists()


def test_canary_phase_sets_dual_mode(tmp_path: Path) -> None:
    code = run(["canary", "--repo-root", str(tmp_path)])
    assert code == 0
    env = load_env_file(tmp_path / ".canon" / "memory-layer.local.env")
    assert env["CANON_AUTH_PHASE"] == "canary"
    assert env["CANON_AUTH_MODE"] == "dual"


def test_rollback_restores_previous_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".canon" / "memory-layer.local.env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        "\n".join(
            [
                "CANON_AUTH_PHASE=enforce",
                "CANON_AUTH_MODE=cognito",
                "CANON_AUTH_PREVIOUS_MODE=dual",
                "CANON_AUTH_PREVIOUS_KNOWLEDGE_API_URL=https://old.example.com",
                "CANON_AUTH_PREVIOUS_KNOWLEDGE_WORKER_URL=https://old.example.com",
                "CANON_AUTH_PREVIOUS_MEMORY_ADAPTER_URL=https://old.example.com",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    code = run(["rollback", "--repo-root", str(tmp_path)])
    assert code == 0
    env = load_env_file(env_path)
    assert env["CANON_AUTH_PHASE"] == "rollback"
    assert env["CANON_AUTH_MODE"] == "dual"
    assert env["KNOWLEDGE_API_URL"] == "https://old.example.com"
