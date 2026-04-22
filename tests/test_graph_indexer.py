from __future__ import annotations

import json
from typing import Any

import pytest

from canon_systems import graph_indexer


def test_index_help_returns_0() -> None:
    assert graph_indexer.run(["index", "--help"]) == 0


def test_reindex_status_help_returns_0() -> None:
    assert graph_indexer.run(["reindex-status", "--help"]) == 0


def test_index_usage_error_missing_commit_sha() -> None:
    assert graph_indexer.run(["index", "--company-id", "c", "--repository-id", "r"]) == 2


def test_index_usage_error_both_full_and_changed() -> None:
    code = graph_indexer.run(
        [
            "index",
            "--commit-sha",
            "s",
            "--company-id",
            "c",
            "--repository-id",
            "r",
            "--full",
            "--changed-files",
            "a",
        ]
    )
    assert code == 2


def test_index_success_with_changed_files(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        captured["url"] = url
        captured["method"] = method
        captured["body"] = json.loads(body.decode()) if body else {}
        assert method == "POST"
        assert captured["body"]["commit_sha"] == "sha1"
        assert any(n.get("path") == "x.py" for n in captured["body"]["nodes"])
        return (200, b'{"company_id":"c","repository_id":"r","commit_sha":"sha1","snapshot_key":"k","uploaded_at":"t","node_count":1,"edge_count":0,"size_bytes":10}\n', {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    code = graph_indexer.run(
        [
            "index",
            "--commit-sha",
            "sha1",
            "--company-id",
            "c",
            "--repository-id",
            "r",
            "--base-url",
            "http://example",
            "--service-token",
            "tok",
            "--changed-files",
            "x.py",
        ]
    )
    assert code == 0
    assert "/axon/c/r/index" in captured["url"]


def test_index_success_full_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_list() -> list[str]:
        return ["src/a.py", "src/b.py"]

    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        payload = json.loads(body.decode()) if body else {}
        assert payload["metadata"]["mode"] == "full"
        assert len(payload["nodes"]) == 2
        assert any(e.get("type") == "sibling" for e in payload["edges"])
        return (201, b"{}\n", {})

    monkeypatch.setattr(graph_indexer, "_list_all_files", fake_list)
    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "index",
                "--commit-sha",
                "s",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--full",
                "--base-url",
                "http://x",
                "--service-token",
                "t",
            ]
        )
        == 0
    )


def test_index_env_fallback_resolves_base_url_and_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AXON_SERVICE_URL", "http://env-base")
    monkeypatch.setenv("AXON_SERVICE_TOKEN", "env-tok")

    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        assert url.startswith("http://env-base/axon/")
        assert headers and "Bearer env-tok" in headers.get("Authorization", "")
        return (200, b'{"ok":true}\n', {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "index",
                "--commit-sha",
                "s",
                "--company-id",
                "co",
                "--repository-id",
                "re",
            ]
        )
        == 0
    )


def test_index_usage_error_when_no_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AXON_SERVICE_URL", raising=False)
    assert (
        graph_indexer.run(
            [
                "index",
                "--commit-sha",
                "s",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--service-token",
                "t",
            ]
        )
        == 2
    )


def test_index_http_4xx_returns_3_and_unwraps_detail(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        return (422, b'{"detail":"bad commit"}', {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    code = graph_indexer.run(
        [
            "index",
            "--commit-sha",
            "s",
            "--company-id",
            "c",
            "--repository-id",
            "r",
            "--base-url",
            "http://h",
            "--service-token",
            "t",
        ]
    )
    assert code == 3
    err = capsys.readouterr().err
    assert "bad commit" in err


def test_index_unexpected_http_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        return (204, b"", {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "index",
                "--commit-sha",
                "s",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--base-url",
                "http://h",
                "--service-token",
                "t",
            ]
        )
        == 1
    )


def test_index_http_5xx_returns_4(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        return (503, b"{}", {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "index",
                "--commit-sha",
                "s",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--base-url",
                "http://h",
                "--service-token",
                "t",
            ]
        )
        == 4
    )


def test_index_transport_error_returns_5(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        raise graph_indexer.TransportError("boom")

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "index",
                "--commit-sha",
                "s",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--base-url",
                "http://h",
                "--service-token",
                "t",
            ]
        )
        == 5
    )


def test_index_soft_budget_warning(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    ticks = iter([0.0, 70.0])

    def fake_mono() -> float:
        return next(ticks)

    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        return (200, b"{}\n", {})

    monkeypatch.setattr(graph_indexer.time, "monotonic", fake_mono)
    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "index",
                "--commit-sha",
                "s",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--base-url",
                "http://h",
                "--service-token",
                "t",
            ]
        )
        == 0
    )
    assert "warning" in capsys.readouterr().err.lower()


def test_reindex_status_success(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        assert method == "GET"
        assert "reindex-status" in url
        assert "commit_sha=" in url
        return (200, b'{"status":"ready","commit_sha":"abc"}\n', {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "reindex-status",
                "--commit-sha",
                "abc",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--base-url",
                "http://h",
                "--service-token",
                "t",
            ]
        )
        == 0
    )
    assert "ready" in capsys.readouterr().out


