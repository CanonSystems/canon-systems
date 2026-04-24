"""Tests for `canon doctor`."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import canon_systems.cli as top_cli
import canon_systems.doctor_cli as dr


@pytest.fixture(autouse=True)
def _doctor_isolate_aws_cache_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real ~/.canon/memory-layer-aws-cache.json must not affect doctor DNS checks."""
    monkeypatch.setattr(dr, "_read_cache_env_loose", lambda: {})


def test_doctor_json_ok_when_wired_no_hits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\nREPOSITORY_ID=demo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    buf = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", buf)
    assert dr.run(["--json"]) == 0
    o = json.loads(buf.getvalue())
    assert o["company_id_file"] == "ACME"
    assert o["tenant_context_mismatch"] is False
    assert o["dns"]["status"] == "skipped"
    assert o["canonical_memory_https_url_keys"] == [
        "KNOWLEDGE_API_URL",
        "KNOWLEDGE_WORKER_URL",
        "MEMORY_ADAPTER_URL",
        "CANON_STATE_API_URL",
    ]


def test_doctor_warns_literal_ip_in_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\n"
        "REPOSITORY_ID=demo\n"
        "KNOWLEDGE_API_URL=http://10.0.0.1:8080\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    assert dr.run(["--json"]) == 1


def test_doctor_dns_split_brain_surfaces_in_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\n"
        "REPOSITORY_ID=demo\n"
        "KNOWLEDGE_API_URL=https://memory.example.com\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)

    def boom(*_a, **_kw):
        raise OSError(8, "nodename nor servname provided, or not known")

    monkeypatch.setattr(dr.socket, "getaddrinfo", boom)
    monkeypatch.setattr(dr, "_resolve_ipv4_via_dig", lambda _h: "203.0.113.1")

    buf = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", buf)
    assert dr.run(["--json"]) == 0
    o = json.loads(buf.getvalue())
    assert o["dns"]["likely_split_dns_cloudflare_warp"] is True
    assert o["dns"]["dig_a_record"] == "203.0.113.1"
    assert "memory.example.com" in o["dns"]["curl_resolve_healthz"]
    assert "203.0.113.1" in o["dns"]["curl_resolve_healthz"]


def test_cli_doctor_forwards_curl_resolve_snippet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\n"
        "REPOSITORY_ID=demo\n"
        "KNOWLEDGE_API_URL=https://memory.example.com\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(dr, "_resolve_ipv4_via_dig", lambda _h: "203.0.113.1")
    buf = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", buf)
    assert top_cli.main(["--repo-root", str(tmp_path), "doctor", "--curl-resolve-snippet"]) == 0
    assert "--resolve" in buf.getvalue()


def test_doctor_curl_resolve_snippet_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\n"
        "REPOSITORY_ID=demo\n"
        "KNOWLEDGE_API_URL=https://memory.example.com\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(dr, "_resolve_ipv4_via_dig", lambda _h: "203.0.113.1")

    buf = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", buf)
    assert dr.run(["--curl-resolve-snippet"]) == 0
    line = buf.getvalue().strip()
    assert line.startswith("curl -sS ")
    assert "--resolve" in line
    assert "memory.example.com" in line
    assert "/healthz" in line


def test_doctor_tenant_mismatch_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\nREPOSITORY_ID=demo\n",
        encoding="utf-8",
    )
    (tmp_path / ".canon" / "memory").mkdir(parents=True)
    (tmp_path / ".canon" / "memory" / "context-latest.md").write_text(
        "# Session Memory Context\n\n- company_id: `OTHER`\n- repository_id: `demo`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    buf = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", buf)
    assert dr.run(["--json"]) == 1
    o = json.loads(buf.getvalue())
    assert o["tenant_context_mismatch"] is True
