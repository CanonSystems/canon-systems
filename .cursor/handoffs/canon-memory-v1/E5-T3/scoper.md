# SCOPE_PACKET — E5-T3: `canon synth publish` CLI (internal driver)

<!-- SCOPER_PACKET: E5-T3 -->

## SCOPE_SUMMARY

Introduce an idempotent `canon synth publish` subcommand that drives the E5-T2 `SynthesisPublisher` from the command line. The CLI reads canonical events (from a `--events-file` JSONL in Wave 5 — per E5-T2 waiver on live state-api event query), renders a `VaultBundle` via `generate_vault`, publishes diff-only to S3 via `SynthesisPublisher.publish`, and emits a single JSON envelope with per-page diff stats to stdout. The command is safe to invoke repeatedly: back-to-back runs with the same inputs produce `written=0, skipped=N` (except `.obsidian/*` which are write-once on first run).

This task is **CLI wiring** on top of E5-T2 — no new core logic, no new event schemas, no new S3 semantics. The contract is "take a canonical-event JSONL and guarantee convergent S3 state".

## Context

- **Peer artifacts (READ-ONLY)**:
  - `backend/synthesis/synthesis/publisher.py` — `SynthesisPublisher.publish(bundle)` returns `PublishResult(written, skipped, keys_written)`. Content-hash via `x-amz-meta-content-hash`. Write-once for `.obsidian/*`.
  - `backend/synthesis/synthesis/generator.py` — `generate_vault(events, *, company_id, repository_id, cutoff_timestamp) -> VaultBundle`. Pure, deterministic, no wallclock.
  - `backend/synthesis/synthesis/sources.py` — `InMemoryEventSource` (we drive from JSONL; no state-api live path this wave).
  - `backend/shared/canon_backend_shared/events.py` — `CanonicalEvent` dataclass (15 fields).
  - `src/canon_systems/resume_engine.py` (E4-T1) — reference for stdlib-only CLI module structure (`_build_parser`, `run(argv)`, exit codes, JSON envelope to stdout, monkeypatchable HTTP seam).
  - `src/canon_systems/cli.py` lines 19 (import), 318-319 (subparser), 538-539 (dispatch) — the three-site additive wire pattern per Precedent §2.
- **Waiver carried forward (Wave 5)**: `StateApiEventSource` is the state-api seam for a future wave. E5-T3 uses `InMemoryEventSource` exclusively; live state-api is out of scope per the E5-T2 scoper's infra waiver.

## Target module + surface

**New file**: `src/canon_systems/synth_cli.py` — single module hosting `canon synth publish`.

**CLI shape** (only the publish subcommand this task):

```
canon synth publish \
  --events-file <path>.jsonl \
  --plan-id <id> \
  --company-id <id> \
  --repository-id <id> \
  --cutoff-timestamp <iso8601-Z> \
  --bucket <s3-bucket> \
  --prefix <s3-prefix> \
  [--task-id <id>] \
  [--dry-run] \
  [--aws-region <region>] \
  [--aws-profile <profile>]
```

All required args MUST be validated before any S3 call. `--dry-run` short-circuits after rendering the bundle and prints the JSON envelope with `written=0, skipped=0, dry_run: true, pages_rendered=<N>` (so operators can inspect bundle size).

**JSON envelope** (single-line to stdout; `sort_keys=True`):

```json
{
  "bucket": "<bucket>",
  "prefix": "<prefix>",
  "plan_id": "<id>",
  "company_id": "<id>",
  "repository_id": "<id>",
  "task_id": "<id-or-null>",
  "cutoff_timestamp": "<iso>",
  "dry_run": false,
  "events_read": <int>,
  "pages_rendered": <int>,
  "written": <int>,
  "skipped": <int>,
  "keys_written": [ "<rel>", ... ]
}
```

