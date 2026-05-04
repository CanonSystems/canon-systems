HANDOFF_TO_QA_SHARD
shard_id: ws2
task_id: run-ledger
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
branch: feature/canon-run-ledger-readiness

implementation_summary: |
  WS2 adds STATE_RUN_LEDGER_TABLE_NAME, RunLedgerStore (separate DynamoDB table from
  checkpoint StateStore), PUT/GET /state/run-ledger with moto coverage, Terraform
  aws_dynamodb_table.run_ledger (${name_prefix}-canon-run-ledger) plus root outputs
  state_run_ledger_table_name/arn. Idempotent PUT replays compare via
  validate_run_ledger_record on both sides; conflicting same ledger_run_id returns 409.
  Packet bodies are rejected by shared validators; archive_refs persist by reference only.

artifacts:
  - backend/state-api/state_api/config.py
  - backend/state-api/state_api/storage.py
  - backend/state-api/state_api/run_ledger.py
  - backend/state-api/state_api/main.py
  - backend/state-api/tests/conftest.py
  - backend/state-api/tests/test_run_ledger.py
  - infra/terraform/modules/dynamodb-canon-state/main.tf
  - infra/terraform/modules/dynamodb-canon-state/outputs.tf
  - infra/terraform/outputs.tf
  - tests/test_infra_layout.py

acceptance_criteria:
  - id: AC2
    status: SATISFIED
    evidence:
      - "Distinct Terraform table run_ledger vs this (canon-state); RunLedgerStore targets STATE_RUN_LEDGER_TABLE_NAME only; ledger pk ends with #run_ledger; no lease_* attributes on ledger writes."
      - "tests/test_run_ledger.py::test_ledger_row_not_in_checkpoint_table"
  - id: AC3
    status: SATISFIED
    evidence:
      - "PUT/GET /state/run-ledger; structured JSON errors (400 validation, 404 not_found, 409 conflict, 503 table unset); checkpoint/archive routers unchanged in behavior."
      - "tests/test_run_ledger.py (round_trip, 503, query)"
  - id: AC4
    status: SATISFIED
    evidence:
      - "validate_run_ledger_record + archive_record_to_ledger_reference on ingest; test_archive_refs_by_reference_only; Dynamo item has no body fields."
  - id: AC5
    status: SATISFIED
    evidence:
      - "Records carry validation_outcomes, commits, pull_request, deployment per shared schema; exercised in test_idempotent_put_same_payload (qa_validate slot)."
  - id: AC8
    status: SATISFIED (ws2 scope)
    evidence:
      - "moto dual-table setup; key isolation; idempotent vs conflict puts; handoff query filter; forbid body_base64 on ledger."
      - "tests/test_run_ledger.py; backend/state-api/tests full suite 39 passed"
  - id: graph
    status: DEGRADED
    evidence:
      - "canon graph query exited 5 (SSL CERTIFICATE_VERIFY_FAILED); file + canonical context used instead."

pytest: |
  backend/state-api: 39 passed (tests/)
  repo tests/test_run_ledger.py: 10 passed
  tests/test_infra_layout.py: root_exposes_state_table_outputs + run_ledger wiring assertions

retrieval_breakdown:
  phase: implementer
  sources:
    graph: { tokens_in: 0, tokens_out: 0 }
    state: { tokens_in: 0, tokens_out: 0 }
    canonical: { tokens_in: 350, tokens_out: 0 }
    file: { tokens_in: 18500, tokens_out: 0 }
  notes: approximate token estimates from tool reads; graph skipped on transport/SSL failure.

END_HANDOFF_TO_QA_SHARD
