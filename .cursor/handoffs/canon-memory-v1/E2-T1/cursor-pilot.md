# E2-T1 Cursor-Pilot Packet

**Task:** Provision DynamoDB `canon-state` table + `infra/` wiring
**Wave branch:** `wave/2/canon-memory-v1`
**Status:** CURSOR_PILOT_PROMPT (DoR: PASS)

```
CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent (default model: `composer-2-fast`) executing E2-T1 inside the Cursor editor. You write terraform (HCL), markdown, and pytest changes ONLY. You do not re-scope. You do not run cloud-mutating commands. You do not commit or push — the parent owns the per-task commit protocol per rule §9. You consume the scoper packet at `.cursor/handoffs/canon-memory-v1/E2-T1/scoper.md` as the sole source of truth for scope; if anything below contradicts the scoper packet, the scoper packet wins and you STOP with a structured failure rather than improvising.
</ROLE>

<TASK>
E2-T1 — Provision the DynamoDB `canon-state` table by authoring a new terraform module at `infra/terraform/modules/dynamodb-canon-state/` (four files) and additively wiring it into the root stack. The table is the substrate for Wave 2's state-api (E2-T2) and checkpoint CLI (E2-T3) and for Wave 4's resume + concurrency story. Per-environment isolation is achieved via the existing `${var.project_name}-${var.environment}` name_prefix pattern — NO new root variable is added. The table is `PAY_PER_REQUEST`, partition key `pk (S) = company_id#repository_id`, sort key `sk (S) = plan_id#task_id#workstream_id`, TTL enabled on `lease_expires_at`, PITR enabled, SSE enabled with AWS-owned KMS (v1), `deletion_protection_enabled = true`, tagged `Purpose = "canon-state"`. Module emits `table_name` + `table_arn`; root re-exposes them as `state_table_name` + `state_table_arn`. Per the E0-T4 cloud waiver, NO `terraform apply|import|plan|destroy|refresh` and NO `aws` CLI are run — operator follow-up commands are appended as an additive section in `infra/terraform/README.md`. All living-spec touchpoints are additive only.
</TASK>

<ACCEPTANCE_CRITERIA>
Verbatim from scoper packet (AC1–AC21):

