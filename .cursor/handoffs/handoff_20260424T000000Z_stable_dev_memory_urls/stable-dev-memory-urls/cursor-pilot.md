CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
This prompt must be executed by that subagent (default model:
`composer-2-fast`), not by the parent planner agent.
</ROLE>

<TASK>
Add the smallest safe repo-only slice for stable dev memory URLs so the current dev `ecs_baseline` ECS stack can be fronted by stable ingress/DNS, repo-owned secret/tooling defaults treat stable `https://` memory URLs as canonical, and operators have an explicit cutover/rollback path without attempting a broader multi-service ECS redesign or live AWS rollout work.
</TASK>

<ACCEPTANCE_CRITERIA>
- The Terraform root and `infra/terraform/modules/ecs-fargate` can model stable ingress for the current dev `ecs_baseline` service without changing existing stack naming/import assumptions: configurable load-balancer/target-group/DNS inputs and outputs exist, and the ECS service can attach to a target group when ingress is enabled.
- Repo-owned secret/default tooling and diagnostics treat stable HTTPS DNS as the canonical shape for `KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, `MEMORY_ADAPTER_URL`, and `CANON_STATE_API_URL`, while preserving the current shared-base behavior where `knowledge-api` mounts `POST /memory/search`.
- Operator-facing docs explain the precise cutover and rollback path for `canon-memory-dev/memory-layer__csc__canon-systems`: apply/import infra, update the secret to stable DNS values, clear `~/.canon/memory-layer-aws-cache.json` or run `canon doctor --fix-cache`, validate endpoints/health, and restore the previous secret version if rollback is needed.
- Focused tests cover the new Terraform contract and any stable-DNS helper/diagnostic behavior added in this task, with no requirement for live AWS mutations in CI.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- company_id: CSC
- repository_id: canon-systems
- prior_work_references:
  - none
</CONTEXT>

<REPOSITORY>
- primaryLanguages: ["Python", "HCL", "Shell", "Markdown"]
- testFramework: pytest
- relevantFiles:
  - infra/terraform/main.tf
  - infra/terraform/variables.tf
  - infra/terraform/outputs.tf
  - infra/terraform/README.md
  - infra/terraform/modules/ecs-fargate/main.tf
  - infra/terraform/modules/ecs-fargate/variables.tf
  - infra/terraform/modules/ecs-fargate/outputs.tf
  - src/canon_systems/secrets_submit.py
  - src/canon_systems/doctor_cli.py
  - scripts/migrate_memory_secrets.py
  - scripts/validate_memory_endpoints.py
  - docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md
  - docs/ONBOARDING.md
  - README.md
  - docs/migrations/cognito-ingress-migration.md
  - docs/runbooks/auth-migration-rollback.md
  - tests/test_infra_layout.py
  - tests/test_doctor.py
  - tests/test_auth_migration_assets.py
  - tests/test_secrets_submit.py
  - backend/knowledge-api/app/main.py
  - src/canon_systems/shared.py
  - src/canon_systems/memory_health.py
  - src/canon_systems/checkpoint_cli.py
- mustNotBreak:
  - Current `canon e2e-check --agent` / `canon memory-health` flows that resolve URLs from AWS Secrets Manager plus `~/.canon/memory-layer-aws-cache.json`.
  - Current `knowledge-api` `/healthz` and mounted `POST /memory/search` behavior used by `MEMORY_ADAPTER_URL`.
  - Existing Terraform layout/import contracts enforced by `tests/test_infra_layout.py`.
  - Existing stable-domain assumptions already present in `src/canon_systems/secrets_submit.py`, `scripts/migrate_memory_secrets.py`, and the auth-migration docs.
- notes:
  - Graph-first retrieval degraded: `canon graph query` and `canon graph impact` returned transport `403` in the readonly sandbox, so blast radius must be inferred from repo evidence instead of graph output.
  - Repo evidence confirms `backend/knowledge-api/app/main.py` mounts the memory search router on the same base as `knowledge-api`, and `src/canon_systems/shared.py` defaults `CANON_STATE_API_URL` from `KNOWLEDGE_API_URL` when no dedicated state URL is set; preserve both behaviors unless explicitly overridden.
  - Scope assumptions remain in force: extend the existing single-service ECS shape only; ACM issuance, Route53 ownership, target-group/import/apply steps, and Secrets Manager writes are operator follow-up and must be documented rather than automated.
</REPOSITORY>

<REASONING>
Implement AC1 by extending the `infra/terraform/modules/ecs-fargate` interface and the root `infra/terraform` stack so ingress is optional, naming/import assumptions for `canon-systems-v2` stay intact, and the current `ecs_baseline` service can register with a target group only when enabled; cover this with focused layout/contract assertions in `tests/test_infra_layout.py` and updated operator guidance in `infra/terraform/README.md`. Implement AC2 by keeping stable HTTPS DNS as the canonical default/template shape in `src/canon_systems/secrets_submit.py`, aligning diagnostics and migration/validation helpers in `src/canon_systems/doctor_cli.py`, `scripts/migrate_memory_secrets.py`, and `scripts/validate_memory_endpoints.py`, and preserving the shared-base deployment model where `MEMORY_ADAPTER_URL` can equal `KNOWLEDGE_API_URL` because `knowledge-api` already exposes the mounted search route. Implement AC3 by documenting the exact cutover and rollback sequence across runtime/onboarding/migration docs: apply/import infra, update `canon-memory-dev/memory-layer__csc__canon-systems` to stable DNS values, clear `~/.canon/memory-layer-aws-cache.json` or run `canon doctor --fix-cache`, validate via health/endpoints, and restore the previous secret version on rollback. AC4 must be satisfied only with repo-local focused tests and fixtures; no live AWS mutation or integration dependency belongs in CI. `ac_traceability` mapping is explicit: AC1 -> Terraform root/module files plus `tests/test_infra_layout.py`; AC2 -> secret/tooling/diagnostic files plus `tests/test_secrets_submit.py`, `tests/test_doctor.py`, and domain-preference assertions in `tests/test_auth_migration_assets.py`; AC3 -> infra/runtime/onboarding/migration/rollback docs plus doc assertions in `tests/test_auth_migration_assets.py` and `tests/test_infra_layout.py`; AC4 -> the focused test files themselves. Key risk controls from assumptions: keep the current single-service ECS shape, preserve `/healthz` and mounted `POST /memory/search`, retain cache-clearing behavior and stable-domain defaults already present in repo-owned tooling, and do not broaden scope into live AWS rollout mechanics.
</REASONING>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - id: "ws1"
    goal: "Extend Terraform root/module for optional stable ingress on the current ecs_baseline service."
    acceptance_criteria:
      - "The Terraform root and `infra/terraform/modules/ecs-fargate` can model stable ingress for the current dev `ecs_baseline` service without changing existing stack naming/import assumptions: configurable load-balancer/target-group/DNS inputs and outputs exist, and the ECS service can attach to a target group when ingress is enabled."
      - "Focused tests cover the new Terraform contract and any stable-DNS helper/diagnostic behavior added in this task, with no requirement for live AWS mutations in CI."
    implementation_targets:
      - "infra/terraform/modules/ecs-fargate/main.tf"
      - "infra/terraform/modules/ecs-fargate/variables.tf"
      - "infra/terraform/modules/ecs-fargate/outputs.tf"
      - "infra/terraform/main.tf"
      - "infra/terraform/variables.tf"
      - "infra/terraform/outputs.tf"
      - "infra/terraform/README.md"
      - "tests/test_infra_layout.py"
    verification_tests:
      - "tests/test_infra_layout.py::assert ecs-fargate module and root expose ingress variables/outputs while preserving required file layout and import-readme contracts"
      - "tests/test_infra_layout.py::new ingress contract assertions"
    depends_on: []
    can_run_parallel: true
  - id: "ws2"
    goal: "Align stable HTTPS memory URL defaults, coercion, and diagnostics across repo-owned secret/tooling surfaces."
    acceptance_criteria:
      - "Repo-owned secret/default tooling and diagnostics treat stable HTTPS DNS as the canonical shape for `KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, `MEMORY_ADAPTER_URL`, and `CANON_STATE_API_URL`, while preserving the current shared-base behavior where `knowledge-api` mounts `POST /memory/search`."
      - "Focused tests cover the new Terraform contract and any stable-DNS helper/diagnostic behavior added in this task, with no requirement for live AWS mutations in CI."
    implementation_targets:
      - "src/canon_systems/secrets_submit.py"
      - "src/canon_systems/doctor_cli.py"
      - "scripts/migrate_memory_secrets.py"
      - "scripts/validate_memory_endpoints.py"
      - "tests/test_secrets_submit.py"
      - "tests/test_doctor.py"
      - "tests/test_auth_migration_assets.py"
    verification_tests:
      - "tests/test_secrets_submit.py::template/default payload emits stable HTTPS DNS and aligned CANON_STATE_API_URL"
      - "tests/test_doctor.py::doctor covers literal-IPv4 guidance for env and any newly-added cache inspection behavior"
      - "tests/test_auth_migration_assets.py::secret migration and endpoint validation helpers prefer domain hosts over raw IPs"
    depends_on: []
    can_run_parallel: true
  - id: "ws3"
    goal: "Document the stable-DNS cutover and rollback runbook for operators after the Terraform and tooling contracts are defined."
    acceptance_criteria:
      - "Operator-facing docs explain the precise cutover and rollback path for `canon-memory-dev/memory-layer__csc__canon-systems`: apply/import infra, update the secret to stable DNS values, clear `~/.canon/memory-layer-aws-cache.json` or run `canon doctor --fix-cache`, validate endpoints/health, and restore the previous secret version if rollback is needed."
      - "Focused tests cover the new Terraform contract and any stable-DNS helper/diagnostic behavior added in this task, with no requirement for live AWS mutations in CI."
    implementation_targets:
      - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
      - "docs/ONBOARDING.md"
      - "README.md"
      - "docs/migrations/cognito-ingress-migration.md"
      - "docs/runbooks/auth-migration-rollback.md"
      - "infra/terraform/README.md"
      - "tests/test_auth_migration_assets.py"
      - "tests/test_infra_layout.py"
    verification_tests:
      - "tests/test_auth_migration_assets.py::migration and rollback docs mention stable-domain rollout and rollback sections"
      - "tests/test_infra_layout.py::terraform README retains import guidance and documents ingress-related operator steps"
    depends_on: ["ws1", "ws2"]
    can_run_parallel: false
