"""E1-T2: mempalace status classifier, queue, and call-site wiring (no live HTTP)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import canon_systems.ask_hybrid as ask_hybrid
import canon_systems.context_preload as context_preload
from canon_systems.memory_queue import classify_mempalace_response, queue_path
from canon_systems.shared import CONTEXT_TENANT_STALE_STATUS, IdentityContext, RepoContext


def _make_identity() -> IdentityContext:
    return IdentityContext(
        actor_id="actor_test",
        display_name="Test",
        email="a@example.com",
        jira_account_id="",
        slack_user_id="",
        company_id="co_test",
        default_repository_id="repo_test",
    )


def _make_repo(tmp_path: Path) -> RepoContext:
    ctx_dir = tmp_path / ".canon" / "memory"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    return RepoContext(
        company_id="co_test",
        repository_id="repo_test",
        knowledge_api_url="http://k.test",
        knowledge_worker_url="http://w.test",
        memory_adapter_url="http://m.test",
        artifact_bucket="b",
        context_dir=ctx_dir,
    )


def _tmp_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("canon_systems.shared._CACHED_REPO_ROOT", None)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))


AC3_KEYS = frozenset(
    {
        "queued_at",
        "call_site",
        "endpoint_ref",
        "request_body",
        "last_status",
        "last_error",
        "actor_id",
        "company_id",
        "repository_id",
    }
)


def test_preflight_invalidates_stale_md_and_json_before_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _tmp_env(monkeypatch, tmp_path)
    ident = _make_identity()
    repo = _make_repo(tmp_path)
    ctx_dir = tmp_path / ".canon" / "memory"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    (ctx_dir / "context-latest.md").write_text(
        "- company_id: `stale_co`\n- repository_id: `stale_repo`\n",
        encoding="utf-8",
    )
    (ctx_dir / "context-latest.json").write_text(
        '{"company_id": "stale_co", "repository_id": "stale_repo", "status": "ok"}\n',
        encoding="utf-8",
    )
    calls = {"n": 0}

    def fake_rj(
        *, url: str, method: str, body: dict[str, Any] | None = None, **kwargs: Any
    ) -> tuple[int, list[Any] | dict[str, Any] | str]:
        calls["n"] += 1
        if calls["n"] == 1:
            side = json.loads((ctx_dir / "context-latest.json").read_text(encoding="utf-8"))
            assert side["status"] == CONTEXT_TENANT_STALE_STATUS
            assert side["company_id"] == repo.company_id
            assert side["repository_id"] == repo.repository_id
        if "/memory/search" in url:
            return 200, {"results": []}
        return 200, []

    monkeypatch.setattr(context_preload, "load_identity_context", lambda: ident)
    monkeypatch.setattr(context_preload, "load_repo_context", lambda _i: repo)
    monkeypatch.setattr(context_preload, "request_json", fake_rj)
    assert context_preload.run(["--quiet", "q"]) == 0
    assert calls["n"] == 2
    final = json.loads((ctx_dir / "context-latest.json").read_text(encoding="utf-8"))
    assert final["status"] == "ok"
    assert final["company_id"] == repo.company_id
    assert final["mempalace_status"]["status"] == "ok"


def test_preflight_invalidates_stale_json_only_before_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _tmp_env(monkeypatch, tmp_path)
    ident = _make_identity()
    repo = _make_repo(tmp_path)
    ctx_dir = tmp_path / ".canon" / "memory"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    (ctx_dir / "context-latest.json").write_text(
        '{"company_id": "json_only_stale", "repository_id": "repo_test"}\n',
        encoding="utf-8",
    )
    calls = {"n": 0}

    def fake_rj(
        *, url: str, method: str, body: dict[str, Any] | None = None, **kwargs: Any
    ) -> tuple[int, list[Any] | dict[str, Any] | str]:
        calls["n"] += 1
        if calls["n"] == 1:
            side = json.loads((ctx_dir / "context-latest.json").read_text(encoding="utf-8"))
            assert side["status"] == CONTEXT_TENANT_STALE_STATUS
        if "/memory/search" in url:
            return 200, {"results": []}
        return 200, []

    monkeypatch.setattr(context_preload, "load_identity_context", lambda: ident)
    monkeypatch.setattr(context_preload, "load_repo_context", lambda _i: repo)
    monkeypatch.setattr(context_preload, "request_json", fake_rj)
    assert context_preload.run(["--quiet", "sync"]) == 0
    j = json.loads((ctx_dir / "context-latest.json").read_text(encoding="utf-8"))
    assert j["status"] == "ok"
    assert j["company_id"] == "co_test"


def test_preflight_invalidates_stale_md_only_before_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _tmp_env(monkeypatch, tmp_path)
    ident = _make_identity()
    repo = _make_repo(tmp_path)
    ctx_dir = tmp_path / ".canon" / "memory"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    (ctx_dir / "context-latest.md").write_text(
        "- company_id: `co_test`\n- repository_id: `md_only_stale`\n",
        encoding="utf-8",
    )
    calls = {"n": 0}

    def fake_rj(
        *, url: str, method: str, body: dict[str, Any] | None = None, **kwargs: Any
    ) -> tuple[int, list[Any] | dict[str, Any] | str]:
        calls["n"] += 1
        if calls["n"] == 1:
            side = json.loads((ctx_dir / "context-latest.json").read_text(encoding="utf-8"))
            assert side["status"] == CONTEXT_TENANT_STALE_STATUS
        if "/memory/search" in url:
            return 200, {"results": []}
        return 200, []

    monkeypatch.setattr(context_preload, "load_identity_context", lambda: ident)
    monkeypatch.setattr(context_preload, "load_repo_context", lambda _i: repo)
    monkeypatch.setattr(context_preload, "request_json", fake_rj)
    assert context_preload.run(["--quiet", "md-only"]) == 0
    md = (ctx_dir / "context-latest.md").read_text(encoding="utf-8")
    assert "co_test" in md
    assert "repo_test" in md
    assert "INVALIDATED" not in md


def test_preflight_stale_tenant_then_unreachable_still_queues_mempalace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tenant invalidation runs first; MemPalace degraded path unchanged."""
    _tmp_env(monkeypatch, tmp_path)
    ident = _make_identity()
    repo = _make_repo(tmp_path)
    ctx_dir = tmp_path / ".canon" / "memory"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    (ctx_dir / "context-latest.md").write_text(
        "- company_id: `stale`\n- repository_id: `stale`\n",
        encoding="utf-8",
    )

    def fake_rj(
        *, url: str, method: str, body: dict[str, Any] | None = None, **kwargs: Any
    ) -> tuple[int, list[Any] | dict[str, Any] | str]:
        if "/memory/search" in url:
            return 0, "request failed: no route to host"
        return 200, []

    monkeypatch.setattr(context_preload, "load_identity_context", lambda: ident)
    monkeypatch.setattr(context_preload, "load_repo_context", lambda _i: repo)
    monkeypatch.setattr(context_preload, "request_json", fake_rj)
    assert context_preload.run(["--quiet", "my query"]) == 0
    j = json.loads((ctx_dir / "context-latest.json").read_text(encoding="utf-8"))
    assert j["mempalace_status"]["status"] == "unreachable"
    assert j["company_id"] == repo.company_id
    q = queue_path()
    assert q.exists()


