HANDOFF_TO_QA_SHARD
shard_id: ws1
task_id: readiness-contract
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
branch: feature/canon-run-ledger-readiness

summary: |
  Implemented GET `/state/run-ledger` client (`get_run_ledger_from_state_api`) with typed errors and added `readiness.py`: archive-ref phase detection, required phase checks without reading bodies, validation slot passthrough, commit/PR/deployment passthrough, stable readiness JSON, latest-row selection, and limit truncation warnings.

acceptance_criteria:
  - id: AC2
    status: satisfied
    evidence:
      - "src/canon_systems/run_ledger.py (`get_run_ledger_from_state_api`)"
      - "tests/test_readiness.py (`test_get_run_ledger_*`)"
  - id: AC3
    status: satisfied
    evidence:
      - "src/canon_systems/readiness.py archive ref evaluation only"
      - "tests/test_readiness.py missing phase / implementer shard / evidence ref cases"
  - id: AC4
    status: satisfied
    evidence:
      - "src/canon_systems/readiness.py validation outcomes and commit/PR/deployment summaries"
  - id: AC5
    status: satisfied
    evidence:
      - "src/canon_systems/readiness.py stable report schema"

tests:
  command: "python3 -m pytest tests/test_readiness.py tests/test_run_ledger_cli.py -q"
  result: "26 passed"
END_HANDOFF_TO_QA_SHARD
