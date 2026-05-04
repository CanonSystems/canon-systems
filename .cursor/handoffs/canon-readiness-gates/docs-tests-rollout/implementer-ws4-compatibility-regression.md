HANDOFF_TO_QA_SHARD
shard_id: ws4-compatibility-regression
task_id: docs-tests-rollout
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8

summary: |
  Regression-locked storage and diagnostic boundaries without production behavior changes:
  readiness stays fetch-only, ledger archive refs strip non-allowlisted credential-like fields,
  packet_archived events use a strict allowlist, and docs preserve local handoffs plus separate
  archive, ledger, and checkpoint stores.

acceptance_criteria:
  - id: AC4
    status: satisfied
    evidence:
      - "tests/test_readiness.py::test_public_docs_retain_storage_boundary_contract"
      - "Focused readiness/run-ledger/packet-archive suite passed."
  - id: AC5
    status: satisfied
    evidence:
      - "tests/test_readiness.py read-only diagnostics and no archive/ledger PUT imports."
      - "tests/test_run_ledger.py metadata-only archive refs and distinct checkpoint keys."
      - "tests/test_packet_archive.py packet_archived event allowlist and body/credential omissions."
      - "docs/SYSTEM-WORKFLOW.md and docs/MEMORY-PLATFORM-PLAN.md boundary language."

artifacts_modified:
  - docs/SYSTEM-WORKFLOW.md
  - docs/MEMORY-PLATFORM-PLAN.md
  - tests/test_readiness.py
  - tests/test_run_ledger.py
  - tests/test_packet_archive.py

verification:
  - "python3 -m pytest tests/test_readiness.py tests/test_run_ledger.py tests/test_packet_archive.py -q -> 42 passed"

notes: |
  Graph retrieval degraded and state checkpoint read was skipped/degraded. The reference plan file was not edited.

END_HANDOFF_TO_QA_SHARD
