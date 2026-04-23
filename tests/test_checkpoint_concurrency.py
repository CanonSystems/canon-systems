"""E4-T2: checkpoint 409 resolution hints + happy-path / contention flows (monkeypatched _http_request)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from canon_systems import checkpoint_cli


REPO_ROOT = Path(__file__).resolve().parents[1]


def _scope_args(extra: list[str] | None = None) -> list[str]:
    base = [
        "--company-id",
        "c-1",
        "--repository-id",
        "r-1",
        "--plan-id",
        "p-1",
        "--task-id",
        "t-1",
        "--workstream-id",
        "ws-1",
    ]
    return base + (extra or [])


def _queue(
    *responses: tuple[int, object | None, dict[str, str]],
) -> object:
    it = iter(responses)

    def _fake(
        method: str, url: str, body: object | None, timeout_ms: int
    ) -> tuple[int, object | None, dict[str, str]]:
        return next(it)  # type: ignore[return-value]

    return _fake


def test_resolution_hint_kinds_enum() -> None:
    for k in (
        "state_version_conflict",
        "lease_held",
        "lease_denied",
        "lease_expired",
    ):
        h = checkpoint_cli._resolution_hint(k)
        assert isinstance(h, dict)
        assert h.get("message", "").strip()
        assert h.get("command", "").strip()
    u = checkpoint_cli._resolution_hint("totally_unknown_kind_xyz")
    d = checkpoint_cli._resolution_hint("lease_denied")
    assert u == d


def test_write_version_conflict_includes_resolution(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _fake(
        method: str, url: str, body: object | None, timeout_ms: int
    ) -> tuple[int, object | None, dict[str, str]]:
        return (
            409,
            {
                "detail": {
                    "error": "state_version_conflict",
                    "expected": 5,
                    "actual": 7,
                }
            },
            {},
        )

    monkeypatch.setattr(checkpoint_cli, "_http_request", _fake)
    rc = checkpoint_cli.run(
        ["write"]
        + _scope_args(
            [
                "--handoff-id",
                "h",
                "--phase",
                "implementer",
                "--phase-status",
                "completed",
                "--expected-version",
                "5",
                "--lease-token",
                "tok-1",
            ]
        )
    )
    assert rc == checkpoint_cli.EXIT_VERSION_CONFLICT
    err = capsys.readouterr().err.strip()
    payload = json.loads(err)
    assert payload["error"] == "state_version_conflict"
    assert payload["expected"] == 5
    assert payload["actual"] == 7
    assert "resolution" in payload
    assert payload["resolution"]["command"].startswith("canon checkpoint read")


def test_write_lease_denied_includes_resolution(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _fake(
        method: str, url: str, body: object | None, timeout_ms: int
    ) -> tuple[int, object | None, dict[str, str]]:
        return (409, {"detail": {"error": "lease_invalid"}}, {})

    monkeypatch.setattr(checkpoint_cli, "_http_request", _fake)
    rc = checkpoint_cli.run(
        ["write"]
        + _scope_args(
            [
                "--handoff-id",
                "h",
                "--phase",
                "implementer",
                "--phase-status",
                "completed",
                "--expected-version",
                "1",
                "--lease-token",
                "tok-1",
            ]
        )
    )
    assert rc == checkpoint_cli.EXIT_LEASE_DENIED
    err = capsys.readouterr().err.strip()
    p = json.loads(err)
    assert p.get("error") == "lease_invalid"
    assert "resolution" in p
    assert p["resolution"]["command"].startswith("canon checkpoint lease-acquire")


def test_acquire_lease_held_includes_owner_and_resolution(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _fake(
        method: str, url: str, body: object | None, timeout_ms: int
    ) -> tuple[int, object | None, dict[str, str]]:
        return (
            409,
            {
                "detail": {
                    "error": "lease_held",
                    "owner_agent_run_id": "run-abc",
                    "expires_at": "2026-04-23T00:00:00Z",
                }
            },
            {},
        )

    monkeypatch.setattr(checkpoint_cli, "_http_request", _fake)
    rc = checkpoint_cli.run(
        ["lease-acquire"]
        + _scope_args(
            [
                "--owner-agent-run-id",
                "run-1",
                "--owner-actor-id",
                "a-1",
                "--ttl-seconds",
                "300",
            ]
        )
    )
    assert rc == checkpoint_cli.EXIT_LEASE_DENIED
    p = json.loads(capsys.readouterr().err.strip())
    assert p["error"] == "lease_held"
    assert p["owner_agent_run_id"] == "run-abc"
    assert p["expires_at"] == "2026-04-23T00:00:00Z"
    assert "resolution" in p
    assert "lease-acquire" in p["resolution"]["command"]


def test_renew_409_includes_resolution(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _fake(
        method: str, url: str, body: object | None, timeout_ms: int
    ) -> tuple[int, object | None, dict[str, str]]:
        return (409, {"detail": {"error": "lease_expired"}}, {})

    monkeypatch.setattr(checkpoint_cli, "_http_request", _fake)
    rc = checkpoint_cli.run(
        ["lease-renew"] + _scope_args(["--lease-token", "t", "--ttl-seconds", "60"])
    )
    assert rc == checkpoint_cli.EXIT_LEASE_DENIED
    p = json.loads(capsys.readouterr().err.strip())
    assert p.get("error") == "lease_expired"
    assert "lease-acquire" in p["resolution"]["command"]


def test_release_409_includes_resolution(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _fake(
        method: str, url: str, body: object | None, timeout_ms: int
    ) -> tuple[int, object | None, dict[str, str]]:
        return (409, {"detail": {"error": "lease_expired"}}, {})

    monkeypatch.setattr(checkpoint_cli, "_http_request", _fake)
    rc = checkpoint_cli.run(["lease-release"] + _scope_args(["--lease-token", "bad"]))
    assert rc == checkpoint_cli.EXIT_LEASE_DENIED
    p = json.loads(capsys.readouterr().err.strip())
    assert "resolution" in p
    assert p["resolution"]["message"]


@pytest.mark.parametrize(
    "http_response,run_argv,expected_keys",
    [
        (
            (
                409,
                {
                    "detail": {
                        "error": "state_version_conflict",
                        "expected": 2,
                        "actual": 3,
                    }
                },
                {},
            ),
            [
                "write",
                *(
                    _scope_args(
                        [
                            "--handoff-id",
                            "h",
                            "--phase",
                            "p",
                            "--phase-status",
                            "s",
                            "--expected-version",
                            "2",
                            "--lease-token",
                            "x",
                        ]
                    )
                ),
            ],
            ("error", "expected", "actual"),
        ),
        (
            (409, {"detail": {"error": "lease_required"}}, {}),
            [
                "write",
                *(
                    _scope_args(
                        [
                            "--handoff-id",
                            "h",
                            "--phase",
                            "p",
                            "--phase-status",
                            "s",
                            "--expected-version",
                            "0",
                            "--lease-token",
                            "x",
                        ]
                    )
                ),
            ],
            ("error",),
        ),
        (
            (
                409,
                {
                    "detail": {
                        "error": "lease_held",
                        "owner_agent_run_id": "o1",
                        "expires_at": "e1",
                    }
                },
                {},
            ),
            [
                "lease-acquire",
                *(
                    _scope_args(
                        [
                            "--owner-agent-run-id",
                            "a",
                            "--owner-actor-id",
                            "b",
                            "--ttl-seconds",
                            "10",
                        ]
                    )
                ),
            ],
            ("error", "owner_agent_run_id", "expires_at"),
        ),
        (
            (409, {"detail": {"error": "lease_token_mismatch"}}, {}),
            [
                "lease-renew",
                *(_scope_args(["--lease-token", "L", "--ttl-seconds", "30"])),
            ],
            ("error",),
        ),
    ],
)
def test_backward_compat_existing_keys_preserved(
    http_response: tuple[int, object, dict[str, str]],
    run_argv: list[str],
    expected_keys: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _f(
        method: str, url: str, body: object | None, timeout_ms: int
    ) -> tuple[int, object | None, dict[str, str]]:
        return http_response  # type: ignore[return-value]

    monkeypatch.setattr(checkpoint_cli, "_http_request", _f)
    checkpoint_cli.run(run_argv)
    p = json.loads(capsys.readouterr().err.strip())
    for k in expected_keys:
        assert k in p
    assert "resolution" in p


def test_acquire_write_renew_release_happy_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = _queue(
        (
            200,
            {
                "lease_token": "tok-1",
                "expires_at": "2026-01-01T00:00:00Z",
            },
            {},
        ),
        (
            200,
            {"state_version": 1, "last_event_id": "ev-1"},
            {},
        ),
        (
            200,
            {
                "lease_token": "tok-1",
                "expires_at": "2026-01-01T00:10:00Z",
            },
            {},
        ),
        (200, {"released": True}, {}),
    )
    monkeypatch.setattr(checkpoint_cli, "_http_request", f)
    a = [
        "lease-acquire",
        *(
            _scope_args(
                [
                    "--owner-agent-run-id",
                    "run-1",
                    "--owner-actor-id",
                    "act-1",
                    "--ttl-seconds",
                    "300",
                ]
            )
        ),
    ]
    w = [
        "write",
        *(
            _scope_args(
                [
                    "--handoff-id",
                    "h1",
                    "--phase",
                    "implementer",
                    "--phase-status",
                    "completed",
                    "--expected-version",
                    "0",
                    "--lease-token",
                    "tok-1",
                ]
            )
        ),
    ]
    r = [
        "lease-renew",
        *(_scope_args(["--lease-token", "tok-1", "--ttl-seconds", "300"])),
    ]
    rel = ["lease-release", *(_scope_args(["--lease-token", "tok-1"]))]
    assert checkpoint_cli.run(a) == 0
    o1 = json.loads(capsys.readouterr().out.strip())
    assert o1["lease_token"] == "tok-1"
    assert checkpoint_cli.run(w) == 0
    o2 = json.loads(capsys.readouterr().out.strip())
    assert o2["state_version"] == 1
    assert checkpoint_cli.run(r) == 0
    o3 = json.loads(capsys.readouterr().out.strip())
    assert o3["lease_token"] == "tok-1"
    assert checkpoint_cli.run(rel) == 0
    o4 = json.loads(capsys.readouterr().out.strip())
    assert o4.get("released") is True


def test_two_clients_second_acquire_denied(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = _queue(
        (200, {"lease_token": "a", "expires_at": "e0"}, {}),
        (
            409,
            {
                "detail": {
                    "error": "lease_held",
                    "owner_agent_run_id": "first",
                    "expires_at": "e0",
                }
            },
            {},
        ),
    )
    monkeypatch.setattr(checkpoint_cli, "_http_request", f)
    base = _scope_args(
        [
            "--owner-agent-run-id",
            "run-x",
            "--owner-actor-id",
            "act-x",
            "--ttl-seconds",
            "60",
        ]
    )
    assert checkpoint_cli.run(["lease-acquire", *base]) == 0
    capsys.readouterr()
    assert checkpoint_cli.run(["lease-acquire", *base]) == 2
    p = json.loads(capsys.readouterr().err.strip())
    assert p["owner_agent_run_id"] == "first"
    assert "resolution" in p


def test_version_conflict_then_reread_then_succeed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = _queue(
        (
            409,
            {
                "detail": {
                    "error": "state_version_conflict",
                    "expected": 5,
                    "actual": 7,
                }
            },
            {},
        ),
        (200, {"state_version": 7, "last_event_id": "k"}, {}),
    )
    monkeypatch.setattr(checkpoint_cli, "_http_request", f)
    w5 = [
        "write",
        *(
            _scope_args(
                [
                    "--handoff-id",
                    "h",
                    "--phase",
                    "implementer",
                    "--phase-status",
                    "completed",
                    "--expected-version",
                    "5",
                    "--lease-token",
                    "t",
                ]
            )
        ),
    ]
    w7 = [
        "write",
        *(
            _scope_args(
                [
                    "--handoff-id",
                    "h",
                    "--phase",
                    "implementer",
                    "--phase-status",
                    "completed",
                    "--expected-version",
                    "7",
                    "--lease-token",
                    "t",
                ]
            )
        ),
    ]
    assert checkpoint_cli.run(w5) == 1
    e1 = capsys.readouterr().err
    p1 = json.loads(e1.strip())
    assert p1.get("error") == "state_version_conflict"
    assert p1.get("expected") == 5
    assert checkpoint_cli.run(w7) == 0
    out2 = capsys.readouterr().out
    p2 = json.loads(out2.strip())
    assert p2["state_version"] == 7


def test_implementer_template_documents_conflict_recovery() -> None:
    p = (REPO_ROOT / "src/canon_systems/templates/agents/implementer.md").read_text(
        encoding="utf-8"
    )
    assert "### Conflict recovery (E4-T2)" in p
    assert "canon checkpoint read" in p
    assert "canon checkpoint lease-acquire" in p
    assert "exit `1`" in p
    assert "or `2`" in p


def test_release_orchestrator_template_references_conflict_recovery() -> None:
    t = (REPO_ROOT / "src/canon_systems/templates/agents/release-orchestrator.md").read_text(
        encoding="utf-8"
    )
    assert "Conflict recovery" in t
    assert "implementer.md" in t


def test_changelog_has_e4t2_bullet() -> None:
    ch = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "**E4-T2**" in ch
    i2 = ch.index("**E4-T2**")
    u = ch.index("## [Unreleased]")
    assert i2 > u
    i1 = ch.index("**E4-T1**")
    assert i2 < i1


def test_system_workflow_documents_enforcement() -> None:
    w = (REPO_ROOT / "docs/SYSTEM-WORKFLOW.md").read_text(encoding="utf-8")
    assert "E4-T2" in w
    assert "resolution" in w
    assert "enforcement" in w.lower() or "lease" in w
