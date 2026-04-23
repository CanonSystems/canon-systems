# E5-T3 implementer handoff — `canon synth publish` CLI

## Implementation notes

- `canon_systems.cli.main` already accepts `argv: list[str] | None = None` and passes it to `parser.parse_args(argv)` (see `src/canon_systems/cli.py`). **AC7** uses `top_cli.main(["synth", "publish", "--help"])` directly — no `sys.argv` monkeypatch.
- Added `_ensure_repo_backend_import_path()` in `synth_cli.py` (after `CANON_SYSTEMS_REPO_ROOT` setdefault in `run()`): inserts `backend/shared` and `backend/synthesis` on `sys.path` when those directories exist under the repo root. Root `pytest.ini` only sets `pythonpath = src`; without this, `canon_backend_shared` / `synthesis` imports fail during `_publish`. Production `canon` entrypoint sets `CANON_SYSTEMS_REPO_ROOT` before dispatch, so monorepo runs resolve correctly.

```text
HANDOFF_TO_QA
handoff_id: handoff_20260423_e5t3_synth_publish_cli
task_id: E5-T3
branch: wave/5/canon-memory-v1
files_created:
  - src/canon_systems/synth_cli.py
  - tests/test_cli_synth_publish.py
files_modified:
  - src/canon_systems/cli.py
  - CHANGELOG.md
  - README.md
  - docs/SYSTEM-WORKFLOW.md
acceptance_criteria:
  - id: AC1
    status: MET
    evidence: "`canon synth publish --help` via `synth_cli.run(['publish','--help'])` returns EXIT_OK; stdout lists all seven required flags."
    covering_tests:
      - tests/test_cli_synth_publish.py::test_ac1_help_exits_zero
  - id: AC2
    status: MET
    evidence: "Three-event JSONL + FakeS3; envelope shows dry_run false, skipped 0, written == pages_rendered, keys_written sorted, put_calls match written."
    covering_tests:
      - tests/test_cli_synth_publish.py::test_ac2_happy_path_writes_pages
  - id: AC3
    status: MET
    evidence: "Second identical publish yields written=0, skipped==first written, keys_written=[], no put_object calls."
    covering_tests:
      - tests/test_cli_synth_publish.py::test_ac3_second_run_is_idempotent
  - id: AC4
    status: MET
    evidence: "`--dry-run` prints envelope with dry_run true, written/skipped 0, pages_rendered>=1; `_s3_client_factory` patched to assert it is never called."
    covering_tests:
      - tests/test_cli_synth_publish.py::test_ac4_dry_run_skips_s3
  - id: AC5
    status: MET
    evidence: "Malformed JSONL (incomplete CanonicalEvent line) → stderr JSON error usage, EXIT_USAGE, zero S3 puts; missing events file → usage JSON with not-found detail."
    covering_tests:
      - tests/test_cli_synth_publish.py::test_ac5_bad_jsonl_exits_usage
      - tests/test_cli_synth_publish.py::test_ac8_missing_file_exits_usage
  - id: AC6
    status: MET
    evidence: "FakeS3 put_object raises ClientError(ServiceUnavailable); EXIT_TRANSPORT, stderr transport JSON, stdout envelope empty."
    covering_tests:
      - tests/test_cli_synth_publish.py::test_ac6_transport_error_maps_to_exit_2
  - id: AC7
    status: MET
    evidence: "Global CLI wiring: `canon_systems.cli.main(['synth','publish','--help'])` with `run_synth_cli` monkeypatched receives argv `['publish','--help']` and returns 0."
    covering_tests:
      - tests/test_cli_synth_publish.py::test_ac7_global_canon_wiring
  - id: AC8
    status: MET
    evidence: "Additive-only living spec — E5-T3 bullet at top of [Unreleased]/Added in CHANGELOG.md; README canon table row appended after stall-watchdog; SYSTEM-WORKFLOW §3 bullet after E5-T2 paragraph."
    covering_tests: []
suite_result: total=390 passed=390 skipped=0
END_HANDOFF_TO_QA
```
