"""Tests for `canon vault sync` (E5-T6)."""

from __future__ import annotations

import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from canon_systems import cli as top_cli
from canon_systems import repo_enable, vault_sync
from canon_systems.synth_show_reader import SynthShowReader

_FORBIDDEN_METHODS = (
    "put_object",
    "put_object_acl",
    "put_object_tagging",
    "put_object_retention",
    "put_object_legal_hold",
    "put_bucket_policy",
    "put_bucket_acl",
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
_WRITE_RE = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in _FORBIDDEN_METHODS) + r")\s*\("
)


class _ListPaginator:
    def __init__(self, parent: "VaultFakeS3") -> None:
        self._parent = parent

    def paginate(self, **kwargs: Any):
        prefix = kwargs.get("Prefix") or ""
        keys = sorted(k for k in self._parent.objects if not prefix or k.startswith(prefix))
        yield (
            {"Contents": [{"Key": k, "Size": 0} for k in keys]}
            if keys
            else {"Contents": []}
        )


class VaultFakeS3:
    def __init__(self, *, fail_mode: str | None = None) -> None:
        self.objects: dict[str, dict[str, Any]] = {}
        self.fail_mode = fail_mode
        self._list_n = 0

    def get_paginator(self, name: str) -> _ListPaginator:  # noqa: ARG002
        if self.fail_mode == "endpoint_once":
            if self._list_n == 0:
                self._list_n += 1
                raise EndpointConnectionError(endpoint_url="https://s3.amazonaws.com")
        elif self.fail_mode == "endpoint":
            raise EndpointConnectionError(endpoint_url="https://s3.amazonaws.com")
        return _ListPaginator(self)

    def head_object(self, *, Bucket, Key):  # noqa: N803
        if self.fail_mode == "endpoint":
            raise EndpointConnectionError(endpoint_url="https://s3.amazonaws.com")
        if self.fail_mode == "denied_head":
            raise ClientError(
                {
                    "Error": {"Code": "AccessDenied", "Message": "d"},
                    "ResponseMetadata": {"HTTPStatusCode": 403},
                },
                "HeadObject",
            )
        if Key not in self.objects:
            raise ClientError(
                {
                    "Error": {"Code": "404", "Message": "not found"},
                    "ResponseMetadata": {"HTTPStatusCode": 404},
                },
                "HeadObject",
            )
        o = self.objects[Key]
        return {
            "ContentType": o.get("ContentType", "text/markdown"),
            "Metadata": dict(o.get("Metadata", {})),
        }

    def get_object(self, *, Bucket, Key):  # noqa: N803
        if self.fail_mode in ("endpoint", "denied_get"):
            if self.fail_mode == "endpoint":
                raise EndpointConnectionError(endpoint_url="https://s3.amazonaws.com")
            raise ClientError(
                {
                    "Error": {"Code": "AccessDenied", "Message": "d"},
                    "ResponseMetadata": {"HTTPStatusCode": 403},
                },
                "GetObject",
            )
        if Key not in self.objects:
            raise ClientError(
                {
                    "Error": {"Code": "NoSuchKey", "Message": "n"},
                    "ResponseMetadata": {"HTTPStatusCode": 404},
                },
                "GetObject",
            )
        o = self.objects[Key]
        raw = o["Body"]
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        return {"Body": io.BytesIO(bytes(raw))}


def _put(fake: VaultFakeS3, prefix: str, rel: str, body: str, *, content_hash: str) -> None:
    key = f"{prefix.rstrip('/')}/{rel}" if prefix else rel
    fake.objects[key] = {
        "Body": body,
        "ContentType": "text/markdown; charset=utf-8",
        "Metadata": {"content-hash": content_hash},
    }