def test_preflight_unreachable_records_md_sidecar_and_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _tmp_env(monkeypatch, tmp_path)
    ident = _make_identity()
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(context_preload, "load_identity_context", lambda: ident)
    monkeypatch.setattr(context_preload, "load_repo_context", lambda _i: repo)

    def fake_rj(
        *, url: str, method: str, body: dict[str, Any] | None = None, **kwargs: Any
    ) -> tuple[int, list[Any] | dict[str, Any] | str]:
        if "/memory/search" in url:
            return 0, "request failed: no route to host"
        return 200, []

    monkeypatch.setattr(context_preload, "request_json", fake_rj)
    assert context_preload.run(["--quiet", "my query"]) == 0

    md = (tmp_path / ".canon" / "memory" / "context-latest.md").read_text(encoding="utf-8")
    assert "## MemPalace Status" in md
    assert "- status: `unreachable`" in md
    assert "- endpoint_ref: `http://m.test/memory/search`" in md

    side = json.loads((tmp_path / ".canon" / "memory" / "context-latest.json").read_text(encoding="utf-8"))
    assert side["mempalace_status"]["status"] == "unreachable"
    assert "latency_ms" in side["mempalace_status"]

    q = queue_path()
    assert q.exists()
    rec = json.loads(q.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert set(rec.keys()) == AC3_KEYS
    assert rec["call_site"] == "context_preload"
    assert rec["actor_id"] == "actor_test"
    assert rec["last_status"] == 0
    assert rec["request_body"]["query"] == "my query"


def test_preflight_ok_no_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _tmp_env(monkeypatch, tmp_path)
    ident = _make_identity()
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(context_preload, "load_identity_context", lambda: ident)
    monkeypatch.setattr(context_preload, "load_repo_context", lambda _i: repo)

    def fake_rj(
        *, url: str, method: str, body: dict[str, Any] | None = None, **kwargs: Any
    ) -> tuple[int, list[Any] | dict[str, Any] | str]:
        if "/memory/search" in url:
            return 200, {"results": []}
        return 200, []

    monkeypatch.setattr(context_preload, "request_json", fake_rj)
    assert context_preload.run(["--quiet", "q"]) == 0
    j = json.loads((tmp_path / ".canon" / "memory" / "context-latest.json").read_text(encoding="utf-8"))
    assert j["mempalace_status"]["status"] == "ok"
    assert not queue_path().exists()


def test_ask_unreachable_json_queue_and_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _tmp_env(monkeypatch, tmp_path)
    ident = _make_identity()
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(ask_hybrid, "load_identity_context", lambda: ident)
    monkeypatch.setattr(ask_hybrid, "load_repo_context", lambda _i: repo)

    def fake_rj(
        *, url: str, method: str, body: dict[str, Any] | None = None, **kwargs: Any
    ) -> tuple[int, list[Any] | dict[str, Any] | str]:
        if "/memory/search" in url:
            return 0, "request failed: connection refused"
        if "/api/v1/artifacts" in url and "artifact_type=memory_capture" in url:
            return 200, []
        return 0, "should-not-happen"

    monkeypatch.setattr(ask_hybrid, "request_json", fake_rj)
    assert ask_hybrid.run(["What?", "--json"]) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["mempalace_status"]["status"] == "unreachable"

    q = queue_path()
    assert q.exists()
    rec = json.loads(q.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert rec["call_site"] == "ask_hybrid"
    assert rec["request_body"]["query"] == "What?"

    # stderr line only in non-JSON mode
    assert ask_hybrid.run(["What?"]) == 0
    err = capsys.readouterr().err
    assert "mempalace: unreachable" in err


def test_classifier_not_configured_no_enqueue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _tmp_env(monkeypatch, tmp_path)
    block = classify_mempalace_response(
        configured=False,
        status=500,
        payload={"x": 1},
        endpoint_ref="",
        latency_ms=10,
    )
    assert block["status"] == "not_configured"
    assert not queue_path().exists()
