GATE_RESULTS
  handoff_id: "canon-readiness-gates"
  verdict: PASS
  acceptance_criteria:
    - criterion: "AC1: `canon qa-validate` parses `covering_tests` evidence only from acceptance-criterion `covering_tests:` blocks, preserving existing unprefixed pytest refs such as `tests/test_qa_validate.py::test_name`."
      status: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_covering_tests_only_parsed_from_criterion_blocks"
        - "tests/test_qa_validate.py::test_covering_tests_preserves_unprefixed_pytest_refs"
      run_result: "pass: `python3 -m pytest tests/test_qa_validate.py -q` passed 22/22"
    - criterion: "AC2: `covering_tests` entries support explicit evidence kind labels for `pytest`, `manual`, `shell`, and `browser`; unknown or empty kinds fail validation with a message listing the allowed kinds."
      status: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_accepts_explicit_evidence_kinds"
        - "tests/test_qa_validate.py::test_unknown_covering_tests_kind_reports_allowed_kinds"
        - "tests/test_qa_validate.py::test_empty_covering_tests_kind_reports_allowed_kinds"
      run_result: "pass: `python3 -m pytest tests/test_qa_validate.py -q` passed 22/22"
    - criterion: "AC3: `pytest` evidence validates the referenced test file exists relative to the repository root, while `manual`, `shell`, and `browser` evidence require non-empty evidence text but do not require a filesystem path."
      status: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_empty_manual_shell_browser_evidence_fails_with_line"
        - "tests/test_qa_validate.py::test_pytest_missing_file_reports_packet_line"
        - "tests/test_qa_validate.py::test_qa_validate_accepts_explicit_evidence_kinds"
      run_result: "pass: `python3 -m pytest tests/test_qa_validate.py -q` passed 22/22"
    - criterion: "AC4: Validation failures include actionable qa-gate packet line numbers for missing `covering_tests`, malformed evidence entries, unknown evidence kinds, and missing pytest files."
      status: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_criterion_missing_covering_tests_reports_line"
        - "tests/test_qa_validate.py::test_empty_covering_tests_list_reports_key_line"
        - "tests/test_qa_validate.py::test_malformed_covering_tests_entry_reports_line"
        - "tests/test_qa_validate.py::test_unknown_covering_tests_kind_reports_allowed_kinds"
        - "tests/test_qa_validate.py::test_pytest_missing_file_reports_packet_line"
      run_result: "pass: added malformed-entry coverage; `python3 -m pytest tests/test_qa_validate.py -q` passed 22/22"
    - criterion: "AC5: Existing `qa-validate` merge-gate behavior remains compatible: `--require-pass`, `--require-dor-telemetry`, `--require-checkpoints`, exit codes `0/1/2`, and current successful qa-gate packets still work."
      status: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_passes_for_valid_gate_packet"
        - "tests/test_qa_validate.py::test_qa_validate_accepts_present_dor_telemetry_artifacts"
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry"
        - "tests/test_qa_validate.py::test_qa_validate_fails_without_gate_block"
      run_result: "pass: `python3 -m pytest tests/test_qa_validate.py tests/test_infra_layout.py -q` passed 48/48"
  iterations: 0
  regression_checked: true
  remaining_gaps: []
  notes: "Focused QA and adjacent regression suites passed. Graph retrieval degraded with SSL certificate verification failure, and checkpoint read/write was skipped because `CANON_STATE_API_URL` is unset; QA capture completed successfully."
END_GATE_RESULTS
