from __future__ import annotations

import importlib.util
import os
import socket
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_fake_canon(bin_dir: Path, capture_file: Path) -> None:
    script_path = bin_dir / "canon"
    script_path.write_text(
        "#!/usr/bin/env bash\n"
        "{\n"
        "  echo __CALL__\n"
        "  printf '%s\\n' \"$@\"\n"
        "} >> \"${CAPTURE_FILE}\"\n",
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    capture_file.touch()


def _read_calls(capture_file: Path) -> list[list[str]]:
    raw = capture_file.read_text(encoding="utf-8").splitlines()
    calls: list[list[str]] = []
    current: list[str] = []
    for line in raw:
        if line == "__CALL__":
            if current:
                calls.append(current)
            current = []
            continue
        current.append(line)
    if current:
        calls.append(current)
    return calls


def test_rollout_script_invokes_phase_command(tmp_path: Path) -> None:
    root = _repo_root()
    capture_file = tmp_path / "canon-calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_fake_canon(bin_dir, capture_file)

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CAPTURE_FILE"] = str(capture_file)

    subprocess.run(
        [
            "bash",
            str(root / "scripts" / "auth-migration" / "rollout-phase.sh"),
            "prepare",
            "--dry-run",
            "--repo-root",
            "/tmp/repo-root",
            "--domain",
            "memory.example.com",
        ],
        check=True,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )

    calls = _read_calls(capture_file)
    assert len(calls) == 1
    assert calls[0] == [
        "--repo-root",
        "/tmp/repo-root",
        "auth-migration",
        "prepare",
        "--domain",
        "memory.example.com",
        "--scheme",
        "https",
        "--dry-run",
    ]


def test_rollback_script_invokes_rollback_then_status(tmp_path: Path) -> None:
    root = _repo_root()
    capture_file = tmp_path / "canon-calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_fake_canon(bin_dir, capture_file)

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CAPTURE_FILE"] = str(capture_file)

    subprocess.run(
        [
            "bash",
            str(root / "scripts" / "auth-migration" / "rollback.sh"),
            "--dry-run",
            "--repo-root",
            "/tmp/repo-root",
        ],
        check=True,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )

    calls = _read_calls(capture_file)
    assert len(calls) == 2
    assert calls[0] == [
        "--repo-root",
        "/tmp/repo-root",
        "auth-migration",
        "rollback",
        "--dry-run",
    ]
    assert calls[1] == ["--repo-root", "/tmp/repo-root", "auth-migration", "status"]


def test_secret_migration_rewrites_to_canonical_domain() -> None:
    root = _repo_root()
    module = _load_module(root / "scripts" / "migrate_memory_secrets.py", "migrate_memory_secrets")
    result = module._rewrite_payload(
        {"KNOWLEDGE_API_URL": "https://old.example.com"},
        "https://memory.canon-systems.com",
        "enforce",
    )
    assert result["KNOWLEDGE_API_URL"] == "https://memory.canon-systems.com"
    assert result["KNOWLEDGE_WORKER_URL"] == "https://memory.canon-systems.com"
    assert result["MEMORY_ADAPTER_URL"] == "https://memory.canon-systems.com"
    assert result["CANON_STATE_API_URL"] == "https://memory.canon-systems.com"
    assert result["CANON_AUTH_PHASE"] == "enforce"
    assert result["CANON_AUTH_MODE"] == "cognito"


def test_validate_script_connectivity_probe_and_ip_detection() -> None:
    root = _repo_root()
    module = _load_module(root / "scripts" / "validate_memory_endpoints.py", "validate_memory_endpoints")

    assert module._is_ip_host("127.0.0.1")
    assert not module._is_ip_host("memory.canon-systems.com")

    ok, detail, _info = module.validate_memory_url(
        key="CANON_STATE_API_URL", value="", timeout=0.5
    )
    assert ok and "skipped" in detail

    ok, detail, _info = module.validate_memory_url(
        key="KNOWLEDGE_API_URL", value="http://memory.example.com", timeout=0.5
    )
    assert not ok and "https" in detail

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    try:
        _host, port = listener.getsockname()
        ok, _detail, info = module.validate_memory_url(
            key="KNOWLEDGE_API_URL",
            value=f"https://localhost:{port}",
            timeout=0.5,
        )
        assert ok
        assert info.get("scheme") == "https"
    finally:
        listener.close()


def test_migration_and_rollback_docs_exist_with_expected_sections() -> None:
    root = _repo_root()
    migration_doc = root / "docs" / "migrations" / "cognito-ingress-migration.md"
    rollback_doc = root / "docs" / "runbooks" / "auth-migration-rollback.md"
    runtime_doc = root / "docs" / "MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
    onboarding_doc = root / "docs" / "ONBOARDING.md"

    assert migration_doc.exists()
    assert rollback_doc.exists()

    migration_text = migration_doc.read_text(encoding="utf-8")
    rollback_text = rollback_doc.read_text(encoding="utf-8")
    runtime_text = runtime_doc.read_text(encoding="utf-8")
    onboarding_text = onboarding_doc.read_text(encoding="utf-8")
    assert "## Phase Workflow" in migration_text
    assert "## Rollback Trigger" in migration_text
    assert "memory-layer__csc__canon-systems" in migration_text
    assert "## Rollback Steps" in rollback_text
    assert "memory-layer__csc__canon-systems" in rollback_text
    assert "canon doctor --fix-cache" in rollback_text
    assert "### 1.2c Stable dev memory URLs" in runtime_text
    assert "memory-layer__csc__canon-systems" in runtime_text
    assert "memory-layer__csc__canon-systems" in onboarding_text
    assert "## Verification Checklist" in rollback_text
