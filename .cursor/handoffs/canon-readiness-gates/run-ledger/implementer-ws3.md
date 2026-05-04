HANDOFF_TO_QA_SHARD

shard_id: ws3
task_id: run-ledger
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
branch: feature/canon-run-ledger-readiness

implementation_summary: |
  Implemented `canon run-ledger` (`run_ledger_cli.py`) wired from `cli.py`: load record from `--record-file` or `--record-json`, optional `--merge-archive-json` (array of archive metadata merged via `merge_archive_snapshots_into_record` / `archive_record_to_ledger_reference`). `--dry-run` validates + prints normalized JSON only. Without `--dry-run`, posts the validated record with `POST {base}/state/run-ledger`. Added `prepare_cli_run_ledger_record`, `post_run_ledger_to_state_api`, and `RUN_LEDGER_STATE_PATH` in `src/canon_systems/run_ledger.py`. Tests cover dry-run, merge, forbidden body on archive snapshots, bad merge array elements, HTTP POST URL/body via mocked `urlopen`, post success path through the CLI, and `canon main` dispatch. Did not touch state-api persistence, DynamoDB, or packet-archive behavior.

artifacts:
  - src/canon_systems/run_ledger.py
  - src/canon_systems/run_ledger_cli.py
  - src/canon_systems/cli.py
  - tests/test_run_ledger_cli.py

acceptance_criteria:
  - id: AC6
    status: SATISFIED
    evidence:
      - "`canon run-ledger --record-file|--record-json` with `--merge-archive-json` optional; `--dry-run` produces normalized ledger JSON with no network; non-dry-run calls `post_run_ledger_to_state_api`."
      - "tests/test_run_ledger_cli.py::test_ac6_dry_run_prints_normalized_record"
      - "tests/test_run_ledger_cli.py::test_ac6_merge_archive_json_adds_refs"
      - "tests/test_run_ledger_cli.py::test_canon_main_dispatches_run_ledger_dry_run"
  - id: AC8
    status: PARTIAL_WS3
    evidence:
      - "CLI/helper dry-run and mocked POST without live AWS: `tests/test_run_ledger_cli.py`."
      - "DynamoDB/state-api moto coverage owned by ws2 per pilot split."

pytest: "20 passed (tests/test_run_ledger_cli.py + tests/test_run_ledger.py + tests/test_packet_archive_cli.py)"
END_HANDOFF_TO_QA_SHARD
