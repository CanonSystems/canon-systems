import os
import socket
import urllib.error
import urllib.request
from pathlib import Path

import canon_systems.shared as shared
from canon_systems.shared import (
    apply_layered_canon_env_for_repo,
    canon_urlopen,
    context_sidecars_stale_vs_authoritative,
    ensure_layered_memory_env,
    merge_canon_systems_env_files,
    parse_context_latest_json_tenant,
    parse_context_latest_md_tenant,
    repo_root,
    resolve_auth_bearer,
)


def test_parse_context_latest_md_tenant_backticks(tmp_path: Path) -> None:
    md = tmp_path / "context-latest.md"
    md.write_text(
        "# Session Memory Context\n\n- company_id: `co_a`\n- repository_id: `repo_b`\n",
        encoding="utf-8",
    )
    assert parse_context_latest_md_tenant(md) == ("co_a", "repo_b")


def test_parse_context_latest_json_tenant_reads_top_level(tmp_path: Path) -> None:
    js = tmp_path / "context-latest.json"
    js.write_text(
        '{"status": "ok", "company_id": "co_x", "repository_id": "repo_y"}\n',
        encoding="utf-8",
    )
    assert parse_context_latest_json_tenant(js) == ("co_x", "repo_y")


def test_context_sidecars_stale_when_md_differs_from_authoritative(tmp_path: Path) -> None:
    ctx = tmp_path / ".canon" / "memory"
    ctx.mkdir(parents=True)
    (ctx / "context-latest.md").write_text(
        "- company_id: `wrong`\n- repository_id: `repo_ok`\n",
        encoding="utf-8",
    )
    assert context_sidecars_stale_vs_authoritative(
        context_dir=ctx,
        authoritative_company_id="co_ok",
        authoritative_repository_id="repo_ok",
    )


def test_context_sidecars_stale_when_json_differs(tmp_path: Path) -> None:
    ctx = tmp_path / ".canon" / "memory"
    ctx.mkdir(parents=True)
    (ctx / "context-latest.json").write_text(
        '{"company_id": "co_ok", "repository_id": "bad_repo"}\n',
        encoding="utf-8",
    )
    assert context_sidecars_stale_vs_authoritative(
        context_dir=ctx,
        authoritative_company_id="co_ok",
        authoritative_repository_id="good_repo",
    )


def test_context_sidecars_stale_when_md_and_json_disagree(tmp_path: Path) -> None:
    ctx = tmp_path / ".canon" / "memory"
    ctx.mkdir(parents=True)
    (ctx / "context-latest.md").write_text(
        "- company_id: `same`\n- repository_id: `r_md`\n",
        encoding="utf-8",
    )
    (ctx / "context-latest.json").write_text(
        '{"company_id": "same", "repository_id": "r_json"}\n',
        encoding="utf-8",
    )
    assert context_sidecars_stale_vs_authoritative(
        context_dir=ctx,
        authoritative_company_id="same",
        authoritative_repository_id="r_md",
    )


def test_context_sidecars_not_stale_when_matching(tmp_path: Path) -> None:
    ctx = tmp_path / ".canon" / "memory"
    ctx.mkdir(parents=True)
    (ctx / "context-latest.md").write_text(
        "- company_id: `co1`\n- repository_id: `r1`\n",
        encoding="utf-8",
    )
    (ctx / "context-latest.json").write_text(
        '{"company_id": "co1", "repository_id": "r1"}\n',
        encoding="utf-8",
    )
    assert not context_sidecars_stale_vs_authoritative(
        context_dir=ctx,
        authoritative_company_id="co1",
        authoritative_repository_id="r1",
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


def test_canon_urlopen_dns_dig_fallback_on_gaierror(monkeypatch) -> None:
    def boom(*_a, **_kw):
        raise urllib.error.URLError(
            socket.gaierror(8, "nodename nor servname provided, or not known")
        )

    monkeypatch.setattr(urllib.request, "urlopen", boom)

    def fake_fb(req: urllib.request.Request, *, timeout_s: float):
        assert req.full_url == "https://example.test/healthz"
        assert timeout_s == 1.5
        return shared._SimpleHttpResponse(200, b'{"status":"ok"}')

    monkeypatch.setattr(shared, "_try_urlopen_dns_dig_fallback", fake_fb)
    req = urllib.request.Request("https://example.test/healthz")
    with canon_urlopen(req, timeout_s=1.5) as resp:
        assert resp.getcode() == 200
        assert resp.read() == b'{"status":"ok"}'


def test_canon_urlopen_dns_dig_fallback_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CANON_DNS_FALLBACK", "0")

    def boom(*_a, **_kw):
        raise urllib.error.URLError(
            socket.gaierror(8, "nodename nor servname provided, or not known")
        )

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    req = urllib.request.Request("https://example.test/z")
    try:
        with canon_urlopen(req, timeout_s=1.0):
            pass
    except urllib.error.URLError:
        return
    raise AssertionError("expected URLError")


def test_resolve_ipv4_via_dig_parses_first_a_record(monkeypatch) -> None:
    class _P:
        returncode = 0
        stdout = "172.64.80.1\n"

    monkeypatch.setattr(shared.subprocess, "run", lambda *a, **k: _P())
    assert shared._resolve_ipv4_via_dig("memory.example.com") == "172.64.80.1"


def test_resolve_ipv4_via_dig_skips_cname_lines(monkeypatch) -> None:
    class _P:
        returncode = 0
        stdout = "target.elb.amazonaws.com.\n172.64.80.1\n"

    monkeypatch.setattr(shared.subprocess, "run", lambda *a, **k: _P())
    assert shared._resolve_ipv4_via_dig("x.example.com") == "172.64.80.1"
