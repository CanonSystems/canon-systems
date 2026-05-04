CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
</ROLE>

<TASK>
Define and implement the DynamoDB-backed run ledger for Canon readiness gates so Canon operators and future readiness checks have a durable, queryable run record tying plans, tasks, phases, packet archive refs, evidence refs, validation outcomes, commits, PRs, and deployments together without depending on mutable checkpoint rows or local handoff files alone.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: A versioned run-ledger record schema is implemented and documented with tenant scope, plan_id, task_id, workstream_id, handoff_id, phase, phase_status/verdict, archived packet refs, evidence refs, validation outcomes, commit refs, deployment refs, timestamps, agent_run_id/actor_id when available, and source event ids.
- AC2: Run-ledger persistence is DynamoDB-backed but logically separate from mutable checkpoint/lease state, with distinct table configuration or clearly namespaced storage that does not read or mutate checkpoint lease attributes.
- AC3: State-api exposes an additive run-ledger write/read surface suitable for agents and later readiness checks, returning structured ledger records and actionable errors while preserving existing checkpoint, lease, and archive APIs.
- AC4: Ledger writes can ingest packet-archive records by reference, including `s3_uri`, `s3_key`, `content_sha256`, `artifact_kind`, `phase`, `status/outcome`, and archive event id when available, without copying packet bodies into DynamoDB.
- AC5: The ledger can represent validation outcomes for `qa-validate`, `flow-audit`, memory-health, CI, deployment smoke checks, merge readiness, commit SHA(s), PR URL, deployment environment, and deployment status in a shape that later `canon readiness check` can consume.
- AC6: A local CLI/helper path can create or dry-run run-ledger records from explicit JSON/archive metadata inputs using tenant and task identifiers, but this task does not implement `canon readiness check` or enforce readiness policy.
- AC7: Documentation explains the boundary between packet archive, run ledger, mutable checkpoint/lease state, and later readiness checks, including required environment variables and expected write/query flow.
- AC8: Tests cover schema validation, DynamoDB key isolation, idempotent or conflict-safe writes, query behavior by plan/task/handoff, archive-reference ingestion, no packet body persistence, state-api behavior with moto DynamoDB, and CLI/helper dry-run behavior without live AWS.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-readiness-gates
- plan_id: canon_readiness_gates_c389cad8
- task_id: run-ledger
- workstream_id: run-ledger
- branch: feature/canon-run-ledger-readiness
- Build on packet-archive implementation: `POST /state/archive`, `canon packet-archive`, `canon_backend_shared.packet_archive`, and packet archive tests.
- Do not edit `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`.
- Do not implement `canon readiness check`.
</CONTEXT>

<REASONING>
Implement the ledger as a new additive surface, not by modifying checkpoint semantics. Put shared validation, schema constants, key helpers, archive-reference conversion, and body-stripping guards in `backend/shared/canon_backend_shared/run_ledger.py`, with CLI-facing helpers in `src/canon_systems/run_ledger.py`. Add state-api request/response models in `backend/state-api/state_api/models.py`, a separate ledger router/store in `backend/state-api/state_api/run_ledger.py`, and register it from `backend/state-api/state_api/main.py`.

For persistence, prefer a distinct `STATE_RUN_LEDGER_TABLE_NAME` configuration and a new table resource in Terraform. Keep keys clearly distinct from checkpoint keys and never read or mutate lease attributes such as `lease_token`, `lease_owner_agent_run_id`, or `lease_expires_at`.

For archive ingestion, consume archive record metadata by reference only. Reject or drop packet body fields such as `body_base64`, `body`, `content`, or raw packet text so DynamoDB never stores packet bodies.
</REASONING>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - id: "ws1"
    goal: "Create shared run-ledger schema, validation, keying, and archive-reference helpers."
    implementation_targets:
      - "backend/shared/canon_backend_shared/run_ledger.py"
      - "src/canon_systems/run_ledger.py"
      - "tests/test_run_ledger.py"
    depends_on: []
    can_run_parallel: true
  - id: "ws2"
    goal: "Add DynamoDB-backed state-api run-ledger persistence and query endpoints."
    implementation_targets:
      - "backend/state-api/state_api/config.py"
      - "backend/state-api/state_api/main.py"
      - "backend/state-api/state_api/models.py"
      - "backend/state-api/state_api/storage.py"
      - "backend/state-api/state_api/run_ledger.py"
      - "backend/state-api/tests/test_run_ledger.py"
      - "infra/terraform/modules/dynamodb-canon-state/main.tf"
    depends_on: ["ws1"]
    can_run_parallel: false
  - id: "ws3"
    goal: "Add local CLI/helper path for dry-run and state-api run-ledger writes."
    implementation_targets:
      - "src/canon_systems/cli.py"
      - "src/canon_systems/run_ledger.py"
      - "src/canon_systems/run_ledger_cli.py"
      - "tests/test_run_ledger_cli.py"
    depends_on: ["ws1"]
    can_run_parallel: false
  - id: "ws4"
    goal: "Document archive, ledger, checkpoint, and later-readiness boundaries and run regression tests."
    implementation_targets:
      - "backend/state-api/README.md"
      - "docs/SYSTEM-WORKFLOW.md"
      - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
      - "README.md"
      - "CHANGELOG.md"
    depends_on: ["ws2", "ws3"]
    can_run_parallel: false
- execution_waves_example:
  - wave: 1
    stream_ids: ["ws1"]
  - wave: 2
    stream_ids: ["ws2", "ws3"]
  - wave: 3
    stream_ids: ["ws4"]
</PARALLELIZATION_PLAN>

<STOP_CONDITIONS>
Each stream emits HANDOFF_TO_QA_SHARD. Parent aggregates all shard outputs into one HANDOFF_TO_QA before qa-gate.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
