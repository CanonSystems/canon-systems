GATE_RESULTS
  handoff_id: "canon-readiness-gates"
  verdict: PASS
  acceptance_criteria:
    - criterion: "AC1: A versioned run-ledger record schema is implemented and documented with tenant scope, plan_id, task_id, workstream_id, handoff_id, phase, phase_status/verdict, archived packet refs, evidence refs, validation outcomes, commit refs, deployment refs, timestamps, agent_run_id/actor_id when available, and source event ids."
      status: PASS
      covering_tests:
        - "tests/test_run_ledger.py::test_ac1_validate_minimal_round_trip"
        - "tests/test_run_ledger.py::test_ac1_optional_verdict_validation_outcomes_commits_pr_deployment"
      run_result: "pass; covered by focused pytest and full regression"
    - criterion: "AC2: Run-ledger persistence is DynamoDB-backed but logically separate from mutable checkpoint/lease state, with distinct table configuration or clearly namespaced storage that does not read or mutate checkpoint lease attributes."
      status: PASS
      covering_tests:
        - "tests/test_run_ledger.py::test_checkpoint_vs_ledger_keys_never_collide"
        - "backend/state-api/tests/test_run_ledger.py::test_ledger_row_not_in_checkpoint_table"
      run_result: "pass; separate table/key isolation verified with moto"
    - criterion: "AC3: State-api exposes an additive run-ledger write/read surface suitable for agents and later readiness checks, returning structured ledger records and actionable errors while preserving existing checkpoint, lease, and archive APIs."
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_run_ledger.py::test_put_get_round_trip"
        - "backend/state-api/tests/test_run_ledger.py::test_query_by_scope_and_handoff_filter"
        - "backend/state-api/tests/test_run_ledger.py::test_run_ledger_table_unset_returns_503"
      run_result: "pass; PUT/GET/query/error paths verified"
    - criterion: "AC4: Ledger writes can ingest packet-archive records by reference, including `s3_uri`, `s3_key`, `content_sha256`, `artifact_kind`, `phase`, `status/outcome`, and archive event id when available, without copying packet bodies into DynamoDB."
      status: PASS
      covering_tests:
        - "tests/test_run_ledger.py::test_ac4_archive_reference_requires_digest_and_kind"
        - "tests/test_run_ledger.py::test_ac4_rejects_body_like_fields_on_archive"
        - "backend/state-api/tests/test_run_ledger.py::test_archive_refs_by_reference_only"
        - "backend/state-api/tests/test_run_ledger.py::test_reject_body_field_on_ledger"
      run_result: "pass; archive refs remain metadata-only and body fields are rejected"
    - criterion: "AC5: The ledger can represent validation outcomes for `qa-validate`, `flow-audit`, memory-health, CI, deployment smoke checks, merge readiness, commit SHA(s), PR URL, deployment environment, and deployment status in a shape that later `canon readiness check` can consume."
      status: PASS
      covering_tests:
        - "tests/test_run_ledger.py::test_ac1_optional_verdict_validation_outcomes_commits_pr_deployment"
        - "tests/test_run_ledger.py::test_ac5_unknown_validation_slot_rejected"
        - "backend/state-api/tests/test_run_ledger.py::test_idempotent_put_same_payload"
      run_result: "pass; supported gate slots, commit refs, PR, and deployment refs verified"
    - criterion: "AC6: A local CLI/helper path can create or dry-run run-ledger records from explicit JSON/archive metadata inputs using tenant and task identifiers, but this task does not implement `canon readiness check` or enforce readiness policy."
      status: PASS
      covering_tests:
        - "tests/test_run_ledger_cli.py::test_ac6_dry_run_prints_normalized_record"
        - "tests/test_run_ledger_cli.py::test_ac6_merge_archive_json_adds_refs"
        - "tests/test_run_ledger_cli.py::test_post_run_ledger_to_state_api_puts_json"
        - "tests/test_run_ledger_cli.py::test_run_ledger_post_branch_success"
        - "tests/test_run_ledger_cli.py::test_canon_main_dispatches_run_ledger_dry_run"
      run_result: "pass; dry-run and mocked state-api PUT paths verified; source search found no readiness command implementation"
    - criterion: "AC7: Documentation explains the boundary between packet archive, run ledger, mutable checkpoint/lease state, and later readiness checks, including required environment variables and expected write/query flow."
      status: PASS
      covering_tests:
        - "tests/test_run_ledger_cli.py::test_canon_main_dispatches_run_ledger_dry_run"
        - "tests/test_run_ledger.py::test_checkpoint_vs_ledger_keys_never_collide"
      run_result: "pass; docs describe STATE_RUN_LEDGER_TABLE_NAME, archive/ledger/checkpoint boundaries, and later readiness deferral"
    - criterion: "AC8: Tests cover schema validation, DynamoDB key isolation, idempotent or conflict-safe writes, query behavior by plan/task/handoff, archive-reference ingestion, no packet body persistence, state-api behavior with moto DynamoDB, and CLI/helper dry-run behavior without live AWS."
      status: PASS
      covering_tests:
        - "tests/test_run_ledger.py::test_checkpoint_vs_ledger_keys_never_collide"
        - "backend/state-api/tests/test_run_ledger.py::test_idempotent_put_same_payload"
        - "backend/state-api/tests/test_run_ledger.py::test_put_conflict_same_run_id_different_payload"
        - "backend/state-api/tests/test_run_ledger.py::test_query_by_scope_and_handoff_filter"
        - "tests/test_run_ledger_cli.py::test_ac6_dry_run_prints_normalized_record"
      run_result: "pass; focused suites, archive regressions, full pytest, and smoke-test passed"
  iterations: 0
  regression_checked: true
  remaining_gaps: []
  notes: "No bounded implementation fixes were required. Test evidence: `pytest backend/state-api/tests/test_run_ledger.py -q` 8 passed; `pytest tests/test_run_ledger.py tests/test_run_ledger_cli.py -q` 19 passed; archive regression sets 16 and 28 passed; `pytest -q` 603 passed; `bash scripts/smoke-test.sh` ALL STAGES PASSED. Canon capture retried after `canon secrets` but AWS credentials were unavailable; retrieval telemetry was emitted locally."
END_GATE_RESULTS
