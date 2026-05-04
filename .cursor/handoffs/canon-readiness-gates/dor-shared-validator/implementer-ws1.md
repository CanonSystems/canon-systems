HANDOFF_TO_QA_SHARD
shard_id: ws1
task_id: dor-shared-validator
workstream_id: dor-shared-validator
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8

summary: |
  Added shared DoR telemetry helper (`dor_telemetry.py`), delegated qa-validate and flow-audit DoR checks to it with `require_task_identity=True`, and preserved flow-audit bulk missing-json warning. Extended CLI/fixture tests for AC2–AC4; pytest 48 passed on test_qa_validate + test_flow_audit.

acceptance_criteria:
  - id: AC2
    status: satisfied
    evidence:
      - "src/canon_systems/dor_telemetry.py::collect_dor_telemetry_errors"
      - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_invalid_json_reports_payload_path"
      - "tests/test_flow_audit.py::test_flow_audit_dor_telemetry_invalid_json_and_non_object_paths"
  - id: AC3
    status: satisfied
    evidence:
      - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_identity_handoff_stage_task"
      - "tests/test_qa_validate.py::test_collect_dor_telemetry_skips_task_id_when_absent_if_not_required"
      - "tests/test_flow_audit.py::test_flow_audit_dor_telemetry_identity_and_exit_code_marker"
  - id: AC4
    status: satisfied
    evidence:
      - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_status_requires_exit_code_marker"
      - "tests/test_flow_audit.py::test_flow_audit_dor_telemetry_identity_and_exit_code_marker"

artifacts:
  - src/canon_systems/dor_telemetry.py
  - src/canon_systems/qa_validate.py
  - src/canon_systems/flow_audit.py
  - tests/test_qa_validate.py
  - tests/test_flow_audit.py

verification:
  command: "python3 -m pytest tests/test_qa_validate.py tests/test_flow_audit.py -q"
  result: "48 passed"
END_HANDOFF_TO_QA_SHARD
