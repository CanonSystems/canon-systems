<!-- CURSOR_PILOT_PROMPT: E5-T3 canon synth publish CLI (internal driver) -->

# CURSOR_PILOT_PROMPT — E5-T3: `canon synth publish` CLI

## ROLE

You are the implementer for Canon Memory Platform v1, Wave 5, Task E5-T3. You will wire a new `canon synth` subcommand with a `publish` action that drives the E5-T2 `SynthesisPublisher` deterministically from a canonical-event JSONL file. This is CLI-wiring only — no changes to `backend/synthesis/synthesis/*.py` are allowed.

## TASK

Deliver:

1. `src/canon_systems/synth_cli.py` — new module with `run(argv) -> int` entrypoint.
2. `src/canon_systems/cli.py` — 3 additive edits (import, subparser, dispatch).
3. `tests/test_cli_synth_publish.py` — new test file, ≥8 tests covering ACs 1–8.
4. Living-spec additive edits: `CHANGELOG.md`, `README.md` (command-table append), `docs/SYSTEM-WORKFLOW.md` §3 bullet.

Target suite: **382 → 390 passed** (+8). No regressions.

## CONTEXT

Read the scoper packet in full: `.cursor/handoffs/canon-memory-v1/E5-T3/scoper.md`.

Key invariants:

- `SynthesisPublisher.publish(bundle) -> PublishResult(written, skipped, keys_written)` is LOCKED from E5-T2.
- `generate_vault(events, *, company_id, repository_id, cutoff_timestamp) -> VaultBundle` is LOCKED.
- `InMemoryEventSource([events]).iter_events(plan_id, task_id, cutoff_timestamp)` filters scope + cutoff. We reuse it.
- `CanonicalEvent` has 15 fields; `to_dict()` produces the JSONL shape we parse.
- Prefer stdlib where possible; `boto3` is already available via `backend/synthesis/pyproject.toml` and is installed in the dev environment. Use `from botocore.exceptions import ClientError` for error mapping.

## REPOSITORY

- Root: `/Users/edwardwalker/localwork/canon-systems`
- Branch: `wave/5/canon-memory-v1` (tip `f8a1715`)
- Test runner: `pytest -q`
- Focused test: `pytest tests/test_cli_synth_publish.py -q`

## REASONING

- The publisher already handles content-hash diff-only writes and `.obsidian/*` write-once. The CLI is a thin wrapper that (a) parses argv, (b) loads events from JSONL, (c) constructs `InMemoryEventSource` → `generate_vault(...)` → `SynthesisPublisher.publish(...)`, (d) emits a JSON envelope.
- Transport errors (ClientError other than 404/NoSuchKey on HEAD paths) bubble out of `SynthesisPublisher.publish`. We catch at the CLI boundary, emit `{"error":"transport", "detail":"..."}` on stderr, return exit 2.
- Tests use a dict-backed fake S3 client (local to `tests/` to avoid `src/` ↔ `backend/` cross-imports). Monkeypatch `canon_systems.synth_cli._s3_client_factory` to return the fake.
- The "keys_written" ordering MUST match what `SynthesisPublisher.publish` emits (already alphabetical by construction). Do NOT re-sort in the CLI.

## OUTPUT FORMAT

### 1. NEW FILE: `src/canon_systems/synth_cli.py`