- AC1: New directory `infra/terraform/modules/dynamodb-canon-state/` exists with exactly these files: `main.tf`, `variables.tf`, `outputs.tf`, `README.md`. No other files in the module dir.
- AC2: `main.tf` declares exactly one resource `aws_dynamodb_table.this` with: `name = "${var.name_prefix}-canon-state"`; `billing_mode = "PAY_PER_REQUEST"`; `hash_key = "pk"`; `range_key = "sk"`; `attribute { name="pk" type="S" }`; `attribute { name="sk" type="S" }`; `ttl { attribute_name = "lease_expires_at" enabled = true }`; `point_in_time_recovery { enabled = true }`; `server_side_encryption { enabled = true }` (AWS-owned key; no `kms_key_arn`); `deletion_protection_enabled = true`; and `tags = { Purpose = "canon-state" }` (default_tags from the root provider augment this).
- AC3: `variables.tf` declares exactly one input `name_prefix` (type=string, no default, with description). Nothing else. This mirrors the `modules/s3-artifacts` / `modules/secrets` pattern already used in the repo.
- AC4: `outputs.tf` declares exactly two outputs: `table_name` (value=`aws_dynamodb_table.this.name`, with description) and `table_arn` (value=`aws_dynamodb_table.this.arn`, with description). No other outputs.
- AC5: `README.md` documents: purpose (Canon Memory Platform operational-state plane per Backlog §B), inputs (`name_prefix` — semantics + expected format), outputs (`table_name`, `table_arn`), key schema (`pk = company_id#repository_id`, `sk = plan_id#task_id#workstream_id`), TTL semantics (auto-expires items whose `lease_expires_at` epoch-seconds value is past — enforces Backlog §B lease semantics), and that E2-T1 does NOT run `terraform apply` (deferred to operator follow-up). At least one fenced code example of module invocation.
- AC6: `infra/terraform/main.tf` gains exactly one additive `module "state_table"` block after the existing `module "rds"` block, invoking `./modules/dynamodb-canon-state` with `name_prefix = "${var.project_name}-${var.environment}"`. No existing module blocks are modified, reordered, or renamed.
- AC7: `infra/terraform/outputs.tf` gains exactly two additive root-level outputs: `state_table_name` (value=`module.state_table.table_name`) and `state_table_arn` (value=`module.state_table.table_arn`), each with a description. No existing outputs are modified.
- AC8: `infra/terraform/variables.tf` is NOT modified. Per-env isolation is achieved via the existing `${var.project_name}-${var.environment}` name_prefix pattern (environment var already exists from E0-T4). A single-line comment in the new module's README explicitly cites this pattern.
- AC9: `infra/terraform/terraform.tfvars`, `infra/terraform/providers.tf`, and `infra/terraform/versions.tf` are NOT modified (no new providers; `hashicorp/aws ~> 5.0` already covers `aws_dynamodb_table`).
- AC10: Per-environment isolation is proven deterministically by: running `terraform console` mentally over the code — for `environment=dev` the table name is `canon-systems-v2-dev-canon-state`; for `environment=staging` it is `canon-systems-v2-staging-canon-state`; for `environment=prod` it is `canon-systems-v2-prod-canon-state`. README documents this and states that switching environments creates/uses a different physical table.
- AC11: `cd infra/terraform && terraform init -backend=false && terraform validate` exits 0 and prints `Success! The configuration is valid.`. qa-gate captures full stdout/stderr.
- AC12: `terraform fmt -check -recursive infra/terraform/modules/dynamodb-canon-state/` exits 0 (module files are canonically formatted).
- AC13: NO `terraform plan`, `terraform apply`, `terraform import`, `terraform destroy`, `terraform refresh`, or any `aws` CLI invocation is performed during implementation or qa-gate. If any of these are attempted, the task is rejected.
- AC14: `infra/terraform/README.md` gains ONE new top-level section `## E2-T1 — DynamoDB canon-state table` appended after the existing `## Deferred items` section, containing: (a) brief description of the new module + per-env table naming, (b) the additive `terraform apply` operator command, (c) the per-env `terraform import 'module.state_table.aws_dynamodb_table.this' "${var.project_name}-${var.environment}-canon-state"` commands for dev/staging/prod, (d) explicit statement that E2-T1 ran zero cloud commands. No existing sections are modified.
- AC15: `infra/README.md` gets ONE additive bullet under the existing terraform row (or a new row under it) describing the new DynamoDB module. No existing rows are reflowed.
- AC16: `CHANGELOG.md` [Unreleased] ### Added gets a NEW TOP-OF-LIST bullet: `E2-T1: DynamoDB canon-state table module (infra/terraform/modules/dynamodb-canon-state/) + root wiring + outputs (state_table_name, state_table_arn); PAY_PER_REQUEST, TTL on lease_expires_at, PITR, SSE; per-env isolation via ${project}-${environment}-canon-state; no cloud commands executed.` Bullet MUST land above all existing E1-* bullets to match Keep-a-Changelog newest-first order.
- AC17: `README.md` infra table (if present) or the nearest infra-referring paragraph gets ONE additive sentence or row referring to the new module. No existing text is rewritten.
- AC18: `docs/SYSTEM-WORKFLOW.md` gets ONE additive bullet under the nearest infra/§10 section referencing the new table, consistent with the E0-T4 augment pattern. No existing bullets are removed or reflowed.
- AC19: `tests/test_infra_layout.py` gains additive assertions: (a) the four files under `infra/terraform/modules/dynamodb-canon-state/` exist and are non-empty; (b) `infra/terraform/main.tf` contains the substring `module "state_table"` and `./modules/dynamodb-canon-state`; (c) `infra/terraform/outputs.tf` contains the substrings `state_table_name` and `state_table_arn`. No existing assertion is removed or weakened.
- AC20: Root `pytest -q` exits 0. `bash scripts/smoke-test.sh` exits 0 (terraform validate path included).
- AC21: Zero diffs under forbidden surfaces (see `out_of_scope_paths` + `forbidden_surface`). Explicitly: `src/canon_systems/cli.py` has zero diff.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E2-T1
- workstream_id: wave-2a
- epic_id: E2
- wave_branch: `wave/2/canon-memory-v1` (already cut from `origin/main` @ `b926a6f` post-Wave-1-merge — DO NOT re-cut, DO NOT change branches)
- repository_id: canon-systems @ wave/2/canon-memory-v1
- aws_account_ref: 222274634742 (identifier only — NEVER invoked)
- aws_region_ref: us-east-1 (identifier only — NEVER invoked)
- live_project_name: "canon-systems-v2" (preserved; do not rename)
- live_environment: "dev" (default in tfvars; preserved)
- cloud_waiver: honored — ONLY `terraform init -backend=false`, `terraform validate`, `terraform fmt -check` are permitted; zero AWS CLI
- cli_py_exclusion: `src/canon_systems/cli.py` MUST have zero diff (E2-T3 owns)
- non-blocking OQs to cite where relevant: OQ-E2-T1-01 (operator apply deferral), OQ-E2-T1-02 (deletion_protection var), OQ-E2-T1-03 (CMK SSE), OQ-E2-T1-04 (streams), OQ-E2-T1-05 (sensitive outputs), OQ-E2-T1-06 (module README precedent)
</CONTEXT>