def test_reindex_status_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        return (200, b'{"status":"missing"}\n', {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "reindex-status",
                "--commit-sha",
                "abc",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--base-url",
                "http://h",
                "--service-token",
                "t",
            ]
        )
        == 0
    )


def test_reindex_status_http_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        return (401, b'{"detail":"nope"}', {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "reindex-status",
                "--commit-sha",
                "abc",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--base-url",
                "http://h",
                "--service-token",
                "t",
            ]
        )
        == 3
    )


def test_graph_query_help_returns_0() -> None:
    assert graph_indexer.run(["query", "--help"]) == 0


def test_graph_impact_help_returns_0() -> None:
    assert graph_indexer.run(["impact", "--help"]) == 0


def test_graph_query_success(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    captured: dict[str, Any] = {}

    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        captured["url"] = url
        captured["headers"] = dict(headers or {})
        assert method == "GET"
        return (200, b'{"ok":true}\n', {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "query",
                "--commit-sha",
                "abc",
                "--company-id",
                "acme",
                "--repository-id",
                "repo1",
                "--q",
                "hello",
                "--base-url",
                "http://h",
                "--service-token",
                "tok",
            ]
        )
        == 0
    )
    assert "/axon/acme/repo1/query?" in captured["url"]
    assert "q=hello" in captured["url"]
    assert "commit_sha=abc" in captured["url"]
    assert captured["headers"].get("Authorization") == "Bearer tok"
    assert "true" in capsys.readouterr().out


def test_graph_query_with_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        captured["url"] = url
        return (200, b"{}\n", {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "query",
                "--commit-sha",
                "s",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--q",
                "x",
                "--limit",
                "25",
                "--base-url",
                "http://h",
                "--service-token",
                "t",
            ]
        )
        == 0
    )
    assert "limit=25" in captured["url"]


def test_graph_query_missing_token_returns_2(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.delenv("AXON_SERVICE_URL", raising=False)
    monkeypatch.delenv("AXON_SERVICE_TOKEN", raising=False)

    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        calls.append(1)
        return (200, b"{}", {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "query",
                "--commit-sha",
                "abc",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--q",
                "hello",
                "--base-url",
                "http://h",
            ]
        )
        == 2
    )
    assert calls == []


def test_graph_query_missing_base_url_returns_2(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.delenv("AXON_SERVICE_URL", raising=False)

    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        calls.append(1)
        return (200, b"{}", {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "query",
                "--commit-sha",
                "abc",
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--q",
                "q",
                "--service-token",
                "t",
            ]
        )
        == 2
    )
    assert calls == []


def test_graph_query_http_4xx_returns_3_and_unwraps_detail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        return (404, b'{"detail":"no snapshot"}', {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "query",
                "--commit-sha",
                "c",
                "--company-id",
                "a",
                "--repository-id",
                "b",
                "--q",
                "q",
                "--base-url",
                "http://h",
                "--service-token",
                "t",
            ]
        )
        == 3
    )
    assert "no snapshot" in capsys.readouterr().err


def test_graph_query_transport_error_returns_5(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        raise graph_indexer.TransportError("boom")

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "query",
                "--commit-sha",
                "a",
                "--company-id",
                "a",
                "--repository-id",
                "a",
                "--q",
                "a",
                "--base-url",
                "http://h",
                "--service-token",
                "h",
            ]
        )
        == 5
    )


def test_graph_query_unexpected_http_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        return (204, b"", {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "query",
                "--commit-sha",
                "a",
                "--company-id",
                "a",
                "--repository-id",
                "a",
                "--q",
                "a",
                "--base-url",
                "http://h",
                "--service-token",
                "h",
            ]
        )
        == 1
    )


def test_graph_impact_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        captured["url"] = url
        assert method == "GET"
        assert headers and "Bearer" in headers.get("Authorization", "")
        return (200, b'{"d":1}\n', {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "impact",
                "--commit-sha",
                "c2",
                "--company-id",
                "a",
                "--repository-id",
                "a",
                "--symbol",
                "foo.bar",
                "--base-url",
                "http://h",
                "--service-token",
                "h",
            ]
        )
        == 0
    )
    assert "/axon/a/a/impact?" in captured["url"]
    assert "symbol=foo.bar" in captured["url"]
    assert "commit_sha=c2" in captured["url"]


def test_graph_impact_with_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        captured["url"] = url
        return (200, b"{}\n", {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "impact",
                "--commit-sha",
                "s",
                "--company-id",
                "a",
                "--repository-id",
                "a",
                "--symbol",
                "S",
                "--depth",
                "3",
                "--base-url",
                "http://h",
                "--service-token",
                "h",
            ]
        )
        == 0
    )
    assert "depth=3" in captured["url"]


def test_graph_impact_http_5xx_returns_4(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_http(
        url: str,
        *,
        method: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, bytes, dict[str, str]]:
        return (503, b"{}", {})

    monkeypatch.setattr(graph_indexer, "_http_request", fake_http)
    assert (
        graph_indexer.run(
            [
                "impact",
                "--commit-sha",
                "a",
                "--company-id",
                "a",
                "--repository-id",
                "a",
                "--symbol",
                "x",
                "--base-url",
                "http://h",
                "--service-token",
                "h",
            ]
        )
        == 4
    )