def sh(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _fake_s3(monkeypatch: pytest.MonkeyPatch, fake: VaultFakeS3) -> None:
    monkeypatch.setattr(vault_sync, "_s3_client_factory", lambda a, p: fake)


def _patch_home(monkeypatch: pytest.MonkeyPatch, h: Path) -> None:
    p = h.resolve()
    monkeypatch.setattr(
        pathlib.Path,
        "home",
        classmethod(lambda cls, _root=p: _root),  # noqa: ARG002
    )


def test_ac1_help_exits_zero_and_lists_flags() -> None:
    assert vault_sync.run(["--help"]) == 0
    p = subprocess.run(
        [sys.executable, "-c", "from canon_systems import vault_sync; assert vault_sync.run(['--help'])==0"],
        env={**os.environ, "PYTHONPATH": "src" + os.pathsep + "backend/shared"},
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    out = p.stdout + p.stderr
    for needle in (
        "--once",
        "--interval-seconds",
        "--company-id",
        "--repository-id",
        "--plan-id",
        "--bucket",
        "--prefix",
        "--target-dir",
        "--aws-region",
        "--aws-profile",
        "--event-log",
        "--dry-run",
        "--install",
    ):
        assert needle in out, needle


def test_ac2_global_canon_wiring_for_vault_sync() -> None:
    assert top_cli.main(["vault", "sync", "--help"]) == 0


def test_ac3_once_mirrors_seeded_vault(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3()
        pfx = "vault/c1/r1"
        _put(fake, pfx, "a.md", "hello\n", content_hash=sh("hello\n"))
        _put(fake, pfx, "b/c.md", "nested\n", content_hash=sh("nested\n"))
        _fake_s3(monkeypatch, fake)
        r = vault_sync.run(
            [
                "--once",
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                pfx,
            ]
        )
        assert r == 0
        assert (vdir / "a.md").read_text() == "hello\n"
        assert (vdir / "b" / "c.md").read_text() == "nested\n"
    finally:
        os.chdir(old)


def test_ac4_loop_runs_multiple_ticks_then_exits(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3()
        pfx = "p"
        _put(fake, pfx, "a.md", "ok\n", content_hash=sh("ok\n"))
        _fake_s3(monkeypatch, fake)
        elog = tmp_path / "e.ndjson"
        os.environ["CANON_VAULT_SYNC_MAX_TICKS"] = "3"
        log_calls: list[float] = []
        monkeypatch.setattr(
            vault_sync, "_sleep", lambda s: log_calls.append(float(s))
        )
        r = vault_sync.run(
            [
                "--interval-seconds",
                "0.01",
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                pfx,
                "--event-log",
                str(elog),
            ]
        )
        del os.environ["CANON_VAULT_SYNC_MAX_TICKS"]
        assert r == 0
        lines = [x for x in elog.read_text().strip().splitlines() if x.strip()]
        assert len({json.loads(x)["event_id"] for x in lines}) == len(lines)
        assert len(lines) >= 2
    finally:
        os.chdir(old)


def test_ac5_reuses_synth_show_reader_shim() -> None:
    assert "from .synth_show_reader import" in Path(vault_sync.__file__).read_text(
        encoding="utf-8"
    )
    s = SynthShowReader(bucket="b", prefix="p", s3_client=object())


def _seed_13(pfx: str, fake: VaultFakeS3) -> None:
    for i in range(13):
        body = f"body{i:02d}\n"
        _put(fake, pfx, f"f{i:02d}.md", body, content_hash=sh(body))


def test_ac6_incremental_skip_on_unchanged_hash(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    pfx = "p"
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3()
        _seed_13(pfx, fake)
        for i in range(13):
            body = f"body{i:02d}\n"
            (vdir / f"f{i:02d}.md").write_text(body, encoding="utf-8")
        _fake_s3(monkeypatch, fake)
        elog = tmp_path / "e.ndjson"
        r = vault_sync.run(
            [
                "--once",
                "--event-log",
                str(elog),
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                pfx,
            ]
        )
        assert r == 0
        last = [json.loads(x) for x in elog.read_text().splitlines() if x.strip()][-1]
        pl = last["payload"]
        assert pl.get("pulled_count") == 0
        assert pl.get("skipped_count") == 13
        assert pl.get("pulled_bytes") == 0
    finally:
        os.chdir(old)


def test_ac7_hash_miss_triggers_download(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3()
        pfx = "p"
        body = "remote-body\n"
        _put(fake, pfx, "a.md", body, content_hash=sh(body))
        (vdir / "a.md").write_text("wrong", encoding="utf-8")
        _fake_s3(monkeypatch, fake)
        r = vault_sync.run(
            [
                "--once",
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                pfx,
            ]
        )
        assert r == 0
        assert (vdir / "a.md").read_text() == body
    finally:
        os.chdir(old)


def test_ac8_deletion_propagation(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    (vdir / "stale" / "x.md").parent.mkdir(parents=True)
    (vdir / "stale" / "x.md").write_text("x", encoding="utf-8")
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3()
        pfx = "p"
        _put(fake, pfx, "keep.md", "k", content_hash=sh("k"))
        _fake_s3(monkeypatch, fake)
        r = vault_sync.run(
            [
                "--once",
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                pfx,
            ]
        )
        assert r == 0
        assert not (vdir / "stale" / "x.md").exists()
        assert (vdir / "keep.md").read_text() == "k"
    finally:
        os.chdir(old)


def test_ac9_local_edits_silently_overwritten(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    body = "remote\n"
    (vdir / "a.md").write_text("local-edit", encoding="utf-8")
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3()
        _put(fake, "p", "a.md", body, content_hash=sh(body))
        _fake_s3(monkeypatch, fake)
        vault_sync.run(
            [
                "--once",
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                "p",
            ]
        )
        o = capsys.readouterr()
        assert "warn" not in (o.out + o.err).lower()
        assert (vdir / "a.md").read_text() == body
    finally:
        os.chdir(old)


def test_ac10_target_dir_auto_derives_from_git_root(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    (vdir / "a.md").write_text("a", encoding="utf-8")
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3()
        _put(fake, "p", "a.md", "a", content_hash=sh("a"))
        _fake_s3(monkeypatch, fake)
        r = vault_sync.run(
            [
                "--once",
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                "p",
            ]
        )
        assert r == 0
    finally:
        os.chdir(old)


def test_ac10_outside_git_repo_exits_usage(monkeypatch, tmp_path: Path) -> None:
    d = tmp_path / "n"
    d.mkdir()
    old = os.getcwd()
    try:
        os.chdir(d)
        r = vault_sync.run(
            [
                "--once",
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                "p",
            ]
        )
        assert r == vault_sync.VAULT_EXIT_USAGE
    finally:
        os.chdir(old)


def test_ac11_env_layering_fills_missing_flags(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    old = os.getcwd()
    keys = (
        "CANON_PLAN_ID",
        "CANON_COMPANY_ID",
        "CANON_REPOSITORY_ID",
        "CANON_VAULT_BUCKET",
        "CANON_VAULT_PREFIX",
    )
    for k in keys:
        os.environ.pop(k, None)
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3()
        _put(fake, "p", "a.md", "a", content_hash=sh("a"))
        _fake_s3(monkeypatch, fake)
        for k, v in (
            ("CANON_PLAN_ID", "P"),
            ("CANON_COMPANY_ID", "C"),
            ("CANON_REPOSITORY_ID", "R"),
            ("CANON_VAULT_BUCKET", "B"),
            ("CANON_VAULT_PREFIX", "p"),
        ):
            os.environ[k] = v
        r = vault_sync.run(
            [
                "--once",
                "--target-dir",
                str(vdir),
            ]
        )
        assert r == 0
    finally:
        for k in keys:
            os.environ.pop(k, None)
        os.chdir(old)


def test_ac11_missing_required_id_exits_usage(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    for k in (
        "CANON_PLAN_ID",
        "CANON_COMPANY_ID",
        "CANON_REPOSITORY_ID",
        "CANON_VAULT_BUCKET",
        "CANON_VAULT_PREFIX",
    ):
        os.environ.pop(k, None)
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        _fake_s3(monkeypatch, VaultFakeS3())
        r = vault_sync.run(
            [
                "--once",
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
            ]
        )
        assert r == vault_sync.VAULT_EXIT_USAGE
    finally:
        os.chdir(old)


def test_ac12_once_mode_transport_error_exits_5(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3(fail_mode="endpoint")
        _fake_s3(monkeypatch, fake)
        epath = tmp_path / "e.ndjson"
        r = vault_sync.run(
            [
                "--once",
                "--event-log",
                str(epath),
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                "p",
            ]
        )
        assert r == 5
        err = capsys.readouterr().err
        assert '"error": "transport"' in err
        ev = [json.loads(x) for x in epath.read_text().splitlines() if x.strip()][-1]
        assert ev["payload"]["result"] == "error"
    finally:
        os.chdir(old)


def test_ac13_loop_mode_tolerates_transport_errors_with_backoff(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3(fail_mode="endpoint_once")
        pfx = "p"
        _put(fake, pfx, "a.md", "a", content_hash=sh("a"))
        _fake_s3(monkeypatch, fake)
        sleeps: list[float] = []
        monkeypatch.setattr(vault_sync, "_sleep", lambda s: sleeps.append(float(s)))
        os.environ["CANON_VAULT_SYNC_MAX_TICKS"] = "2"
        r = vault_sync.run(
            [
                "--interval-seconds",
                "0.5",
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                pfx,
            ]
        )
        del os.environ["CANON_VAULT_SYNC_MAX_TICKS"]
        assert r == 0
        assert any(s >= 0.5 for s in sleeps)
    finally:
        os.chdir(old)


def test_ac14_vault_sync_event_payload_shape(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3()
        _put(fake, "p", "a.md", "a", content_hash=sh("a"))
        _fake_s3(monkeypatch, fake)
        elog = tmp_path / "e.ndjson"
        vault_sync.run(
            [
                "--once",
                "--event-log",
                str(elog),
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                "p",
            ]
        )
        o = json.loads(
            [x for x in elog.read_text().splitlines() if x.strip()][-1]
        )
        pl = o["payload"]
        for k in (
            "result",
            "pulled_bytes",
            "pulled_count",
            "deleted_count",
            "skipped_count",
        ):
            assert k in pl
    finally:
        os.chdir(old)


def test_ac14_dry_run_event_goes_to_stderr(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = VaultFakeS3()
        _put(fake, "p", "a.md", "a", content_hash=sh("a"))
        _fake_s3(monkeypatch, fake)
        vault_sync.run(
            [
                "--once",
                "--dry-run",
                "--target-dir",
                str(vdir),
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                "p",
            ]
        )
        err = capsys.readouterr().err
        assert "vault_sync" in err
    finally:
        os.chdir(old)


def test_ac15_launchd_plist_generation_matches_fixture() -> None:
    got = vault_sync._render_launchd_plist(  # noqa: SLF001
        ch="aa",
        rh="bb",
        canon_bin="/x/canon",
        interval_seconds=10,
        company_id="C",
        repository_id="R",
        plan_id="P",
        bucket="B",
        prefix="vault/c/r",
        target_dir=Path("/r/vault"),
        log_out="/o.log",
        log_err="/e.log",
    )
    assert "systems.canon.vault-sync.aa-bb" in got
    assert "RunAtLoad" in got
    assert "KeepAlive" in got


def test_ac15_launchd_install_is_idempotent(
    monkeypatch, tmp_path: Path
) -> None:
    h = (tmp_path / "home").resolve()
    h.mkdir()
    la = h / "Library" / "LaunchAgents"
    la.mkdir(parents=True)
    _patch_home(monkeypatch, h)
    pl = vault_sync._render_launchd_plist(  # noqa: SLF001
        ch="a",
        rh="b",
        canon_bin="/b",
        interval_seconds=10,
        company_id="C",
        repository_id="R",
        plan_id="P",
        bucket="B",
        prefix="p",
        target_dir=Path("/r/vault"),
        log_out="/o",
        log_err="/e",
    )
    for _ in range(2):
        vault_sync._install_launchd(  # noqa: SLF001
            plist_body=pl,
            ch="a",
            rh="b",
            company_id="C",
            repository_id="R",
            plan_id="P",
            event_log=None,
            dry_run=True,
        )
    p = (la / "systems.canon.vault-sync.a-b.plist").read_text()
    assert p == pl


def test_ac16_systemd_unit_generation_matches_fixture() -> None:
    u = vault_sync._render_systemd_unit(  # noqa: SLF001
        ch="aa",
        rh="bb",
        canon_bin="/x/canon",
        interval_seconds=10,
        company_id="C",
        repository_id="R",
        plan_id="P",
        bucket="B",
        prefix="vault/c/r",
        target_dir=Path("/r/vault"),
    )
    assert "ExecStart=" in u
    assert "Restart=always" in u
    assert "WantedBy=default.target" in u


def test_ac17_windows_schtasks_invocation_captured(
    monkeypatch, tmp_path: Path
) -> None:
    h = (tmp_path / "h").resolve()
    h.mkdir()
    _patch_home(monkeypatch, h)
    calls: list = []
    monkeypatch.setattr(
        vault_sync, "platform", type("P", (), {"system": staticmethod(lambda: "Windows")})
    )

    def _rp(*a, **k):
        calls.append((a, k))
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(vault_sync, "_run_subprocess", _rp)
    x = vault_sync._render_schtasks_xml(  # noqa: SLF001
        ch="a",
        rh="b",
        canon_bin="C:/canon",
        interval_seconds=10,
        company_id="C",
        repository_id="R",
        plan_id="P",
        bucket="B",
        prefix="p",
        target_dir=Path("C:/v"),
    )
    tml = (Path(vault_sync.__file__).parent / "templates" / "vault-sync" / "schtasks.xml.tmpl").read_text(
        encoding="utf-8"
    )
    tml = (
        tml.replace("{COMPANY_SHORTHASH}", "a")
        .replace("{REPO_SHORTHASH}", "b")
        .replace("{CANON_BIN}", "C:/canon")
        .replace("{INTERVAL_SECONDS}", "10")
        .replace("{COMPANY_ID}", "C")
        .replace("{REPOSITORY_ID}", "R")
        .replace("{PLAN_ID}", "P")
        .replace("{BUCKET}", "B")
        .replace("{PREFIX}", "p")
        .replace("{TARGET_DIR}", "C:/v")
    )
    assert x == tml, "rendered Windows Task XML should match the checked-in .tmpl"
    vault_sync._install_schtasks(  # noqa: SLF001
        xml_body=x,
        task_name="a-b",
        company_id="C",
        repository_id="R",
        plan_id="P",
        event_log=None,
        dry_run=True,
    )
    data = (h / ".canon" / "vault-schtasks-a-b.last.xml").read_text()
    assert "C:/canon" in data
    assert "vault sync" in data
    assert any("schtasks" in str(c[0]) for c in calls)


def test_ac18_install_dispatch_selects_by_platform_system(
    monkeypatch, tmp_path: Path
) -> None:
    h = (tmp_path / "H").resolve()
    h.mkdir()
    la = h / "Library" / "LaunchAgents"
    la.mkdir(parents=True)
    sdu = h / ".config" / "systemd" / "user"
    sdu.mkdir(parents=True)
    _patch_home(monkeypatch, h)
    monkeypatch.setattr(
        vault_sync, "platform", type("D", (), {"system": staticmethod(lambda: "Darwin")})
    )
    vault_sync.install_service(
        company_id="C",
        repository_id="R",
        plan_id="P",
        bucket="B",
        prefix="p",
        target_dir=Path("/a/vault"),
    )
    assert list(la.glob("*.plist"))
    monkeypatch.setattr(
        vault_sync, "platform", type("L", (), {"system": staticmethod(lambda: "Linux")})
    )
    vault_sync.install_service(
        company_id="C",
        repository_id="R",
        plan_id="P",
        bucket="B",
        prefix="p",
        target_dir=Path("/a/vault"),
    )
    assert list(sdu.glob("canon-vault-*.service"))


def test_ac19_gitignore_block_is_idempotent(tmp_path: Path) -> None:
    r = tmp_path / "r"
    r.mkdir()
    repo_enable._apply_vault_sync_gitignore_block(r)  # noqa: SLF001
    a = (r / ".gitignore").read_text(encoding="utf-8")
    repo_enable._apply_vault_sync_gitignore_block(r)
    b = (r / ".gitignore").read_text(encoding="utf-8")
    assert a == b
    assert "vault/" in a


def test_ac20_sync_source_has_no_s3_write_calls() -> None:
    src = Path(vault_sync.__file__).read_text(encoding="utf-8")
    assert _WRITE_RE.search(src) is None


def test_ac21_pre_turn_hook_install_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = tmp_path / "o"
    r.mkdir()
    p1 = r / ".cursor" / "hooks" / "vault-sync-preflight.sh"
    repo_enable.enable_repo(r)
    b1 = p1.read_text(encoding="utf-8")
    m1 = p1.stat().st_mode
    repo_enable.enable_repo(r)
    b2 = p1.read_text(encoding="utf-8")
    assert b1 == b2
    assert b1.startswith("#!/")
    assert (m1 & 0o111) != 0


# ---------------------------------------------------------------------------
# QA-gate augmentations (E5-T6): strengthen idempotence + backoff math checks.
# ---------------------------------------------------------------------------


class _CountingFakeS3(VaultFakeS3):
    """Fake S3 that fails list_objects N times then succeeds."""

    def __init__(self, *, fails: int, objects: dict[str, dict[str, Any]]) -> None:
        super().__init__()
        self._fails_remaining = fails
        self.objects = objects

    def get_paginator(self, name: str) -> _ListPaginator:  # noqa: ARG002
        if self._fails_remaining > 0:
            self._fails_remaining -= 1
            raise EndpointConnectionError(endpoint_url="https://s3.amazonaws.com")
        return _ListPaginator(self)


def test_ac13_backoff_math_two_consecutive_failures_then_recovery(
    monkeypatch, tmp_path: Path
) -> None:
    """Exercise min(base * 2**(k-1), 60) across 2 consecutive fails + success."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "vault").mkdir()
    vdir = tmp_path / "vault"
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        fake = _CountingFakeS3(
            fails=2,
            objects={
                "p/a.md": {
                    "Body": "ok",
                    "ContentType": "text/markdown",
                    "Metadata": {"content-hash": sh("ok")},
                }
            },
        )
        _fake_s3(monkeypatch, fake)
        sleeps: list[float] = []
        monkeypatch.setattr(vault_sync, "_sleep", lambda s: sleeps.append(float(s)))
        os.environ["CANON_VAULT_SYNC_MAX_TICKS"] = "3"
        r = vault_sync.run(
            [
                "--interval-seconds",
                "0.5",
                "--target-dir",
                str(vdir),
                "--company-id",
                "c",
                "--repository-id",
                "r",
                "--plan-id",
                "P",
                "--bucket",
                "b",
                "--prefix",
                "p",
            ]
        )
        del os.environ["CANON_VAULT_SYNC_MAX_TICKS"]
        assert r == 0
        # tick1 fail -> sleep 1.0 (min(1*2**0,60))
        # tick2 fail -> sleep 2.0 (min(1*2**1,60))
        # tick3 success -> MAX_TICKS reached before sleep; no third sleep observed.
        assert sleeps == [1.0, 2.0], sleeps
        # File mirrored on recovery.
        assert (vdir / "a.md").read_text() == "ok"
    finally:
        os.chdir(old)


def test_ac15_launchd_second_install_is_byte_identical_noop(
    monkeypatch, tmp_path: Path
) -> None:
    h = (tmp_path / "home").resolve()
    h.mkdir()
    la = h / "Library" / "LaunchAgents"
    la.mkdir(parents=True)
    _patch_home(monkeypatch, h)
    pl = vault_sync._render_launchd_plist(  # noqa: SLF001
        ch="a",
        rh="b",
        canon_bin="/b",
        interval_seconds=10,
        company_id="C",
        repository_id="R",
        plan_id="P",
        bucket="B",
        prefix="p",
        target_dir=Path("/r/vault"),
        log_out="/o",
        log_err="/e",
    )
    vault_sync._install_launchd(  # noqa: SLF001
        plist_body=pl,
        ch="a",
        rh="b",
        company_id="C",
        repository_id="R",
        plan_id="P",
        event_log=None,
        dry_run=True,
    )
    dest = la / "systems.canon.vault-sync.a-b.plist"
    st1 = dest.stat()
    # Age the file so mtime comparison is meaningful on coarse-resolution FS.
    os.utime(dest, (st1.st_atime - 5, st1.st_mtime - 5))
    st_aged = dest.stat()
    vault_sync._install_launchd(  # noqa: SLF001
        plist_body=pl,
        ch="a",
        rh="b",
        company_id="C",
        repository_id="R",
        plan_id="P",
        event_log=None,
        dry_run=True,
    )
    st2 = dest.stat()
    assert dest.read_text(encoding="utf-8") == pl
    # No write on second call: mtime must equal the aged mtime.
    assert st2.st_mtime == st_aged.st_mtime


def test_ac16_systemd_second_install_is_byte_identical_noop(
    monkeypatch, tmp_path: Path
) -> None:
    h = (tmp_path / "H").resolve()
    h.mkdir()
    sdu = h / ".config" / "systemd" / "user"
    sdu.mkdir(parents=True)
    _patch_home(monkeypatch, h)
    unit = vault_sync._render_systemd_unit(  # noqa: SLF001
        ch="a",
        rh="b",
        canon_bin="/b",
        interval_seconds=10,
        company_id="C",
        repository_id="R",
        plan_id="P",
        bucket="B",
        prefix="p",
        target_dir=Path("/r/vault"),
    )
    name = "canon-vault-sync-a-b.service"
    vault_sync._install_systemd(  # noqa: SLF001
        unit_body=unit,
        name=name,
        company_id="C",
        repository_id="R",
        plan_id="P",
        event_log=None,
        dry_run=True,
    )
    dest = sdu / name
    assert dest.read_text(encoding="utf-8") == unit
    os.utime(dest, (dest.stat().st_atime - 5, dest.stat().st_mtime - 5))
    aged = dest.stat().st_mtime
    vault_sync._install_systemd(  # noqa: SLF001
        unit_body=unit,
        name=name,
        company_id="C",
        repository_id="R",
        plan_id="P",
        event_log=None,
        dry_run=True,
    )
    assert dest.stat().st_mtime == aged


def test_ac17_schtasks_second_install_skips_subprocess(
    monkeypatch, tmp_path: Path
) -> None:
    h = (tmp_path / "Hs").resolve()
    h.mkdir()
    _patch_home(monkeypatch, h)
    calls: list = []
    monkeypatch.setattr(
        vault_sync,
        "_run_subprocess",
        lambda *a, **k: calls.append((a, k)) or MagicMock(returncode=0, stdout="", stderr=""),
    )
    xml = vault_sync._render_schtasks_xml(  # noqa: SLF001
        ch="a",
        rh="b",
        canon_bin="C:/canon",
        interval_seconds=10,
        company_id="C",
        repository_id="R",
        plan_id="P",
        bucket="B",
        prefix="p",
        target_dir=Path("C:/v"),
    )
    for _ in range(2):
        vault_sync._install_schtasks(  # noqa: SLF001
            xml_body=xml,
            task_name="a-b",
            company_id="C",
            repository_id="R",
            plan_id="P",
            event_log=None,
            dry_run=True,
        )
    # schtasks.exe should fire exactly once; second call must short-circuit.
    assert len(calls) == 1, calls


def test_ac21_hooks_json_merge_preserves_memory_preflight(
    tmp_path: Path,
) -> None:
    """Installing vault-sync hooks must not evict the existing memory-preflight entry."""
    r = tmp_path / "o2"
    r.mkdir()
    repo_enable.enable_repo(r)
    hooks_json = r / ".cursor" / "hooks.json"
    parsed = json.loads(hooks_json.read_text(encoding="utf-8"))
    before = parsed["hooks"]["beforeSubmitPrompt"]
    cmds = {entry["command"] for entry in before}
    assert "bash .cursor/hooks/memory-preflight.sh" in cmds
    assert "bash .cursor/hooks/vault-sync-preflight.sh" in cmds
    # Re-running enable_repo must not duplicate or drop entries.
    repo_enable.enable_repo(r)
    parsed2 = json.loads(hooks_json.read_text(encoding="utf-8"))
    after = parsed2["hooks"]["beforeSubmitPrompt"]
    cmds2 = {entry["command"] for entry in after}
    assert cmds == cmds2
    # Count of each specific command is exactly 1.
    assert sum(1 for e in after if e["command"].endswith("memory-preflight.sh")) == 1
    assert sum(1 for e in after if e["command"].endswith("vault-sync-preflight.sh")) == 1