<REPOSITORY>
- primaryLanguages: HCL (Terraform ≥ 1.5.0), Markdown, Python 3.10+ (tests)
- testFramework: pytest (root) + `terraform validate` + `bash scripts/smoke-test.sh`
- provider_pins_unchanged: aws ~> 5.0, random ~> 3.6
- write_surface (create):
  - `infra/terraform/modules/dynamodb-canon-state/main.tf`
  - `infra/terraform/modules/dynamodb-canon-state/variables.tf`
  - `infra/terraform/modules/dynamodb-canon-state/outputs.tf`
  - `infra/terraform/modules/dynamodb-canon-state/README.md`
- write_surface (additive modify only — no reflow, no rename, no reorder):
  - `infra/terraform/main.tf` (append ONE `module "state_table"` block after `module "rds"`)
  - `infra/terraform/outputs.tf` (append TWO outputs: `state_table_name`, `state_table_arn`)
  - `infra/terraform/README.md` (append ONE `## E2-T1 — DynamoDB canon-state table` section after `## Deferred items`)
  - `infra/README.md` (append ONE row/bullet)
  - `CHANGELOG.md` (prepend ONE bullet at TOP of `[Unreleased]` → `### Added`, above all existing E1-* bullets)
  - `README.md` (append ONE sentence/row in the nearest infra-referring paragraph/table)
  - `docs/SYSTEM-WORKFLOW.md` (append ONE bullet under the nearest infra/§10 augment section)
  - `tests/test_infra_layout.py` (append additive assertions ONLY — do not weaken/remove existing ones)
- mustNotBreak:
  - `cd infra/terraform && terraform validate`
  - Root `pytest -q` including existing `tests/test_infra_layout.py` assertions
  - `bash scripts/smoke-test.sh`
  - Existing modules (vpc, ecr, ecs-fargate, rds-postgres, s3-artifacts, secrets) — ZERO edits
  - Existing root outputs (no renames, no removals)
  - `infra/auth-ingress/**` — ZERO edits
  - CHANGELOG structure (Keep-a-Changelog; newest-first in `[Unreleased]`)
- explicitly_excluded_zero_diff (verify before HANDOFF_TO_QA):
  - `src/canon_systems/cli.py` (E2-T3 owns)
  - `src/canon_systems/**` (all)
  - `backend/**`
  - `infra/terraform/variables.tf`, `infra/terraform/terraform.tfvars`, `infra/terraform/providers.tf`, `infra/terraform/versions.tf`
  - `infra/terraform/modules/{vpc,ecr,ecs-fargate,rds-postgres,s3-artifacts,secrets}/**`
  - `infra/auth-ingress/**`
  - `canon-systems-v2/**`
  - `.cursor/rules/**`, `.cursor/plans/**`
  - Frozen Wave-0 docs: `docs/MEMORY-PLATFORM-PLAN.md`, `docs/MEMORY-PLATFORM-BACKLOG.md`, `docs/WAVE-0-AUDIT.md`, `docs/WAVE-0-CLOSEOUT.md`, `docs/E0-T3-MIGRATION-NOTES.md`, `docs/E0-T4-INFRA-IMPORT.md`, `docs/DEPRECATIONS.md`, `docs/OBSIDIAN-MIND-CATALOGUE.md`
  - `.github/workflows/**`, `pyproject.toml`, `pytest.ini`, `requirements-dev.txt`, any `Dockerfile*`, `deploy/**`
