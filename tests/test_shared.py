import os
from pathlib import Path

from canon_systems.shared import (
    apply_layered_canon_env_for_repo,
    ensure_layered_memory_env,
    merge_canon_systems_env_files,
    repo_root,
    resolve_auth_bearer,
)


def test_merge_canon_systems_env_files_order(tmp_path: Path) -> None:
    a = tmp_path / "a.env"
    b = tmp_path / "b.env"
    a.write_text("FOO=1\nBAR=a\n", encoding="utf-8")
    b.write_text("BAR=b\nBAZ=2\n", encoding="utf-8")
    merged = merge_canon_systems_env_files([a, b])
    assert merged == {"FOO": "1", "BAR": "b", "BAZ": "2"}


def test_resolve_auth_bearer_profiles(monkeypatch) -> None:
    monkeypatch.delenv("CANON_HTTP_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("KNOWLEDGE_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("KNOWLEDGE_API_TOKEN", raising=False)
    monkeypatch.delenv("MEMORY_ADAPTER_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("KNOWLEDGE_WORKER_BEARER_TOKEN", raising=False)

    monkeypatch.setenv("CANON_HTTP_BEARER_TOKEN", "uni")
    assert resolve_auth_bearer("memory_adapter") == "uni"
    assert resolve_auth_bearer("knowledge_api") == "uni"

    monkeypatch.delenv("CANON_HTTP_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("MEMORY_ADAPTER_BEARER_TOKEN", "mem")
    assert resolve_auth_bearer("memory_adapter") == "mem"

    monkeypatch.setenv("KNOWLEDGE_API_BEARER_TOKEN", "kapi")
    assert resolve_auth_bearer("knowledge_api") == "kapi"


def test_repo_root_respects_explicit_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("CANON_MEMORY_LAYER_REPO_ROOT", str(tmp_path))
    assert repo_root() == tmp_path.resolve()


def test_ensure_layered_memory_env_loads_canon_systems_machine_env(monkeypatch, tmp_path: Path) -> None:
    canon_home = tmp_path / ".canon"
    canon_home.mkdir(parents=True, exist_ok=True)
    (canon_home / "canon-systems.env").write_text(
        "AWS_PROFILE=canon-systems\nAWS_REGION=us-east-1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("canon_systems.shared.Path.home", lambda: tmp_path)
    monkeypatch.setattr("canon_systems.shared.repo_root", lambda: tmp_path)
    monkeypatch.setattr("canon_systems.shared._LAYERED_MEMORY_ENV_APPLIED", False)
    monkeypatch.setattr("canon_systems.aws_secrets.apply_canon_systems_secrets_from_aws", lambda: None)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)

    ensure_layered_memory_env()
    assert os.environ.get("AWS_PROFILE") == "canon-systems"
    assert os.environ.get("AWS_REGION") == "us-east-1"


def test_apply_layered_env_sets_state_url_from_knowledge(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".canon").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "KNOWLEDGE_API_URL=http://k.example:8080\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("canon_systems.shared.Path.home", lambda: tmp_path)
    monkeypatch.delenv("CANON_STATE_API_URL", raising=False)
    monkeypatch.delenv("STATE_API_URL", raising=False)
    monkeypatch.delenv("KNOWLEDGE_API_URL", raising=False)
    monkeypatch.setattr("canon_systems.aws_secrets.apply_canon_systems_secrets_from_aws", lambda: None)

    apply_layered_canon_env_for_repo(tmp_path)
    assert os.environ.get("CANON_STATE_API_URL") == "http://k.example:8080"


def test_apply_layered_env_respects_explicit_state_url(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".canon").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "KNOWLEDGE_API_URL=http://k.example:8080\n"
        "CANON_STATE_API_URL=http://state.example:9000\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("canon_systems.shared.Path.home", lambda: tmp_path)
    monkeypatch.delenv("CANON_STATE_API_URL", raising=False)
    monkeypatch.delenv("STATE_API_URL", raising=False)
    monkeypatch.delenv("KNOWLEDGE_API_URL", raising=False)
    monkeypatch.setattr("canon_systems.aws_secrets.apply_canon_systems_secrets_from_aws", lambda: None)

    apply_layered_canon_env_for_repo(tmp_path)
    assert os.environ.get("CANON_STATE_API_URL") == "http://state.example:9000"
