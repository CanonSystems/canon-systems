HANDOFF_TO_CURSOR_PILOT
  scope_summary: Extract the duplicated HANDOFF_NOT_READY DoR telemetry validation from `qa_validate` and `flow_audit` into a shared Python helper so both commands enforce the same artifact contract. Keep the task tightly scoped to rejection telemetry: matching rejection-packet stems, telemetry JSON/status presence, status `exit_code:` markers, `handoff_id` checks, and `task_id` checks where the payload provides or the caller requires task identity; do not touch credential or deploy attestation logic.
  scope_packet:
    identifiers:
      handoff_id: "canon-readiness-gates"
      company_id: "CSC"
      repository_id: "canon-systems"
      plan_id: "canon_readiness_gates_c389cad8"
      task_id: "dor-shared-validator"
      workstream_id: "dor-shared-validator"
      branch: "feature/canon-run-ledger-readiness"
      repo_ref: "d3528041e391dc930c7634ff906a70eaa7561a14"
    story:
      title: "Extract shared DoR telemetry validation"
      userValue: "Release governance benefits because qa-validate and flow-audit will enforce one consistent DoR telemetry artifact contract instead of drifting across duplicated implementations."
      acceptanceCriteria:
        - "AC1: `canon qa-validate --require-dor-telemetry` and `canon flow-audit` both call a shared DoR telemetry validation helper rather than maintaining separate rejection telemetry validation loops."
        - "AC2: For every `.cursor/handoffs/<handoff_id>/<task_id>/handoff-not-ready/<stem>.md` packet, both commands require `.cursor/handoffs/<handoff_id>/<task_id>/dor-failure/<stem>.json` and `<stem>.status`, reject invalid/non-object telemetry JSON, and report missing artifacts using actionable paths."
        - "AC3: The shared helper validates telemetry identity consistently: payload `handoff_id` must match the CLI handoff id, `stage` must be non-empty, and `task_id` must match when present or when the caller opts into requiring task identity."
        - "AC4: The shared helper validates each telemetry status file contains an `exit_code:` marker, and both commands preserve existing exit-code behavior (`0` pass, `1` validation failure, `2` usage/file errors)."
        - "AC5: Existing non-DoR behavior remains unchanged: qa-gate evidence parsing, checkpoint validation, memory-health validation, release-status checks, plan-file checks, credential handling, and deploy attestation are not refactored or semantically changed."
    repository:
      primaryLanguages: ["Python", "Markdown", "HCL/Terraform"]
      testFramework: "pytest"
      relevantFiles:
        - "src/canon_systems/qa_validate.py"
        - "src/canon_systems/flow_audit.py"
        - "src/canon_systems/dor_telemetry.py"
        - "tests/test_qa_validate.py"
        - "tests/test_flow_audit.py"
    constraints:
      dependencies:
        - "`canon qa-validate` and `canon flow-audit` command wiring must remain unchanged."
        - "Existing `repo_root()` behavior and `CANON_SYSTEMS_REPO_ROOT` test override must continue to work."
      mustNotBreak:
        - "Do not edit `.cursor/plans/canon_readiness_gates_c389cad8.plan.md`."
        - "Do not change credential, secret, deploy attestation, memory-health, run-ledger, packet-archive, or readiness evaluation behavior."
        - "`canon qa-validate --file <qa-gate.md> --require-pass` must still pass for valid qa-gate packets with unprefixed pytest evidence."
        - "`canon qa-validate --file <qa-gate.md> --require-pass --require-dor-telemetry --handoff-id <id> --task-id <id>` must still pass for valid existing DoR telemetry artifacts that include handoff id and stage but omit task id, unless a new caller explicitly opts into requiring task id."
        - "`canon flow-audit --handoff-id <id> --task-id <id>` must still validate required artifacts and sample-rate behavior exactly as before."
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "AC1: `canon qa-validate --require-dor-telemetry` and `canon flow-audit` both call a shared DoR telemetry validation helper rather than maintaining separate rejection telemetry validation loops."
        implementation_targets: ["src/canon_systems/dor_telemetry.py", "src/canon_systems/qa_validate.py", "src/canon_systems/flow_audit.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_uses_shared_dor_telemetry_validation", "tests/test_flow_audit.py::test_flow_audit_uses_shared_dor_telemetry_validation"]
      - criterion: "AC2: For every `.cursor/handoffs/<handoff_id>/<task_id>/handoff-not-ready/<stem>.md` packet, both commands require `.cursor/handoffs/<handoff_id>/<task_id>/dor-failure/<stem>.json` and `<stem>.status`, reject invalid/non-object telemetry JSON, and report missing artifacts using actionable paths."
        implementation_targets: ["src/canon_systems/dor_telemetry.py", "tests/test_qa_validate.py", "tests/test_flow_audit.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_fails_when_rejection_telemetry_missing", "tests/test_flow_audit.py::test_flow_audit_fails_when_rejection_missing_telemetry", "tests/test_qa_validate.py::test_qa_validate_rejects_invalid_dor_telemetry_json", "tests/test_flow_audit.py::test_flow_audit_rejects_invalid_dor_telemetry_json"]
      - criterion: "AC3: The shared helper validates telemetry identity consistently: payload `handoff_id` must match the CLI handoff id, `stage` must be non-empty, and `task_id` must match when present or when the caller opts into requiring task identity."
        implementation_targets: ["src/canon_systems/dor_telemetry.py", "tests/test_qa_validate.py", "tests/test_flow_audit.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_rejects_dor_telemetry_handoff_id_mismatch", "tests/test_flow_audit.py::test_flow_audit_rejects_dor_telemetry_handoff_id_mismatch", "tests/test_qa_validate.py::test_qa_validate_rejects_dor_telemetry_task_id_mismatch_when_present", "tests/test_flow_audit.py::test_flow_audit_rejects_dor_telemetry_task_id_mismatch_when_present"]
      - criterion: "AC4: The shared helper validates each telemetry status file contains an `exit_code:` marker, and both commands preserve existing exit-code behavior (`0` pass, `1` validation failure, `2` usage/file errors)."
        implementation_targets: ["src/canon_systems/dor_telemetry.py", "src/canon_systems/qa_validate.py", "src/canon_systems/flow_audit.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_rejects_dor_telemetry_status_without_exit_code", "tests/test_flow_audit.py::test_flow_audit_rejects_dor_telemetry_status_without_exit_code", "tests/test_qa_validate.py::test_qa_validate_require_dor_telemetry_exits_2_without_handoff_or_task_id"]
      - criterion: "AC5: Existing non-DoR behavior remains unchanged: qa-gate evidence parsing, checkpoint validation, memory-health validation, release-status checks, plan-file checks, credential handling, and deploy attestation are not refactored or semantically changed."
        implementation_targets: ["src/canon_systems/qa_validate.py", "src/canon_systems/flow_audit.py", "tests/test_qa_validate.py", "tests/test_flow_audit.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_passes_for_valid_gate_packet", "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry", "tests/test_flow_audit.py::test_flow_audit_passes_for_valid_artifacts", "tests/test_flow_audit.py::test_flow_audit_passes_with_memory_health_evidence_ok", "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid"]
    risks_and_assumptions:
      assumptions:
        - "A small helper module such as `src/canon_systems/dor_telemetry.py` is acceptable for shared CLI validation logic."
        - "Task-id telemetry should be enforced on mismatch when present and optionally required by helper configuration, avoiding a compatibility break for existing DoR telemetry JSON that currently records handoff id and stage only."
      openQuestions: []
END_HANDOFF_TO_CURSOR_PILOT
