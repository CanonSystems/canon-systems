"""Tests for `canon memory-health` (E1-T1) — all probes mocked; no live HTTP."""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import pytest

import canon_systems.memory_health as mh


def _write_repo(tmp: Path, **env_vars: str) -> Path:
    (tmp / ".canon").mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"{k}={v}" for k, v in env_vars.items()) + "\n"
    (tmp / ".canon" / "memory-layer.local.env").write_text(body, encoding="utf-8")
    return tmp


def _ok_200() -> dict:
    return {
        "http_status": 200,
        "body_text": '{"status":"ok","version":"1.2.3"}',
        "body_json": {"status": "ok", "version": "1.2.3"},
        "error": None,
        "latency_ms": 3,
    }


def _run_captured(
    *, argv: list[str], monkeypatch: pytest.MonkeyPatch
) -> tuple[int, str]:
    buf = io.StringIO()
    monkeypatch.setattr(mh.sys, "stdout", buf)
    code = mh.run(argv)
    return code, buf.getvalue()


@pytest.fixture
def four_urls_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = _write_repo(
        tmp_path,
        KNOWLEDGE_API_URL="http://k.test",
        MEMORY_ADAPTER_URL="http://m.test",
        STATE_API_URL="http://s.test",
        AXON_SERVICE_URL="http://a.test",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(root))
    for v in (
        "KNOWLEDGE_API_URL",
        "MEMORY_ADAPTER_URL",
        "STATE_API_URL",
        "AXON_SERVICE_URL",
    ):
        monkeypatch.delenv(v, raising=False)
    return root


