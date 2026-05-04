HANDOFF_TO_QA
  handoff_id: "canon-readiness-gates"
  task_id: "readiness-contract"
  acceptance_criteria_covered:
    - criterion: "AC1: The public CLI exposes `canon readiness check` with required tenant/task scope flags (`--company-id`, `--repository-id`, `--plan-id`, `--task-id`, `--workstream-id`, `--handoff-id`) plus optional `--ledger-run-id`, `--state-api-url`, `--limit`, `--output`, and `--quiet` flags."
      evidence_files:
        - "src/canon_systems/readiness_cli.py"
        - "src/canon_systems/cli.py"
      evidence_tests:
        - "tests/test_readiness_cli.py::test_ac1_requires_scope_flags"
        - "tests/test_readiness_cli.py::test_readiness_check_help_documents_flags"
    - criterion: "AC2: The readiness implementation queries `GET /state/run-ledger` using the existing run-ledger API, supports both latest scoped query and explicit `ledger_run_id` lookup, and handles state-api 400/404/503/network failures with actionable errors and stable exit codes."
      evidence_files:
        - "src/canon_systems/readiness.py"
        - "src/canon_systems/run_ledger.py"
        - "src/canon_systems/readiness_cli.py"
      evidence_tests:
        - "tests/test_readiness.py::test_fetch_readiness_records_queries_scope_endpoint"
        - "tests/test_readiness.py::test_fetch_readiness_record_queries_explicit_ledger_run_id"
        - "tests/test_readiness_cli.py::test_ac2_query_errors_exit_2"
    - criterion: "AC3: Readiness evaluation derives its report from run-ledger records and archive refs only, verifying the presence/status of required phase packet archive refs (`scoper`, `cursor-pilot`, `qa-gate`, `release-status`, and implementer or implementer shard evidence where present) without reading packet bodies or storing bodies in the snapshot."
      evidence_files:
        - "src/canon_systems/readiness.py"
      evidence_tests:
        - "tests/test_readiness.py::test_readiness_passes_with_required_phase_archive_refs"
        - "tests/test_readiness.py::test_readiness_fails_when_required_phase_ref_missing"
        - "tests/test_readiness.py::test_readiness_snapshot_omits_body_fields"
    - criterion: "AC4: The readiness report summarizes existing validation outcome slots from the run ledger (`qa_validate`, `flow_audit`, `memory_health`, `ci`, `deployment_smoke`, `merge_readiness`), commit refs, PR refs, and deployment refs when present, but does not implement new QA evidence normalization, credential attestation, shared DoR validation, or deploy attestation rules."
      evidence_files:
        - "src/canon_systems/readiness.py"
        - "docs/SYSTEM-WORKFLOW.md"
      evidence_tests:
        - "tests/test_readiness.py::test_readiness_summarizes_existing_validation_outcomes"
        - "tests/test_readiness.py::test_readiness_includes_commit_pr_and_deployment_refs_when_present"
        - "tests/test_readiness.py::test_readiness_does_not_require_future_attestation_fields"
    - criterion: "AC5: The command emits a stable JSON object with `schema_version`, scope identifiers, `overall_status`, `ready`, `checks[]`, `records[]` or `record_refs[]`, `missing[]`, `failures[]`, `warnings[]`, and `generated_at`; `--output` writes the same JSON snapshot to the requested path such as `.cursor/handoffs/<handoff_id>/<task_id>/readiness.json`."
      evidence_files:
        - "src/canon_systems/readiness.py"
        - "src/canon_systems/readiness_cli.py"
      evidence_tests:
        - "tests/test_readiness.py::test_readiness_report_schema_is_stable"
        - "tests/test_readiness_cli.py::test_ac5_snapshot_keys_and_schema"
        - "tests/test_readiness_cli.py::test_ac5_output_matches_stdout"
    - criterion: "AC6: Exit codes are deterministic: `0` when all required readiness checks pass, `1` when readiness is evaluated but not ready, and `2` for CLI usage/configuration/query errors."
      evidence_files:
        - "src/canon_systems/readiness_cli.py"
      evidence_tests:
        - "tests/test_readiness_cli.py::test_ac6_exit_0_when_ready"
        - "tests/test_readiness_cli.py::test_ac6_exit_1_when_not_ready"
        - "tests/test_readiness_cli.py::test_ac6_exit_2_invalid_limit"
    - criterion: "AC7: State-api may add a read-only readiness convenience endpoint only if it delegates to existing run-ledger records and does not mutate checkpoint, archive, or ledger state; the CLI must still be testable without live AWS by mocking HTTP/query helpers."
      evidence_files:
        - "backend/state-api/state_api/run_ledger.py"
        - "backend/state-api/state_api/main.py"
      evidence_tests:
        - "backend/state-api/tests/test_run_ledger.py::test_ac7_get_run_ledger_preserves_ledger_row_in_dynamodb"
        - "backend/state-api/tests/test_run_ledger.py::test_ac7_get_run_ledger_preserves_checkpoint_table_row"
        - "backend/state-api/tests/test_run_ledger.py::test_ac7_get_run_ledger_preserves_s3_artifact_bucket"
    - criterion: "AC8: Documentation and tests describe the readiness contract, run-ledger/archive boundary, snapshot semantics, flags, exit codes, and explicit deferrals, without editing `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`."
      evidence_files:
        - "README.md"
        - "docs/SYSTEM-WORKFLOW.md"
        - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
        - "backend/state-api/README.md"
        - "CHANGELOG.md"
      evidence_tests:
        - "tests/test_readiness_cli.py::test_readiness_check_help_documents_flags"
  summary: "Added `canon readiness check` as a run-ledger-backed readiness evaluator with stable JSON output/snapshot support, deterministic exit codes, archive-ref-only packet checks, validation/commit/PR/deploy summaries, state-api read-only boundary tests, and documentation."
  decisions:
    - "Readiness is a consumer of run-ledger/archive records; local `readiness.json` is a snapshot artifact, not the source of truth."
    - "Future QA evidence normalization, credential attestation, DoR validator refactor, and deploy attestation remain deferred to their own tasks."
  next_actions:
    - "Normalize QA evidence labels in the next task."
  open_questions: []
END_HANDOFF_TO_QA
