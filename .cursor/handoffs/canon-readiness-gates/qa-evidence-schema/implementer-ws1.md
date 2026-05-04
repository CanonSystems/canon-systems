HANDOFF_TO_QA_SHARD
shard_id: ws1
task_id: qa-evidence-schema
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
branch: feature/canon-run-ledger-readiness

summary: |
  Implemented scoped covering_tests extraction from criterion blocks and evidence kind normalization in qa_validate (ws1). Extended tests for AC1 (scoped parsing + unprefixed pytest refs) and AC2 (unknown/empty kinds + allowed kinds text). Left broader diagnostics / non-pytest evidence rules to ws2.

artifacts:
  - src/canon_systems/qa_validate.py
  - tests/test_qa_validate.py

verification:
  command: "python3 -m pytest tests/test_qa_validate.py -q"
  result: "16 passed"

acceptance_criteria:
  - id: AC1
    status: SATISFIED
    evidence:
      - "src/canon_systems/qa_validate.py::_extract_covering_tests_entries"
      - "tests/test_qa_validate.py::test_covering_tests_only_parsed_from_criterion_blocks"
      - "tests/test_qa_validate.py::test_covering_tests_preserves_unprefixed_pytest_refs"
  - id: AC2
    status: SATISFIED
    evidence:
      - "src/canon_systems/qa_validate.py::_ALLOWED_COVERING_TEST_KINDS"
      - "tests/test_qa_validate.py::test_unknown_covering_tests_kind_reports_allowed_kinds"
      - "tests/test_qa_validate.py::test_empty_covering_tests_kind_reports_allowed_kinds"
END_HANDOFF_TO_QA_SHARD
