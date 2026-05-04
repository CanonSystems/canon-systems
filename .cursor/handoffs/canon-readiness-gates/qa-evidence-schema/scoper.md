HANDOFF_TO_CURSOR_PILOT
  scope_summary: Normalize `canon qa-validate` QA evidence handling so `covering_tests` entries are parsed only from the intended QA packet fields, support explicit evidence kinds (`pytest`, `manual`, `shell`, `browser`), and emit actionable diagnostics with qa-gate packet line numbers. Keep the change scoped to QA evidence normalization and diagnostics; do not refactor shared DoR validation, readiness policy, run-ledger schema, packet archive contracts, or the plan file.
  scope_packet:
    identifiers:
      handoff_id: "canon-readiness-gates"
      company_id: "IMC"
      repository_id: "innermost"
      plan_id: "canon_readiness_gates_c389cad8"
      task_id: "qa-evidence-schema"
      workstream_id: "qa-evidence-schema"
      repo_ref: "feature/canon-run-ledger-readiness@d3528041e391dc930c7634ff906a70eaa7561a14"
    story:
      title: "Normalize QA evidence labels and actionable qa-validate diagnostics"
      userValue: "Release orchestrators and reviewers get reliable merge-gate validation because QA evidence is typed, parsed from the correct fields, and failures point to the exact packet line to fix."
      acceptanceCriteria:
        - "AC1: `canon qa-validate` parses `covering_tests` evidence only from acceptance-criterion `covering_tests:` blocks, preserving existing unprefixed pytest refs such as `tests/test_qa_validate.py::test_name`."
        - "AC2: `covering_tests` entries support explicit evidence kind labels for `pytest`, `manual`, `shell`, and `browser`; unknown or empty kinds fail validation with a message listing the allowed kinds."
        - "AC3: `pytest` evidence validates the referenced test file exists relative to the repository root, while `manual`, `shell`, and `browser` evidence require non-empty evidence text but do not require a filesystem path."
        - "AC4: Validation failures include actionable qa-gate packet line numbers for missing `covering_tests`, malformed evidence entries, unknown evidence kinds, and missing pytest files."
        - "AC5: Existing `qa-validate` merge-gate behavior remains compatible: `--require-pass`, `--require-dor-telemetry`, `--require-checkpoints`, exit codes `0/1/2`, and current successful qa-gate packets still work."
    repository:
      primaryLanguages: ["Python", "Markdown", "HCL/Terraform"]
      testFramework: "pytest"
      relevantFiles:
        - "src/canon_systems/qa_validate.py"
        - "tests/test_qa_validate.py"
        - "src/canon_systems/cli.py"
    constraints:
      dependencies:
        - "Do not edit `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`."
        - "Do not refactor shared DoR validation; that is a later task."
        - "Do not change readiness policy, run-ledger schema, packet archive kind validation, state-api endpoints, or packet body storage behavior."
      mustNotBreak:
        - "`canon qa-validate --file <qa-gate.md> --require-pass` returns 0 for existing valid packets with unprefixed pytest refs."
        - "`canon qa-validate --require-dor-telemetry --handoff-id <id> --task-id <id>` still enforces DoR telemetry artifacts exactly as today."
        - "`canon qa-validate --require-checkpoints --handoff-id <id> --task-id <id>` still composes with pass and telemetry checks."
        - "Exit code semantics remain: 0 pass, 1 validation failure, 2 usage/configuration/missing GATE_RESULTS."
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "AC1: `canon qa-validate` parses `covering_tests` evidence only from acceptance-criterion `covering_tests:` blocks, preserving existing unprefixed pytest refs such as `tests/test_qa_validate.py::test_name`."
        implementation_targets: ["src/canon_systems/qa_validate.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_passes_for_valid_gate_packet", "tests/test_qa_validate.py::test_covering_tests_parser_ignores_non_covering_double_colon_list_items"]
      - criterion: "AC2: `covering_tests` entries support explicit evidence kind labels for `pytest`, `manual`, `shell`, and `browser`; unknown or empty kinds fail validation with a message listing the allowed kinds."
        implementation_targets: ["src/canon_systems/qa_validate.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_accepts_explicit_evidence_kinds", "tests/test_qa_validate.py::test_qa_validate_rejects_unknown_evidence_kind_with_allowed_kinds"]
      - criterion: "AC3: `pytest` evidence validates the referenced test file exists relative to the repository root, while `manual`, `shell`, and `browser` evidence require non-empty evidence text but do not require a filesystem path."
        implementation_targets: ["src/canon_systems/qa_validate.py"]
        verification_tests: ["tests/test_qa_validate.py::test_pytest_evidence_requires_existing_test_file", "tests/test_qa_validate.py::test_non_pytest_evidence_requires_non_empty_detail_only"]
      - criterion: "AC4: Validation failures include actionable qa-gate packet line numbers for missing `covering_tests`, malformed evidence entries, unknown evidence kinds, and missing pytest files."
        implementation_targets: ["src/canon_systems/qa_validate.py"]
        verification_tests: ["tests/test_qa_validate.py::test_missing_covering_tests_reports_line_number", "tests/test_qa_validate.py::test_malformed_evidence_reports_line_number", "tests/test_qa_validate.py::test_missing_pytest_file_diagnostic_includes_line_number"]
      - criterion: "AC5: Existing `qa-validate` merge-gate behavior remains compatible: `--require-pass`, `--require-dor-telemetry`, `--require-checkpoints`, exit codes `0/1/2`, and current successful qa-gate packets still work."
        implementation_targets: ["src/canon_systems/qa_validate.py", "tests/test_qa_validate.py", "src/canon_systems/cli.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_accepts_present_dor_telemetry_artifacts", "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry", "tests/test_qa_validate.py::test_qa_validate_fails_without_gate_block"]
    risks_and_assumptions:
      assumptions:
        - "Bare `tests/...::test_name` remains valid pytest evidence for backwards compatibility."
        - "Typed non-pytest evidence labels are metadata labels, not filesystem paths."
      openQuestions: []
END_HANDOFF_TO_CURSOR_PILOT
