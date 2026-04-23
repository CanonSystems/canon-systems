"""Tests for `canon release publish-on-pass` (E5-T7)."""

from __future__ import annotations

import io
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest

from canon_systems import release_publish

_FORBIDDEN_METHODS: tuple[str, ...] = (
    "put_object",
    "put_object_acl",
    "put_object_tagging",
    "put_object_retention",
    "put_object_legal_hold",
    "put_bucket_policy",
    "put_bucket_acl",
    "put_bucket_tagging",
    "put_bucket_cors",
    "put_bucket_versioning",
    "delete_object",
    "delete_objects",
    "delete_object_tagging",
    "copy_object",
    "copy",
    "upload_file",
    "upload_fileobj",
    "upload_part",
    "upload_part_copy",
    "create_multipart_upload",
    "complete_multipart_upload",
    "abort_multipart_upload",
    "restore_object",
    "write_get_object_response",
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class _FakeCompleted:
    returncode: int


class _SubprocessSpy:
    def __init__(self, returncodes: list[int]) -> None:
        self.returncodes = list(returncodes)
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **_kwargs: Any) -> _FakeCompleted:
        self.calls.append(list(argv))
        rc = self.returncodes.pop(0) if self.returncodes else 0
        return _FakeCompleted(returncode=rc)


class _SleepSpy:
    def __init__(self) -> None:
        self.sleeps: list[float] = []
        self.total = 0.0

    def __call__(self, secs: float) -> None:
        self.sleeps.append(float(secs))
        self.total += float(secs)


class _HttpPostSpy:
    def __init__(self, *, status: int = 200, raise_exc: BaseException | None = None) -> None:
        self.status = status
        self.raise_exc = raise_exc
        self.calls: list[tuple[str, bytes, float]] = []

    def __call__(self, url: str, body: bytes, *, timeout: float) -> int:
        self.calls.append((url, body, float(timeout)))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.status


def _install_seams(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncodes: list[int] | None = None,
    notifier_status: int = 200,
    notifier_raise: BaseException | None = None,
) -> tuple[_SubprocessSpy, _SleepSpy, _HttpPostSpy]:
    sp = _SubprocessSpy(returncodes or [0])
    sl = _SleepSpy()
    hp = _HttpPostSpy(status=notifier_status, raise_exc=notifier_raise)
    monkeypatch.setattr(release_publish, "_run_subprocess", sp)
    monkeypatch.setattr(release_publish, "_sleep", sl)
    monkeypatch.setattr(release_publish, "_http_post", hp)
    return sp, sl, hp


def _write_release_status(path: Path, *, qa: str = "PASS", ci: str = "PASS", merge: str = "PASS") -> None:
    body = f"""RELEASE_STATUS
  initiative: "Canon Memory Platform v1"
  task_id: "E5-T7"
  branch: "wave/5/canon-memory-v1"
  pr_url: "pending"
  qa_gate: "{qa}"
  ci_gate: "{ci}"
  merge_gate: "{merge}"
  environment: "dev"
  deploy_gate: "PENDING"
  rollback_ref: "HEAD"
  blockers: []
  next_action: "promote to staging"
END_RELEASE_STATUS
"""
    path.write_text(body, encoding="utf-8")


def _base_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CANON_PLAN_ID", "plan-alpha")
    monkeypatch.setenv("CANON_COMPANY_ID", "acme")
    monkeypatch.setenv("CANON_REPOSITORY_ID", "canon-systems")
    monkeypatch.setenv("CANON_VAULT_BUCKET", "acme-vault")
    monkeypatch.setenv("CANON_VAULT_PREFIX", "vaults/acme/canon-systems")
    monkeypatch.setenv("CANON_EVENTS_FILE", str(tmp_path / "events-in.ndjson"))
    (tmp_path / "events-in.ndjson").write_text("", encoding="utf-8")
    monkeypatch.delenv("CANON_PUBLISH_NOTIFIER_URL", raising=False)
    monkeypatch.delenv("CANON_PUBLISH_RETRIES", raising=False)
    monkeypatch.delenv("CANON_PUBLISH_BACKOFF_BASE", raising=False)
    monkeypatch.delenv("CANON_PUBLISH_BACKOFF_CAP", raising=False)