- parent_orchestration:
  - "Launch one `implementer` subagent per workstream marked can_run_parallel=true in a single parallel subagent call."
  - "Pin each coding subagent to `composer-2-fast`."
  - "For dependent streams, execute only after required upstream streams complete."
  - "After all workstreams finish, merge shard outputs into one HANDOFF_TO_QA block for qa-gate."
- execution_waves_example:
  - wave: 1
    stream_ids: ["ws1", "ws2"]
  - wave: 2
    stream_ids: ["ws3"]
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Produce only the code changes needed to satisfy all acceptance criteria, plus
tests that cover each. Do not refactor unrelated code.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
When running a single implementation stream, emit this block verbatim (filled
in):

HANDOFF_TO_QA
  handoff_id: "handoff_20260424T000000Z_stable_dev_memory_urls"
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

When running multiple parallel streams, each implementer must emit:

HANDOFF_TO_QA_SHARD
  handoff_id: "handoff_20260424T000000Z_stable_dev_memory_urls"
  shard_id: "<workstream id>"
  acceptance_criteria_covered:
    - criterion: "<exact AC text>"
      evidence_files:
        - "path/to/impl.ext:<line range>"
      evidence_tests:
        - "path/to/test.ext::<test name>"
  summary: "<1 sentence on this shard's changes>"
END_HANDOFF_TO_QA_SHARD

Parent must aggregate all shard outputs into one final `HANDOFF_TO_QA` before
invoking `qa-gate`.

Do not declare the task complete without the required handoff block(s).
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
