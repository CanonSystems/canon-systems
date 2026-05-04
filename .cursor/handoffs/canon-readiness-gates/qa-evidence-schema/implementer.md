HANDOFF_TO_QA
  handoff_id: "canon-readiness-gates"
  task_id: "qa-evidence-schema"
  acceptance_criteria_covered:
    - criterion: "AC1: `canon qa-validate` parses `covering_tests` evidence only from acceptance-criterion `covering_tests:` blocks, preserving existing unprefixed pytest refs such as `tests/test_qa_validate.py::test_name`."
      evidence_files:
        - "src/canon_systems/qa_validate.py"
        - "tests/test_qa_validate.py"
      evidence_tests:
        - "tests/test_qa_validate.py::test_covering_tests_only_parsed_from_criterion_blocks"
        - "tests/test_qa_validate.py::test_covering_tests_preserves_unprefixed_pytest_refs"
    - criterion: "AC2: `covering_tests` entries support explicit evidence kind labels for `pytest`, `manual`, `shell`, and `browser`; unknown or empty kinds fail validation with a message listing the allowed kinds."
      evidence_files:
        - "src/canon_systems/qa_validate.py"
        - "tests/test_qa_validate.py"
      evidence_tests:
        - "tests/test_qa_validate.py::test_unknown_covering_tests_kind_reports_allowed_kinds"
        - "tests/test_qa_validate.py::test_empty_covering_tests_kind_reports_allowed_kinds"
    - criterion: "AC3: `pytest` evidence validates the referenced test file exists relative to the repository root, while `manual`, `shell`, and `browser` evidence require non-empty evidence text but do not require a filesystem path."
      evidence_files:
        - "src/canon_systems/qa_validate.py"
      evidence_tests:
        - "tests/test_qa_validate.py::test_empty_manual_shell_browser_evidence_fails_with_line"
        - "tests/test_qa_validate.py::test_pytest_missing_file_reports_packet_line"
    - criterion: "AC4: Validation failures include actionable qa-gate packet line numbers for missing `covering_tests`, malformed evidence entries, unknown evidence kinds, and missing pytest files."
      evidence_files:
        - "src/canon_systems/qa_validate.py"
      evidence_tests:
        - "tests/test_qa_validate.py::test_criterion_missing_covering_tests_reports_line"
        - "tests/test_qa_validate.py::test_empty_covering_tests_list_reports_key_line"
        - "tests/test_qa_validate.py::test_no_covering_tests_anywhere_reports_acceptance_criteria_line"
    - criterion: "AC5: Existing `qa-validate` merge-gate behavior remains compatible: `--require-pass`, `--require-dor-telemetry`, `--require-checkpoints`, exit codes `0/1/2`, and current successful qa-gate packets still work."
      evidence_files:
        - "src/canon_systems/qa_validate.py"
        - "tests/test_qa_validate.py"
      evidence_tests:
        - "tests/test_qa_validate.py::test_qa_validate_accepts_present_dor_telemetry_artifacts"
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry"
        - "tests/test_qa_validate.py::test_qa_validate_fails_without_gate_block"
  summary: "Scoped `qa-validate` evidence parsing to `covering_tests` blocks, added typed evidence labels for pytest/manual/shell/browser, validated pytest paths separately from non-file evidence, and added line-numbered diagnostics."
  decisions:
    - "Bare `tests/...::test_name` remains implicit pytest evidence for backward compatibility."
    - "Non-pytest evidence labels require detail text but are not treated as paths."
  next_actions:
    - "Extract shared DoR telemetry validation in the next task."
  open_questions: []
END_HANDOFF_TO_QA