- permitted_commands: `terraform init -backend=false`, `terraform validate`, `terraform fmt -check`, `pytest`, `bash scripts/smoke-test.sh`, read-only `git status` / `git diff --name-only`
- forbidden_commands: `terraform apply|import|plan|destroy|refresh`, any `aws *`, `aws-vault *`, any boto3/AWS SDK call, `git commit`, `git push`, `git checkout -b`, `git branch -D`
</REPOSITORY>

<REASONING>
Implementation approach (single parent-elected stream):

1. Author the new module byte-minimally, mirroring the three-file shape of `modules/s3-artifacts` and `modules/secrets`:
   - `main.tf`: exactly one `aws_dynamodb_table.this` resource satisfying AC2 verbatim. Two `attribute {}` blocks only (pk + sk). `tags = { Purpose = "canon-state" }` — root provider `default_tags` augments Project/Environment/ManagedBy.
   - `variables.tf`: one `name_prefix` string variable with description; no default; no validation block (parity with peer modules).
   - `outputs.tf`: `table_name` + `table_arn` with descriptions. No `sensitive = true` (OQ-E2-T1-05 resolution).
   - `README.md`: purpose (Backlog §B operational-state plane), inputs, outputs, key schema, TTL semantics, per-env table name examples (dev/staging/prod), explicit "E2-T1 did NOT run terraform apply" statement, at least one fenced HCL example of module invocation, one-line comment citing the existing `${var.project_name}-${var.environment}` pattern (AC8 requirement).

2. Root wiring — additive only:
   - Append to `infra/terraform/main.tf` AFTER the `module "rds"` block:
     ```hcl
     module "state_table" {
       source      = "./modules/dynamodb-canon-state"
       name_prefix = "${var.project_name}-${var.environment}"
     }
     ```
   - Append to `infra/terraform/outputs.tf`:
     ```hcl
     output "state_table_name" {
       description = "..."
       value       = module.state_table.table_name
     }
     output "state_table_arn" {
       description = "..."
       value       = module.state_table.table_arn
     }
     ```

3. `infra/terraform/README.md` — append `## E2-T1 — DynamoDB canon-state table` section AFTER the existing `## Deferred items` section. Contains: (a) module summary + per-env naming, (b) operator `terraform apply` command, (c) three `terraform import 'module.state_table.aws_dynamodb_table.this' "<name>"` commands for dev/staging/prod, (d) explicit "E2-T1 executed zero cloud commands" statement.

4. Living-spec mirror (additive; follow the E0-T4 augment template):
   - `CHANGELOG.md` [Unreleased] ### Added — prepend the exact bullet from AC16 at the TOP.
   - `README.md` — one additive sentence/row in the infra paragraph/table.
   - `docs/SYSTEM-WORKFLOW.md` — one additive bullet under the infra/§10 augment section.
   - `infra/README.md` — one additive row/bullet under the existing terraform row.

5. Tests (`tests/test_infra_layout.py` — additive only):
   - `test_dynamodb_canon_state_module_files_exist` — the 4 files exist and are non-empty.
   - `test_dynamodb_module_has_only_name_prefix_var` — `variables.tf` contains `name_prefix` and does NOT contain other `variable "<name>" {` declarations.
   - `test_dynamodb_module_outputs` — `outputs.tf` contains `output "table_name"` and `output "table_arn"`.
   - `test_dynamodb_module_readme_mentions_keys_ttl_ppr` — README substrings: `pk`, `sk`, `lease_expires_at`, `PAY_PER_REQUEST`.
   - `test_root_wires_state_table_module` — `infra/terraform/main.tf` contains `module "state_table"` AND `./modules/dynamodb-canon-state`.
   - `test_root_exposes_state_table_outputs` — `infra/terraform/outputs.tf` contains `state_table_name` AND `state_table_arn`.
   - `test_dynamodb_main_tf_key_attrs_present` — `main.tf` contains `billing_mode = "PAY_PER_REQUEST"`, `hash_key = "pk"`, `range_key = "sk"`, `lease_expires_at`, `point_in_time_recovery`, `server_side_encryption`, `deletion_protection_enabled = true`.
   - `test_infra_terraform_readme_e2t1_section` — `infra/terraform/README.md` contains `## E2-T1` and `terraform import 'module.state_table.aws_dynamodb_table.this'`.

