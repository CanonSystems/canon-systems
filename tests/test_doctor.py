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
    ctx = o["context_tenant"]
    assert isinstance(ctx, dict)
    assert ctx["expected_company_id"] == "ACME"
    assert ctx["authoritative_tenant_mismatch"] is False
    assert ctx["context_sidecars_trust_status"] == "trusted"
    assert ctx["remediation"]
    assert o["dns"]["status"] == "skipped"
    assert o["canonical_memory_https_url_keys"] == [
        "KNOWLEDGE_API_URL",
        "KNOWLEDGE_WORKER_URL",
        "MEMORY_ADAPTER_URL",
        "CANON_STATE_API_URL",
    ]
    ca = o["credential_attestation"]
    assert ca["schema_version"] == 1
    assert "aws_secrets_resolution" in ca
    assert ca["env_precedence"]["layered_env_source"] == "memory-layer.local.env"
    assert ca["env_precedence"]["mismatches"] == []


def test_doctor_json_includes_credential_attestation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\nREPOSITORY_ID=demo\nAWS_PROFILE=file-profile\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    buf = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", buf)
    assert dr.run(["--json"]) == 0
    o = json.loads(buf.getvalue())
    sec = o["credential_attestation"]["aws_secrets_resolution"]
    assert "resolved_secret_id" in sec
    assert "cache_path" in sec
    assert "cache_exists" in sec
    assert "resolution" in sec
    assert "effective_aws_profile" in sec
    prec = o["credential_attestation"]["env_precedence"]
    assert prec["schema_version"] == 1
    assert prec["tracked_keys"] == ["AWS_PROFILE", "AWS_REGION", "AWS_DEFAULT_REGION"]
    assert sec["effective_aws_profile"] == "file-profile"
    dump = json.dumps(o)
    assert "CANON_HTTP_BEARER_TOKEN" not in dump
    assert "MEMORY_ADAPTER_BEARER" not in dump


def test_doctor_human_output_warns_on_aws_profile_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\nREPOSITORY_ID=demo\nAWS_PROFILE=canon-systems-v2\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("AWS_PROFILE", "canon-systems")
    err = io.StringIO()
    monkeypatch.setattr(dr.sys, "stderr", err)
    assert dr.run([]) == 0
    err_s = err.getvalue()
    assert "shadows repo-local" in err_s
    assert "canon-systems-v2" in err_s
    assert "canon-systems" in err_s


def test_doctor_existing_dns_and_tenant_diagnostics_remain(
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
    assert o["tenant_context_mismatch"] is False
    assert "credential_attestation" in o
    assert isinstance(o["credential_attestation"]["aws_secrets_resolution"], dict)

    (tmp_path / ".canon" / "memory").mkdir(parents=True)
    (tmp_path / ".canon" / "memory" / "context-latest.md").write_text(
        "# Session Memory Context\n\n- company_id: `OTHER`\n- repository_id: `demo`\n",
        encoding="utf-8",
    )
    buf2 = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", buf2)
    assert dr.run(["--json"]) == 1
    o2 = json.loads(buf2.getvalue())
    assert o2["tenant_context_mismatch"] is True
    assert o2["dns"]["likely_split_dns_cloudflare_warp"] is True
    assert "credential_attestation" in o2


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


def test_doctor_tenant_mismatch_context_markdown_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    ctx = o["context_tenant"]
    assert ctx["expected_company_id"] == "ACME"
    assert ctx["expected_repository_id"] == "demo"
    assert ctx["observed_markdown_company_id"] == "OTHER"
    assert ctx["observed_markdown_repository_id"] == "demo"
    assert ctx["observed_json_company_id"] == ""
    assert ctx["authoritative_tenant_mismatch"] is True
    assert ctx["context_sidecars_trust_status"] == "do_not_trust"
    assert "preflight" in ctx["remediation"].lower() or "context-latest" in ctx["remediation"].lower()


def test_doctor_tenant_mismatch_json_sidecar_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Markdown matches wiring but JSON sidecar still carries a stale tenant (no live services)."""
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".canon").mkdir(parents=True)
    (tmp_path / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=ACME\nREPOSITORY_ID=demo\n",
        encoding="utf-8",
    )
    (tmp_path / ".canon" / "memory").mkdir(parents=True)
    (tmp_path / ".canon" / "memory" / "context-latest.md").write_text(
        "# Session Memory Context\n\n- company_id: `ACME`\n- repository_id: `demo`\n",
        encoding="utf-8",
    )
    (tmp_path / ".canon" / "memory" / "context-latest.json").write_text(
        json.dumps({"company_id": "OTHER", "repository_id": "demo"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(dr, "repo_root", lambda: tmp_path)
    buf = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", buf)
    assert dr.run(["--json"]) == 1
    o = json.loads(buf.getvalue())
    assert o["tenant_context_mismatch"] is True
    ctx = o["context_tenant"]
    assert ctx["observed_markdown_company_id"] == "ACME"
    assert ctx["observed_json_company_id"] == "OTHER"
    assert ctx["authoritative_tenant_mismatch"] is True
    assert ctx["context_sidecars_trust_status"] == "do_not_trust"


def test_doctor_tenant_mismatch_human_stderr_banner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(dr.sys, "stdout", out)
    monkeypatch.setattr(dr.sys, "stderr", err)
    assert dr.run([]) == 1
    banner = err.getvalue()
    assert "CONTEXT TENANT MISMATCH" in banner
    assert "Expected (authoritative wiring)" in banner
    assert "context-latest.json" in banner
    assert "Remediation:" in banner