```python
"""canon synth publish: idempotent diff-only driver for SynthesisPublisher.

Reads canonical events from a JSONL file, renders a deterministic VaultBundle
via backend/synthesis generate_vault, and publishes to S3 with content-hash
diff-only writes. Safe to invoke repeatedly.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_TRANSPORT = 2
EXIT_USAGE = 4

_REQUIRED_EVENT_FIELDS = (
    "schema_version",
    "event_id",
    "parent_event_id",
    "event_type",
    "company_id",
    "repository_id",
    "plan_id",
    "task_id",
    "handoff_id",
    "agent_name",
    "agent_run_id",
    "actor_id",
    "model",
    "timestamp",
    "state_version",
    "payload",
)


def _s3_client_factory(aws_region: str, aws_profile: str) -> Any:
    """Return a boto3 S3 client. Monkeypatched in tests to return a dict-fake."""
    import boto3  # lazy import to keep --help cheap and avoid hard dep at import-time

    session = boto3.Session(
        profile_name=aws_profile or None,
        region_name=aws_region or None,
    )
    return session.client("s3")


def _load_events(path: Path) -> list[Any]:
    from canon_backend_shared.events import CanonicalEvent

    raw = path.read_text(encoding="utf-8")
    out: list[Any] = []
    for ln_no, ln in enumerate(raw.splitlines(), start=1):
        s = ln.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {ln_no}: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"line {ln_no}: expected JSON object")
        for k in _REQUIRED_EVENT_FIELDS:
            if k not in obj:
                raise ValueError(f"line {ln_no}: missing field '{k}'")
        if obj["schema_version"] != 1:
            raise ValueError(f"line {ln_no}: schema_version must be 1")
        ev = CanonicalEvent(
            schema_version=int(obj["schema_version"]),
            event_id=str(obj["event_id"]),
            parent_event_id=str(obj["parent_event_id"]),
            event_type=str(obj["event_type"]),
            company_id=str(obj["company_id"]),
            repository_id=str(obj["repository_id"]),
            plan_id=str(obj["plan_id"]),
            task_id=str(obj["task_id"]),
            handoff_id=str(obj["handoff_id"]),
            agent_name=str(obj["agent_name"]),
            agent_run_id=str(obj["agent_run_id"]),
            actor_id=str(obj["actor_id"]),
            model=str(obj["model"]),
            timestamp=str(obj["timestamp"]),
            state_version=int(obj["state_version"]),
            payload=dict(obj["payload"]),
        )
        out.append(ev)
    return out


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon synth",
        description="Synthesis vault publishing driver (internal).",
    )
    sub = p.add_subparsers(dest="subcommand", required=True)

    pub = sub.add_parser("publish", help="Publish vault bundle to S3 (idempotent, diff-only).")
    pub.add_argument("--events-file", required=True)
    pub.add_argument("--plan-id", required=True)
    pub.add_argument("--company-id", required=True)
    pub.add_argument("--repository-id", required=True)
    pub.add_argument("--cutoff-timestamp", required=True, help="ISO-8601 Z; only events strictly after are included.")
    pub.add_argument("--bucket", required=True)
    pub.add_argument("--prefix", required=True, help="S3 key prefix (e.g. 'vaults/c1/r1').")
    pub.add_argument("--task-id", default=None)
    pub.add_argument("--dry-run", action="store_true")
    pub.add_argument("--aws-region", default="")
    pub.add_argument("--aws-profile", default="")
    return p


def _print_envelope(envelope: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(envelope, sort_keys=True) + "\n")
    sys.stdout.flush()


def _print_error(payload: dict[str, Any]) -> None:
    sys.stderr.write(json.dumps(payload, sort_keys=True) + "\n")
    sys.stderr.flush()


def _publish(args: argparse.Namespace) -> int:
    from synthesis.generator import generate_vault
    from synthesis.publisher import SynthesisPublisher
    from synthesis.sources import InMemoryEventSource

    events_path = Path(args.events_file)
    try:
        events = _load_events(events_path)
    except FileNotFoundError:
        _print_error({"error": "usage", "detail": f"events-file not found: {events_path}"})
        return EXIT_USAGE
    except ValueError as exc:
        _print_error({"error": "usage", "detail": str(exc)})
        return EXIT_USAGE
    except OSError as exc:
        _print_error({"error": "usage", "detail": f"io: {exc}"})
        return EXIT_USAGE

    src = InMemoryEventSource(events)
    filtered = list(
        src.iter_events(
            plan_id=args.plan_id,
            task_id=args.task_id,
            cutoff_timestamp=args.cutoff_timestamp,
        )
    )
    bundle = generate_vault(
        filtered,
        company_id=args.company_id,
        repository_id=args.repository_id,
        cutoff_timestamp=args.cutoff_timestamp,
    )
    pages_rendered = len(bundle.pages)

    base_envelope: dict[str, Any] = {
        "bucket": args.bucket,
        "prefix": args.prefix,
        "plan_id": args.plan_id,
        "company_id": args.company_id,
        "repository_id": args.repository_id,
        "task_id": args.task_id,
        "cutoff_timestamp": args.cutoff_timestamp,
        "dry_run": bool(args.dry_run),
        "events_read": len(events),
        "pages_rendered": pages_rendered,
        "written": 0,
        "skipped": 0,
        "keys_written": [],
    }

    if args.dry_run:
        _print_envelope(base_envelope)
        return EXIT_OK

    try:
        client = _s3_client_factory(args.aws_region, args.aws_profile)
    except Exception as exc:  # noqa: BLE001 — boundary mapping
        _print_error({"error": "transport", "detail": f"s3_factory: {exc!r}"})
        return EXIT_TRANSPORT

    publisher = SynthesisPublisher(bucket=args.bucket, s3_client=client, prefix=args.prefix)
    try:
        result = publisher.publish(bundle)
    except Exception as exc:  # noqa: BLE001 — boundary mapping of ClientError/Boto3Error/OSError
        _print_error({"error": "transport", "detail": f"{type(exc).__name__}: {exc}"})
        return EXIT_TRANSPORT

    base_envelope["written"] = int(result.written)
    base_envelope["skipped"] = int(result.skipped)
    base_envelope["keys_written"] = list(result.keys_written)
    _print_envelope(base_envelope)
    return EXIT_OK


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    av = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parser.parse_args(av)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return EXIT_OK
        return EXIT_USAGE

    # Inject repo-root into environment for peer modules that honor it.
    os.environ.setdefault("CANON_SYSTEMS_REPO_ROOT", str(Path.cwd()))

    if args.subcommand == "publish":
        return _publish(args)
    return EXIT_USAGE


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
```

