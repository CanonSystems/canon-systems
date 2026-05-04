import json
import time

from canon_systems.aws_secrets import (
    build_aws_secrets_resolution_attestation,
    parse_secret_string,
)


def test_parse_secret_string_json() -> None:
    raw = json.dumps(
        {
            "CANON_HTTP_BEARER_TOKEN": "tok",
            "KNOWLEDGE_API_URL": "http://example",
            "FLAG": True,
        }
    )
    assert parse_secret_string(raw) == {
        "CANON_HTTP_BEARER_TOKEN": "tok",
        "KNOWLEDGE_API_URL": "http://example",
        "FLAG": "True",
    }


def test_parse_secret_string_dotenv() -> None:
    body = "# c\nCANON_HTTP_BEARER_TOKEN=abc\nFOO=bar\n"
    assert parse_secret_string(body) == {"CANON_HTTP_BEARER_TOKEN": "abc", "FOO": "bar"}


def test_build_aws_secrets_resolution_attestation_no_secret_id(monkeypatch) -> None:
    monkeypatch.delenv("MEMORY_LAYER_AWS_SECRET_ID", raising=False)
    monkeypatch.delenv("MEMORY_LAYER_AWS_SECRET_NAME_PREFIX", raising=False)
    monkeypatch.delenv("COMPANY_ID", raising=False)
    monkeypatch.delenv("REPOSITORY_ID", raising=False)
    monkeypatch.setenv("AWS_PROFILE", "canon-systems")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    att = build_aws_secrets_resolution_attestation()
    assert att["resolution"]["status"] == "no_secret_id"
    assert att["effective_aws_profile"] == "canon-systems"
    assert att["effective_aws_region"] == "us-east-1"
    assert att["cache_hit_when_known"] is None
    assert att["resolved_secret_id"] == ""
    assert "CANON_HTTP_BEARER_TOKEN" not in json.dumps(att)


def test_build_aws_secrets_resolution_attestation_cache_hit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("canon_systems.aws_secrets.Path.home", lambda: tmp_path)
    cache_dir = tmp_path / ".canon"
    cache_dir.mkdir(parents=True)
    monkeypatch.setenv("MEMORY_LAYER_AWS_SECRET_ID", "pref/my-secret")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    payload = {
        "secret_id": "pref/my-secret",
        "region_tag": "eu-west-1",
        "expires_at": time.time() + 3600,
        "env": {"KNOWLEDGE_API_URL": "http://x"},
    }
    (cache_dir / "memory-layer-aws-cache.json").write_text(json.dumps(payload), encoding="utf-8")
    att = build_aws_secrets_resolution_attestation()
    assert att["resolution"]["status"] == "cache_hit"
    assert att["cache_hit_when_known"] is True
    assert att["cache_exists"] is True
    assert att["resolved_secret_id"] == "pref/my-secret"


def test_build_aws_secrets_resolution_attestation_explicit_id_flag(monkeypatch) -> None:
    monkeypatch.setenv("MEMORY_LAYER_AWS_SECRET_ID", "explicit/name")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    monkeypatch.delenv("AWS_REGION", raising=False)
    att = build_aws_secrets_resolution_attestation()
    assert att["memory_layer_aws_secret_id_from_explicit_env"] is True
    assert att["effective_aws_region"] == "us-west-2"


def test_aws_secret_resolution_attestation_has_non_secret_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("canon_systems.aws_secrets.Path.home", lambda: tmp_path)
    monkeypatch.setenv("MEMORY_LAYER_AWS_SECRET_ID", "canon-memory-dev/memory-layer__co__repo")
    monkeypatch.setenv("AWS_PROFILE", "canon-systems")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    att = build_aws_secrets_resolution_attestation()

    assert att["effective_aws_profile"] == "canon-systems"
    assert att["effective_aws_region"] == "us-east-1"
    assert att["resolved_secret_id"] == "canon-memory-dev/memory-layer__co__repo"
    assert att["cache_path"].endswith(".canon/memory-layer-aws-cache.json")
    assert att["cache_exists"] is False
    assert att["cache_hit_when_known"] is False
    assert att["resolution"]["status"] == "cache_miss"
    assert "env" not in att


def test_aws_secret_resolution_attestation_redacts_secret_values(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("canon_systems.aws_secrets.Path.home", lambda: tmp_path)
    cache_dir = tmp_path / ".canon"
    cache_dir.mkdir(parents=True)
    monkeypatch.setenv("MEMORY_LAYER_AWS_SECRET_ID", "pref/my-secret")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    payload = {
        "secret_id": "pref/my-secret",
        "region_tag": "us-east-1",
        "expires_at": time.time() + 3600,
        "env": {
            "CANON_HTTP_BEARER_TOKEN": "super-secret-bearer",
            "KNOWLEDGE_API_KEY": "super-secret-api-key",
            "AWS_SECRET_ACCESS_KEY": "super-secret-aws-key",
            "KNOWLEDGE_API_URL": "https://memory.example.com",
        },
    }
    (cache_dir / "memory-layer-aws-cache.json").write_text(json.dumps(payload), encoding="utf-8")

    att = build_aws_secrets_resolution_attestation()
    dumped = json.dumps(att)

    assert att["resolution"]["status"] == "cache_hit"
    assert att["cache_hit_when_known"] is True
    for forbidden in (
        "super-secret-bearer",
        "super-secret-api-key",
        "super-secret-aws-key",
        "CANON_HTTP_BEARER_TOKEN",
        "KNOWLEDGE_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
    ):
        assert forbidden not in dumped