`keys_written` MUST be sorted (it's already sorted by `SynthesisPublisher.publish` via `sorted(bundle.pages.items())`; preserve that order — do NOT re-sort inside the CLI).

## Exit codes

- `0` — ok (including dry-run, 0-events, 0-written-N-skipped).
- `2` — transport/S3 error (`botocore.exceptions.ClientError` other than NoSuchKey/404; `boto3.exceptions.Boto3Error`; `OSError`).
- `4` — usage (bad JSONL, missing file, invalid ISO timestamp, unknown arg).

## Event-file format (JSONL)

One JSON object per line, each a `CanonicalEvent.to_dict()` shape:

```json
{"schema_version":1,"event_id":"evt-001","parent_event_id":"","event_type":"release_status",
 "company_id":"c1","repository_id":"r1","plan_id":"canon-memory-v1","task_id":"E5-T3",
 "handoff_id":"handoff-001","agent_name":"release-orchestrator","agent_run_id":"run-001",
 "actor_id":"actor-1","model":"claude-opus-4","timestamp":"2026-04-23T12:00:00Z",
 "state_version":1,"payload":{"verdict":"PASS"}}
```

The parser MUST reject lines where `schema_version != 1` or any field is missing (raise `ValueError` → exit 4). Empty/whitespace-only lines are silently skipped.

## S3 client factory (test seam)

Expose `_s3_client_factory(aws_region: str, aws_profile: str) -> Any` in `synth_cli.py`. Default implementation wraps:

```python
import boto3
session = boto3.Session(profile_name=aws_profile or None, region_name=aws_region or None)
return session.client("s3")
```

Tests monkeypatch `synth_cli._s3_client_factory` to return `DictS3Client` (from `backend/synthesis/synthesis_tests/_fakes.py`) — or a local minimal clone if importing across the `src/` + `backend/` boundary is awkward. Prefer a small local `DictS3Client` in `tests/` to avoid cross-package imports; the publisher doesn't need the moto backend here.

## Forbidden surfaces

- `backend/synthesis/synthesis/{publisher,generator,sources,redaction}.py` — E5-T2 contract is locked.
- `docs/VAULT-LAYOUT.md` — E5-T1 locks schema v1.
- `backend/shared/canon_backend_shared/events.py` — canonical event contract.
- `src/canon_systems/checkpoint_cli.py`, `src/canon_systems/stall_watchdog.py`, `src/canon_systems/resume_engine.py` — peer CLIs, out of scope.
- Any existing test module must not be edited except additively (new test file preferred).

## Allowed edits

- **CREATE**: `src/canon_systems/synth_cli.py`
- **CREATE**: `tests/test_cli_synth_publish.py` (new test module; ≥8 tests)
- **MODIFY (additive-only)**:
  - `src/canon_systems/cli.py` — add import, subparser, dispatch. 3 edits only.
  - `CHANGELOG.md` — single new bullet at TOP of `[Unreleased] ### Added`.
  - `README.md` — append a row to the canon command table (do NOT reflow).
  - `docs/SYSTEM-WORKFLOW.md` — single additive bullet in §3.

## Acceptance criteria (from backlog lines 490-500)

- **AC1** — `canon synth publish --help` exits 0 and lists the required args (`--events-file`, `--plan-id`, `--company-id`, `--repository-id`, `--cutoff-timestamp`, `--bucket`, `--prefix`).
- **AC2** — Happy path: with 3 canonical events in JSONL, publish writes all generated pages and emits a JSON envelope with `written>=pages_rendered`, `skipped=0` (on a fresh bucket), `keys_written` sorted ASCII-ascending.
- **AC3** — Idempotence: second invocation with identical args + unchanged bucket state yields `written=0, skipped=<all>`, `keys_written=[]`, exit 0. Contract: safe to invoke repeatedly; no duplicate writes.
- **AC4** — Dry-run: `--dry-run` skips all S3 I/O (assertable by fake client receiving 0 put_object calls), prints `{…, "dry_run": true, "written": 0, "skipped": 0, "pages_rendered": N}`.
- **AC5** — Bad JSONL: malformed line → stderr JSON `{"error":"usage", …}`, exit 4, no S3 calls.
- **AC6** — Transport error: `put_object` raises `ClientError(ServiceUnavailable)` → stderr JSON `{"error":"transport", …}`, exit 2; output envelope is NOT printed.
- **AC7** — Wiring: `canon synth publish --help` works via the global `canon` entrypoint (not just `python -m canon_systems.synth_cli`), proving the cli.py wire is correct.
- **AC8** — Living-spec edits are strictly additive: CHANGELOG top-of-Unreleased, README command-table append, SYSTEM-WORKFLOW §3 append.

## Done signal

```
tests/test_cli_synth_publish.py PASS
pytest -q → 390 passed (was 382 at E5-T2 tip; E5-T3 adds 8 tests)
```

## Parallelizability

E5-T3 depends on E5-T2 only (completed at `f8a1715`). No other Wave-5 task blocks on this; E5-T4/T5/T6 are web/agent/mirror readers — not publishers.

## Prior work references

- `prior_work_references`:
  - E5-T2 `backend/synthesis/synthesis_tests/test_publisher_moto.py` — idempotence pattern (second publish = 0-written) we mirror for AC3.
  - E4-T1 `src/canon_systems/resume_engine.py` — stdlib CLI shape (argparse, JSON envelope, monkeypatchable HTTP seam) we mirror structurally.
  - E3-T5 `src/canon_systems/report_cli.py` — dispatch-tail pattern already live in `cli.py`.

---

```text
HANDOFF_TO_CURSOR_PILOT

task_id: E5-T3
title: "canon synth publish CLI (internal driver)"
branch: wave/5/canon-memory-v1

scope_locked:
  - Single new CLI module src/canon_systems/synth_cli.py wiring SynthesisPublisher.
  - Three additive edits to src/canon_systems/cli.py (import, subparser, dispatch).
  - One new test module tests/test_cli_synth_publish.py (≥8 tests).
  - Living-spec: additive CHANGELOG + README table append + SYSTEM-WORKFLOW §3 bullet.

cursor-pilot MUST:
  - Begin with `<!-- CURSOR_PILOT_PROMPT: E5-T3 canon synth publish CLI -->`
  - Provide verbatim code skeleton for synth_cli.py (argparse, _build_parser, run, _s3_client_factory, _load_events, _print_envelope).
  - Provide verbatim test skeletons for the 8 ACs (AC1 help, AC2 happy, AC3 idempotence, AC4 dry-run, AC5 bad JSONL, AC6 transport error, AC7 global canon wiring via entry_points, AC8 living-spec).
  - Provide verbatim CHANGELOG / README / SYSTEM-WORKFLOW diffs.
  - State: generator/publisher/redaction/sources are LOCKED; CLI MUST import from them unchanged.

do_not:
  - Modify any file under backend/synthesis/synthesis/*.py or docs/VAULT-LAYOUT.md.
  - Add new cross-module state or globals beyond the test monkeypatch seam.
  - Re-sort keys_written inside the CLI (SynthesisPublisher already emits sorted).

END_HANDOFF_TO_CURSOR_PILOT
```
