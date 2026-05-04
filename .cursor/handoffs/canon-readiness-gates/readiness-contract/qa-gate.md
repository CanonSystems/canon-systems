GATE_RESULTS
  handoff_id: "canon-readiness-gates"
  verdict: PASS
  acceptance_criteria:
    - criterion: "AC1: The public CLI exposes `canon readiness check` with required tenant/task scope flags (`--company-id`, `--repository-id`, `--plan-id`, `--task-id`, `--workstream-id`, `--handoff-id`) plus optional `--ledger-run-id`, `--state-api-url`, `--limit`, `--output`, and `--quiet` flags."
      status: PASS
      covering_tests:
        - "tests/test_readiness_cli.py::test_ac1_requires_scope_flags"
        - "tests/test_readiness_cli.py::test_readiness_check_help_documents_flags"
        - "tests/test_readiness_cli.py::test_canon_main_dispatches_readiness_check"
      run_result: "pass - covered by focused suite: 30 passed"
    - criterion: "AC2: The readiness implementation queries `GET /state/run-ledger` using the existing run-ledger API, supports both latest scoped query and explicit `ledger_run_id` lookup, and handles state-api 400/404/503/network failures with actionable errors and stable exit codes."
      status: PASS
      covering_tests:
        - "tests/test_readiness.py::test_get_run_ledger_http_404_raises_not_found"
        - "tests/test_readiness.py::test_get_run_ledger_http_errors"
        - "tests/test_readiness.py::test_get_run_ledger_transport_error"
        - "tests/test_readiness_cli.py::test_ac2_query_errors_exit_2"
        - "tests/test_readiness_cli.py::test_explicit_ledger_run_id_uses_single_record_shape"
      run_result: "pass - focused suite and ledger/readiness regression passed"
    - criterion: "AC3: Readiness evaluation derives its report from run-ledger records and archive refs only, verifying the presence/status of required phase packet archive refs (`scoper`, `cursor-pilot`, `qa-gate`, `release-status`, and implementer or implementer shard evidence where present) without reading packet bodies or storing bodies in the snapshot."
      status: PASS
      covering_tests:
        - "tests/test_readiness.py::test_build_readiness_report_ready_when_packets_present"
        - "tests/test_readiness.py::test_missing_phase_not_ready"
        - "tests/test_readiness.py::test_implementer_shard_kind_satisfies_implementer"
        - "tests/test_readiness.py::test_evidence_ref_implementer_shard_without_archive_impl"
        - "tests/test_readiness.py::test_readiness_snapshot_omits_body_fields"
      run_result: "pass - focused suite passed"
    - criterion: "AC4: The readiness report summarizes existing validation outcome slots from the run ledger (`qa_validate`, `flow_audit`, `memory_health`, `ci`, `deployment_smoke`, `merge_readiness`), commit refs, PR refs, and deployment refs when present, but does not implement new QA evidence normalization, credential attestation, shared DoR validation, or deploy attestation rules."
      status: PASS
      covering_tests:
        - "tests/test_readiness.py::test_summarize_validation_outcomes_filters_slots_only"
        - "tests/test_readiness.py::test_build_readiness_report_ready_when_packets_present"
        - "tests/test_readiness.py::test_bad_archive_status_warns_not_pass"
      run_result: "pass - focused suite passed; docs confirm deferred normalization/attestation work remains out of scope"
    - criterion: "AC5: The command emits a stable JSON object with `schema_version`, scope identifiers, `overall_status`, `ready`, `checks[]`, `records[]` or `record_refs[]`, `missing[]`, `failures[]`, `warnings[]`, and `generated_at`; `--output` writes the same JSON snapshot to the requested path such as `.cursor/handoffs/<handoff_id>/<task_id>/readiness.json`."
      status: PASS
      covering_tests:
        - "tests/test_readiness_cli.py::test_ac5_snapshot_keys_and_schema"
        - "tests/test_readiness_cli.py::test_ac5_output_matches_stdout"
      run_result: "pass - focused suite passed"
    - criterion: "AC6: Exit codes are deterministic: `0` when all required readiness checks pass, `1` when readiness is evaluated but not ready, and `2` for CLI usage/configuration/query errors."
      status: PASS
      covering_tests:
        - "tests/test_readiness_cli.py::test_ac6_exit_0_when_ready"
        - "tests/test_readiness_cli.py::test_ac6_exit_1_when_not_ready"
        - "tests/test_readiness_cli.py::test_ac6_exit_2_invalid_limit"
        - "tests/test_readiness_cli.py::test_custom_evaluate_readiness_drives_exit_code"
      run_result: "pass - focused suite passed"
    - criterion: "AC7: State-api may add a read-only readiness convenience endpoint only if it delegates to existing run-ledger records and does not mutate checkpoint, archive, or ledger state; the CLI must still be testable without live AWS by mocking HTTP/query helpers."
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_run_ledger.py::test_ac7_get_run_ledger_preserves_ledger_row_in_dynamodb"
        - "backend/state-api/tests/test_run_ledger.py::test_ac7_get_run_ledger_preserves_checkpoint_table_row"
        - "backend/state-api/tests/test_run_ledger.py::test_ac7_get_run_ledger_preserves_s3_artifact_bucket"
        - "tests/test_readiness_cli.py::test_canon_main_dispatches_readiness_check"
      run_result: "pass - backend state-api suite: 11 passed"
    - criterion: "AC8: Documentation and tests describe the readiness contract, run-ledger/archive boundary, snapshot semantics, flags, exit codes, and explicit deferrals, without editing `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`."
      status: PASS
      covering_tests:
        - "tests/test_readiness_cli.py::test_readiness_check_help_documents_flags"
        - "tests/test_readiness_cli.py::test_ac5_snapshot_keys_and_schema"
        - "tests/test_readiness_cli.py::test_ac6_exit_0_when_ready"
        - "tests/test_readiness_cli.py::test_ac6_exit_1_when_not_ready"
        - "tests/test_readiness_cli.py::test_ac6_exit_2_invalid_limit"
      run_result: "pass - docs inspected in README.md, docs/SYSTEM-WORKFLOW.md, docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md, backend/state-api/README.md, and CHANGELOG.md"
  iterations: 0
  regression_checked: true
  remaining_gaps: []
  notes: "Relevant tests passed: `python3 -m pytest tests/test_readiness.py tests/test_readiness_cli.py -q` -> 30 passed; `python3 -m pytest tests/test_run_ledger.py tests/test_run_ledger_cli.py tests/test_readiness.py tests/test_readiness_cli.py -q` -> 49 passed; `python3 -m pytest backend/state-api/tests/test_run_ledger.py -q` -> 11 passed; `python3 -m pytest -q` -> 636 passed; `bash scripts/smoke-test.sh` -> build, pytest, terraform validate all passed. `CANON_STATE_API_URL` was unset, so checkpoint HTTP was skipped per policy."
END_GATE_RESULTS