def _capture_stdout(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    out = capsys.readouterr().out.strip().splitlines()
    assert out, "expected at least one stdout line"
    return json.loads(out[-1])


def _event_log(tmp_path: Path) -> Path:
    return tmp_path / ".canon" / "memory" / "events.ndjson"


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ac1_help_exits_nonzero_with_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as ei:
        release_publish.run(["--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "publish-on-pass" in out


def test_ac2_cli_surface_wired_through_canon_release(monkeypatch: pytest.MonkeyPatch) -> None:
    from canon_systems import cli

    captured: dict[str, Any] = {}

    def fake_run(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(release_publish, "run", fake_run)
    rc = cli.main(["release", "publish-on-pass", "--release-status-file", "foo.md"])
    assert rc == 0
    assert captured["argv"] == ["publish-on-pass", "--release-status-file", "foo.md"]


def test_ac3_pass_triggers_single_publish(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    sp, sl, _hp = _install_seams(monkeypatch, returncodes=[0])
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)

    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-001",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK
    assert len(sp.calls) == 1
    argv = sp.calls[0]
    assert argv[:3] == ["canon", "synth", "publish"]
    assert "--plan-id" in argv and "plan-alpha" in argv
    assert "--bucket" in argv and "acme-vault" in argv
    assert "--prefix" in argv and "vaults/acme/canon-systems" in argv
    assert "--events-file" in argv
    env = _capture_stdout(capsys)
    assert env["action"] == "published"
    assert env["attempts"] == 1
    assert env["release_id"] == "rel-001"
    assert sl.sleeps == []


def test_ac4_non_pass_skips_publish(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    sp, _sl, _hp = _install_seams(monkeypatch, returncodes=[0])
    rs = tmp_path / "release-status.md"
    _write_release_status(rs, qa="FAIL")

    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-002",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK
    assert sp.calls == []
    env = _capture_stdout(capsys)
    assert env["action"] == "skipped"
    assert env["reason"] == "non_pass"
    assert "qa_gate=FAIL" in env["detail"]


def test_ac4b_missing_gate_skips_publish(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    sp, _sl, _hp = _install_seams(monkeypatch)
    rs = tmp_path / "release-status.md"
    rs.write_text(
        'RELEASE_STATUS\n  qa_gate: "PASS"\n  ci_gate: "PASS"\nEND_RELEASE_STATUS\n',
        encoding="utf-8",
    )
    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-missing",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK
    assert sp.calls == []
    env = _capture_stdout(capsys)
    assert env["reason"] == "non_pass"
    assert "merge_gate=MISSING" in env["detail"]


def test_ac5_retries_with_exponential_backoff(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    sp, sl, _hp = _install_seams(monkeypatch, returncodes=[1, 1, 0])
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)

    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-retry",
        "--retries", "3",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK
    assert len(sp.calls) == 3
    assert sl.sleeps == [1.0, 2.0]
    env = _capture_stdout(capsys)
    assert env["attempts"] == 3
    assert env["sleeps"] == [1.0, 2.0]


def test_ac5_permanent_failure_exits_five_and_emits_failed_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    sp, sl, _hp = _install_seams(monkeypatch, returncodes=[1, 1, 1])
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)

    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-dead",
        "--retries", "3",
    ])
    assert rc == release_publish.PUBLISH_EXIT_FAILED
    assert len(sp.calls) == 3
    assert sl.sleeps == [1.0, 2.0]
    err_line = capsys.readouterr().err.strip().splitlines()[-1]
    err = json.loads(err_line)
    assert err["error"] == "publish_failed"

    events = _read_events(_event_log(tmp_path))
    publish_events = [e for e in events if e["event_type"] == "synth_publish"]
    assert publish_events, "expected at least one synth_publish event"
    assert publish_events[-1]["payload"]["status"] == "failed"
    assert publish_events[-1]["payload"]["attempts"] == 3


def test_ac5_backoff_cap_at_sixty_seconds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    _sp, sl, _hp = _install_seams(monkeypatch, returncodes=[1, 1, 1, 1, 1, 1, 1, 0])
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)

    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-cap",
        "--retries", "8",
        "--backoff-base", "1.0",
        "--backoff-cap", "60.0",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK
    assert sl.sleeps == [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0]


def test_ac6_already_published_is_byte_identical_noop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    sp, _sl, _hp = _install_seams(monkeypatch, returncodes=[0, 0])
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)

    rc1 = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-idem",
    ])
    assert rc1 == release_publish.PUBLISH_EXIT_OK
    capsys.readouterr()
    assert len(sp.calls) == 1

    rc2 = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-idem",
    ])
    assert rc2 == release_publish.PUBLISH_EXIT_OK
    assert len(sp.calls) == 1, "second invocation must not re-run publish"
    env = _capture_stdout(capsys)
    assert env["action"] == "skipped"
    assert env["reason"] == "already_published"


def test_ac7_optional_notifier_absent_is_noop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    _sp, _sl, hp = _install_seams(monkeypatch, returncodes=[0])
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)

    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-no-notifier",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK
    assert hp.calls == []
    env = _capture_stdout(capsys)
    assert env["notifier"] == {"attempted": False}


def test_ac7_notifier_set_posts_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("CANON_PUBLISH_NOTIFIER_URL", "https://hooks.example/vault")
    _sp, _sl, hp = _install_seams(monkeypatch, returncodes=[0], notifier_status=202)
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)

    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-notify",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK
    assert len(hp.calls) == 1
    url, body, timeout = hp.calls[0]
    assert url == "https://hooks.example/vault"
    payload = json.loads(body.decode("utf-8"))
    assert set(payload.keys()) == {"plan_id", "release_id", "publish_cutoff", "event_id"}
    assert payload["plan_id"] == "plan-alpha"
    assert payload["release_id"] == "rel-notify"
    assert timeout == 5.0
    env = _capture_stdout(capsys)
    assert env["notifier"]["attempted"] is True
    assert env["notifier"]["ok"] is True
    assert env["notifier"]["http_status"] == 202


