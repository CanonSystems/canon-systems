HANDOFF_TO_QA_SHARD
shard_id: ws2
task_id: dor-shared-validator
workstream_id: dor-shared-validator
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8

summary: |
  qa-validate now calls `collect_dor_telemetry_errors_for_task` directly, with no separate DoR wrapper. Added tests proving delegation to the shared helper, exit code 2 when `--require-dor-telemetry` is set without both ids, and that HANDOFF_NOT_READY artifacts are ignored unless the flag is set.

acceptance_criteria:
  - id: AC1
    status: satisfied
    evidence:
      - "src/canon_systems/qa_validate.py"
      - "tests/test_qa_validate.py::test_qa_validate_require_dor_telemetry_delegates_to_shared_helper"
  - id: AC4
    status: satisfied
    evidence:
      - "tests/test_qa_validate.py::test_qa_validate_require_dor_telemetry_exits_2_without_handoff_or_task_id"
      - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_status_requires_exit_code_marker"
  - id: AC5
    status: satisfied
    evidence:
      - "tests/test_qa_validate.py::test_qa_validate_without_require_dor_telemetry_ignores_rejection_artifacts"

artifacts:
  - src/canon_systems/qa_validate.py
  - tests/test_qa_validate.py

verification:
  command: "python3 -m pytest tests/test_qa_validate.py -q"
  result: "30 passed"
END_HANDOFF_TO_QA_SHARD
