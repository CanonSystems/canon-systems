HANDOFF_TO_QA
  handoff_id: "canon-readiness-gates"
  task_id: "run-ledger"
  acceptance_criteria_covered:
    - criterion: "AC1: A versioned run-ledger record schema is implemented and documented with tenant scope, plan_id, task_id, workstream_id, handoff_id, phase, phase_status/verdict, archived packet refs, evidence refs, validation outcomes, commit refs, deployment refs, timestamps, agent_run_id/actor_id when available, and source event ids."
      evidence_files:
        - "backend/shared/canon_backend_shared/run_ledger.py"
        - "src/canon_systems/run_ledger.py"
      evidence_tests:
        - "tests/test_run_ledger.py::test_ac1_validate_minimal_round_trip"
        - "tests/test_run_ledger.py::test_ac1_optional_verdict_validation_outcomes_commits_pr_deployment"
    - criterion: "AC2: Run-ledger persistence is DynamoDB-backed but logically separate from mutable checkpoint/lease state, with distinct table configuration or clearly namespaced storage that does not read or mutate checkpoint lease attributes."
      evidence_files:
        - "backend/state-api/state_api/run_ledger.py"
        - "backend/state-api/state_api/config.py"
        - "infra/terraform/modules/dynamodb-canon-state/main.tf"
      evidence_tests:
        - "tests/test_run_ledger.py::test_checkpoint_vs_ledger_keys_never_collide"
        - "backend/state-api/tests/test_run_ledger.py::test_ledger_row_not_in_checkpoint_table"
    - criterion: "AC3: State-api exposes an additive run-ledger write/read surface suitable for agents and later readiness checks, returning structured ledger records and actionable errors while preserving existing checkpoint, lease, and archive APIs."
      evidence_files:
        - "backend/state-api/state_api/main.py"
        - "backend/state-api/state_api/run_ledger.py"
        - "backend/state-api/state_api/models.py"
      evidence_tests:
        - "backend/state-api/tests/test_run_ledger.py::test_put_run_ledger_writes_record"
        - "backend/state-api/tests/test_run_ledger.py::test_get_run_ledger_queries_by_scope"
    - criterion: "AC4: Ledger writes can ingest packet-archive records by reference, including `s3_uri`, `s3_key`, `content_sha256`, `artifact_kind`, `phase`, `status/outcome`, and archive event id when available, without copying packet bodies into DynamoDB."
      evidence_files:
        - "backend/shared/canon_backend_shared/run_ledger.py"
        - "backend/state-api/state_api/run_ledger.py"
      evidence_tests:
        - "tests/test_run_ledger.py::test_ac4_archive_reference_requires_digest_and_kind"
        - "backend/state-api/tests/test_run_ledger.py::test_run_ledger_rejects_packet_body_fields"
    - criterion: "AC5: The ledger can represent validation outcomes for `qa-validate`, `flow-audit`, memory-health, CI, deployment smoke checks, merge readiness, commit SHA(s), PR URL, deployment environment, and deployment status in a shape that later `canon readiness check` can consume."
      evidence_files:
        - "backend/shared/canon_backend_shared/run_ledger.py"
        - "src/canon_systems/run_ledger.py"
      evidence_tests:
        - "tests/test_run_ledger.py::test_ac5_unknown_validation_slot_rejected"
        - "backend/state-api/tests/test_run_ledger.py::test_run_ledger_accepts_gate_outcomes_and_deployment_refs"
    - criterion: "AC6: A local CLI/helper path can create or dry-run run-ledger records from explicit JSON/archive metadata inputs using tenant and task identifiers, but this task does not implement `canon readiness check` or enforce readiness policy."
      evidence_files:
        - "src/canon_systems/cli.py"
        - "src/canon_systems/run_ledger.py"
        - "src/canon_systems/run_ledger_cli.py"
      evidence_tests:
        - "tests/test_run_ledger_cli.py::test_ac6_dry_run_prints_normalized_record"
        - "tests/test_run_ledger_cli.py::test_run_ledger_post_branch_success"
    - criterion: "AC7: Documentation explains the boundary between packet archive, run ledger, mutable checkpoint/lease state, and later readiness checks, including required environment variables and expected write/query flow."
      evidence_files:
        - "backend/state-api/README.md"
        - "docs/SYSTEM-WORKFLOW.md"
        - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
        - "README.md"
        - "CHANGELOG.md"
      evidence_tests:
        - "tests/test_run_ledger_cli.py::test_canon_main_dispatches_run_ledger_dry_run"
    - criterion: "AC8: Tests cover schema validation, DynamoDB key isolation, idempotent or conflict-safe writes, query behavior by plan/task/handoff, archive-reference ingestion, no packet body persistence, state-api behavior with moto DynamoDB, and CLI/helper dry-run behavior without live AWS."
      evidence_files:
        - "tests/test_run_ledger.py"
        - "tests/test_run_ledger_cli.py"
        - "backend/state-api/tests/test_run_ledger.py"
      evidence_tests:
        - "tests/test_run_ledger.py::test_checkpoint_vs_ledger_keys_never_collide"
        - "backend/state-api/tests/test_run_ledger.py::test_idempotent_put_same_payload"
        - "tests/test_run_ledger_cli.py::test_post_run_ledger_to_state_api_puts_json"
  summary: "Added a shared run-ledger schema/key/reference layer, DynamoDB-backed state-api run-ledger PUT/GET endpoints with a separate table, local `canon run-ledger` dry-run/post helper, Terraform outputs, and docs describing the archive/ledger/checkpoint/readiness boundary."
  decisions:
    - "Run-ledger records are separate from checkpoint/lease rows and store archive/evidence references only, not packet bodies."
    - "The CLI writes to `PUT /state/run-ledger`, matching the state-api router and preserving readiness checks as a later task."
  next_actions:
    - "Implement `canon readiness check` as a consumer of archive + run-ledger records in the next task."
  open_questions: []
END_HANDOFF_TO_QA
