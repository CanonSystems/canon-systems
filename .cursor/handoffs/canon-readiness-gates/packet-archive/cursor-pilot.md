CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
This prompt must be executed by that subagent (default model:
`composer-2-fast`), not by the parent planner agent.
</ROLE>

<TASK>
Define durable S3 packet and evidence archive semantics so Canon operators and later readiness/run-ledger tasks have a server-side source of truth for phase packet bodies and evidence blobs, while preserving the existing local `.cursor/handoffs/...` packet requirements. Keep this task limited to packet/evidence archival; do not implement the DynamoDB run ledger or `canon readiness check`.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: A versioned packet/evidence archive record schema is implemented and documented with required fields for tenant scope, plan/task/workstream/handoff ids, phase, artifact kind, local path or source label, S3 URI/key, content SHA-256, byte length, content type, created_at, agent_run_id/actor_id when available, outcome/status when available, and optional S3 version id.
- AC2: Archive key generation is deterministic, tenant-scoped, path-traversal-safe, and content-addressed or otherwise immutable so the same body resolves to the same durable object identity without overwriting a different body.
- AC3: Packet kinds cover the five phase packets (`scoper.md`, `cursor-pilot.md`, `implementer.md` or shard handoff, `qa-gate.md`, `release-status.md`) plus HANDOFF_NOT_READY packets and DoR telemetry artifacts; evidence kinds cover JSON evidence blobs such as memory-health, deployment smoke, runtime/browser/shell evidence, and future typed QA evidence labels without hard-coding the run ledger.
- AC4: A state-api/backend archive write surface stores packet/evidence bodies in the configured S3 artifact bucket and returns a structured archive record; failures are actionable and do not create partial success claims.
- AC5: Successful archive writes emit one canonical `packet_archived` or equivalent event containing archive metadata but not full packet/evidence body text; this task does not create DynamoDB run-ledger records.
- AC6: A local/CLI-facing helper can archive an explicit packet/evidence file using tenant and task identifiers, supports dry-run or no-network test injection, and preserves existing local packet requirements.
- AC7: Documentation explains the archive semantics, required environment/configuration, retention/immutability expectations, and the boundary with later run-ledger/readiness tasks.
- AC8: Tests prove hashing/key safety, idempotent same-body writes, non-overwrite behavior for different bodies, canonical event shape, backend API behavior with moto S3, and CLI/helper behavior without live AWS.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- company_id: CSC
- repository_id: canon-systems
- handoff_id: canon-readiness-gates
- plan_id: canon_readiness_gates_c389cad8
- task_id: packet-archive
- workstream_id: packet-archive
- branch: feature/canon-run-ledger-readiness
- repo_ref: feature/canon-run-ledger-readiness@d3528041e391dc930c7634ff906a70eaa7561a14
- user_constraints:
  - Do not edit `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`.
  - Keep this task scoped to durable S3 packet/evidence archive semantics.
  - Do not implement the DynamoDB run ledger.
  - Do not implement `canon readiness check`.
  - Preserve local `.cursor/handoffs/...` files as required working-copy/git-review artifacts.
</CONTEXT>

<REPOSITORY>
- primaryLanguages: Python, Terraform, Markdown
- testFramework: pytest; backend/state-api uses FastAPI TestClient plus moto for AWS-backed tests; repo smoke uses scripts/smoke-test.sh with pytest and terraform validate
- files_to_inspect:
  - src/canon_systems/cli.py
  - src/canon_systems/checkpoint_cli.py
  - src/canon_systems/checkpoints.py
  - src/canon_systems/flow_audit.py
  - src/canon_systems/qa_validate.py
  - backend/state-api/state_api/main.py
  - backend/state-api/state_api/config.py
  - backend/state-api/state_api/models.py
  - backend/state-api/state_api/storage.py
  - backend/state-api/state_api/checkpoints.py
  - backend/state-api/state_api/events.py
  - backend/state-api/tests/conftest.py
  - backend/state-api/tests/test_checkpoint_put.py
  - backend/shared/canon_backend_shared/events.py
  - backend/synthesis/synthesis/publisher.py
  - infra/terraform/modules/s3-artifacts/main.tf
  - infra/terraform/modules/s3-artifacts/variables.tf
  - infra/terraform/modules/s3-artifacts/outputs.tf
  - docs/SYSTEM-WORKFLOW.md
  - docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md
  - backend/state-api/README.md
  - README.md
  - CHANGELOG.md
