HANDOFF_TO_QA
  handoff_id: "canon-readiness-gates"
  task_id: "dor-shared-validator"
  acceptance_criteria_covered:
    - criterion: "AC1: `canon qa-validate --require-dor-telemetry` and `canon flow-audit` both call a shared DoR telemetry validation helper rather than maintaining separate rejection telemetry validation loops."
      evidence_files:
        - "src/canon_systems/dor_telemetry.py"
        - "src/canon_systems/qa_validate.py"
        - "src/canon_systems/flow_audit.py"
      evidence_tests:
        - "tests/test_qa_validate.py::test_qa_validate_require_dor_telemetry_delegates_to_shared_helper"
        - "tests/test_flow_audit.py::test_flow_audit_ac1_invokes_collect_dor_telemetry_errors_for_task"
    - criterion: "AC2: For every `.cursor/handoffs/<handoff_id>/<task_id>/handoff-not-ready/<stem>.md` packet, both commands require `.cursor/handoffs/<handoff_id>/<task_id>/dor-failure/<stem>.json` and `<stem>.status`, reject invalid/non-object telemetry JSON, and report missing artifacts using actionable paths."
      evidence_files:
        - "src/canon_systems/dor_telemetry.py"
      evidence_tests:
        - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_missing_artifacts_reference_packet_path"
        - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_invalid_json_reports_payload_path"
        - "tests/test_flow_audit.py::test_flow_audit_dor_telemetry_invalid_json_and_non_object_paths"
    - criterion: "AC3: The shared helper validates telemetry identity consistently: payload `handoff_id` must match the CLI handoff id, `stage` must be non-empty, and `task_id` must match when present or when the caller opts into requiring task identity."
      evidence_files:
        - "src/canon_systems/dor_telemetry.py"
      evidence_tests:
        - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_identity_handoff_stage_task"
        - "tests/test_qa_validate.py::test_collect_dor_telemetry_skips_task_id_when_absent_if_not_required"
        - "tests/test_flow_audit.py::test_flow_audit_dor_telemetry_identity_and_exit_code_marker"
    - criterion: "AC4: The shared helper validates each telemetry status file contains an `exit_code:` marker, and both commands preserve existing exit-code behavior (`0` pass, `1` validation failure, `2` usage/file errors)."
      evidence_files:
        - "src/canon_systems/dor_telemetry.py"
        - "src/canon_systems/qa_validate.py"
        - "src/canon_systems/flow_audit.py"
      evidence_tests:
        - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_status_requires_exit_code_marker"
        - "tests/test_qa_validate.py::test_qa_validate_require_dor_telemetry_exits_2_without_handoff_or_task_id"
        - "tests/test_flow_audit.py::test_flow_audit_ac4_telemetry_status_requires_exit_code_marker"
    - criterion: "AC5: Existing non-DoR behavior remains unchanged: qa-gate evidence parsing, checkpoint validation, memory-health validation, release-status checks, plan-file checks, credential handling, and deploy attestation are not refactored or semantically changed."
      evidence_files:
        - "src/canon_systems/qa_validate.py"
        - "src/canon_systems/flow_audit.py"
      evidence_tests:
        - "tests/test_qa_validate.py::test_qa_validate_passes_for_valid_gate_packet"
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry"
        - "tests/test_flow_audit.py::test_flow_audit_passes_for_valid_artifacts"
        - "tests/test_flow_audit.py::test_flow_audit_passes_with_memory_health_evidence_ok"
  summary: "Extracted shared DoR telemetry validation into `dor_telemetry.py`, wired qa-validate and flow-audit through it, and added regression coverage for missing/invalid/mismatched telemetry, status `exit_code:`, and preserved non-DoR behavior."
  decisions:
    - "Task id is enforced when present and when required by caller, while helper-level behavior can remain compatible with older telemetry that omitted task_id."
  next_actions:
    - "Implement structured credential attestation in the next task."
  open_questions: []
END_HANDOFF_TO_QA
