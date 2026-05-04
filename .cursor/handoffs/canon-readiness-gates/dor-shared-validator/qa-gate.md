GATE_RESULTS
  handoff_id: "canon-readiness-gates"
  verdict: PASS
  acceptance_criteria:
    - criterion: "AC1: `canon qa-validate --require-dor-telemetry` and `canon flow-audit` both call a shared DoR telemetry validation helper rather than maintaining separate rejection telemetry validation loops."
      status: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_require_dor_telemetry_delegates_to_shared_helper"
        - "tests/test_flow_audit.py::test_flow_audit_ac1_invokes_collect_dor_telemetry_errors_for_task"
      run_result: "pass; included in 55-test focused suite and 81-test adjacent regression sweep"
    - criterion: "AC2: For every `.cursor/handoffs/<handoff_id>/<task_id>/handoff-not-ready/<stem>.md` packet, both commands require `.cursor/handoffs/<handoff_id>/<task_id>/dor-failure/<stem>.json` and `<stem>.status`, reject invalid/non-object telemetry JSON, and report missing artifacts using actionable paths."
      status: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_missing_artifacts_reference_packet_path"
        - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_invalid_json_reports_payload_path"
        - "tests/test_flow_audit.py::test_flow_audit_dor_telemetry_invalid_json_and_non_object_paths"
        - "tests/test_flow_audit.py::test_flow_audit_dor_telemetry_bulk_warns_when_no_json_files"
      run_result: "pass; missing/invalid telemetry path coverage passed"
    - criterion: "AC3: The shared helper validates telemetry identity consistently: payload `handoff_id` must match the CLI handoff id, `stage` must be non-empty, and `task_id` must match when present or when the caller opts into requiring task identity."
      status: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_identity_handoff_stage_task"
        - "tests/test_qa_validate.py::test_collect_dor_telemetry_skips_task_id_when_absent_if_not_required"
        - "tests/test_qa_validate.py::test_qa_validate_accepts_dor_telemetry_without_task_id"
        - "tests/test_flow_audit.py::test_flow_audit_dor_telemetry_identity_and_exit_code_marker"
      run_result: "pass; added compatibility regression for qa-validate telemetry without task_id"
    - criterion: "AC4: The shared helper validates each telemetry status file contains an `exit_code:` marker, and both commands preserve existing exit-code behavior (`0` pass, `1` validation failure, `2` usage/file errors)."
      status: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_dor_telemetry_status_requires_exit_code_marker"
        - "tests/test_qa_validate.py::test_qa_validate_require_dor_telemetry_exits_2_without_handoff_or_task_id"
        - "tests/test_flow_audit.py::test_flow_audit_ac4_telemetry_status_requires_exit_code_marker"
      run_result: "pass; status marker and usage-exit coverage passed"
    - criterion: "AC5: Existing non-DoR behavior remains unchanged: qa-gate evidence parsing, checkpoint validation, memory-health validation, release-status checks, plan-file checks, credential handling, and deploy attestation are not refactored or semantically changed."
      status: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_passes_for_valid_gate_packet"
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry"
        - "tests/test_flow_audit.py::test_flow_audit_passes_for_valid_artifacts"
        - "tests/test_flow_audit.py::test_flow_audit_passes_with_memory_health_evidence_ok"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid"
        - "tests/test_flow_audit.py::test_flow_audit_ac5_sample_rate_skip_does_not_call_dor_helper"
      run_result: "pass; adjacent regression sweep passed"
  iterations: 1
  regression_checked: true
  remaining_gaps: []
  notes: "Applied one bounded QA fix in `src/canon_systems/qa_validate.py` plus a regression in `tests/test_qa_validate.py` so existing DoR telemetry that omits task_id remains valid for qa-validate. Ran `python3 -m pytest tests/test_qa_validate.py tests/test_flow_audit.py -q` -> 55 passed, and `python3 -m pytest tests/test_qa_validate.py tests/test_flow_audit.py tests/test_infra_layout.py -q` -> 81 passed."
END_GATE_RESULTS
