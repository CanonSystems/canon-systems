HANDOFF_TO_QA_SHARD
shard_id: ws2
task_id: qa-evidence-schema
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
branch: feature/canon-run-ledger-readiness

summary: |
  Implemented ws2 evidence rules and line-number diagnostics in qa_validate: per-criterion
  covering_tests structure errors (missing key or empty list), non-pytest kinds require
  non-empty text, pytest evidence resolves paths against repo root with errors at the
  covering_tests item line, and aggregate empty packets surface the acceptance_criteria line.
  Preserved merge-gate flags and exit semantics. Graph/checkpoint retrieval degraded in this
  session (transport); validation used file reads only.

artifacts:
  - src/canon_systems/qa_validate.py
  - tests/test_qa_validate.py

verification:
  command: "python3 -m pytest tests/test_qa_validate.py -q"
  result: "21 passed"

acceptance_criteria:
  - id: AC1
    status: SATISFIED
    evidence:
      - "tests/test_qa_validate.py (passing regression)"
      - "src/canon_systems/qa_validate.py::_extract_covering_tests_entries"
  - id: AC2
    status: SATISFIED
    evidence:
      - "tests/test_qa_validate.py::test_unknown_covering_tests_kind_reports_allowed_kinds"
      - "tests/test_qa_validate.py::test_empty_covering_tests_kind_reports_allowed_kinds"
  - id: AC3
    status: SATISFIED
    evidence:
      - "src/canon_systems/qa_validate.py::_collect_errors (manual/shell/browser non-empty; pytest path exists)"
      - "tests/test_qa_validate.py::test_empty_manual_shell_browser_evidence_fails_with_line"
      - "tests/test_qa_validate.py::test_pytest_missing_file_reports_packet_line"
  - id: AC4
    status: SATISFIED
    evidence:
      - "src/canon_systems/qa_validate.py::_finalize_criterion_covering_tests_structure"
      - "tests/test_qa_validate.py::test_criterion_missing_covering_tests_reports_line"
      - "tests/test_qa_validate.py::test_empty_covering_tests_list_reports_key_line"
      - "tests/test_qa_validate.py::test_no_covering_tests_anywhere_reports_acceptance_criteria_line"
  - id: AC5
    status: SATISFIED
    evidence:
      - "tests/test_qa_validate.py (require-pass, require-dor-telemetry, require-checkpoints, exit 2 cases)"

notes: |
  Retrieval: `canon graph query` failed with SSL certificate verify failure (exit 5);
  `canon checkpoint read` failed with connection refused to localhost state-api (exit 5).
  Implemented using file reads of src/canon_systems/qa_validate.py and tests only.
  retrieval_breakdown (canonical event shape): graph tokens_in/out 0/0; state 0/0;
  canonical 0/0; file ~8k/4k estimated — emit via build_retrieval_breakdown_event in
  orchestrator if required for canon report.

END_HANDOFF_TO_QA_SHARD
