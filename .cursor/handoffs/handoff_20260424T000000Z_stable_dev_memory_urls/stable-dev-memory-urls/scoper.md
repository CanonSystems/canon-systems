HANDOFF_TO_CURSOR_PILOT
  scope_summary: Implement the smallest safe repo-only slice of `stable-dev-memory-urls`: make `infra/terraform` capable of fronting the current dev ECS baseline with stable ingress/DNS, align repo-owned secret/tooling defaults around stable `https://` memory URLs, and document the exact cutover/rollback path. Do not attempt a full external rollout or a multi-service ECS redesign in this task; ACM issuance, Route53 ownership, Terraform apply/import, and Secrets Manager rotation remain operator follow-up, but the repo should become ready for that rollout.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260424T000000Z_stable_dev_memory_urls"
      company_id: "CSC"
      repository_id: "canon-systems"
    story:
      title: "Add stable dev memory URL support for the current ECS dev stack"
      userValue: "Canon developers and operators need dev memory endpoints that survive ECS redeploys so `canon` commands stop depending on ephemeral public task IPs and stale local cache entries."
      acceptanceCriteria:
        - "The Terraform root and `infra/terraform/modules/ecs-fargate` can model stable ingress for the current dev `ecs_baseline` service without changing existing stack naming/import assumptions: configurable load-balancer/target-group/DNS inputs and outputs exist, and the ECS service can attach to a target group when ingress is enabled."
        - "Repo-owned secret/default tooling and diagnostics treat stable HTTPS DNS as the canonical shape for `KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, `MEMORY_ADAPTER_URL`, and `CANON_STATE_API_URL`, while preserving the current shared-base behavior where `knowledge-api` mounts `POST /memory/search`."
        - "Operator-facing docs explain the precise cutover and rollback path for `canon-memory-dev/memory-layer__csc__canon-systems`: apply/import infra, update the secret to stable DNS values, clear `~/.canon/memory-layer-aws-cache.json` or run `canon doctor --fix-cache`, validate endpoints/health, and restore the previous secret version if rollback is needed."
        - "Focused tests cover the new Terraform contract and any stable-DNS helper/diagnostic behavior added in this task, with no requirement for live AWS mutations in CI."
    repository:
      primaryLanguages: ["Python", "HCL", "Shell", "Markdown"]
      testFramework: "pytest"
      relevantFiles:
        - "infra/terraform/main.tf"
        - "infra/terraform/variables.tf"
        - "infra/terraform/outputs.tf"
        - "infra/terraform/README.md"
        - "infra/terraform/modules/ecs-fargate/main.tf"
        - "infra/terraform/modules/ecs-fargate/variables.tf"
        - "infra/terraform/modules/ecs-fargate/outputs.tf"
        - "src/canon_systems/secrets_submit.py"
        - "src/canon_systems/doctor_cli.py"
        - "scripts/migrate_memory_secrets.py"
        - "scripts/validate_memory_endpoints.py"
        - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
        - "docs/ONBOARDING.md"
        - "README.md"
        - "docs/migrations/cognito-ingress-migration.md"
        - "docs/runbooks/auth-migration-rollback.md"
        - "tests/test_infra_layout.py"
        - "tests/test_doctor.py"
        - "tests/test_auth_migration_assets.py"
        - "tests/test_secrets_submit.py"
    constraints:
      dependencies:
        - "`infra/terraform` currently models one `ecs_baseline` service only; this task must extend that contract rather than attempt a repo-wide split into separate `knowledge-api` / `knowledge-worker` / `memory-adapter` ECS services."
        - "Preserve the live `canon-systems-v2` naming/import assumptions documented in `infra/terraform/README.md` and `infra/terraform/terraform.tfvars`."
        - "Do not edit `.cursor/plans/memory-ablation-parallelism_3dca6a5c.plan.md`."
        - "`infra/auth-ingress/` is a separate workstream; its ALB/Route53 pattern may be referenced for conventions, but coupling to it must be explicit and documented."
      mustNotBreak:
        - "Current `canon e2e-check --agent` / `canon memory-health` flows that resolve URLs from AWS Secrets Manager plus `~/.canon/memory-layer-aws-cache.json`."
        - "Current `knowledge-api` `/healthz` and mounted `POST /memory/search` behavior used by `MEMORY_ADAPTER_URL`."
        - "Existing Terraform layout/import contracts enforced by `tests/test_infra_layout.py`."
        - "Existing stable-domain assumptions already present in `src/canon_systems/secrets_submit.py`, `scripts/migrate_memory_secrets.py`, and the auth-migration docs."
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "The Terraform root and `infra/terraform/modules/ecs-fargate` can model stable ingress for the current dev `ecs_baseline` service without changing existing stack naming/import assumptions: configurable load-balancer/target-group/DNS inputs and outputs exist, and the ECS service can attach to a target group when ingress is enabled."
        implementation_targets: ["infra/terraform/modules/ecs-fargate/main.tf", "infra/terraform/modules/ecs-fargate/variables.tf", "infra/terraform/modules/ecs-fargate/outputs.tf", "infra/terraform/main.tf", "infra/terraform/variables.tf", "infra/terraform/outputs.tf", "infra/terraform/README.md"]
        verification_tests: ["tests/test_infra_layout.py::assert ecs-fargate module and root expose ingress variables/outputs while preserving required file layout and import-readme contracts"]
      - criterion: "Repo-owned secret/default tooling and diagnostics treat stable HTTPS DNS as the canonical shape for `KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, `MEMORY_ADAPTER_URL`, and `CANON_STATE_API_URL`, while preserving the current shared-base behavior where `knowledge-api` mounts `POST /memory/search`."
        implementation_targets: ["src/canon_systems/secrets_submit.py", "src/canon_systems/doctor_cli.py", "scripts/migrate_memory_secrets.py", "scripts/validate_memory_endpoints.py", "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md", "README.md"]
        verification_tests: ["tests/test_secrets_submit.py::template/default payload emits stable HTTPS DNS and aligned CANON_STATE_API_URL", "tests/test_doctor.py::doctor covers literal-IPv4 guidance for env and any newly-added cache inspection behavior", "tests/test_auth_migration_assets.py::secret migration and endpoint validation helpers prefer domain hosts over raw IPs"]
      - criterion: "Operator-facing docs explain the precise cutover and rollback path for `canon-memory-dev/memory-layer__csc__canon-systems`: apply/import infra, update the secret to stable DNS values, clear `~/.canon/memory-layer-aws-cache.json` or run `canon doctor --fix-cache`, validate endpoints/health, and restore the previous secret version if rollback is needed."
        implementation_targets: ["infra/terraform/README.md", "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md", "docs/ONBOARDING.md", "README.md", "docs/migrations/cognito-ingress-migration.md", "docs/runbooks/auth-migration-rollback.md"]
        verification_tests: ["tests/test_auth_migration_assets.py::migration and rollback docs mention stable-domain rollout and rollback sections", "tests/test_infra_layout.py::terraform README retains import guidance and documents ingress-related operator steps"]
      - criterion: "Focused tests cover the new Terraform contract and any stable-DNS helper/diagnostic behavior added in this task, with no requirement for live AWS mutations in CI."
        implementation_targets: ["tests/test_infra_layout.py", "tests/test_doctor.py", "tests/test_auth_migration_assets.py", "tests/test_secrets_submit.py"]
        verification_tests: ["tests/test_infra_layout.py::new ingress contract assertions", "tests/test_doctor.py::stable-url diagnostic assertions", "tests/test_auth_migration_assets.py::domain migration helper assertions", "tests/test_secrets_submit.py::stable secret template assertions"]
    risks_and_assumptions:
      assumptions:
        - "Repo ref verified at branch `main`, commit `02dcefec366a079d72e8f4320b8e0e938568927d`, remote `git@github.com:CanonSystems/canon-systems.git`."
        - "Current resolved secret cache for `canon-memory-dev/memory-layer__csc__canon-systems` still points `KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, and `MEMORY_ADAPTER_URL` at `http://54.242.74.242:8080`, with `_memory_layer_note` explicitly saying to replace it with stable ingress."
        - "The minimum safe scope is ingress support for the existing single `ecs_baseline` service plus secret/doc/tooling alignment; actual ACM certificate values, hosted-zone IDs, target-group ARNs, Terraform apply/import, and Secrets Manager writes are operator-owned follow-up."
        - "Because `backend/knowledge-api/app/main.py` mounts `memory_adapter.api.router.search_router`, it is acceptable for the first-cut stable DNS plan to keep `MEMORY_ADAPTER_URL` aligned with `KNOWLEDGE_API_URL`."
        - "Canon retrieval degraded for this scoping pass: `.canon/memory/context-latest.md` is stale for `IMC/innermost`, `canon graph query` in this readonly environment hit the local cache-write path, and `canon checkpoint read` resolved `CANON_STATE_API_URL` to `http://localhost:8080` and refused connection."
      openQuestions: []
    prior_work_references: []
END_HANDOFF_TO_CURSOR_PILOT