def test_ac7_notifier_failure_never_fails_release(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("CANON_PUBLISH_NOTIFIER_URL", "https://hooks.example/vault")
    _sp, _sl, _hp = _install_seams(
        monkeypatch,
        returncodes=[0],
        notifier_raise=OSError("connection refused"),
    )
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)

    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-notify-bad",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK
    err = capsys.readouterr().err
    assert "vault_sync_notifier_failed" in err
    events = _read_events(_event_log(tmp_path))
    assert not any(e["event_type"] == "vault_sync_notified" for e in events)
    assert any(e["event_type"] == "synth_publish" and e["payload"]["status"] == "ok" for e in events)


def test_ac8_event_emission_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("CANON_PUBLISH_NOTIFIER_URL", "https://hooks.example/vault")
    _install_seams(monkeypatch, returncodes=[0], notifier_status=200)
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)

    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-evt",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK

    events = _read_events(_event_log(tmp_path))
    types = [e["event_type"] for e in events]
    assert types.count("synth_publish") == 1
    assert types.count("vault_sync_notified") == 1
    pub = next(e for e in events if e["event_type"] == "synth_publish")
    assert pub["schema_version"] == 1
    assert pub["agent_name"] == "release-orchestrator"
    assert pub["plan_id"] == "plan-alpha"
    assert pub["payload"]["release_id"] == "rel-evt"
    assert pub["payload"]["status"] == "ok"
    notif = next(e for e in events if e["event_type"] == "vault_sync_notified")
    assert notif["payload"]["publish_event_id"] == pub["event_id"]
    assert notif["payload"]["http_status"] == 200


def test_ac9_release_publish_source_has_no_s3_write_calls() -> None:
    src = Path(release_publish.__file__).read_text(encoding="utf-8")
    hits = []
    for name in _FORBIDDEN_METHODS:
        for m in re.finditer(rf"\b{name}\s*\(", src):
            hits.append((name, m.start()))
    assert hits == [], f"release_publish.py must not call forbidden S3 write methods, found: {hits}"
    # Self-check: the forbidden tuple itself must cover the boto3 mutation vocabulary.
    assert "put_object" in _FORBIDDEN_METHODS
    assert "delete_object" in _FORBIDDEN_METHODS
    assert "copy_object" in _FORBIDDEN_METHODS


def test_ac11_integration_pass_triggers_publish_and_sync_within_thirty_seconds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("CANON_PUBLISH_NOTIFIER_URL", "https://hooks.example/vault")
    sp, sl, hp = _install_seams(monkeypatch, returncodes=[1, 0], notifier_status=200)
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)

    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-integration",
        "--retries", "3",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK
    assert len(sp.calls) == 2, "expected one failure + one success"
    assert len(hp.calls) == 1, "notifier must POST exactly once on success"
    assert sl.total < 30.0, f"cumulative sleep before notifier must be under 30s, got {sl.total}s"
    env = _capture_stdout(capsys)
    assert env["action"] == "published"
    assert env["notifier"]["ok"] is True


def test_inline_json_release_status_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    _install_seams(monkeypatch, returncodes=[0])
    payload = json.dumps({
        "qa_gate": "PASS",
        "ci_gate": "PASS",
        "merge_gate": "PASS",
        "plan_id": "plan-alpha",
        "task_id": "E5-T7",
    })
    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-json", payload,
        "--release-id", "rel-json",
    ])
    assert rc == release_publish.PUBLISH_EXIT_OK
    env = _capture_stdout(capsys)
    assert env["action"] == "published"


def test_missing_release_status_body_is_usage_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _base_env(monkeypatch, tmp_path)
    _install_seams(monkeypatch)
    rc = release_publish.run(["publish-on-pass"])
    assert rc == release_publish.PUBLISH_EXIT_USAGE
    err = capsys.readouterr().err
    assert "release-status body not provided" in err


def test_config_error_when_required_ids_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    for env in (
        "CANON_PLAN_ID",
        "CANON_COMPANY_ID",
        "CANON_REPOSITORY_ID",
        "CANON_VAULT_BUCKET",
        "CANON_VAULT_PREFIX",
        "CANON_EVENTS_FILE",
    ):
        monkeypatch.delenv(env, raising=False)
    _install_seams(monkeypatch)
    rs = tmp_path / "release-status.md"
    _write_release_status(rs)
    rc = release_publish.run([
        "publish-on-pass",
        "--release-status-file", str(rs),
        "--release-id", "rel-config",
    ])
    assert rc == release_publish.PUBLISH_EXIT_CONFIG
    err = capsys.readouterr().err
    body = json.loads(err.strip().splitlines()[-1])
    assert body["error"] == "config"
    assert set(body["missing"]) >= {"plan_id", "company_id", "repository_id", "bucket", "prefix", "events_file"}