### 2. EDIT: `src/canon_systems/cli.py`

**Edit #1** — add import near the existing canon-subcommand imports (after `from .stall_watchdog import run as run_stall_watchdog`, line 20):

```python
from .synth_cli import run as run_synth_cli
```

**Edit #2** — add subparser after the `stall_watchdog_parser` block (around line 325):

```python
    synth_parser = sub.add_parser(
        "synth",
        help="Synthesis vault publishing driver (internal; subcommands: publish).",
    )
    synth_parser.add_argument("args", nargs=argparse.REMAINDER)
```

**Edit #3** — add dispatch after the `stall-watchdog` dispatch (around line 542):

```python
    if args.command == "synth":
        return run_synth_cli(list(getattr(args, "args", [])))
```

### 3. NEW FILE: `tests/test_cli_synth_publish.py`

```python
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
```

**Note on AC7**: `canon_systems.cli.main` must accept an optional `argv` parameter and forward it to `parser.parse_args(argv)`. Inspect the existing signature — the current `main()` in `cli.py` uses `argparse.parse_args(argv)` with `argv=None` default. If the current `main()` signature does not accept `argv`, fall back to monkeypatching `sys.argv` around the call. Choose whichever matches the existing pattern used in `tests/test_cli_*` files and cite the reference test.

### 4. EDIT: `CHANGELOG.md`

Insert at TOP of `## [Unreleased] ### Added`:

```markdown
- **E5-T3**: New `canon synth publish` CLI drives the E5-T2 `SynthesisPublisher` deterministically from a canonical-event JSONL file. Emits a single JSON envelope with per-page diff stats (`written`, `skipped`, `keys_written`); safe to invoke repeatedly (content-hash idempotence from E5-T2). `--dry-run` renders the bundle without S3 I/O; transport failures map to exit 2, usage errors to exit 4.
```

### 5. EDIT: `README.md`

Append a row to the canon command table (find the existing table with rows like `canon checkpoint`, `canon graph`, `canon resume`, `canon stall-watchdog`):

```markdown
| `canon synth publish` | Publish a deterministic Obsidian vault bundle to S3 (idempotent, diff-only). Internal driver for backend/synthesis. |
```

Do NOT reflow any existing rows.

### 6. EDIT: `docs/SYSTEM-WORKFLOW.md`

Append a single bullet to §3 (after the existing E5-T2 bullet):

```markdown
- E5-T3 (canon synth publish CLI): operators and release-orchestrator may invoke `canon synth publish --events-file <jsonl> --plan-id ... --bucket ... --prefix ...` to converge an S3 vault to the current canonical-event set. The command is idempotent: repeat invocations with unchanged inputs + bucket state report `written=0, skipped=<all>`. `--dry-run` renders the bundle in-memory and prints the JSON envelope without any S3 I/O.
```

## STOP CONDITIONS

- ❌ Any change to `backend/synthesis/synthesis/*.py` or `docs/VAULT-LAYOUT.md` — HARD STOP.
- ❌ Full suite drops below 382 at any point — investigate before proceeding.
- ❌ `canon synth publish --help` fails via global `canon` entrypoint — the cli.py wire is broken.
- ❌ Second-run idempotence test fails — SynthesisPublisher contract is being violated (impossible from CLI-side unless bundle hashing is non-deterministic, which E5-T2 already locked).

## DONE

- `pytest tests/test_cli_synth_publish.py -q` → 8 passed.
- `pytest -q` → 390 passed / 0 skipped / 0 failed.
- `git diff --stat` shows only: 1 new CLI module, 1 new test module, 3 files with small additive edits (`cli.py`, `CHANGELOG.md`, `README.md`, `docs/SYSTEM-WORKFLOW.md`).
- Handoff packet emitted to `.cursor/handoffs/canon-memory-v1/E5-T3/implementer.md` with `HANDOFF_TO_QA` block, 8 ACs all MET, suite_result `total=390 passed=390 skipped=0`.
