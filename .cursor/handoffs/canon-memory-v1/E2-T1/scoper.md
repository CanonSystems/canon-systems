# E2-T1 Scoper Packet

**Task:** Provision DynamoDB `canon-state` table + `infra/` wiring
**Wave branch:** `wave/2/canon-memory-v1` (cut from `origin/main` @ `b926a6f` post-Wave-1-merge)
**DoR verdict:** PASS

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E2-T1 opens Wave 2 by standing up the operational-state plane's substrate: a new Terraform module `infra/terraform/modules/dynamodb-canon-state/` plus additive root-wiring that provisions one DynamoDB table named `${var.project_name}-${var.environment}-canon-state` per environment with partition key `pk` (S) = `company_id#repository_id`, sort key `sk` (S) = `plan_id#task_id#workstream_id`, billing_mode `PAY_PER_REQUEST`, TTL enabled on attribute `lease_expires_at`, point-in-time recovery enabled, server-side encryption enabled (AWS-owned KMS key — sufficient for v1 per Backlog §B), and deletion protection enabled. The module emits `table_name` and `table_arn`; the root `main.tf` invokes it once and surfaces those as root-level outputs `state_table_name` and `state_table_arn`. Per-environment isolation is achieved via the existing `${var.project_name}-${var.environment}` name_prefix pattern already used by every other module — no new root variable is added. Per the E0-T4 cloud-execution waiver, this task MUST NOT run `terraform apply`, `terraform import`, `aws` CLI, or any state-mutating cloud command; the only terraform commands permitted in qa-gate are `terraform init -backend=false`, `terraform validate`, and `terraform fmt -check`. A `terraform plan` is explicitly NOT required (it needs AWS credentials the sandbox lacks); operator follow-up is captured in `infra/terraform/README.md` as an additive section with the exact `terraform apply` and per-env `terraform import 'module.state_table.aws_dynamodb_table.this' <name>` commands. Additive-only living-spec mirroring goes to: top of `CHANGELOG.md` [Unreleased] ### Added; new row in `README.md` infra table; new bullet in `docs/SYSTEM-WORKFLOW.md`; new section in `infra/terraform/README.md`; new row in `infra/README.md`. `tests/test_infra_layout.py` gains additive assertions for the new module's three-file layout + root-wiring references (no existing assertion is weakened or removed). Explicitly OUT OF SCOPE: `backend/**` (E2-T2 owns state-api), `src/canon_systems/**` including `src/canon_systems/cli.py` (E2-T3 owns the checkpoint CLI), edits to Wave-0/Wave-1 terraform modules, edits to `.cursor/rules/**` or `.cursor/plans/**`, real AWS apply/import. No git commit/push — parent handles per-task commit on READY_TO_MERGE per rule §9."

  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      plan_id: "canon_memory_platform_build_d21073e1"
      task_id: "E2-T1"
      workstream_id: "wave-2a"
      epic_id: "E2"
      repo_ref: "canon-systems @ wave/2/canon-memory-v1 (cut from origin/main tip b926a6f post-Wave-1-merge)"
      aws_account_ref: "222274634742 (parity with E0-T4 import plane; not touched by this task)"
      aws_region_ref: "us-east-1 (parity with E0-T4; not touched by this task)"

    story:
      title: "Provision DynamoDB state table + infra/"
      userValue: "Wave 2 (E2-T2 state-api + E2-T3 checkpoint CLI) and Wave 4 (resume + concurrency) require a durable, leased, version-checked table for operational state. E2-T1 lands the substrate so E2-T2 can wire REST + conditional-write enforcement in the next task, and so crash-safe agent resume is physically possible. Per-environment isolation means dev/staging/prod agents never collide. PAY_PER_REQUEST + PITR + SSE + TTL gives us crash-safety and auto-expiring leases with zero ops burden."

      acceptanceCriteria:
        - "AC1: New directory `infra/terraform/modules/dynamodb-canon-state/` exists with exactly these files: `main.tf`, `variables.tf`, `outputs.tf`, `README.md`. No other files in the module dir."
        - "AC2: `main.tf` declares exactly one resource `aws_dynamodb_table.this` with: `name = \"${var.name_prefix}-canon-state\"`; `billing_mode = \"PAY_PER_REQUEST\"`; `hash_key = \"pk\"`; `range_key = \"sk\"`; `attribute { name=\"pk\" type=\"S\" }`; `attribute { name=\"sk\" type=\"S\" }`; `ttl { attribute_name = \"lease_expires_at\" enabled = true }`; `point_in_time_recovery { enabled = true }`; `server_side_encryption { enabled = true }` (AWS-owned key; no `kms_key_arn`); `deletion_protection_enabled = true`; and `tags = { Purpose = \"canon-state\" }` (default_tags from the root provider augment this)."
        - "AC3: `variables.tf` declares exactly one input `name_prefix` (type=string, no default, with description). Nothing else. This mirrors the `modules/s3-artifacts` / `modules/secrets` pattern already used in the repo."
        - "AC4: `outputs.tf` declares exactly two outputs: `table_name` (value=`aws_dynamodb_table.this.name`, with description) and `table_arn` (value=`aws_dynamodb_table.this.arn`, with description). No other outputs."
        - "AC5: `README.md` documents: purpose (Canon Memory Platform operational-state plane per Backlog §B), inputs (`name_prefix` — semantics + expected format), outputs (`table_name`, `table_arn`), key schema (`pk = company_id#repository_id`, `sk = plan_id#task_id#workstream_id`), TTL semantics (auto-expires items whose `lease_expires_at` epoch-seconds value is past — enforces Backlog §B lease semantics), and that E2-T1 does NOT run `terraform apply` (deferred to operator follow-up). At least one fenced code example of module invocation."
        - "AC6: `infra/terraform/main.tf` gains exactly one additive `module \"state_table\"` block after the existing `module \"rds\"` block, invoking `./modules/dynamodb-canon-state` with `name_prefix = \"${var.project_name}-${var.environment}\"`. No existing module blocks are modified, reordered, or renamed."
        - "AC7: `infra/terraform/outputs.tf` gains exactly two additive root-level outputs: `state_table_name` (value=`module.state_table.table_name`) and `state_table_arn` (value=`module.state_table.table_arn`), each with a description. No existing outputs are modified."
        - "AC8: `infra/terraform/variables.tf` is NOT modified. Per-env isolation is achieved via the existing `${var.project_name}-${var.environment}` name_prefix pattern (environment var already exists from E0-T4). A single-line comment in the new module's README explicitly cites this pattern."
        - "AC9: `infra/terraform/terraform.tfvars`, `infra/terraform/providers.tf`, and `infra/terraform/versions.tf` are NOT modified (no new providers; `hashicorp/aws ~> 5.0` already covers `aws_dynamodb_table`)."
        - "AC10: Per-environment isolation is proven deterministically by: running `terraform console` mentally over the code — for `environment=dev` the table name is `canon-systems-v2-dev-canon-state`; for `environment=staging` it is `canon-systems-v2-staging-canon-state`; for `environment=prod` it is `canon-systems-v2-prod-canon-state`. README documents this and states that switching environments creates/uses a different physical table."
        - "AC11: `cd infra/terraform && terraform init -backend=false && terraform validate` exits 0 and prints `Success! The configuration is valid.`. qa-gate captures full stdout/stderr."
        - "AC12: `terraform fmt -check -recursive infra/terraform/modules/dynamodb-canon-state/` exits 0 (module files are canonically formatted)."
        - "AC13: NO `terraform plan`, `terraform apply`, `terraform import`, `terraform destroy`, `terraform refresh`, or any `aws` CLI invocation is performed during implementation or qa-gate. If any of these are attempted, the task is rejected."
        - "AC14: `infra/terraform/README.md` gains ONE new top-level section `## E2-T1 — DynamoDB canon-state table` appended after the existing `## Deferred items` section, containing: (a) brief description of the new module + per-env table naming, (b) the additive `terraform apply` operator command, (c) the per-env `terraform import 'module.state_table.aws_dynamodb_table.this' \"${var.project_name}-${var.environment}-canon-state\"` commands for dev/staging/prod, (d) explicit statement that E2-T1 ran zero cloud commands. No existing sections are modified."
        - "AC15: `infra/README.md` gets ONE additive bullet under the existing terraform row (or a new row under it) describing the new DynamoDB module. No existing rows are reflowed."
        - "AC16: `CHANGELOG.md` [Unreleased] ### Added gets a NEW TOP-OF-LIST bullet: `E2-T1: DynamoDB canon-state table module (`infra/terraform/modules/dynamodb-canon-state/`) + root wiring + outputs (`state_table_name`, `state_table_arn`); PAY_PER_REQUEST, TTL on `lease_expires_at`, PITR, SSE; per-env isolation via `${project}-${environment}-canon-state`; no cloud commands executed.` Bullet MUST land above all existing E1-* bullets to match Keep-a-Changelog newest-first order."
        - "AC17: `README.md` infra table (if present) or the nearest infra-referring paragraph gets ONE additive sentence or row referring to the new module. No existing text is rewritten."
        - "AC18: `docs/SYSTEM-WORKFLOW.md` gets ONE additive bullet under the nearest infra/§10 section referencing the new table, consistent with the E0-T4 augment pattern. No existing bullets are removed or reflowed."
        - "AC19: `tests/test_infra_layout.py` gains additive assertions: (a) the four files under `infra/terraform/modules/dynamodb-canon-state/` exist and are non-empty; (b) `infra/terraform/main.tf` contains the substring `module \"state_table\"` and `./modules/dynamodb-canon-state`; (c) `infra/terraform/outputs.tf` contains the substrings `state_table_name` and `state_table_arn`. No existing assertion is removed or weakened."
        - "AC20: Root `pytest -q` exits 0. `bash scripts/smoke-test.sh` exits 0 (terraform validate path included)."
        - "AC21: Zero diffs under forbidden surfaces (see `out_of_scope_paths` + `forbidden_surface`). Explicitly: `src/canon_systems/cli.py` has zero diff."

      done_signal:
        - "`cd infra/terraform && terraform init -backend=false` exits 0"
        - "`cd infra/terraform && terraform validate` exits 0 (prints 'Success! The configuration is valid.')"
        - "`terraform fmt -check -recursive infra/terraform/modules/dynamodb-canon-state/` exits 0"
        - "`pytest tests/test_infra_layout.py -q` exits 0"
        - "Root `pytest -q` exits 0"
        - "`bash scripts/smoke-test.sh` exits 0"
        - "`git diff --name-only wave/2/canon-memory-v1..HEAD` intersected with the forbidden-surface globs is empty"
        - "No AWS CLI or `terraform apply|import|plan|destroy|refresh` invocation in the task transcript"

      deferred_done_signal_from_backlog:
        - criterion: "terraform apply / cdk deploy succeeds in dev with no drift"
          deferred_to: "OQ-E2-T1-01 — operator-run apply post-merge (mirrors E0-T4 OQ-E0-T4-01 waiver)"

    repository:
      primaryLanguages: ["HCL (Terraform)", "Markdown", "Python 3.10+ (tests)"]
      testFramework: "pytest (root)"
      terraform_version_required: ">= 1.5.0 (already pinned in infra/terraform/versions.tf)"
      provider_pins_unchanged: { aws: "~> 5.0", random: "~> 3.6" }
      relevantFiles:
        - "infra/terraform/main.tf (additive edit: new module block)"
        - "infra/terraform/outputs.tf (additive edit: two new outputs)"
        - "infra/terraform/variables.tf (read only — reference for existing `environment` + `project_name` vars)"
        - "infra/terraform/terraform.tfvars (read only — reference for environment=dev default)"
        - "infra/terraform/versions.tf (read only — aws ~> 5.0 already covers aws_dynamodb_table)"
        - "infra/terraform/providers.tf (read only — default_tags already set)"
        - "infra/terraform/modules/s3-artifacts/{main,variables,outputs}.tf (convention reference)"
        - "infra/terraform/modules/secrets/{main,variables,outputs}.tf (convention reference)"
        - "infra/terraform/README.md (additive section append)"
        - "infra/README.md (additive row/bullet)"
        - "CHANGELOG.md (top-of-Unreleased-Added)"
        - "README.md (additive)"
        - "docs/SYSTEM-WORKFLOW.md (additive)"
        - "tests/test_infra_layout.py (additive assertions)"
        - "docs/MEMORY-PLATFORM-BACKLOG.md §B (schema authority; read only)"
        - ".cursor/handoffs/canon-memory-v1/E0-T4/scoper.md (infra-task precedent)"

    constraints:
      dependencies: ["E0-T4 (infra/terraform/ exists and validates) — satisfied"]
      mustNotBreak:
        - "`cd infra/terraform && terraform validate` (must still succeed)"
        - "Root `pytest -q` including existing tests/test_infra_layout.py assertions"
        - "`bash scripts/smoke-test.sh`"
        - "Existing modules vpc, ecr, ecs-fargate, rds-postgres, s3-artifacts, secrets (zero edits)"
        - "Existing root outputs (no renames, no removals)"
        - "infra/auth-ingress/** (zero edits)"
        - "CHANGELOG structure (Keep-a-Changelog; newest-first in [Unreleased])"

    invariants:
      rule_compliance:
        - "§1 agent chain respected: parent → scoper (this) → cursor-pilot → implementer → qa-gate → release-orchestrator"
        - "§2 non-markdown writes only after valid scoper.md + cursor-pilot.md CURSOR_PILOT_PROMPT on disk"
        - "§3 pre-flight Step-0 context assessment is parent's responsibility (already performed upstream)"
        - "§4 packet persistence at `.cursor/handoffs/canon-memory-v1/E2-T1/scoper.md` (this file)"
        - "§5 DoR rejections (if any) produce the telemetry triple — not applicable here since DoR=PASS"
        - "§6 merge gates cumulative — enforced by qa-gate + release-orchestrator downstream"
        - "§7 wave boundary re-ran Step 0 at wave/2 start — parent's responsibility"
        - "§8 escape hatch — no conflict with user intent"
        - "§9 per-task commit protocol — parent handles on READY_TO_MERGE, NOT this task"
        - "§10 wave branch `wave/2/canon-memory-v1` cut from main post-wave-1-merge — parent's responsibility"
      cloud_waiver_honored: "YES — `terraform validate` only; no apply/import/plan/destroy/refresh; no aws CLI. Mirrors E0-T4 precedent."
      additive_only_shared_surfaces:
        - "CHANGELOG.md: newest bullet at TOP of [Unreleased] ### Added"
        - "README.md: additive only (no reflow)"
        - "docs/SYSTEM-WORKFLOW.md: additive only"
        - "infra/terraform/README.md: additive append (new `## E2-T1 …` section after `## Deferred items`)"
        - "infra/README.md: additive only"
      cli_py_excluded_for_this_task: "YES — `src/canon_systems/cli.py` MUST have zero diff. E2-T3 owns the checkpoint CLI."
      convention_deviations_documented:
        - "Module-level `README.md` is added for the new module despite prior modules (vpc/ecr/…) having none. This is explicitly required by the parent brief and is additive — no existing module is changed to match. Future modules MAY follow this new convention; not required."

    non_goals:
      - "Do NOT implement backend/state-api (REST endpoints, conditional writes, lease enforcement) — that is E2-T2."
      - "Do NOT implement `canon checkpoint read|write|lease` CLI — that is E2-T3."
      - "Do NOT edit `src/canon_systems/cli.py` (zero diff required)."
      - "Do NOT run `terraform apply`, `terraform import`, `terraform plan`, `terraform destroy`, `terraform refresh`, or any `aws` CLI."
      - "Do NOT declare a remote state backend (S3 + DynamoDB lock) — deferred per E0-T4 OQ-E0-T4-05."
      - "Do NOT rename `project_name`, `environment`, or any existing resource."
      - "Do NOT add Global Secondary Indexes. Backlog §B uses pk/sk only; GSIs are out of scope for v1."
      - "Do NOT add DynamoDB Streams. Event emission is handled by state-api (E2-T2) via canonical events, not DDB streams."
      - "Do NOT add CloudWatch alarms / autoscaling. PAY_PER_REQUEST makes both irrelevant."
      - "Do NOT edit `.cursor/rules/**` or `.cursor/plans/**` (frozen)."

    target_files:
      to_create:
        - "infra/terraform/modules/dynamodb-canon-state/main.tf"
        - "infra/terraform/modules/dynamodb-canon-state/variables.tf"
        - "infra/terraform/modules/dynamodb-canon-state/outputs.tf"
        - "infra/terraform/modules/dynamodb-canon-state/README.md"
      to_modify_additive_only:
        - "infra/terraform/main.tf  # append one module block; no edits elsewhere"
        - "infra/terraform/outputs.tf  # append two outputs; no edits elsewhere"
        - "infra/terraform/README.md  # append one section after `## Deferred items`"
        - "infra/README.md  # append one row/bullet"
        - "CHANGELOG.md  # prepend one bullet at top of [Unreleased] ### Added"
        - "README.md  # append one sentence or row in the infra-referring paragraph"
        - "docs/SYSTEM-WORKFLOW.md  # append one bullet near infra/§10 augment"
        - "tests/test_infra_layout.py  # append assertions; do not weaken existing ones"
      explicitly_excluded_zero_diff:
        - "src/canon_systems/cli.py  # E2-T3 owns; MUST be untouched in E2-T1"
        - "infra/terraform/variables.tf  # no new root vars required"
        - "infra/terraform/terraform.tfvars  # no default changes"
        - "infra/terraform/providers.tf  # unchanged"
        - "infra/terraform/versions.tf  # unchanged"
        - "infra/terraform/modules/{vpc,ecr,ecs-fargate,rds-postgres,s3-artifacts,secrets}/**  # not owned by E2-T1"
        - "infra/auth-ingress/**  # separate workstream"

    forbidden_surfaces:
      hard_forbidden:
        - "backend/**  # E2-T2 owns state-api"
        - "src/canon_systems/**  # E2-T3 owns checkpoint CLI; zero diff here"
        - ".cursor/rules/**  # frozen"
        - ".cursor/plans/**  # frozen"
        - "docs/MEMORY-PLATFORM-PLAN.md, docs/MEMORY-PLATFORM-BACKLOG.md  # frozen Wave-0 docs"
        - "docs/WAVE-0-AUDIT.md, docs/WAVE-0-CLOSEOUT.md, docs/E0-T3-MIGRATION-NOTES.md, docs/E0-T4-INFRA-IMPORT.md, docs/DEPRECATIONS.md, docs/OBSIDIAN-MIND-CATALOGUE.md  # frozen Wave-0 artifacts"
        - "infra/terraform/modules/{vpc,ecr,ecs-fargate,rds-postgres,s3-artifacts,secrets}/**  # Wave-0 modules, unrelated"
        - "infra/auth-ingress/**"
        - "canon-systems-v2/**  # sibling, read-only"
        - ".github/workflows/**"
        - "pyproject.toml (root), pytest.ini, requirements-dev.txt"
        - "Any Dockerfile, deploy/**"
      no_cloud_commands:
        - "terraform apply, terraform destroy, terraform import, terraform plan, terraform refresh"
        - "aws *, aws-vault *, any AWS SDK / boto3 invocation"
      permitted_cloud_commands:
        - "terraform init -backend=false"
        - "terraform validate"
        - "terraform fmt -check"

    acceptable_scope_expansion:
      pre_authorized:
        - "Add a `tags` block to the new `aws_dynamodb_table` resource (e.g., Purpose=canon-state, Wave=E2). Non-functional; provider default_tags already cover Project/Environment/ManagedBy."
        - "Add `deletion_protection_enabled = true` to the resource (included in AC2) — protects v1 data from accidental destroy."
        - "Within-minor AWS provider bump (`~> 5.0` → `~> 5.x`) ONLY if `terraform validate` fails on current 5.100.0; document in README addendum."
        - "Adding `infra/terraform/modules/dynamodb-canon-state/` to any .gitignore comment for terraform artifacts if needed (no new ignore rules required since module dir itself is the artifact)."
      not_pre_authorized:
        - "Adding GSIs, LSIs, streams, replica regions (Global Tables), provisioned capacity, autoscaling, backup plans, or KMS CMK."
        - "Introducing a remote state backend (S3 + DynamoDB lock) — deferred to post-E2 per OQ-E0-T4-05."
        - "Renaming or restructuring existing Wave-0 modules."
        - "Adding new root variables (e.g., `state_table_enabled`, `state_table_name_override`) — not needed; per-env isolation works via existing `environment`."
        - "Writing code in `backend/**` or `src/canon_systems/**`."
        - "Running `terraform apply` or any cloud-mutating command."

    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
      story_title: "pass"
      story_userValue: "pass"
      story_acceptanceCriteria: "pass (21 testable ACs)"
      repository_primaryLanguages: "pass"
      repository_testFramework: "pass (pytest root + terraform validate in smoke)"
      constraints_dependencies: "pass (E0-T4 satisfied)"
      constraints_mustNotBreak: "pass"
      risks_and_assumptions_openQuestions: "pass (all non-blocking)"
      prior_work_references: "pass"
      cloud_waiver_honored: "pass"
      additive_only_discipline: "pass"
      forbidden_surfaces_enumerated: "pass"
      overall: "pass"

    ac_traceability:
      - criterion: "AC1: module dir exists with exactly 4 files"
        implementation_targets: ["infra/terraform/modules/dynamodb-canon-state/{main.tf,variables.tf,outputs.tf,README.md}"]
        verification_tests: ["tests/test_infra_layout.py::test_dynamodb_canon_state_module_files_exist"]
      - criterion: "AC2: main.tf declares aws_dynamodb_table.this with required attrs"
        implementation_targets: ["infra/terraform/modules/dynamodb-canon-state/main.tf"]
        verification_tests: ["qa-gate shell: terraform validate", "tests/test_infra_layout.py (substring assertions: billing_mode, PAY_PER_REQUEST, lease_expires_at, hash_key pk, range_key sk, point_in_time_recovery, server_side_encryption)"]
      - criterion: "AC3: variables.tf declares only name_prefix"
        implementation_targets: ["infra/terraform/modules/dynamodb-canon-state/variables.tf"]
        verification_tests: ["tests/test_infra_layout.py::test_dynamodb_module_has_only_name_prefix_var (substring + absence checks)"]
      - criterion: "AC4: outputs.tf exposes table_name + table_arn"
        implementation_targets: ["infra/terraform/modules/dynamodb-canon-state/outputs.tf"]
        verification_tests: ["tests/test_infra_layout.py::test_dynamodb_module_outputs"]
      - criterion: "AC5: README.md documents inputs/outputs/key-schema/TTL"
        implementation_targets: ["infra/terraform/modules/dynamodb-canon-state/README.md"]
        verification_tests: ["tests/test_infra_layout.py::test_dynamodb_module_readme_mentions_keys_ttl_ppr (substring assertions: 'pk', 'sk', 'lease_expires_at', 'PAY_PER_REQUEST')"]
      - criterion: "AC6: root main.tf gains one additive module block"
        implementation_targets: ["infra/terraform/main.tf"]
        verification_tests: ["tests/test_infra_layout.py::test_root_wires_state_table_module (substring 'module \"state_table\"' and './modules/dynamodb-canon-state')", "terraform validate"]
      - criterion: "AC7: root outputs.tf gains state_table_name + state_table_arn"
        implementation_targets: ["infra/terraform/outputs.tf"]
        verification_tests: ["tests/test_infra_layout.py::test_root_exposes_state_table_outputs"]
      - criterion: "AC8-AC9: root variables.tf / terraform.tfvars / providers.tf / versions.tf unchanged"
        implementation_targets: ["infra/terraform/{variables.tf,terraform.tfvars,providers.tf,versions.tf}"]
        verification_tests: ["qa-gate: git diff --name-only shows zero entries for these four paths"]
      - criterion: "AC10: per-env isolation deterministic via name_prefix"
        implementation_targets: ["infra/terraform/main.tf (module invocation with ${var.project_name}-${var.environment})"]
        verification_tests: ["module README documents dev/staging/prod names", "terraform validate with each environment tfvar override mentally verified (optional: document in README, no new test needed)"]
      - criterion: "AC11: terraform init -backend=false && terraform validate exits 0"
        implementation_targets: ["all infra/terraform files"]
        verification_tests: ["qa-gate shell: cd infra/terraform && terraform init -backend=false && terraform validate"]
      - criterion: "AC12: terraform fmt -check passes for new module"
        implementation_targets: ["infra/terraform/modules/dynamodb-canon-state/**"]
        verification_tests: ["qa-gate shell: terraform fmt -check -recursive infra/terraform/modules/dynamodb-canon-state/"]
      - criterion: "AC13: zero cloud mutation commands"
        implementation_targets: ["n/a — process discipline"]
        verification_tests: ["qa-gate transcript search for 'terraform apply|import|plan|destroy|refresh' and 'aws ' returns zero matches"]
      - criterion: "AC14: infra/terraform/README.md additive section"
        implementation_targets: ["infra/terraform/README.md"]
        verification_tests: ["tests/test_infra_layout.py::test_infra_terraform_readme_e2t1_section (substring '## E2-T1' + import command substring)"]
      - criterion: "AC15-AC17: living-spec additive edits"
        implementation_targets: ["infra/README.md, CHANGELOG.md, README.md"]
        verification_tests: ["tests/test_infra_layout.py or dedicated grep in qa-gate: CHANGELOG.md [Unreleased] top-bullet contains 'E2-T1'; README.md mentions canon-state"]
      - criterion: "AC18: docs/SYSTEM-WORKFLOW.md additive"
        implementation_targets: ["docs/SYSTEM-WORKFLOW.md"]
        verification_tests: ["qa-gate grep: new bullet present; git diff shows only additions"]
      - criterion: "AC19: tests/test_infra_layout.py additive assertions"
        implementation_targets: ["tests/test_infra_layout.py"]
        verification_tests: ["pytest tests/test_infra_layout.py -q exits 0"]
      - criterion: "AC20: root pytest + smoke green"
        implementation_targets: ["all"]
        verification_tests: ["pytest -q at repo root", "bash scripts/smoke-test.sh"]
      - criterion: "AC21: zero diff on forbidden surfaces incl. src/canon_systems/cli.py"
        implementation_targets: ["n/a — negative assertion"]
        verification_tests: ["qa-gate: git diff --name-only wave/2/canon-memory-v1..HEAD intersected with forbidden globs is empty"]

    risks_and_assumptions:
      assumptions:
        - "The existing `project_name`+`environment` tfvar pattern is the intended per-env isolation mechanism (parent brief explicitly says 'prefer that pattern for consistency')."
        - "AWS-owned KMS key is acceptable for v1 server-side encryption (Backlog §B + parent brief both say so)."
        - "`hashicorp/aws ~> 5.0` covers `aws_dynamodb_table` including `point_in_time_recovery`, `ttl`, `server_side_encryption`, and `deletion_protection_enabled` (confirmed: these are stable since aws provider 3.x)."
        - "Per-env workspace is achieved by running terraform with different -var-file values (dev/staging/prod tfvars), not via `terraform workspace new` — matches existing pattern. Operator follow-up README documents this."
        - "`terraform validate` is sufficient for qa-gate (no credentials needed); `terraform plan` is explicitly waived."
        - "Current AWS provider cached in .terraform/ (5.100.0) supports all required DynamoDB features — no bump needed."
      openQuestions:
        - id: "OQ-E2-T1-01"
          question: "Zero-drift verification via `terraform plan` against a live DynamoDB table."
          proposed_resolution: "Deferred to operator follow-up post-wave-2 merge (mirrors E0-T4 OQ-E0-T4-01). README import manifest includes the per-env command."
          blocking_for_this_task: false
        - id: "OQ-E2-T1-02"
          question: "Should the module expose `deletion_protection_enabled` as a configurable var (default true) for future dev-env wipes?"
          proposed_resolution: "NO in v1 — hard-code true. Add as tf var only if a real need emerges; keeps module surface minimal."
          blocking_for_this_task: false
        - id: "OQ-E2-T1-03"
          question: "Customer-managed KMS key (CMK) for SSE instead of AWS-owned?"
          proposed_resolution: "NO in v1 per Backlog §B explicit statement ('AWS-owned key sufficient for v1'). Revisit in Wave 6/7 hardening."
          blocking_for_this_task: false
        - id: "OQ-E2-T1-04"
          question: "DynamoDB Streams for canonical-event emission?"
          proposed_resolution: "NO. E2-T2 emits canonical `checkpoint_write` events at the application layer via the canonical API, not via DDB streams. Backlog §B mandates app-layer event emission."
          blocking_for_this_task: false
        - id: "OQ-E2-T1-05"
          question: "Should root outputs for state table be marked `sensitive`?"
          proposed_resolution: "NO — ARN and name are not sensitive. Consistent with existing non-sensitive outputs (bucket ARN, ECR URLs)."
          blocking_for_this_task: false
        - id: "OQ-E2-T1-06"
          question: "Module README as a precedent for all future modules?"
          proposed_resolution: "Document as additive-only; do not retrofit existing modules. Future modules MAY follow. Flagged in `convention_deviations_documented`."
          blocking_for_this_task: false

    dor_telemetry:
      dor_questions_answered:
        Q_repo_state_clean_for_infra_edits: "YES — wave/2 branch cut post-wave-1-merge at b926a6f; only stray .egg-info/.terraform cache files in git status (ignored)."
        Q_environment_isolation_mechanism: "existing ${project_name}-${environment} name_prefix pattern — NO new root var."
        Q_billing_mode: "PAY_PER_REQUEST (Backlog §B + parent brief)."
        Q_ttl_attribute: "lease_expires_at (Backlog §B; maps to state-api lease.expires_at in E2-T2)."
        Q_pitr_enabled: "YES."
        Q_sse: "YES, AWS-owned KMS (v1)."
        Q_deletion_protection: "YES (v1 safety)."
        Q_streams: "NO (app-layer events)."
        Q_gsi: "NO (pk/sk only per Backlog §B)."
        Q_remote_backend: "NO (deferred, OQ-E0-T4-05)."
        Q_outputs: "table_name + table_arn at root; same names at module."
        Q_cloud_apply: "WAIVED per E0-T4 precedent; validate-only in qa-gate."
        Q_plan_required: "NO (needs credentials; waived)."
        Q_module_readme: "YES (parent brief explicit; deviation from existing modules — additive)."
        Q_cli_py_touched: "NO — zero diff required."
        Q_wave_branch: "wave/2/canon-memory-v1."
      next_phase_entry: "cursor-pilot should consume this packet as the sole scope source. No additional discovery required; implementer may proceed directly to TF authoring."

    prior_work_references:
      - ".cursor/handoffs/canon-memory-v1/E0-T4/scoper.md (infra-task precedent; cloud waiver shape; import manifest convention)"
      - ".cursor/handoffs/canon-memory-v1/E1-T1/scoper.md (HANDOFF_TO_CURSOR_PILOT block-shape precedent)"
      - "docs/MEMORY-PLATFORM-BACKLOG.md §B (authoritative DynamoDB schema)"
      - "docs/MEMORY-PLATFORM-BACKLOG.md E2-T1 task def (lines ~277-287)"
      - ".cursor/rules/memory-platform-build-discipline.mdc §§1-10 (hard-lock)"
      - ".cursor/plans/canon_memory_platform_build_d21073e1.plan.md (plan)"
      - "infra/terraform/modules/s3-artifacts/**, modules/secrets/** (three-file module convention)"
      - "infra/terraform/{main.tf,outputs.tf,variables.tf} (root-wiring pattern: ${project}-${environment} name_prefix)"
      - "infra/terraform/README.md (E0-T4 augment — import-manifest + deferred-items section to be mirrored for E2-T1)"
      - "tests/test_infra_layout.py (additive-assertion pattern from E0-T4)"
      - "CHANGELOG.md [Unreleased] (Keep-a-Changelog newest-first bullet discipline)"

END_HANDOFF_TO_CURSOR_PILOT
```
