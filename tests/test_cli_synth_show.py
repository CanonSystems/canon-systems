"""Tests for `canon synth show` (E5-T5)."""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest
from botocore.exceptions import ClientError

from canon_systems import cli as top_cli, stall_watchdog, synth_cli, synth_show_reader

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


class _ListPaginator:
    def __init__(self, parent: "ShowFakeS3") -> None:
        self._parent = parent

    def paginate(self, **kwargs: Any):
        prefix = kwargs.get("Prefix") or ""
        keys = sorted(k for k in self._parent.objects if not prefix or k.startswith(prefix))
        yield (
            {"Contents": [{"Key": k, "Size": 0} for k in keys]}
            if keys
            else {"Contents": []}
        )


class ShowFakeS3:
    """Dict-backed S3 read/write like tests/test_cli_synth_publish FakeS3, plus get_object."""

    def __init__(self, *, fail_mode: str | None = None) -> None:
        self.objects: dict[str, dict[str, Any]] = {}
        self.fail_mode = fail_mode

    def get_paginator(self, name: str) -> _ListPaginator:
        _ = name
        return _ListPaginator(self)

    def head_object(self, *, Bucket, Key):  # noqa: N803
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
                {"Error": {"Code": "404", "Message": "not found"}, "ResponseMetadata": {"HTTPStatusCode": 404}},
                "HeadObject",
            )
        o = self.objects[Key]
        return {"ContentType": o.get("ContentType", "text/markdown"), "Metadata": dict(o.get("Metadata", {}))}

    def get_object(self, *, Bucket, Key):  # noqa: N803
        if self.fail_mode in ("denied_get", "access_denied"):
            raise ClientError(
                {
                    "Error": {"Code": "AccessDenied", "Message": "d"},
                    "ResponseMetadata": {"HTTPStatusCode": 403},
                },
                "GetObject",
            )
        if self.fail_mode == "denied_list":
            raise ClientError(
                {
                    "Error": {"Code": "AccessDenied", "Message": "d"},
                    "ResponseMetadata": {"HTTPStatusCode": 403},
                },
                "GetObject",
            )
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "n"}, "ResponseMetadata": {"HTTPStatusCode": 404}},
                "GetObject",
            )
        o = self.objects[Key]
        raw = o["Body"]
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        return {"Body": io.BytesIO(bytes(raw))}


def _put(fake: ShowFakeS3, prefix: str, rel: str, body: str, **meta: str) -> None:
    key = f"{prefix.rstrip('/')}/{rel}" if prefix else rel
    fake.objects[key] = {
        "Body": body,
        "ContentType": "text/markdown; charset=utf-8",
        "Metadata": {"content-hash": meta.get("content_hash", "deadbeef" * 8)},
    }


def _seed_sample_vault(fake: ShowFakeS3, *, prefix: str, plan_id: str = "P", order: str = "T2_first") -> None:
    _ = order
    _put(fake, prefix, "README.md", "# r\n", content_hash="a" * 64)
    _put(
        fake,
        prefix,
        f"plans/{plan_id}/index.md",
        "---\nschema_version: 1\ntimestamp: 2026-01-01T00:00:00Z\nevent_ids: [\"e-plan\"]\n---\n# Plan {plan_id}\n".format(
            plan_id=plan_id
        ),
        content_hash="b" * 64,
    )
    for tid, ts in (("T2", "2026-02-01T00:00:00Z"), ("T1", "2026-01-15T00:00:00Z")):
        _put(
            fake,
            prefix,
            f"plans/{plan_id}/tasks/{tid}/index.md",
            f"---\nschema_version: 1\ntimestamp: {ts}\nevent_id: \"e-{tid}\"\n---\n# {tid} idx\n",
            content_hash="c" * 64,
        )
        for ph in ("scoper", "cursor-pilot", "implementer", "qa-gate", "release-orchestrator"):
            _put(
                fake,
                prefix,
                f"plans/{plan_id}/tasks/{tid}/{ph}.md",
                f"---\nschema_version: 1\ntimestamp: {ts}\n---\n# {ph}\n",
                content_hash="d" * 64,
            )


