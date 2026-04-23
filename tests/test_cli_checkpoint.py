"""E2-T3: checkpoint_cli + canon checkpoint wiring — all HTTP via _http_request monkeypatch."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest

import canon_systems.checkpoint_cli as cc
from canon_systems.cli import main


def _mk_handler(
    out: list[tuple[int, object | None, dict[str, str]]],
) -> object:
    received: list[tuple[str, str, object | None, int]] = []

    def _h(method: str, url: str, body: object | None, timeout_ms: int) -> object:
        received.append((method, url, body, timeout_ms))
        if not out:
            return (-1, None, {cc._HDR_TRANSPORT_ERR: "eof", cc._HDR_TRANSPORT_URL: url})
        st, j, h = out.pop(0)
        return (st, j, h)

    _h._received = received  # type: ignore[attr-defined]
    return _h


def _scope_flags() -> list[str]:
    return [
        "--company-id",
        "IMC",
        "--repository-id",
        "r1",
        "--plan-id",
        "p1",
        "--task-id",
        "t1",
        "--workstream-id",
        "w1",
    ]


def _read_argv() -> list[str]:
    return ["read", *_scope_flags()]


# --- AC1, imports ---

def test_stdlib_only_imports_no_banned_third_party() -> None:
    p = Path(__file__).resolve().parents[1] / "src" / "canon_systems" / "checkpoint_cli.py"
    text = p.read_text(encoding="utf-8")
    for bad in (
        "requests",
        "httpx",
        "aiohttp",
        "urllib3",
    ):
        assert re.search(rf"^(\s*import {bad}\s*$|from {bad} )", text, re.M) is None
    for need in (
        "import argparse",
        "import json",
        "import urllib.request",
    ):
        assert need in text


# --- AC2, entry ---

def test_module_exposes_run_entrypoint() -> None:
    assert callable(cc.run)
    assert cc.run(["read", "-h"]) == 0  # -h and --help both exit 0 in parse


def test_missing_checkpoint_subcommand_exits_usage() -> None:
    assert cc.run([]) == cc.EXIT_USAGE


def test_no_live_http_in_suite_monkeypatch_required(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: object, **k: object) -> object:  # noqa: ARG001
        raise AssertionError("live urlopen would have been used")

    monkeypatch.setattr(cc.urllib.request, "urlopen", boom)
    h = _mk_handler(
        [
            (200, {"ok": True}, {}),
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    buf = io.StringIO()
    monkeypatch.setattr(cc.sys, "stdout", buf)
    code = cc.run(_read_argv() + ["--base-url", "http://192.0.2.1:9"])
    assert code == 0
    o = json.loads(buf.getvalue())
    assert o.get("ok") is True
    u = h._received[0][1]  # type: ignore[attr-defined]
    assert "192.0.2.1" in u


# --- exit catalog AC22 ---

def test_exit_code_catalog_values() -> None:
    assert cc.EXIT_OK == 0
    assert cc.EXIT_VERSION_CONFLICT == 1
    assert cc.EXIT_LEASE_DENIED == 2
    assert cc.EXIT_NOT_FOUND == 3
    assert cc.EXIT_USAGE == 4
    assert cc.EXIT_TRANSPORT == 5


# --- base url AC4 ---

def test_base_url_flag_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(200, {"x": 1}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    monkeypatch.setattr(cc.sys, "stdout", io.StringIO())
    cc.run(_read_argv() + ["--base-url", "http://a.example/ "])
    r = h._received  # type: ignore[attr-defined]
    assert r[0][1].startswith("http://a.example/state/checkpoint?")
    assert "http://a.example//" not in r[0][1]


def test_base_url_env_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANON_STATE_API_URL", "http://env.test/")
    h = _mk_handler([(200, {}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    monkeypatch.setattr(cc.sys, "stdout", io.StringIO())
    cc.run(_read_argv())
    assert h._received[0][1].startswith("http://env.test/state/checkpoint?")  # type: ignore[attr-defined]


def test_base_url_default_localhost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CANON_STATE_API_URL", raising=False)
    h = _mk_handler([(200, {}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    monkeypatch.setattr(cc.sys, "stdout", io.StringIO())
    cc.run(_read_argv())
    assert "http://localhost:8080/state/checkpoint" in h._received[0][1]  # type: ignore[attr-defined]


def test_trailing_slash_stripped_in_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(200, {}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    monkeypatch.setattr(cc.sys, "stdout", io.StringIO())
    cc.run(_read_argv() + ["--base-url", "https://h.example/"])
    u = h._received[0][1]  # type: ignore[attr-defined]
    assert u.startswith("https://h.example/state/")
    assert "https://h.example//" not in u


# --- missing scope / usage AC5 AC9 AC15 ---

def test_read_missing_scope_flag_exits_usage() -> None:
    code = cc.run(
        [
            "read",
            "--company-id",
            "a",
            # missing other ids
        ]
    )
    assert code == cc.EXIT_USAGE


def test_write_missing_lease_exits_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([])
    monkeypatch.setattr(cc, "_http_request", h)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h1",
            "--phase",
            "p",
            "--phase-status",
            "s",
            "--expected-version",
            "0",
        ]
    )  # no --lease-token
    assert code == cc.EXIT_USAGE
    assert h._received == []  # type: ignore[attr-defined]


def test_write_body_file_rejects_forbidden_key_exit_usage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "b.json"
    f.write_text('{"inputs":{},"nope":1}', encoding="utf-8")
    h = _mk_handler([])
    monkeypatch.setattr(cc, "_http_request", h)
    o = io.StringIO()
    e = io.StringIO()
    monkeypatch.setattr(cc.sys, "stdout", o)
    monkeypatch.setattr(cc.sys, "stderr", e)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h",
            "--phase",
            "a",
            "--phase-status",
            "b",
            "--expected-version",
            "0",
            "--lease-token",
            "t",
            "--body-file",
            str(f),
        ]
    )
    assert code == cc.EXIT_USAGE
    j = json.loads(e.getvalue())
    assert j.get("error") == "forbidden_key" and j.get("key") == "nope"
    assert h._received == []  # type: ignore[attr-defined]


# --- read AC6-8 ---

def test_read_happy_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(200, {"a": 1, "b": 2}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    out = io.StringIO()
    monkeypatch.setattr(cc.sys, "stdout", out)
    code = cc.run(_read_argv())
    assert code == 0
    assert json.loads(out.getvalue()) == {"a": 1, "b": 2}
    m, u, b, t = h._received[0]  # type: ignore[attr-defined]
    assert m == "GET" and b is None and u.endswith("workstream_id=w1")
    assert "company_id=IMC" in u


def test_read_404_not_found_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = {
        "detail": {"error": "not_found", "pk": "p#k", "sk": "s#k"},
    }
    h = _mk_handler(
        [
            (404, detail, {}),
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    _out, err = _capture(monkeypatch)
    code = cc.run(_read_argv())
    assert code == 3
    o = json.loads(err.getvalue())
    assert o["error"] == "not_found" and o["pk"] == "p#k"


def test_read_422_validation_exit_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(422, {"detail": [{"type": "missing", "loc": ["q"]}]}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(_read_argv())
    assert code == 4
    e = json.loads(err.getvalue())
    assert e["error"] == "validation"


def test_read_transport_exits_5(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler(
        [
            (
                -1,
                None,
                {
                    cc._HDR_TRANSPORT_ERR: "nope",
                    cc._HDR_TRANSPORT_URL: "http://u/x",
                },
            ),
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(_read_argv())
    assert code == 5
    assert "transport" in err.getvalue()


def test_read_5xx_is_transport_5(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(503, {"detail": "nope"}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(_read_argv())
    assert code == 5
    assert "transport" in err.getvalue()


def _capture(monkeypatch: pytest.MonkeyPatch) -> tuple[io.StringIO, io.StringIO]:
    o = io.StringIO()
    e = io.StringIO()
    monkeypatch.setattr(cc.sys, "stdout", o)
    monkeypatch.setattr(cc.sys, "stderr", e)
    return o, e


# --- write AC11-14 ---

def test_write_happy_200_event_header_stderr_and_flat_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "b.json"
    f.write_text('{"inputs":{},"last_event_id":"e0"}', encoding="utf-8")
    h = _mk_handler(
        [
            (
                200,
                {"state_version": 1, "ok": True},
                {"X-Canon-Event-Id": "eid-1", "X-Other": "x"},
            ),
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    o = io.StringIO()
    e = io.StringIO()
    monkeypatch.setattr(cc.sys, "stdout", o)
    monkeypatch.setattr(cc.sys, "stderr", e)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h",
            "--phase",
            "ph",
            "--phase-status",
            "st",
            "--expected-version",
            "3",
            "--lease-token",
            "lt",
            "--body-file",
            str(f),
        ]
    )
    assert code == 0
    m, u, b, t = h._received[0]  # type: ignore[attr-defined]
    assert m == "PUT" and u.endswith("/state/checkpoint")
    assert b is not None and isinstance(b, dict)  # noqa: SIM102
    assert b["state_version"] == 3
    assert b["lease_token"] == "lt"
    assert b["inputs"] == {}
    assert b["last_event_id"] == "e0"
    assert "scope_ids" not in b
    assert "eid-1" in e.getvalue()
    assert o.getvalue().count("state_version") >= 1


def test_write_409_state_version_conflict_unwraps_detail_exit_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    b = {
        "detail": {
            "error": "state_version_conflict",
            "expected": 7,
            "actual": 8,
        }
    }
    h = _mk_handler([(409, b, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h",
            "--phase",
            "p",
            "--phase-status",
            "s",
            "--expected-version",
            "7",
            "--lease-token",
            "t",
        ]
    )
    assert code == 1
    j = json.loads(err.getvalue())
    assert j["error"] == "state_version_conflict"
    assert j["expected"] == 7
    assert j["actual"] == 8
    assert "resolution" in j
    assert j["resolution"]["message"]
    assert j["resolution"]["command"]


@pytest.mark.parametrize(
    "err_code",
    (
        "lease_required",
        "lease_expired",
        "lease_token_mismatch",
        "lease_held",
    ),
)
def test_write_409_lease_errors_exit_2(
    err_code: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    b = {"detail": {"error": err_code}}
    h = _mk_handler([(409, b, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h",
            "--phase",
            "p",
            "--phase-status",
            "s",
            "--expected-version",
            "1",
            "--lease-token",
            "t",
        ]
    )
    assert code == 2, err.getvalue()
    j = json.loads(err.getvalue())
    assert j.get("error") == err_code


def test_write_409_other_code_exit_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(409, {"detail": {"error": "weird_409", "a": 1}}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h",
            "--phase",
            "p",
            "--phase-status",
            "s",
            "--expected-version",
            "1",
            "--lease-token",
            "t",
        ]
    )
    assert code == 2


def test_write_404_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler(
        [
            (404, {"detail": {"error": "not_found", "pk": "P", "sk": "S"}}, {}),
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h",
            "--phase",
            "p",
            "--phase-status",
            "s",
            "--expected-version",
            "0",
            "--lease-token",
            "t",
        ]
    )
    assert code == 3


def test_write_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(422, {"detail": {"msg": 1}}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h",
            "--phase",
            "p",
            "--phase-status",
            "s",
            "--expected-version",
            "0",
            "--lease-token",
            "t",
        ]
    )
    assert code == 4


def test_write_5xx_is_transport_5(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(502, {"detail": "bad gateway"}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h",
            "--phase",
            "p",
            "--phase-status",
            "s",
            "--expected-version",
            "0",
            "--lease-token",
            "t",
        ]
    )
    assert code == 5
    assert "transport" in err.getvalue().lower() or "502" in err.getvalue()


# --- lease AC15-21 ---

def test_lease_acquire_flat_body_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler(
        [
            (
                200,
                {
                    "lease_token": "t",
                    "expires_at": 1,
                    "acquired_at": 2,
                    "owner_agent_run_id": "o",
                    "owner_actor_id": "a",
                },
                {},
            )
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    o = io.StringIO()
    monkeypatch.setattr(cc.sys, "stdout", o)
    code = cc.run(
        ["lease-acquire"] + _scope_flags()
        + [
            "--owner-agent-run-id",
            "run1",
            "--owner-actor-id",
            "ac1",
            "--ttl-seconds",
            "30",
        ]
    )
    assert code == 0
    m, u, b, t = h._received[0]  # type: ignore[attr-defined]
    assert m == "POST" and u.endswith("/state/lease/acquire")
    assert b is not None
    assert "scope_ids" not in b
    assert b["owner_agent_run_id"] == "run1"
    assert b["ttl_seconds"] == 30


def test_lease_acquire_409_lease_held_no_token_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler(
        [
            (
                409,
                {
                    "detail": {
                        "error": "lease_held",
                        "owner_agent_run_id": "other",
                        "expires_at": 99,
                        "lease_token": "secret",
                    }
                },
                {},
            )
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(
        ["lease-acquire"] + _scope_flags()
        + [
            "--owner-agent-run-id",
            "a",
            "--owner-actor-id",
            "b",
            "--ttl-seconds",
            "10",
        ]
    )
    assert code == 2
    j = json.loads(err.getvalue())
    assert "lease_token" not in j
    assert j["error"] == "lease_held"


def test_lease_acquire_bad_ttl_exit_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, err = _capture(monkeypatch)
    code = cc.run(
        ["lease-acquire"] + _scope_flags()
        + [
            "--owner-agent-run-id",
            "a",
            "--owner-actor-id",
            "b",
            "--ttl-seconds",
            "9000",  # > 3600
        ]
    )
    assert code == 4
    es = err.getvalue()
    assert "3600" in es or "ttl" in es.lower()


def test_lease_renew_nested_scope_ids_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler(
        [
            (200, {"lease_token": "L", "expires_at": 3, "extra": 9}, {}),
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    o = io.StringIO()
    monkeypatch.setattr(cc.sys, "stdout", o)
    code = cc.run(
        ["lease-renew"] + _scope_flags()
        + [
            "--lease-token",
            "L",
            "--ttl-seconds",
            "60",
        ]
    )
    assert code == 0
    m, u, b, t = h._received[0]  # type: ignore[attr-defined]
    assert b is not None
    assert b.get("scope_ids", {}).get("company_id") == "IMC"
    assert b.get("lease_token") == "L"
    j = json.loads(o.getvalue())
    assert j == {"lease_token": "L", "expires_at": 3}


def test_lease_renew_409_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler(
        [
            (409, {"detail": {"error": "lease_token_mismatch"}}, {}),
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    _o, _e = _capture(monkeypatch)
    code = cc.run(
        ["lease-renew"] + _scope_flags()
        + [
            "--lease-token",
            "L",
            "--ttl-seconds",
            "30",
        ]
    )
    assert code == 2


def test_lease_renew_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(422, {"detail": []}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, _e = _capture(monkeypatch)
    code = cc.run(
        ["lease-renew"] + _scope_flags()
        + [
            "--lease-token",
            "L",
            "--ttl-seconds",
            "30",
        ]
    )
    assert code == 4


def test_lease_renew_5xx_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(500, {}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, e = _capture(monkeypatch)
    code = cc.run(
        ["lease-renew"] + _scope_flags()
        + [
            "--lease-token",
            "L",
            "--ttl-seconds",
            "30",
        ]
    )
    assert code == 5 and "transport" in e.getvalue()


def test_lease_release_nested_and_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(200, {"released": True, "x": 1}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    o = io.StringIO()
    monkeypatch.setattr(cc.sys, "stdout", o)
    code = cc.run(
        ["lease-release"] + _scope_flags()
        + [
            "--lease-token",
            "L",
        ]
    )
    assert code == 0
    b = h._received[0][2]  # type: ignore[attr-defined]
    assert b["scope_ids"]["task_id"] == "t1"
    assert json.loads(o.getvalue()) == {"released": True}


def test_lease_release_409_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler(
        [
            (409, {"detail": {"error": "lease_token_mismatch"}}, {}),
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    _o, e = _capture(monkeypatch)
    code = cc.run(
        ["lease-release"] + _scope_flags()
        + [
            "--lease-token",
            "bad",
        ]
    )
    assert code == 2


def test_lease_release_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(422, {"detail": {"z": 1}}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    _o, _e = _capture(monkeypatch)
    code = cc.run(
        ["lease-release"] + _scope_flags()
        + [
            "--lease-token",
            "L",
        ]
    )
    assert code == 4


# --- help / main ---

def test_run_help_exits_0() -> None:
    assert cc.run(["--help"]) == 0


def test_main_checkpoint_help_exits_0() -> None:
    with pytest.raises(SystemExit) as e:
        main(["checkpoint", "--help"])
    assert e.value.code == 0


@pytest.mark.parametrize(
    "tail",
    [
        ["read", "--help"],
        ["write", "--help"],
        ["lease-acquire", "--help"],
        ["lease-renew", "--help"],
        ["lease-release", "--help"],
    ],
)
def test_main_checkpoint_subcommand_help_exits_0(tail: list[str]) -> None:
    assert main(["checkpoint", *tail]) == 0


def test_cli_py_registers_checkpoint_subcommand(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as ei:
        main(["--help"])
    assert ei.value.code == 0
    s = capsys.readouterr().out
    assert "checkpoint" in s


def test_main_delegates_to_checkpoint_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = _mk_handler([(200, {"k": 1}, {})])
    monkeypatch.setattr(cc, "_http_request", h)
    o = io.StringIO()
    monkeypatch.setattr(cc.sys, "stdout", o)
    assert (
        main(
            [
                "checkpoint",
                "read",
                "--company-id",
                "IMC",
                "--repository-id",
                "r1",
                "--plan-id",
                "p1",
                "--task-id",
                "t1",
                "--workstream-id",
                "w1",
            ]
        )
        == 0
    )


# --- living spec greps AC30-32 ---

def test_changelog_e2t3_bullet_above_e2t2_bullet() -> None:
    p = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
    t = p.read_text(encoding="utf-8")
    i3 = t.index("E2-T3: canon checkpoint")
    i2 = t.index("E2-T2: backend/state-api")
    assert i3 < i2


def test_readme_table_row_mentions_checkpoint_above_secrets() -> None:
    p = Path(__file__).resolve().parents[1] / "README.md"
    t = p.read_text(encoding="utf-8")
    a = t.index("canon checkpoint")
    b = t.index("canon secrets")
    row = t[a : a + 400]
    assert a < b
    assert "read" in row.lower() or "lease" in row.lower()


def test_system_workflow_section_6_mentions_checkpoint_and_state_api() -> None:
    p = Path(__file__).resolve().parents[1] / "docs" / "SYSTEM-WORKFLOW.md"
    t = p.read_text(encoding="utf-8")
    s = t.index("## 6) Validation")
    e = t.index("## 7) Automation", s)
    sec = t[s:e]
    assert "canon checkpoint" in sec and "state-api" in sec


# --- more coverage ---

def test_write_malformed_json_body_file_exit_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "x.json"
    f.write_text("notjson", encoding="utf-8")
    h = _mk_handler([])
    monkeypatch.setattr(cc, "_http_request", h)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h",
            "--phase",
            "p",
            "--phase-status",
            "s",
            "--expected-version",
            "0",
            "--lease-token",
            "t",
            "--body-file",
            str(f),
        ]
    )
    assert code == 4


def test_write_body_file_and_stdin_mutex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "x.json"
    f.write_text("{}", encoding="utf-8")
    h = _mk_handler([])
    monkeypatch.setattr(cc, "_http_request", h)
    code = cc.run(
        ["write"] + _scope_flags()
        + [
            "--handoff-id",
            "h",
            "--phase",
            "p",
            "--phase-status",
            "s",
            "--expected-version",
            "0",
            "--lease-token",
            "t",
            "--body-file",
            str(f),
            "--stdin",
        ]
    )
    assert code == 4
    assert h._received == []  # type: ignore[attr-defined]


def test_unwrap_fastapi_404_uses_detail_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # no double nesting in stderr
    h = _mk_handler(
        [
            (404, {"detail": {"error": "not_found", "pk": "1", "sk": "2"}}, {}),
        ]
    )
    monkeypatch.setattr(cc, "_http_request", h)
    _o, e = _capture(monkeypatch)
    code = cc.run(_read_argv())
    assert code == 3
    j = json.loads(e.getvalue())
    assert "detail" not in j or "error" in j  # we emit flat not_found
