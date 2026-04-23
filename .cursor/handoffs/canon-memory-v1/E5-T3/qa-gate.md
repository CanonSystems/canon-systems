# E5-T3 qa-gate — `canon synth publish` CLI

## Summary

Verification PASS for Wave 5 / E5-T3. All 8 acceptance criteria are covered by
deterministic tests (or, for the doc-only AC8, by additive living-spec diffs).
Full suite advances 382 → 390 (8 new tests, zero regressions). Forbidden
surfaces (`backend/synthesis/synthesis/`, `docs/VAULT-LAYOUT.md`,
`backend/shared/canon_backend_shared/events.py`) are byte-for-byte unchanged.
`result.keys_written` ordering is delegated to the publisher — no re-sort in
the CLI (source-grep confirmed). CHANGELOG bullet sits at the top of
`[Unreleased] ### Added`; README canon-table row is an additive insert (no row
above it reflowed); SYSTEM-WORKFLOW §3 gains a single additive bullet.

## Reconcile

- Scope files touched (6): `src/canon_systems/synth_cli.py`,
  `tests/test_cli_synth_publish.py`, `src/canon_systems/cli.py`,
  `CHANGELOG.md`, `README.md`, `docs/SYSTEM-WORKFLOW.md`.
- Non-scope changes in tree: `.canon/memory/capture-latest.json` and
  `.canon/memory/capture-failures.log` (Canon capture telemetry — expected
  side effect of running `canon capture`; not production code).
- Forbidden surfaces: `git diff HEAD -- backend/synthesis/synthesis/
  docs/VAULT-LAYOUT.md backend/shared/canon_backend_shared/events.py` is
  empty (0 lines).
- `keys_written` sort: `rg sort|sorted src/canon_systems/synth_cli.py`
  returns only `json.dumps(..., sort_keys=True)` — no explicit
  `result.keys_written.sort()` / `sorted(result.keys_written)`. Publisher
  ordering is preserved per scoper contract line 65.
- CHANGELOG: E5-T3 bullet is line 12, immediately under `### Added` (line 10);
  no intervening entry. Top-of-Unreleased confirmed.
- README: diff shows a single `+` line at the end of the canon command-table
  block (after `stall-watchdog`, before `secrets`); no adjacent rows were
  reflowed.
- SYSTEM-WORKFLOW: §3 gains one `+` bullet after the E5-T2 paragraph; no
  existing text changed.

## Deviations ratified

- **DEV-1 (sys.path patch)** — `synth_cli._ensure_repo_backend_import_path()`
  prepends `backend/shared/` and `backend/synthesis/` to `sys.path` in `run()`
  before dispatching `_publish`. Root `pytest.ini` only sets
  `pythonpath = src`, so absent the patch `from synthesis.generator import
  generate_vault` and `from canon_backend_shared.events import CanonicalEvent`
  fail under `pytest` and plain `python -m canon_systems.synth_cli` runs.
  Production `canon` entrypoint sets `CANON_SYSTEMS_REPO_ROOT` before
  dispatch, so monorepo installs resolve correctly. Scope-contained (no
  forbidden surfaces). Ratified.
- **DEV-2 (AC8 covering_tests filled at gate)** — The implementer handoff
  left `acceptance_criteria[AC8].covering_tests` empty. Per QA-gate precedent
  §5 ("every AC needs ≥1 covering_tests entry"), this gate fills AC8 with the
  three additive-only living-spec files (`CHANGELOG.md`, `README.md`,
  `docs/SYSTEM-WORKFLOW.md`) as bare file paths. These are the canonical
  doc-only AC pattern and are not interpreted as pytest nodes by
  `canon qa-validate` (the validator's regex requires `::` to bind a node
  id). Ratified.

