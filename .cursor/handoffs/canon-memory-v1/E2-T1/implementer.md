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
      verified_by: "git diff --name-only (no entry for src/canon_systems/cli.py); file not in modified set"
    - path: "src/canon_systems/**, backend/**, infra/terraform/variables.tf, infra/terraform/terraform.tfvars, infra/terraform/providers.tf, infra/terraform/versions.tf, infra/terraform/modules/{vpc,ecr,ecs-fargate,rds-postgres,s3-artifacts,secrets}/**, infra/auth-ingress/**, .cursor/rules/**, .cursor/plans/**, canon-systems-v2/**, .github/workflows/**, pyproject.toml, pytest.ini, requirements-dev.txt, Dockerfile*, deploy/**"
      verified_by: "git diff --name-only lists only E2-T1 allowlisted paths; new module under dynamodb-canon-state/ only; no forbidden paths in diff"
  terraform_validate_output_capture_ref: "cd infra/terraform && terraform init -backend=false && terraform validate → exit 0; stdout includes \"Success! The configuration is valid.\""
  terraform_fmt_check_output_capture_ref: "terraform fmt -recursive infra/terraform/modules/dynamodb-canon-state/ (normalized main.tf, variables.tf); then terraform fmt -check -recursive infra/terraform/modules/dynamodb-canon-state/ → exit 0, \"FMT_CHECK_OK\""
  pytest_output_capture_ref: "pytest -q (repo root) → exit 0; 146 passed"
  smoke_output_capture_ref: "bash scripts/smoke-test.sh → exit 0; last lines: smoke-test: [terraform] ok, smoke-test: ALL STAGES PASSED"
  ac_verification_map:
    - { ac: "AC1",  status: "pass", evidence: "Module dir has exactly main.tf, variables.tf, outputs.tf, README.md; test_dynamodb_canon_state_module_files_exist" }
    - { ac: "AC2",  status: "pass", evidence: "aws_dynamodb_table.this in modules/dynamodb-canon-state/main.tf with all required keys/attrs; test_dynamodb_main_tf_key_attrs_present; terraform validate OK" }
    - { ac: "AC3",  status: "pass", evidence: "variables.tf: only variable name_prefix, type string, with description" }
    - { ac: "AC4",  status: "pass", evidence: "outputs table_name, table_arn → aws_dynamodb_table.this; test_dynamodb_module_outputs" }
    - { ac: "AC5",  status: "pass", evidence: "README: purpose, inputs, outputs, pk/sk/lease, PAY_PER_REQUEST, E2 apply deferred, HCL example" }
    - { ac: "AC6",  status: "pass", evidence: "main.tf: module state_table after module rds, source ./modules/dynamodb-canon-state, name_prefix pattern" }
    - { ac: "AC7",  status: "pass", evidence: "outputs.tf: state_table_name, state_table_arn from module.state_table; no sensitive; test_root_exposes_state_table_outputs" }
    - { ac: "AC8",  status: "pass", evidence: "variables.tf unchanged; module README + infra/terraform README cite name_prefix = project_name-environment pattern" }
    - { ac: "AC9",  status: "pass", evidence: "terraform.tfvars, providers.tf, versions.tf not in git diff" }
    - { ac: "AC10", status: "pass", evidence: "Module README table: dev/staging/prod table names; switching env uses different physical table" }
    - { ac: "AC11", status: "pass", evidence: "terraform init -backend=false && terraform validate → Success! The configuration is valid." }
    - { ac: "AC12", status: "pass", evidence: "terraform fmt -check -recursive infra/terraform/modules/dynamodb-canon-state/ exit 0" }
    - { ac: "AC13", status: "pass", evidence: "No apply/import/plan/destroy/refresh/aws; permitted commands only" }
    - { ac: "AC14", status: "pass", evidence: "infra/terraform/README.md: ## E2-T1 after ## Deferred items; apply + import + zero cloud statement; test_infra_terraform_readme_e2t1_section" }
    - { ac: "AC15", status: "pass", evidence: "infra/README.md: new table row for dynamodb-canon-state module" }
    - { ac: "AC16", status: "pass", evidence: "CHANGELOG [Unreleased] Added: E2-T1 bullet first under ### Added" }
    - { ac: "AC17", status: "pass", evidence: "README.md Infra §: additive mention of dynamodb-canon-state + outputs" }
    - { ac: "AC18", status: "pass", evidence: "docs/SYSTEM-WORKFLOW.md §10: bullet for DynamoDB canon-state (E2-T1)" }
    - { ac: "AC19", status: "pass", evidence: "test_infra_layout.py: new tests for module files, root wiring, outputs, README, main.tf attrs, terraform README E2" }
    - { ac: "AC20", status: "pass", evidence: "pytest -q 146 passed; smoke-test.sh ALL STAGES PASSED" }
    - { ac: "AC21", status: "pass", evidence: "git diff name-only has no src/canon_systems/**, backend/**, forbidden tf roots, etc." }
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