6. Local verification quadrant (MUST all pass before HANDOFF_TO_QA):
   - `cd infra/terraform && terraform init -backend=false && terraform validate` → expect `Success! The configuration is valid.`
   - `terraform fmt -check -recursive infra/terraform/modules/dynamodb-canon-state/` → exit 0
   - `pytest -q` at repo root → exit 0
   - `bash scripts/smoke-test.sh` → exit 0

7. Forbidden-surface verification (AC21) BEFORE HANDOFF_TO_QA:
   - `git diff --name-only` intersected with forbidden globs MUST be empty.
   - Specifically verify `src/canon_systems/cli.py` has zero diff.
</REASONING>

<OUTPUT_FORMAT>
Produce ONLY the code changes needed to satisfy AC1–AC21, plus the additive pytest assertions. No unrelated refactors. No new dependencies. No new root tf variables. No changes outside `write_surface`. No module README copy-paste into other modules.

When finished and after the full local verification quadrant has passed, emit EXACTLY one `HANDOFF_TO_QA` block (filled in):

```
HANDOFF_TO_QA
  handoff_id: "canon-memory-v1"
  task_id: "E2-T1"
  wave_branch: "wave/2/canon-memory-v1"
  files_created:
    - "infra/terraform/modules/dynamodb-canon-state/main.tf"
    - "infra/terraform/modules/dynamodb-canon-state/variables.tf"
    - "infra/terraform/modules/dynamodb-canon-state/outputs.tf"
    - "infra/terraform/modules/dynamodb-canon-state/README.md"
  files_modified:
    - "infra/terraform/main.tf"
    - "infra/terraform/outputs.tf"
    - "infra/terraform/README.md"
    - "infra/README.md"
    - "CHANGELOG.md"
    - "README.md"
    - "docs/SYSTEM-WORKFLOW.md"
    - "tests/test_infra_layout.py"
  forbidden_surfaces_verified_zero_diff:
    - path: "src/canon_systems/cli.py"
      verified_by: "git diff --name-only | grep -c 'src/canon_systems/cli.py' == 0"
    - path: "src/canon_systems/**, backend/**, infra/terraform/variables.tf, infra/terraform/terraform.tfvars, infra/terraform/providers.tf, infra/terraform/versions.tf, infra/terraform/modules/{vpc,ecr,ecs-fargate,rds-postgres,s3-artifacts,secrets}/**, infra/auth-ingress/**, .cursor/rules/**, .cursor/plans/**, canon-systems-v2/**, .github/workflows/**, pyproject.toml, pytest.ini, requirements-dev.txt, Dockerfile*, deploy/**"
      verified_by: "git diff --name-only output"
  terraform_validate_output_capture_ref: "<path-or-inline ref>"
  terraform_fmt_check_output_capture_ref: "<path-or-inline ref>"
  pytest_output_capture_ref: "<path-or-inline ref>"
  smoke_output_capture_ref: "<path-or-inline ref>"
  ac_verification_map:
    - { ac: "AC1",  status: "pass|fail", evidence: "..." }
    - { ac: "AC2",  status: "pass|fail", evidence: "..." }
    - { ac: "AC3",  status: "pass|fail", evidence: "..." }
    - { ac: "AC4",  status: "pass|fail", evidence: "..." }
    - { ac: "AC5",  status: "pass|fail", evidence: "..." }
    - { ac: "AC6",  status: "pass|fail", evidence: "..." }
    - { ac: "AC7",  status: "pass|fail", evidence: "..." }
    - { ac: "AC8",  status: "pass|fail", evidence: "..." }
    - { ac: "AC9",  status: "pass|fail", evidence: "..." }
    - { ac: "AC10", status: "pass|fail", evidence: "..." }
    - { ac: "AC11", status: "pass|fail", evidence: "..." }
    - { ac: "AC12", status: "pass|fail", evidence: "..." }
    - { ac: "AC13", status: "pass|fail", evidence: "..." }
    - { ac: "AC14", status: "pass|fail", evidence: "..." }
    - { ac: "AC15", status: "pass|fail", evidence: "..." }
    - { ac: "AC16", status: "pass|fail", evidence: "..." }
    - { ac: "AC17", status: "pass|fail", evidence: "..." }
    - { ac: "AC18", status: "pass|fail", evidence: "..." }
    - { ac: "AC19", status: "pass|fail", evidence: "..." }
    - { ac: "AC20", status: "pass|fail", evidence: "..." }
    - { ac: "AC21", status: "pass|fail", evidence: "..." }
  open_issues: []
  suggested_qa_focus_areas:
    - "Confirm AC2 HCL-level completeness: all nine required attrs present."
    - "Confirm per-env isolation via exact ${var.project_name}-${var.environment} interpolation."
    - "Confirm CHANGELOG bullet lands ABOVE all E1-* bullets."
    - "Confirm `## E2-T1` section in infra/terraform/README.md lands AFTER `## Deferred items`."
    - "Confirm zero diff on src/canon_systems/cli.py."
    - "Confirm zero terraform apply|import|plan|destroy|refresh + zero aws CLI in transcript."
    - "Confirm additive-only diff shape on shared surfaces."
    - "Confirm no `sensitive = true` on root outputs (OQ-E2-T1-05)."
    - "Confirm `deletion_protection_enabled = true` hard-coded (OQ-E2-T1-02)."
    - "Confirm no GSI/streams/CMK (OQ-E2-T1-03/04 + non_goals)."
  next_actions:
    - "Operator `terraform apply` post-merge (OQ-E2-T1-01, deferred)."
    - "Operator `terraform import` per env if tables pre-provisioned (manifest in README)."