- expected_files_to_change_or_add:
  - src/canon_systems/packet_archive.py
  - src/canon_systems/cli.py
  - backend/state-api/state_api/models.py
  - backend/state-api/state_api/config.py
  - backend/state-api/state_api/storage.py
  - backend/state-api/state_api/main.py
  - optional: backend/state-api/state_api/packet_archive.py if keeping archive router separate from `main.py`
  - backend/state-api/tests/conftest.py
  - backend/state-api/tests/test_packet_archive.py
  - tests/test_packet_archive.py
  - tests/test_packet_archive_cli.py
  - backend/state-api/README.md
  - docs/SYSTEM-WORKFLOW.md
  - docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md
  - README.md
  - CHANGELOG.md
  - optional: backend/state-api/pyproject.toml only if moto S3 extras are not already available to backend tests
</REPOSITORY>

<REASONING>
Implement this as one cohesive additive slice because backend schema/storage, CLI helper behavior, event emission, and documentation all depend on the exact archive record contract.

Ordered implementation steps:
1. Create `src/canon_systems/packet_archive.py` as the shared local contract for archive metadata, supported artifact kinds, SHA-256/body metadata calculation, path-traversal-safe deterministic key generation, dry-run archive records, and HTTP/client helper behavior. Keep it stdlib plus existing dependencies; do not add a new HTTP client dependency.
2. Add a `canon packet-archive` CLI command in `src/canon_systems/cli.py` that archives an explicit file with required scope fields, artifact kind, phase, source/local path metadata, optional content type/status/outcome/agent fields, and `--dry-run`.
3. Extend state-api settings in `backend/state-api/state_api/config.py` with an artifact bucket env var such as `STATE_ARTIFACT_BUCKET` and, if needed, an archive prefix env var.
4. Add Pydantic archive request/response models in `backend/state-api/state_api/models.py`.
5. Add S3 archive write support in `backend/state-api/state_api/storage.py` or a small dedicated module used by the API.
6. Add a state-api archive endpoint, preferably `POST /state/archive`. On success it writes the body to S3, returns the archive record, emits a canonical `packet_archived` event with metadata only, and sets `X-Canon-Event-Id`.
7. Keep canonical event envelope usage exactly compatible with `backend/shared/canon_backend_shared/events.py`.
8. Add tests in repo root for key/schema/CLI helper behavior and backend tests with moto S3/FastAPI TestClient for S3 writes and event emission.
9. Update docs in `backend/state-api/README.md`, `docs/SYSTEM-WORKFLOW.md`, `docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md`, `README.md`, and `CHANGELOG.md`. Do not edit `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`.
10. Run focused tests first, then broader tests as feasible.
</REASONING>

<PARALLELIZATION_PLAN>
- strategy: "single-stream"
- rationale: "Parallel implementation is not safe for this task because the shared archive record/key contract must be defined once and then reused consistently across CLI, backend API, event emission, tests, and docs."
- workstreams:
  - id: "ws1"
    goal: "Implement durable packet/evidence archive contract, backend S3 write surface, CLI helper, tests, and docs as one cohesive change."
    depends_on: []
    can_run_parallel: false
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Produce only the code, tests, and documentation changes needed to satisfy all acceptance criteria. Do not refactor unrelated code. Do not edit `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`. Do not implement DynamoDB run-ledger storage, readiness checks, or automatic phase-template archival wiring beyond the explicit helper/API required here.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
Emit:

HANDOFF_TO_QA
  handoff_id: "canon-readiness-gates"
  acceptance_criteria_covered:
    - criterion: "<exact AC text>"
      evidence_files:
        - "path/to/impl.ext:<line range>"
      evidence_tests:
        - "path/to/test.ext::<test name>"
  summary: "<1-2 sentences on what changed>"
  decisions:
    - "<notable design decision made during implementation>"
  next_actions:
    - "<follow-up work explicitly deferred>"
  open_questions:
    - "<anything still unclear that QA should verify>"
END_HANDOFF_TO_QA
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
