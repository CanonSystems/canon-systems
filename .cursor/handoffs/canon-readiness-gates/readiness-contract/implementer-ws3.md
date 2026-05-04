HANDOFF_TO_QA_SHARD
shard_id: ws3
task_id: readiness-contract
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
branch: feature/canon-run-ledger-readiness

scope_summary: |
  Locked the state-api read-only boundary for readiness against GET /state/run-ledger: documented semantics, narrowed the GET dependency to RunLedgerReadAccessor (reads only), and added moto-backed AC7 tests proving GET does not mutate ledger rows, checkpoint DynamoDB items, or S3 artifact keys.

acceptance_criteria:
  - id: AC7
    status: SATISFIED
    evidence:
      - "backend/state-api/state_api/run_ledger.py"
      - "backend/state-api/state_api/main.py"
      - "backend/state-api/tests/test_run_ledger.py::test_ac7_get_run_ledger_preserves_ledger_row_in_dynamodb"
      - "backend/state-api/tests/test_run_ledger.py::test_ac7_get_run_ledger_preserves_checkpoint_table_row"
      - "backend/state-api/tests/test_run_ledger.py::test_ac7_get_run_ledger_preserves_s3_artifact_bucket"

verification:
  command: "python3 -m pytest backend/state-api/tests/test_run_ledger.py -v --tb=short"
  result: "11 passed"
END_HANDOFF_TO_QA_SHARD