def test_healthy(four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    c, s = _run_captured(argv=[], monkeypatch=monkeypatch)
    o = json.loads(s)
    assert c == 0
    assert o["overall_status"] == "ok"
    assert {b["name"] for b in o["backends"]} == {"canonical", "mempalace", "state", "graph"}


def test_required_degraded(four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def probe(url: str, t: int) -> dict:  # noqa: ARG001
        if "k.test" in url:
            return {
                "http_status": 200,
                "body_text": '{"status":"scaffold"}',
                "body_json": {"status": "scaffold"},
                "error": None,
                "latency_ms": 1,
            }
        return _ok_200()

    monkeypatch.setattr(mh, "_probe", probe)
    c, s = _run_captured(argv=[], monkeypatch=monkeypatch)
    assert c == 1
    assert json.loads(s)["overall_status"] == "unhealthy"


def test_all_required_unreachable(four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def bad(_u, _t) -> dict:  # noqa: ANN001
        return {
            "http_status": 0,
            "body_text": "",
            "body_json": None,
            "error": "connection refused",
            "latency_ms": 1,
        }

    monkeypatch.setattr(mh, "_probe", bad)
    c, s = _run_captured(argv=[], monkeypatch=monkeypatch)
    assert c == 1
    assert json.loads(s)["overall_status"] == "unhealthy"


def test_not_configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _write_repo(tmp_path)
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(root))
    for v in (
        "KNOWLEDGE_API_URL",
        "MEMORY_ADAPTER_URL",
        "STATE_API_URL",
        "AXON_SERVICE_URL",
        "CANON_MEMORY_HEALTH_REQUIRED",
    ):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("CANON_MEMORY_HEALTH_REQUIRED", "state")
    monkeypatch.setattr(mh, "_probe", lambda u, t: _ok_200())  # noqa: ARG001
    c, s = _run_captured(
        argv=[],
        monkeypatch=monkeypatch,
    )
    assert c == 1
    st = {b["name"]: b["status"] for b in json.loads(s)["backends"]}
    assert st["state"] == "not_configured"


def test_env_override_expands(four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_MEMORY_HEALTH_REQUIRED", "canonical,mempalace,state")
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    c, s = _run_captured(argv=[], monkeypatch=monkeypatch)
    o = json.loads(s)
    assert c == 0
    req = {b["name"] for b in o["backends"] if b["required"]}
    assert req == {"canonical", "mempalace", "state"}


def test_env_override_shrinks(four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Shrink required set: mempalace failure is optional impairment — exit 0, overall degraded."""
    monkeypatch.setenv("CANON_MEMORY_HEALTH_REQUIRED", "canonical")

    def probe(url, t) -> dict:  # noqa: ANN001
        if "k.test" in url:
            return _ok_200()
        return {
            "http_status": 503,
            "body_text": "",
            "body_json": None,
            "error": None,
            "latency_ms": 1,
        }

    monkeypatch.setattr(mh, "_probe", probe)
    c, s = _run_captured(argv=[], monkeypatch=monkeypatch)
    o = json.loads(s)
    assert c == 0
    assert o["overall_status"] == "degraded"
    m = next(b for b in o["backends"] if b["name"] == "mempalace")
    assert m["required"] is False
    assert m["status"] == "not_deployed"


def test_unknown_backend_fails_closed(
    four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    c, s = _run_captured(
        argv=["--required", "canonical,florp"],
        monkeypatch=monkeypatch,
    )
    o = json.loads(s)
    assert c == 1
    assert o["overall_status"] == "unhealthy"
    u = next(b for b in o["backends"] if b["name"] == "florp")
    assert u["status"] == "unknown_backend"


def test_timeout_budget(
    four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[str, int]] = []

    def probe(url, t) -> dict:  # noqa: ANN001
        seen.append((url, t))
        return _ok_200()

    monkeypatch.setattr(mh, "_probe", probe)
    c, _ = _run_captured(argv=["--timeout-ms", "5000"], monkeypatch=monkeypatch)
    assert c == 0
    assert all(t == 5000 for _u, t in seen), seen


def test_json_shape(
    four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    c, s = _run_captured(argv=["--json"], monkeypatch=monkeypatch)
    o = json.loads(s)
    assert c == 0
    for k in (
        "schema_version",
        "generated_at",
        "overall_status",
        "required_set",
        "timeout_ms",
        "backends",
    ):
        assert k in o, k
    for b in o["backends"]:
        for k2 in (
            "name",
            "required",
            "endpoint_ref",
            "status",
            "latency_ms",
            "version",
            "last_error",
        ):
            assert k2 in b, k2


def test_output_flag_writes_file(
    four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out = tmp_path / "h.json"
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    c, s = _run_captured(
        argv=["--output", str(out)],
        monkeypatch=monkeypatch,
    )
    assert c == 0
    assert s == out.read_text(encoding="utf-8")


def test_empty_required_exits_zero(
    four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    c, s = _run_captured(
        argv=["--required", ""],
        monkeypatch=monkeypatch,
    )
    assert c == 0
    assert json.loads(s)["required_set"] == []


def test_cli_help_registers_subcommand() -> None:
    from canon_systems.cli import main

    with pytest.raises(SystemExit) as ei:
        main(["--repo-root", str(Path(__file__).resolve().parents[1]), "memory-health", "--help"])
    assert ei.value.code == 0


def test_unknown_flag_exits_2() -> None:
    c = mh.run(["--nope"])
    assert c == 2


def test_stdlib_only_imports() -> None:
    text = Path(mh.__file__).read_text(encoding="utf-8")
    for bad in ("requests", "httpx", "aiohttp", "urllib3"):
        assert bad not in text


def test_verbose_routes_logs_to_stderr(
    four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    # Restore real stdout for JSON so we only check stderr
    buf = io.StringIO()
    monkeypatch.setattr(mh.sys, "stdout", buf)
    code = mh.run(["--verbose"])
    err = capsys.readouterr().err
    assert code == 0
    assert "memory-health:" in err


@pytest.mark.parametrize(
    (
        "probe_label",
        "expected_exit",
        "expected_overall",
    ),
    [
        ("all_ok", 0, "ok"),
        ("all_required_down", 1, "unhealthy"),
        ("optional_state_down", 0, "degraded"),
    ],
)
def test_exit_code_matrix(
    four_urls_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe_label: str,
    expected_exit: int,
    expected_overall: str,
) -> None:
    if probe_label == "all_ok":
        monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    elif probe_label == "all_required_down":

        def all_bad(_u, _t) -> dict:  # noqa: ANN001
            return {
                "http_status": 0,
                "body_text": "",
                "body_json": None,
                "error": "e",
                "latency_ms": 0,
            }

        monkeypatch.setattr(mh, "_probe", all_bad)
    else:

        def opt_bad(url, t) -> dict:  # noqa: ANN001
            if "s.test" in url:
                return {
                    "http_status": 0,
                    "body_text": "",
                    "body_json": None,
                    "error": "e",
                    "latency_ms": 0,
                }
            return _ok_200()

        monkeypatch.setattr(mh, "_probe", opt_bad)

    c, s = _run_captured(argv=[], monkeypatch=monkeypatch)
    o = json.loads(s)
    assert c == expected_exit, (probe_label, s)
    assert o["overall_status"] == expected_overall


def test_not_deployed_only_for_optional(
    four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def probe(url, t) -> dict:  # noqa: ANN001
        if "s.test" in url and "healthz" in url:
            return {
                "http_status": 404,
                "body_text": "",
                "body_json": None,
                "error": None,
                "latency_ms": 1,
            }
        return _ok_200()

    monkeypatch.setattr(mh, "_probe", probe)
    c, s = _run_captured(
        argv=["--required", "canonical"],
        monkeypatch=monkeypatch,
    )
    o = json.loads(s)
    assert c == 0
    st = next(b for b in o["backends"] if b["name"] == "state")
    assert st["status"] == "not_deployed"

    def probe2(url, t) -> dict:  # noqa: ANN001
        if "k.test" in url and "healthz" in url:
            return {
                "http_status": 404,
                "body_text": "",
                "body_json": None,
                "error": None,
                "latency_ms": 1,
            }
        return _ok_200()

    monkeypatch.setattr(mh, "_probe", probe2)
    c2, s2 = _run_captured(
        argv=["--required", "canonical"],
        monkeypatch=monkeypatch,
    )
    row = next(b for b in json.loads(s2)["backends"] if b["name"] == "canonical")
    assert row["status"] == "unreachable"
    assert c2 == 1


def test_readme_row_present() -> None:
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    i = readme.find("canon flow-audit")
    j = readme.find("canon memory-health", i)
    assert j > i
    # Row immediately after flow-audit: memory-health should appear before the next `canon` row
    k = readme.find("canon secrets", j)
    assert j < k
    assert "Probe canonical" in readme


def test_changelog_unreleased_added_bullet() -> None:
    ch = (Path(__file__).resolve().parents[1] / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"##\s+\[Unreleased\]", ch)
    assert "E1-T1" in ch
    assert "canon memory-health" in ch
    assert "CANON_MEMORY_HEALTH" in ch


def test_system_workflow_section_6_bullet() -> None:
    p = Path(__file__).resolve().parents[1] / "docs" / "SYSTEM-WORKFLOW.md"
    text = p.read_text(encoding="utf-8")
    assert "Memory health probe" in text
    assert "canon memory-health" in text


def test_graph_optional_not_configured_exit_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default required set: graph not configured does not degrade overall (plug-and-play)."""
    root = _write_repo(
        tmp_path,
        KNOWLEDGE_API_URL="http://k.test",
        MEMORY_ADAPTER_URL="http://m.test",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(root))
    for v in (
        "KNOWLEDGE_API_URL",
        "MEMORY_ADAPTER_URL",
        "STATE_API_URL",
        "AXON_SERVICE_URL",
        "CANON_MEMORY_HEALTH_REQUIRED",
    ):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    c, s = _run_captured(argv=[], monkeypatch=monkeypatch)
    o = json.loads(s)
    assert c == 0
    assert o["overall_status"] == "ok"
    graph = next(b for b in o["backends"] if b["name"] == "graph")
    assert graph["status"] == "not_configured"
    assert graph["required"] is False


def test_graph_required_unhealthy_when_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_repo(
        tmp_path,
        KNOWLEDGE_API_URL="http://k.test",
        MEMORY_ADAPTER_URL="http://m.test",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(root))
    monkeypatch.setenv("CANON_MEMORY_HEALTH_REQUIRED", "canonical,mempalace,graph")
    for v in (
        "KNOWLEDGE_API_URL",
        "MEMORY_ADAPTER_URL",
        "STATE_API_URL",
        "AXON_SERVICE_URL",
    ):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(mh, "_probe", lambda _u, _t: _ok_200())
    c, s = _run_captured(argv=[], monkeypatch=monkeypatch)
    o = json.loads(s)
    assert c == 1
    assert o["overall_status"] == "unhealthy"
    graph = next(b for b in o["backends"] if b["name"] == "graph")
    assert graph["name"] == "graph"
    assert graph["status"] == "not_configured"
    assert graph.get("last_error") == "URL not set"


def test_urls_from_home_canon_env_when_local_env_omits_urls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """memory-health hydrates ~/.canon/*.env like hooks; do not fall back to localhost only."""
    home = tmp_path / "home"
    (home / ".canon").mkdir(parents=True)
    (home / ".canon" / "canon-systems.env").write_text(
        "KNOWLEDGE_API_URL=http://from.home.k\nMEMORY_ADAPTER_URL=http://from.home.m\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    root = tmp_path / "repo"
    (root / ".canon").mkdir(parents=True)
    (root / ".canon" / "memory-layer.local.env").write_text(
        "COMPANY_ID=testco\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(root))
    for v in (
        "KNOWLEDGE_API_URL",
        "MEMORY_ADAPTER_URL",
        "STATE_API_URL",
        "AXON_SERVICE_URL",
    ):
        monkeypatch.delenv(v, raising=False)

    seen: list[str] = []

    def probe(url: str, t: int) -> dict:  # noqa: ANN001
        seen.append(url)
        return _ok_200()

    monkeypatch.setattr(mh, "_probe", probe)
    c, s = _run_captured(argv=[], monkeypatch=monkeypatch)
    assert c == 0
    o = json.loads(s)
    assert o["overall_status"] == "ok"
    assert any("from.home.k" in u for u in seen)
    assert any("from.home.m" in u for u in seen)
    assert not any("localhost:8080" in u for u in seen)
    assert not any("localhost:8090" in u for u in seen)


def test_no_live_http_in_suite(
    four_urls_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = 0

    def probe(_u, _t) -> dict:  # noqa: ANN001
        nonlocal called
        called += 1
        return _ok_200()

    monkeypatch.setattr(mh, "_probe", probe)
    c, _ = _run_captured(argv=[], monkeypatch=monkeypatch)
    assert c == 0
    assert called == 4
    # Ensure tests patch the seam (not urlopen) for isolation.
    assert mh._probe is probe
