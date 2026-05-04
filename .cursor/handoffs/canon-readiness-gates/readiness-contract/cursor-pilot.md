CURSOR_PILOT_PROMPT

<TASK>
Define `canon readiness check` over the run ledger so Canon operators and release agents get a deterministic readiness diagnosis before merge or release, derived from durable run-ledger rows and packet-archive references rather than scattered local checks.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: The public CLI exposes `canon readiness check` with required tenant/task scope flags (`--company-id`, `--repository-id`, `--plan-id`, `--task-id`, `--workstream-id`, `--handoff-id`) plus optional `--ledger-run-id`, `--state-api-url`, `--limit`, `--output`, and `--quiet` flags.
- AC2: The readiness implementation queries `GET /state/run-ledger` using the existing run-ledger API, supports both latest scoped query and explicit `ledger_run_id` lookup, and handles state-api 400/404/503/network failures with actionable errors and stable exit codes.
- AC3: Readiness evaluation derives its report from run-ledger records and archive refs only, verifying the presence/status of required phase packet archive refs (`scoper`, `cursor-pilot`, `qa-gate`, `release-status`, and implementer or implementer shard evidence where present) without reading packet bodies or storing bodies in the snapshot.
- AC4: The readiness report summarizes existing validation outcome slots from the run ledger (`qa_validate`, `flow_audit`, `memory_health`, `ci`, `deployment_smoke`, `merge_readiness`), commit refs, PR refs, and deployment refs when present, but does not implement new QA evidence normalization, credential attestation, shared DoR validation, or deploy attestation rules.
- AC5: The command emits a stable JSON object with `schema_version`, scope identifiers, `overall_status`, `ready`, `checks[]`, `records[]` or `record_refs[]`, `missing[]`, `failures[]`, `warnings[]`, and `generated_at`; `--output` writes the same JSON snapshot to the requested path such as `.cursor/handoffs/<handoff_id>/<task_id>/readiness.json`.
- AC6: Exit codes are deterministic: `0` when all required readiness checks pass, `1` when readiness is evaluated but not ready, and `2` for CLI usage/configuration/query errors.
- AC7: State-api may add a read-only readiness convenience endpoint only if it delegates to existing run-ledger records and does not mutate checkpoint, archive, or ledger state; the CLI must still be testable without live AWS by mocking HTTP/query helpers.
- AC8: Documentation and tests describe the readiness contract, run-ledger/archive boundary, snapshot semantics, flags, exit codes, and explicit deferrals, without editing `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-readiness-gates
- plan_id: canon_readiness_gates_c389cad8
- task_id: readiness-contract
- workstream_id: readiness-contract
- branch: feature/canon-run-ledger-readiness
- Do not edit `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`.
- Do not implement QA evidence normalization, shared DoR validator refactor, credential attestation, or deploy attestation beyond summarizing existing run-ledger fields.
</CONTEXT>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - id: "ws1"
    goal: "Add run-ledger read client and readiness evaluation"
    implementation_targets:
      - "src/canon_systems/readiness.py"
      - "src/canon_systems/run_ledger.py"
      - "backend/shared/canon_backend_shared/run_ledger.py"
      - "tests/test_readiness.py"
    depends_on: []
    can_run_parallel: true
  - id: "ws2"
    goal: "Add readiness CLI surface and exit-code behavior"
    implementation_targets:
      - "src/canon_systems/cli.py"
      - "src/canon_systems/readiness_cli.py"
      - "src/canon_systems/readiness.py"
      - "tests/test_readiness_cli.py"
    depends_on: []
    can_run_parallel: true
  - id: "ws3"
    goal: "Lock state-api read-only boundary"
    implementation_targets:
      - "backend/state-api/state_api/run_ledger.py"
      - "backend/state-api/state_api/main.py"
      - "backend/state-api/tests/test_run_ledger.py"
    depends_on: []
    can_run_parallel: true
  - id: "ws4"
    goal: "Document readiness contract and deferrals"
    implementation_targets:
      - "README.md"
      - "docs/SYSTEM-WORKFLOW.md"
      - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
      - "backend/state-api/README.md"
      - "CHANGELOG.md"
      - "tests/test_readiness_cli.py"
    depends_on: ["ws1", "ws2"]
    can_run_parallel: false
- execution_waves_example:
  - wave: 1
    stream_ids: ["ws1", "ws2", "ws3"]
  - wave: 2
    stream_ids: ["ws4"]
</PARALLELIZATION_PLAN>

<STOP_CONDITIONS>
Each stream emits HANDOFF_TO_QA_SHARD. Parent aggregates all shard outputs into one HANDOFF_TO_QA before qa-gate.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
