HANDOFF_TO_QA_SHARD
shard_id: ws2-cli-parity
task_id: docs-tests-rollout
handoff_id: canon-readiness-gates
branch: feature/canon-run-ledger-readiness

summary: |
  Top-level `canon qa-validate` and `canon flow-audit` now parse, document, and forward
  `--require-checkpoints` in line with `qa_validate.run` and `flow_audit.run`, without
  changing other merge-gate flags or sampling behavior. Public help tests cover validators,
  readiness, run-ledger, and packet-archive.

acceptance_criteria:
  - id: AC2
    status: satisfied
    evidence:
      - "src/canon_systems/cli.py registers and forwards `--require-checkpoints` for qa-validate and flow-audit."
      - "src/canon_systems/flow_audit.py documents `--require-checkpoints` with validator intent."
      - "tests/test_readiness_cli.py, tests/test_run_ledger_cli.py, and tests/test_packet_archive_cli.py include public help coverage."
  - id: AC4
    status: satisfied
    evidence:
      - "tests/test_flow_audit.py::test_public_cli_flow_audit_forwards_require_checkpoints"
      - "tests/test_flow_audit.py::test_top_level_help_lists_flow_audit_require_checkpoints"
      - "tests/test_qa_validate.py::test_public_cli_qa_validate_forwards_require_checkpoints"
      - "tests/test_qa_validate.py::test_top_level_help_lists_qa_validate_require_checkpoints"

verification:
  - "python3 -m pytest <five target CLI/test files> -> 98 passed"

artifacts:
  - src/canon_systems/cli.py
  - src/canon_systems/flow_audit.py
  - tests/test_flow_audit.py
  - tests/test_qa_validate.py
  - tests/test_readiness_cli.py
  - tests/test_run_ledger_cli.py
  - tests/test_packet_archive_cli.py

notes: |
  Graph retrieval degraded because AXON/AWS configuration was unavailable. The reference plan file was not edited.

END_HANDOFF_TO_QA_SHARD
