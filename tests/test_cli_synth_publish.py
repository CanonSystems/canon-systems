"""Tests for canon synth publish CLI (E5-T3)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from botocore.exceptions import ClientError

from canon_systems import synth_cli


class _ListPaginator:
    def __init__(self, parent: "FakeS3") -> None:
        self._parent = parent

    def paginate(self, **kwargs: Any):
        prefix = kwargs.get("Prefix") or ""
        keys = sorted(k for k in self._parent.objects if not prefix or k.startswith(prefix))
        yield {"Contents": [{"Key": k, "Size": 0} for k in keys]} if keys else {"Contents": []}


class FakeS3:
    def __init__(self, *, fail_mode: str | None = None) -> None:
        self.objects: dict[str, dict[str, Any]] = {}
        self.put_calls: list[str] = []
        self.fail_mode = fail_mode

    def put_object(self, *, Bucket, Key, Body, ContentType=None, Metadata=None):  # noqa: N803
        if self.fail_mode == "service_unavailable":
            raise ClientError(
                {"Error": {"Code": "ServiceUnavailable", "Message": "down"},
                 "ResponseMetadata": {"HTTPStatusCode": 503}},
                "PutObject",
            )
        self.objects[Key] = {
            "Body": Body,
            "ContentType": ContentType or "application/octet-stream",
            "Metadata": dict(Metadata) if Metadata else {},
        }
        self.put_calls.append(Key)
        return {"ETag": '"fake"'}

    def head_object(self, *, Bucket, Key):  # noqa: N803
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "not found"},
                 "ResponseMetadata": {"HTTPStatusCode": 404}},
                "HeadObject",
            )
        o = self.objects[Key]
        return {"ContentType": o.get("ContentType"), "Metadata": o.get("Metadata", {})}

    def get_paginator(self, name: str) -> _ListPaginator:
        _ = name
        return _ListPaginator(self)


def _event(event_id: str, event_type: str = "release_status", *, timestamp: str = "2026-04-23T12:00:00Z",
           plan_id: str = "canon-memory-v1", task_id: str = "E5-T3",
           payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event_id": event_id,
        "parent_event_id": "",
        "event_type": event_type,
        "company_id": "c1",
        "repository_id": "r1",
        "plan_id": plan_id,
        "task_id": task_id,
        "handoff_id": f"h-{event_id}",
        "agent_name": "release-orchestrator",
        "agent_run_id": f"run-{event_id}",
        "actor_id": "actor-1",
        "model": "claude-opus-4",
        "timestamp": timestamp,
        "state_version": 1,
        "payload": payload or {"verdict": "PASS"},
    }


def _write_events(tmp_path: Path, events: list[dict[str, Any]]) -> Path:
    p = tmp_path / "events.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return p


@pytest.fixture
def fake_s3(monkeypatch: pytest.MonkeyPatch) -> FakeS3:
    fake = FakeS3()
    monkeypatch.setattr(synth_cli, "_s3_client_factory", lambda region, profile: fake)
    return fake


def test_ac1_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    # argparse SystemExit(0) on --help; run() normalizes to EXIT_OK.
    rc = synth_cli.run(["publish", "--help"])
    assert rc == synth_cli.EXIT_OK
    out = capsys.readouterr().out
    for flag in ("--events-file", "--plan-id", "--company-id", "--repository-id",
                 "--cutoff-timestamp", "--bucket", "--prefix"):
        assert flag in out


def test_ac2_happy_path_writes_pages(tmp_path: Path, fake_s3: FakeS3,
                                     capsys: pytest.CaptureFixture[str]) -> None:
    ev_file = _write_events(tmp_path, [
        _event("e1", timestamp="2026-04-23T12:00:00Z"),
        _event("e2", event_type="checkpoint_write", timestamp="2026-04-23T12:05:00Z"),
        _event("e3", event_type="retrieval_breakdown", timestamp="2026-04-23T12:10:00Z"),
    ])
    rc = synth_cli.run([
        "publish",
        "--events-file", str(ev_file),
        "--plan-id", "canon-memory-v1",
        "--company-id", "c1",
        "--repository-id", "r1",
        "--cutoff-timestamp", "2026-04-23T00:00:00Z",
        "--bucket", "b-test",
        "--prefix", "vaults/c1/r1",
    ])
    assert rc == synth_cli.EXIT_OK
    out = capsys.readouterr().out.strip()
    env = json.loads(out)
    assert env["dry_run"] is False
    assert env["events_read"] == 3
    assert env["pages_rendered"] >= 1
    assert env["written"] == env["pages_rendered"]
    assert env["skipped"] == 0
    assert env["keys_written"] == sorted(env["keys_written"])
    assert len(fake_s3.put_calls) == env["written"]


def test_ac3_second_run_is_idempotent(tmp_path: Path, fake_s3: FakeS3,
                                      capsys: pytest.CaptureFixture[str]) -> None:
    ev_file = _write_events(tmp_path, [
        _event("e1", timestamp="2026-04-23T12:00:00Z"),
        _event("e2", event_type="checkpoint_write", timestamp="2026-04-23T12:05:00Z"),
    ])
    argv = [
        "publish",
        "--events-file", str(ev_file),
        "--plan-id", "canon-memory-v1",
        "--company-id", "c1", "--repository-id", "r1",
        "--cutoff-timestamp", "2026-04-23T00:00:00Z",
        "--bucket", "b-test", "--prefix", "vaults/c1/r1",
    ]
    rc1 = synth_cli.run(argv)
    first = json.loads(capsys.readouterr().out.strip())
    assert rc1 == synth_cli.EXIT_OK
    assert first["written"] >= 1
    fake_s3.put_calls.clear()

    rc2 = synth_cli.run(argv)
    second = json.loads(capsys.readouterr().out.strip())
    assert rc2 == synth_cli.EXIT_OK
    assert second["written"] == 0
    assert second["skipped"] == first["written"]
    assert second["keys_written"] == []
    assert fake_s3.put_calls == []


def test_ac4_dry_run_skips_s3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                              capsys: pytest.CaptureFixture[str]) -> None:
    def _boom(region: str, profile: str):
        raise AssertionError("dry-run must not build an S3 client")

    monkeypatch.setattr(synth_cli, "_s3_client_factory", _boom)
    ev_file = _write_events(tmp_path, [_event("e1")])
    rc = synth_cli.run([
        "publish",
        "--events-file", str(ev_file),
        "--plan-id", "canon-memory-v1",
        "--company-id", "c1", "--repository-id", "r1",
        "--cutoff-timestamp", "2026-04-23T00:00:00Z",
        "--bucket", "b-test", "--prefix", "vaults/c1/r1",
        "--dry-run",
    ])
    assert rc == synth_cli.EXIT_OK
    env = json.loads(capsys.readouterr().out.strip())
    assert env["dry_run"] is True
    assert env["written"] == 0 and env["skipped"] == 0
    assert env["pages_rendered"] >= 1


def test_ac5_bad_jsonl_exits_usage(tmp_path: Path, fake_s3: FakeS3,
                                   capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"schema_version":1,"event_id":"x"}\n', encoding="utf-8")
    rc = synth_cli.run([
        "publish",
        "--events-file", str(bad),
        "--plan-id", "p", "--company-id", "c", "--repository-id", "r",
        "--cutoff-timestamp", "2026-01-01T00:00:00Z",
        "--bucket", "b", "--prefix", "x",
    ])
    assert rc == synth_cli.EXIT_USAGE
    err = capsys.readouterr().err.strip()
    payload = json.loads(err)
    assert payload["error"] == "usage"
    assert fake_s3.put_calls == []


def test_ac6_transport_error_maps_to_exit_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                            capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeS3(fail_mode="service_unavailable")
    monkeypatch.setattr(synth_cli, "_s3_client_factory", lambda r, p: fake)
    ev_file = _write_events(tmp_path, [_event("e1")])
    rc = synth_cli.run([
        "publish",
        "--events-file", str(ev_file),
        "--plan-id", "canon-memory-v1",
        "--company-id", "c1", "--repository-id", "r1",
        "--cutoff-timestamp", "2026-04-23T00:00:00Z",
        "--bucket", "b-test", "--prefix", "vaults/c1/r1",
    ])
    assert rc == synth_cli.EXIT_TRANSPORT
    cap = capsys.readouterr()
    assert cap.out.strip() == ""  # envelope must NOT be printed on failure
    err = json.loads(cap.err.strip())
    assert err["error"] == "transport"


def test_ac7_global_canon_wiring(monkeypatch: pytest.MonkeyPatch,
                                 capsys: pytest.CaptureFixture[str]) -> None:
    from canon_systems import cli as top_cli

    called: dict[str, Any] = {}

    def fake_run(argv: list[str]) -> int:
        called["argv"] = list(argv)
        return 0

    monkeypatch.setattr(top_cli, "run_synth_cli", fake_run)
    rc = top_cli.main(["synth", "publish", "--help"])
    assert rc == 0
    assert called["argv"] == ["publish", "--help"]


def test_ac8_missing_file_exits_usage(tmp_path: Path, fake_s3: FakeS3,
                                     capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "does-not-exist.jsonl"
    rc = synth_cli.run([
        "publish",
        "--events-file", str(missing),
        "--plan-id", "p", "--company-id", "c", "--repository-id", "r",
        "--cutoff-timestamp", "2026-01-01T00:00:00Z",
        "--bucket", "b", "--prefix", "x",
    ])
    assert rc == synth_cli.EXIT_USAGE
    err = json.loads(capsys.readouterr().err.strip())
    assert err["error"] == "usage"
    assert "events-file" in err["detail"] or "not found" in err["detail"].lower()