END_HANDOFF_TO_QA
```
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
The following are HARD STOPS. If any is violated or unavoidably cannot be satisfied, STOP immediately and emit `IMPLEMENTER_FAILURE`:

- Do NOT write to `src/canon_systems/cli.py` (zero diff required — E2-T3 owns).
- Do NOT write to any file under `src/canon_systems/**` or `backend/**`.
- Do NOT run `terraform apply|import|plan|destroy|refresh` under any circumstance.
- Do NOT run any `aws` CLI command, `aws-vault`, or any AWS SDK / boto3 invocation.
- Do NOT edit files under `.cursor/rules/**` or `.cursor/plans/**`.
- Do NOT modify any existing Wave-0 module under `infra/terraform/modules/{vpc,ecr,ecs-fargate,rds-postgres,s3-artifacts,secrets}/**`.
- Do NOT edit `infra/terraform/variables.tf`, `infra/terraform/terraform.tfvars`, `infra/terraform/providers.tf`, `infra/terraform/versions.tf`, or `infra/auth-ingress/**`.
- Do NOT edit frozen Wave-0 docs listed in REPOSITORY.explicitly_excluded_zero_diff.
- Do NOT edit `canon-systems-v2/**` (sibling).
- Do NOT edit `.github/workflows/**`, `pyproject.toml`, `pytest.ini`, `requirements-dev.txt`, `Dockerfile*`, `deploy/**`.
- Do NOT add new root-level terraform variables.
- Do NOT add GSIs/LSIs, DynamoDB Streams, replica regions, provisioned capacity, autoscaling, backup plans, or a customer-managed KMS CMK.
- Do NOT introduce a remote state backend.
- Do NOT rewrite/reflow/reorder any existing line in shared living-spec files. Additive only.
- Do NOT weaken, remove, or rewrite any existing assertion in `tests/test_infra_layout.py`.
- Do NOT run `git commit`, `git push`, `git checkout -b`, or any branch-mutating command.
- Do NOT declare the task complete without HANDOFF_TO_QA covering every AC1–AC21.

Failure-mode disciplines:

- If `terraform validate` fails, STOP and return the failure verbatim. DO NOT "fix" by editing unrelated infra, DO NOT bump provider pins unilaterally.
- If `terraform fmt -check` fails, run `terraform fmt` ONLY inside the new module directory and re-verify.
- If `pytest -q` or `smoke-test.sh` fails on a pre-existing error unrelated to this task, DIAGNOSE and REPORT in `open_issues`; DO NOT mask.

On any STOP trigger, emit:

```
IMPLEMENTER_FAILURE
  handoff_id: "canon-memory-v1"
  task_id: "E2-T1"
  stop_condition_triggered: "<which rule>"
  ac_blocked: "<AC id>"
  diagnostic: "<what was observed, not improvised>"
  proposed_remediation: "<scope amendment the parent/scoper would need to authorize>"
END_IMPLEMENTER_FAILURE
```

END_CURSOR_PILOT_PROMPT
```
