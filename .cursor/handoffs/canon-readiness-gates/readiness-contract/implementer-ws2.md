HANDOFF_TO_QA_SHARD
shard_id: ws2
task_id: readiness-contract
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
workstream_id: readiness-contract

implementation_summary: |
  Implemented `canon readiness check` with required scope flags, optional `--ledger-run-id`, `--state-api-url`, `--limit`, `--output`, and `--quiet`. The CLI calls `evaluate_readiness`, writes snapshots, and maps ready/not-ready/query errors to exits 0/1/2.

acceptance_criteria:
  - id: AC1
    status: satisfied
    evidence:
      - "src/canon_systems/readiness_cli.py"
      - "src/canon_systems/cli.py"
      - "tests/test_readiness_cli.py::test_ac1_requires_scope_flags"
  - id: AC2
    status: satisfied
    evidence:
      - "src/canon_systems/readiness_cli.py query error handling"
      - "tests/test_readiness_cli.py::test_ac2_query_errors_exit_2"
  - id: AC5
    status: satisfied
    evidence:
      - "tests/test_readiness_cli.py::test_ac5_snapshot_keys_and_schema"
      - "tests/test_readiness_cli.py::test_ac5_output_matches_stdout"
  - id: AC6
    status: satisfied
    evidence:
      - "tests/test_readiness_cli.py::test_ac6_exit_0_when_ready"
      - "tests/test_readiness_cli.py::test_ac6_exit_1_when_not_ready"
      - "tests/test_readiness_cli.py::test_ac6_exit_2_invalid_limit"

tests:
  command: "python3 -m pytest tests/test_readiness_cli.py tests/test_readiness.py -q"
  result: "28 passed"
END_HANDOFF_TO_QA_SHARD
