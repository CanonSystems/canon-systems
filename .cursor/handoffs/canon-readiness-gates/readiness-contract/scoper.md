HANDOFF_TO_CURSOR_PILOT
  scope_summary: Define `canon readiness check` as an additive query over the already-scoped run ledger and packet archive metadata, producing a deterministic operator report and optional local JSON snapshot without making local files the source of truth. The task should add the CLI/API/helper contract needed to read existing ledger rows for a plan/task/workstream/handoff, summarize required gate state, and report missing or failing readiness inputs while explicitly deferring QA evidence normalization, shared DoR validator refactor, credential attestation, and deploy attestation hardening.
  scope_packet:
    identifiers:
      handoff_id: "canon-readiness-gates"
      company_id: "CSC"
      repository_id: "canon-systems"
      plan_id: "canon_readiness_gates_c389cad8"
      task_id: "readiness-contract"
      workstream_id: "readiness-contract"
      repo_ref: "feature/canon-run-ledger-readiness@d3528041e391dc930c7634ff906a70eaa7561a14"
    story:
      title: "Define canon readiness check over the run ledger"
      userValue: "Canon operators and release agents get one deterministic readiness diagnosis before merge or release, derived from durable run-ledger and packet-archive references instead of scattered local checks, so missing packets, failed gates, and incomplete evidence can be fixed early."
      acceptanceCriteria:
        - "AC1: The public CLI exposes `canon readiness check` with required tenant/task scope flags (`--company-id`, `--repository-id`, `--plan-id`, `--task-id`, `--workstream-id`, `--handoff-id`) plus optional `--ledger-run-id`, `--state-api-url`, `--limit`, `--output`, and `--quiet` flags."
        - "AC2: The readiness implementation queries `GET /state/run-ledger` using the existing run-ledger API, supports both latest scoped query and explicit `ledger_run_id` lookup, and handles state-api 400/404/503/network failures with actionable errors and stable exit codes."
        - "AC3: Readiness evaluation derives its report from run-ledger records and archive refs only, verifying the presence/status of required phase packet archive refs (`scoper`, `cursor-pilot`, `qa-gate`, `release-status`, and implementer or implementer shard evidence where present) without reading packet bodies or storing bodies in the snapshot."
        - "AC4: The readiness report summarizes existing validation outcome slots from the run ledger (`qa_validate`, `flow_audit`, `memory_health`, `ci`, `deployment_smoke`, `merge_readiness`), commit refs, PR refs, and deployment refs when present, but does not implement new QA evidence normalization, credential attestation, shared DoR validation, or deploy attestation rules."
        - "AC5: The command emits a stable JSON object with `schema_version`, scope identifiers, `overall_status`, `ready`, `checks[]`, `records[]` or `record_refs[]`, `missing[]`, `failures[]`, `warnings[]`, and `generated_at`; `--output` writes the same JSON snapshot to the requested path such as `.cursor/handoffs/<handoff_id>/<task_id>/readiness.json`."
        - "AC6: Exit codes are deterministic: `0` when all required readiness checks pass, `1` when readiness is evaluated but not ready, and `2` for CLI usage/configuration/query errors."
        - "AC7: State-api may add a read-only readiness convenience endpoint only if it delegates to existing run-ledger records and does not mutate checkpoint, archive, or ledger state; the CLI must still be testable without live AWS by mocking HTTP/query helpers."
        - "AC8: Documentation and tests describe the readiness contract, run-ledger/archive boundary, snapshot semantics, flags, exit codes, and explicit deferrals, without editing `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`."
    repository:
      primaryLanguages: ["Python", "Markdown"]
      testFramework: "pytest; CLI tests use pytest, tmp_path, capsys, and mocked urllib/state-api helpers; backend/state-api uses FastAPI TestClient where needed"
      relevantFiles:
        - "src/canon_systems/cli.py"
        - "src/canon_systems/readiness.py"
        - "src/canon_systems/readiness_cli.py"
        - "src/canon_systems/run_ledger.py"
        - "backend/state-api/state_api/run_ledger.py"
        - "backend/shared/canon_backend_shared/run_ledger.py"
        - "tests/test_readiness.py"
        - "tests/test_readiness_cli.py"
        - "README.md"
        - "docs/SYSTEM-WORKFLOW.md"
        - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
        - "backend/state-api/README.md"
        - "CHANGELOG.md"
    constraints:
      dependencies:
        - "Build on packet-archive and run-ledger task-level READY_TO_MERGE surfaces."
        - "Do not edit `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`."
        - "Scope only `readiness-contract`; do not implement QA evidence normalization, shared DoR validator refactor, credential attestation, or deploy attestation except to surface existing ledger fields when already present."
        - "Use existing argparse, urllib, JSON, FastAPI/TestClient, pytest, and mocked HTTP patterns; avoid new dependencies."
      mustNotBreak:
        - "Existing `canon run-ledger` dry-run and PUT behavior."
        - "Existing `GET /state/run-ledger` query semantics and error shapes."
        - "Existing packet archive schema, deterministic archive keys, and no-body ledger/archive reference guarantees."
        - "Existing `canon qa-validate`, `canon flow-audit`, `canon memory-health`, `canon checkpoint`, and state-api checkpoint/lease behavior."
        - "Existing task-level READY_TO_MERGE packet quartet under `.cursor/handoffs/canon-readiness-gates/packet-archive` and `.cursor/handoffs/canon-readiness-gates/run-ledger`."
      requiredTests:
        - "pytest tests/test_readiness.py tests/test_readiness_cli.py -q"
        - "pytest tests/test_run_ledger.py tests/test_run_ledger_cli.py tests/test_readiness.py tests/test_readiness_cli.py -q"
        - "pytest backend/state-api/tests/test_run_ledger.py -q"
        - "pytest -q"
        - "bash scripts/smoke-test.sh when environment permits"
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "AC1: The public CLI exposes `canon readiness check` with required tenant/task scope flags (`--company-id`, `--repository-id`, `--plan-id`, `--task-id`, `--workstream-id`, `--handoff-id`) plus optional `--ledger-run-id`, `--state-api-url`, `--limit`, `--output`, and `--quiet` flags."
        implementation_targets: ["src/canon_systems/cli.py", "src/canon_systems/readiness_cli.py", "README.md"]
        verification_tests: ["tests/test_readiness_cli.py::test_canon_main_dispatches_readiness_check", "tests/test_readiness_cli.py::test_readiness_check_requires_scope_flags", "tests/test_readiness_cli.py::test_readiness_check_accepts_optional_ledger_run_id_output_and_quiet"]
      - criterion: "AC2: The readiness implementation queries `GET /state/run-ledger` using the existing run-ledger API, supports both latest scoped query and explicit `ledger_run_id` lookup, and handles state-api 400/404/503/network failures with actionable errors and stable exit codes."
        implementation_targets: ["src/canon_systems/readiness.py", "src/canon_systems/readiness_cli.py", "src/canon_systems/run_ledger.py"]
        verification_tests: ["tests/test_readiness.py::test_fetch_readiness_records_queries_scope_endpoint", "tests/test_readiness.py::test_fetch_readiness_record_queries_explicit_ledger_run_id", "tests/test_readiness_cli.py::test_readiness_check_reports_state_api_503_as_usage_error"]
      - criterion: "AC3: Readiness evaluation derives its report from run-ledger records and archive refs only, verifying the presence/status of required phase packet archive refs (`scoper`, `cursor-pilot`, `qa-gate`, `release-status`, and implementer or implementer shard evidence where present) without reading packet bodies or storing bodies in the snapshot."
        implementation_targets: ["src/canon_systems/readiness.py", "backend/shared/canon_backend_shared/run_ledger.py"]
        verification_tests: ["tests/test_readiness.py::test_readiness_passes_with_required_phase_archive_refs", "tests/test_readiness.py::test_readiness_fails_when_required_phase_ref_missing", "tests/test_readiness.py::test_readiness_snapshot_omits_body_fields"]
      - criterion: "AC4: The readiness report summarizes existing validation outcome slots from the run ledger (`qa_validate`, `flow_audit`, `memory_health`, `ci`, `deployment_smoke`, `merge_readiness`), commit refs, PR refs, and deployment refs when present, but does not implement new QA evidence normalization, credential attestation, shared DoR validation, or deploy attestation rules."
        implementation_targets: ["src/canon_systems/readiness.py", "tests/test_readiness.py", "docs/SYSTEM-WORKFLOW.md"]
        verification_tests: ["tests/test_readiness.py::test_readiness_summarizes_existing_validation_outcomes", "tests/test_readiness.py::test_readiness_includes_commit_pr_and_deployment_refs_when_present", "tests/test_readiness.py::test_readiness_does_not_require_future_attestation_fields"]
      - criterion: "AC5: The command emits a stable JSON object with `schema_version`, scope identifiers, `overall_status`, `ready`, `checks[]`, `records[]` or `record_refs[]`, `missing[]`, `failures[]`, `warnings[]`, and `generated_at`; `--output` writes the same JSON snapshot to the requested path such as `.cursor/handoffs/<handoff_id>/<task_id>/readiness.json`."
        implementation_targets: ["src/canon_systems/readiness.py", "src/canon_systems/readiness_cli.py", "tests/test_readiness_cli.py"]
        verification_tests: ["tests/test_readiness.py::test_readiness_report_schema_is_stable", "tests/test_readiness_cli.py::test_readiness_check_prints_json_report", "tests/test_readiness_cli.py::test_readiness_check_writes_output_snapshot"]
      - criterion: "AC6: Exit codes are deterministic: `0` when all required readiness checks pass, `1` when readiness is evaluated but not ready, and `2` for CLI usage/configuration/query errors."
        implementation_targets: ["src/canon_systems/readiness_cli.py", "tests/test_readiness_cli.py"]
        verification_tests: ["tests/test_readiness_cli.py::test_readiness_exit_zero_when_ready", "tests/test_readiness_cli.py::test_readiness_exit_one_when_not_ready", "tests/test_readiness_cli.py::test_readiness_exit_two_on_invalid_args_or_query_error"]
      - criterion: "AC7: State-api may add a read-only readiness convenience endpoint only if it delegates to existing run-ledger records and does not mutate checkpoint, archive, or ledger state; the CLI must still be testable without live AWS by mocking HTTP/query helpers."
        implementation_targets: ["backend/state-api/state_api/main.py", "backend/state-api/state_api/run_ledger.py", "backend/state-api/tests/test_run_ledger.py", "src/canon_systems/readiness.py"]
        verification_tests: ["backend/state-api/tests/test_run_ledger.py::test_readiness_query_does_not_mutate_run_ledger_rows", "tests/test_readiness_cli.py::test_readiness_cli_uses_mocked_fetch_without_live_aws"]
      - criterion: "AC8: Documentation and tests describe the readiness contract, run-ledger/archive boundary, snapshot semantics, flags, exit codes, and explicit deferrals, without editing `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`."
        implementation_targets: ["README.md", "docs/SYSTEM-WORKFLOW.md", "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md", "backend/state-api/README.md", "CHANGELOG.md", "tests/test_readiness.py", "tests/test_readiness_cli.py"]
        verification_tests: ["tests/test_readiness_cli.py::test_readiness_help_documents_snapshot_and_exit_codes", "pytest tests/test_readiness.py tests/test_readiness_cli.py -q"]
    risks_and_assumptions:
      assumptions:
        - "Readiness JSON snapshots are local interchange artifacts for CI/operator review and must be reproducible from state-api run-ledger data; they are not the authoritative store."
        - "Missing future attestation fields should be warnings or surfaced existing-null fields in this task, not hard failures, because dedicated credential/deploy attestation tasks are pending."
      openQuestions: []
END_HANDOFF_TO_CURSOR_PILOT