```
GATE_RESULTS
  handoff_id: "handoff_20260423_e5t3_synth_publish_cli"
  task_id: "E5-T3"
  branch: "wave/5/canon-memory-v1"
  verdict: PASS
  regression_checked: true
  iterations: 0
  suite_result: total=390 passed=390 skipped=0
  acceptance_criteria:
    - id: AC1
      status: MET
      evidence: "`synth_cli.run(['publish','--help'])` returns EXIT_OK; captured stdout contains all seven required flags (`--events-file`, `--plan-id`, `--company-id`, `--repository-id`, `--cutoff-timestamp`, `--bucket`, `--prefix`)."
      covering_tests:
        - "tests/test_cli_synth_publish.py::test_ac1_help_exits_zero"
    - id: AC2
      status: MET
      evidence: "Happy path with 3-event JSONL + FakeS3 on fresh bucket: envelope shows dry_run false, events_read=3, pages_rendered>=1, written==pages_rendered, skipped=0, keys_written ASCII-sorted, fake_s3.put_calls length equals written."
      covering_tests:
        - "tests/test_cli_synth_publish.py::test_ac2_happy_path_writes_pages"
    - id: AC3
      status: MET
      evidence: "Back-to-back invocation with identical argv against the same FakeS3: first run writes N, second run reports written=0, skipped==N, keys_written=[], and fake_s3.put_calls is empty after clearing between runs. Exit 0 on both."
      covering_tests:
        - "tests/test_cli_synth_publish.py::test_ac3_second_run_is_idempotent"
    - id: AC4
      status: MET
      evidence: "`--dry-run` with `_s3_client_factory` monkeypatched to AssertionError on call: run exits 0, envelope has dry_run=true, written=0, skipped=0, pages_rendered>=1. Factory is never invoked (no S3 I/O)."
      covering_tests:
        - "tests/test_cli_synth_publish.py::test_ac4_dry_run_skips_s3"
    - id: AC5
      status: MET
      evidence: "Malformed JSONL (truncated CanonicalEvent line) → EXIT_USAGE, stderr JSON `{error: usage, detail: ...}`, zero put_object calls. Missing events-file → EXIT_USAGE, stderr usage JSON with not-found detail."
      covering_tests:
        - "tests/test_cli_synth_publish.py::test_ac5_bad_jsonl_exits_usage"
        - "tests/test_cli_synth_publish.py::test_ac8_missing_file_exits_usage"
    - id: AC6
      status: MET
      evidence: "FakeS3 configured with fail_mode='service_unavailable' raises `ClientError(ServiceUnavailable, HTTP 503)` on put_object: run exits EXIT_TRANSPORT, stderr JSON `{error: transport, ...}`, stdout envelope is empty (not printed)."
      covering_tests:
        - "tests/test_cli_synth_publish.py::test_ac6_transport_error_maps_to_exit_2"
    - id: AC7
      status: MET
      evidence: "Global wiring: `canon_systems.cli.main(['synth','publish','--help'])` with `run_synth_cli` monkeypatched on the top-level `cli` module receives argv=['publish','--help'] and returns 0, proving the import + subparser + dispatch wire in `src/canon_systems/cli.py` (lines 21, 328-332, 551-552)."
      covering_tests:
        - "tests/test_cli_synth_publish.py::test_ac7_global_canon_wiring"
    - id: AC8
      status: MET
      evidence: "Additive-only living-spec: CHANGELOG.md new E5-T3 bullet is the FIRST entry under `[Unreleased] ### Added` (line 12, immediately after the heading — E5-T2 now second); README.md canon command table gained a single appended row after stall-watchdog with no reflow of existing rows; docs/SYSTEM-WORKFLOW.md §3 gained a single additive bullet after the E5-T2 paragraph. `git diff HEAD -- backend/synthesis/synthesis/ docs/VAULT-LAYOUT.md backend/shared/canon_backend_shared/events.py` is empty — no forbidden surface mutated."
      covering_tests:
        - "CHANGELOG.md"
        - "README.md"
        - "docs/SYSTEM-WORKFLOW.md"
  remaining_gaps: []
  notes: "All 8 ACs pass on first verification iteration. Focused module `pytest tests/test_cli_synth_publish.py -q` → 8 passed. Broad regression sweep `pytest -q` → 390 passed in 5.71s (baseline 382 at E5-T2 tip + 8 new = 390). `keys_written` ordering delegated to publisher per scoper contract; source grep confirms zero explicit sort calls in synth_cli.py. DEV-1 (backend sys.path patch) and DEV-2 (AC8 covering_tests filled at gate) ratified above."
END_GATE_RESULTS
```
