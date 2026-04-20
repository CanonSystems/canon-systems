from pathlib import Path

from memory_layer.shared import merge_memory_layer_env_files, repo_root, resolve_auth_bearer


def test_merge_memory_layer_env_files_order(tmp_path: Path) -> None:
    a = tmp_path / "a.env"
    b = tmp_path / "b.env"
    a.write_text("FOO=1\nBAR=a\n", encoding="utf-8")
    b.write_text("BAR=b\nBAZ=2\n", encoding="utf-8")
    merged = merge_memory_layer_env_files([a, b])
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
    monkeypatch.setenv("CANON_MEMORY_LAYER_REPO_ROOT", str(tmp_path))
    assert repo_root() == tmp_path.resolve()
