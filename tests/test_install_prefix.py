from pathlib import Path

import pytest

from canon_systems import aws_secrets
from canon_systems.install_wizard import resolve_setup_secret_prefix


def test_resolve_prefix_prefers_existing_repo_env(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / ".canon").mkdir(parents=True)
    (root / ".canon" / "memory-layer.local.env").write_text(
        "MEMORY_LAYER_AWS_SECRET_NAME_PREFIX=from-file\n",
        encoding="utf-8",
    )
    prefix, src = resolve_setup_secret_prefix(
        root,
        "IMC",
        "innermost",
        region="us-east-1",
        profile="test-profile",
        ent={"aws_secret_name_prefix": "from-registry"},
    )
    assert prefix == "from-file"
    assert "memory-layer.local.env" in src


def test_resolve_prefix_registry_when_no_file(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    prefix, src = resolve_setup_secret_prefix(
        root,
        "IMC",
        "innermost",
        region="us-east-1",
        profile="test-profile",
        ent={"aws_secret_name_prefix": "registry-prefix"},
    )
    assert prefix == "registry-prefix"
    assert "registry" in src


def test_resolve_prefix_default_when_aws_probe_finds_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    monkeypatch.setattr(
        aws_secrets,
        "discover_memory_layer_secret_prefix",
        lambda *a, **k: None,
    )
    prefix, src = resolve_setup_secret_prefix(
        root,
        "IMC",
        "innermost",
        region="us-east-1",
        profile="test-profile",
        ent={},
    )
    assert prefix == aws_secrets.DEFAULT_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX
    assert "default" in src.lower()