@pytest.fixture
def show_fake_s3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ShowFakeS3:
    fake = ShowFakeS3()
    monkeypatch.setattr(synth_cli, "_s3_client_factory", lambda r, p: fake)
    monkeypatch.setattr(stall_watchdog, "_DEFAULT_EVENT_LOG", str(tmp_path / "default-events.ndjson"))
    return fake


# --- 20 scoper test nodes ----------------------------------------------------------------)


def test_ac1_help_exits_zero_and_lists_flags(capsys: pytest.CaptureFixture[str]) -> None:
    rc = synth_cli.run(["show", "--help"])
    assert rc == synth_cli.EXIT_OK
    out = capsys.readouterr().out
    for f in (
        "--plan-id",
        "--task-id",
        "--company-id",
        "--repository-id",
        "--cutoff-ts",
        "--format",
        "--bucket",
        "--prefix",
        "--aws-region",
        "--aws-profile",
        "--event-log",
        "--dry-run",
    ):
        assert f in out


def test_ac2_happy_path_streams_plan_and_tasks(capsys: pytest.CaptureFixture[str], show_fake_s3: ShowFakeS3) -> None:
    pfx = "vault/c1/r1"
    _seed_sample_vault(show_fake_s3, prefix=pfx, plan_id="P")
    rc = synth_cli.run(
        [
            "show",
            "--plan-id",
            "P",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            pfx,
            "--format",
            "markdown",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "# Plan P" in out
    t1i = out.index("# T1 idx")
    t2i = out.index("# T2 idx")
    # canonical order: plan, then T1, then T2
    first_plan = out.index("# Plan P")
    assert first_plan < t1i < t2i


def test_ac3_task_scoping_narrows_to_one_task(capsys: pytest.CaptureFixture[str], show_fake_s3: ShowFakeS3) -> None:
    pfx = "vault/c1/r1"
    _seed_sample_vault(show_fake_s3, prefix=pfx, plan_id="P")
    rc = synth_cli.run(
        [
            "show",
            "--task-id",
            "T1",
            "--plan-id",
            "P",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            pfx,
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "T1" in out and "T1 idx" in out
    assert "T2 idx" not in out


def test_ac4_streaming_writes_incrementally_per_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = ShowFakeS3()
    monkeypatch.setattr(synth_cli, "_s3_client_factory", lambda r, p: fake)
    monkeypatch.setattr(stall_watchdog, "_DEFAULT_EVENT_LOG", str(tmp_path / "default-events.ndjson"))
    pfx = "vault/c1/r1"
    _seed_sample_vault(fake, prefix=pfx, plan_id="P")
    sizes: list[int] = []

    class _Out:
        def __init__(self) -> None:
            self._orig = sys.stdout

        def write(self, s: str) -> int:
            sizes.append(len(s))
            return self._orig.write(s)

        def flush(self) -> None:
            self._orig.flush()

    fake_out = _Out()
    monkeypatch.setattr(sys, "stdout", fake_out)
    rc = synth_cli.run(
        [
            "show",
            "--plan-id",
            "P",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            pfx,
        ]
    )
    assert rc == 0
    assert all(sz > 0 for sz in sizes)
    # _seed_sample_vault: plan index + T1(6) + T2(6) task pages
    assert len(sizes) >= 13


def test_ac5_json_mode_deterministic_shape(
    show_fake_s3: ShowFakeS3, capsys: pytest.CaptureFixture[str]
) -> None:
    pfx = "vault/c1/r1"
    _put(show_fake_s3, pfx, "plans/P/index.md", "---\n---\n# p\n", content_hash="0" * 64)
    rc = synth_cli.run(
        [
            "show",
            "--format",
            "json",
            "--plan-id",
            "P",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            pfx,
        ]
    )
    assert rc == 0
    obj = json.loads(capsys.readouterr().out)
    for k in ("schema_version", "plan_id", "cutoff_ts", "bucket", "prefix", "pages", "retrieval_breakdown", "page_count", "byte_count", "task_id"):
        assert k in obj
    assert obj["retrieval_breakdown"]["sources"]["canonical"]["tokens_out"] == obj["byte_count"]


def test_ac5_json_mode_back_to_back_byte_identical(show_fake_s3: ShowFakeS3, capsys: pytest.CaptureFixture[str]) -> None:
    pfx = "vault/c1/r1"
    _seed_sample_vault(show_fake_s3, prefix=pfx, plan_id="P")
    args = [
        "show",
        "--format",
        "json",
        "--plan-id",
        "P",
        "--company-id",
        "c1",
        "--repository-id",
        "r1",
        "--bucket",
        "b1",
        "--prefix",
        pfx,
    ]
    r1 = synth_cli.run(args)
    b1 = capsys.readouterr().out
    r2 = synth_cli.run(args)
    b2 = capsys.readouterr().out
    assert r1 == r2 == 0
    assert b1 == b2


def test_ac6_missing_plan_id_exits_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stall_watchdog, "_DEFAULT_EVENT_LOG", str(tmp_path / "default-events.ndjson"))
    rc = synth_cli.run(
        [
            "show",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            "p",
        ]
    )
    assert rc == synth_cli.SHOW_EXIT_USAGE
    err = json.loads(capsys.readouterr().err.strip())
    assert err["error"] == "usage" and "plan_id" in err["detail"]


def test_ac6_env_layering_fills_missing_flags(
    show_fake_s3: ShowFakeS3, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    pfx = "vault/c1/r1"
    _put(show_fake_s3, pfx, "plans/P/index.md", "# x\n", content_hash="0" * 64)
    env = {
        "CANON_PLAN_ID": "P",
        "CANON_COMPANY_ID": "c1",
        "CANON_REPOSITORY_ID": "r1",
        "CANON_VAULT_BUCKET": "b1",
        "CANON_VAULT_PREFIX": pfx,
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert synth_cli.run(["show", "--format", "markdown"]) == 0
    out = capsys.readouterr().out
    assert len(out) > 0 and "# x" in out


def test_ac6_flag_overrides_env(
    show_fake_s3: ShowFakeS3, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    pfx2 = "vault/override"
    for pid in ("P", "Q"):
        _put(show_fake_s3, pfx2, f"plans/{pid}/index.md", f"---\n---\n# {pid}\n", content_hash="0" * 64)
    monkeypatch.setenv("CANON_PLAN_ID", "P")
    rc = synth_cli.run(
        [
            "show",
            "--plan-id",
            "Q",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            pfx2,
        ]
    )
    assert rc == 0
    assert "Q" in capsys.readouterr().out and "P" not in capsys.readouterr().out


def test_ac7_missing_plan_returns_exit_3_not_found(capsys: pytest.CaptureFixture[str], show_fake_s3: ShowFakeS3) -> None:
    _put(show_fake_s3, "p", "README.md", "x", content_hash="0" * 64)
    rc = synth_cli.run(
        [
            "show",
            "--plan-id",
            "NOMATCH",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            "p",
        ]
    )
    assert rc == synth_cli.SHOW_EXIT_NOT_FOUND
    cap = capsys.readouterr()
    err = json.loads(cap.err.strip())
    assert err["error"] == "not_found" and "NOMATCH" in err["detail"]
    assert cap.out == ""


def test_ac8_access_denied_returns_exit_4_and_emits_denied_event(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = ShowFakeS3(fail_mode="denied_get")
    monkeypatch.setattr(synth_cli, "_s3_client_factory", lambda r, p: fake)
    log = tmp_path / "ev.ndjson"
    rc = synth_cli.run(
        [
            "show",
            "--plan-id",
            "P",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            "vault/x",
            "--event-log",
            str(log),
        ]
    )
    assert rc == synth_cli.SHOW_EXIT_DENIED
    cap = capsys.readouterr()
    err = json.loads(cap.err.strip().splitlines()[-1])
    assert err["error"] == "denied" and "get_object" in err["detail"]
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert any(
        json.loads(x).get("event_type") == "synth_show" and json.loads(x).get("payload", {}).get("result") == "denied"
        for x in lines
    )


def test_ac9_show_source_has_no_s3_write_calls() -> None:
    import canon_systems.synth_cli as m

    src = Path(m.__file__).read_text(encoding="utf-8")
    a = src.index('# <READ-ONLY-REGION-BEGIN id="synth-show"')
    b = src.index('# <READ-ONLY-REGION-END id="synth-show">')
    region = src[a:b]
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(mn) for mn in _FORBIDDEN_METHODS) + r")\s*\("
    )
    assert pattern.search(region) is None, "forbidden S3 write call in synth-show region"


def test_ac9_source_scan_regex_detects_sample_writes() -> None:
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(m) for m in _FORBIDDEN_METHODS) + r")\s*\("
    )
    for name in _FORBIDDEN_METHODS:
        assert pattern.search(f'self._s3.{name}(Bucket="b", Key="k")') is not None


def test_ac10_synth_show_event_written_to_ndjson_on_success(
    tmp_path: Path, show_fake_s3: ShowFakeS3, capsys: pytest.CaptureFixture[str]
) -> None:
    pfx = "vault/c1/r1"
    log = tmp_path / "e.ndjson"
    _put(show_fake_s3, pfx, "plans/P/index.md", "---\n---\n# p\n", content_hash="0" * 64)
    rc = synth_cli.run(
        [
            "show",
            "--plan-id",
            "P",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            pfx,
            "--event-log",
            str(log),
        ]
    )
    assert rc == 0
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    show_lines = [json.loads(s) for s in lines if "synth_show" in s]
    assert any(x.get("event_type") == "synth_show" for x in show_lines)


def test_ac10_synth_show_event_payload_shape(
    tmp_path: Path, show_fake_s3: ShowFakeS3
) -> None:
    pfx = "v/p"
    _put(show_fake_s3, pfx, "plans/P/index.md", "body\n", content_hash="0" * 64)
    log = tmp_path / "e.ndjson"
    assert (
        0
        == synth_cli.run(
            [
                "show",
                "--plan-id",
                "P",
                "--format",
                "json",
                "--company-id",
                "a",
                "--repository-id",
                "b",
                "--bucket",
                "b1",
                "--prefix",
                pfx,
                "--event-log",
                str(log),
            ]
        )
    )
    for ln in log.read_text(encoding="utf-8").splitlines():
        o = json.loads(ln)
        if o.get("event_type") == "synth_show":
            p = o.get("payload", {})
            for k in ("plan_id", "task_id", "cutoff_ts", "bucket", "prefix", "page_count", "byte_count", "result", "format"):
                assert k in p
            break
    else:
        raise AssertionError("no synth_show in log")


def test_ac11_retrieval_breakdown_emitted_with_canonical_tokens_out(
    tmp_path: Path, show_fake_s3: ShowFakeS3
) -> None:
    pfx = "v/p2"
    _put(show_fake_s3, pfx, "plans/P/index.md", "markdown-content\n", content_hash="0" * 64)
    log = tmp_path / "e.ndjson"
    synth_cli.run(
        [
            "show",
            "--plan-id",
            "P",
            "--company-id",
            "a",
            "--repository-id",
            "b",
            "--bucket",
            "b1",
            "--prefix",
            pfx,
            "--event-log",
            str(log),
        ]
    )
    br = None
    for ln in log.read_text(encoding="utf-8").splitlines():
        o = json.loads(ln)
        if o.get("event_type") == "retrieval_breakdown":
            br = o
            break
    assert br is not None
    assert br["payload"]["sources"]["canonical"]["tokens_out"] == br["payload"]["totals"]["tokens_out"]


def test_ac11_retrieval_breakdown_emitted_before_synth_show_in_log(
    tmp_path: Path, show_fake_s3: ShowFakeS3
) -> None:
    pfx = "v/order"
    _put(show_fake_s3, pfx, "plans/P/index.md", "body\n", content_hash="0" * 64)
    log = tmp_path / "e.ndjson"
    assert (
        0
        == synth_cli.run(
            [
                "show",
                "--plan-id",
                "P",
                "--company-id",
                "c1",
                "--repository-id",
                "r1",
                "--bucket",
                "b1",
                "--prefix",
                pfx,
                "--event-log",
                str(log),
            ]
        )
    )
    lines = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    idx_breakdown = next(
        (i for i, e in enumerate(lines) if e.get("event_type") == "retrieval_breakdown"),
        None,
    )
    idx_show = next(
        (i for i, e in enumerate(lines) if e.get("event_type") == "synth_show"),
        None,
    )
    assert idx_breakdown is not None and idx_show is not None
    assert idx_breakdown < idx_show, "retrieval_breakdown must appear before synth_show in the NDJSON log"


def test_ac12_stream_order_is_canonical_regardless_of_insertion_order(
    capsys: pytest.CaptureFixture[str], show_fake_s3: ShowFakeS3
) -> None:
    pfx = "vault/sort"
    _seed_sample_vault(show_fake_s3, prefix=pfx, plan_id="P", order="T2_first")
    tids: list[str] = []
    for k in show_fake_s3.objects:
        if "/tasks/" in k and k.endswith("index.md"):
            parts = k.split("/")
            tids.append(parts[parts.index("tasks") + 1])
    assert "T1" in tids and "T2" in tids
    synth_cli.run(
        [
            "show",
            "--plan-id",
            "P",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            pfx,
        ]
    )
    t = capsys.readouterr().out
    assert t.find("T1") < t.find("T2") or t.index("T1 idx") < t.index("T2 idx")


def test_ac12_cutoff_ts_filters_pages_by_frontmatter_timestamp(
    capsys: pytest.CaptureFixture[str], show_fake_s3: ShowFakeS3
) -> None:
    pfx = "vault/cu"
    _put(
        show_fake_s3,
        pfx,
        "plans/P/index.md",
        "---\ntimestamp: 2026-12-01T00:00:00Z\n---\n# big\n",
        content_hash="0" * 64,
    )
    _put(
        show_fake_s3,
        pfx,
        "plans/P/tasks/T1/index.md",
        "---\ntimestamp: 2026-01-01T00:00:00Z\n---\n# small\n",
        content_hash="0" * 64,
    )
    rc = synth_cli.run(
        [
            "show",
            "--plan-id",
            "P",
            "--cutoff-ts",
            "2026-06-01T00:00:00Z",
            "--company-id",
            "c1",
            "--repository-id",
            "r1",
            "--bucket",
            "b1",
            "--prefix",
            pfx,
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "small" in out and "big" not in out


def test_ac13_global_canon_wiring_for_show_verb(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, Any] = {}

    def fake_run(a: list[str]) -> int:
        called["argv"] = list(a)
        return 0

    monkeypatch.setattr(top_cli, "run_synth_cli", fake_run)
    assert top_cli.main(["synth", "show", "--help"]) == 0
    assert called["argv"] == ["show", "--help"]


def test_ac14_reader_shim_source_has_no_s3_write_calls() -> None:
    path = Path(synth_show_reader.__file__)
    src = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(m) for m in _FORBIDDEN_METHODS) + r")\s*\("
    )
    assert pattern.search(src) is None, "reader must not call S3 write methods"
