HANDOFF_TO_QA
  task_id: E0-T4
  handoff_id: canon-memory-v1
  branch: wave/0/canon-memory-v1
  acceptance_criteria_covered:
    - "infra/terraform/ mirrors v2 HCL @ ebecb91 minus state/lock/cache/plan; diff -rq verified (exit 0)"
    - "Six modules × three files + six root .tf/.tfvars present"
    - "terraform init -backend=false && terraform validate: PASS (aws 5.100.0, random 3.8.1 downloaded; then .terraform cache removed for layout test hygiene)"
    - "infra/terraform/README.md: per-resource import table with real AWS IDs sourced read-only from v2 tfstate"
    - "docs/E0-T4-INFRA-IMPORT.md: cites ebecb91, exclusions, preservation table, no-cloud-commands statement, OQ-E0-T4-01..06"
    - "tests/test_infra_layout.py: 8 tests covering presence, tfstate/lock/cache absence, auth-ingress file set invariance, manifest + migration assertions"
    - "Root pytest: 102 passed (no regressions vs prior 94 baseline; 8 new layout tests added)"
    - "Living-spec: README, CHANGELOG, SYSTEM-WORKFLOW §10, DEPRECATIONS, .gitignore all updated"
    - "Forbidden paths untouched: backend/**, infra/auth-ingress/**, canon-systems-v2/**, src/canon_systems/**, Dockerfiles, deploy/**, .github/workflows/**"
  changed_files:
    created:
      - "infra/terraform/main.tf"
      - "infra/terraform/variables.tf"
      - "infra/terraform/outputs.tf"
      - "infra/terraform/providers.tf"
      - "infra/terraform/versions.tf"
      - "infra/terraform/terraform.tfvars"
      - "infra/terraform/modules/vpc/{main.tf,variables.tf,outputs.tf}"
      - "infra/terraform/modules/ecr/{main.tf,variables.tf,outputs.tf}"
      - "infra/terraform/modules/ecs-fargate/{main.tf,variables.tf,outputs.tf}"
      - "infra/terraform/modules/rds-postgres/{main.tf,variables.tf,outputs.tf}"
      - "infra/terraform/modules/s3-artifacts/{main.tf,variables.tf,outputs.tf}"
      - "infra/terraform/modules/secrets/{main.tf,variables.tf,outputs.tf}"
      - "infra/terraform/README.md"
      - "infra/README.md"
      - "docs/E0-T4-INFRA-IMPORT.md"
      - "tests/test_infra_layout.py"
    modified:
      - "README.md"
      - "CHANGELOG.md"
      - "docs/SYSTEM-WORKFLOW.md"
      - "docs/DEPRECATIONS.md"
      - ".gitignore"
    deleted: []
  how_to_run_tests:
    commands:
      - "cd infra/terraform && terraform init -backend=false && terraform validate"
      - "pytest tests/test_infra_layout.py -v"
      - "pytest -q"
    results:
      - "terraform init + validate: Success (aws 5.100.0, random 3.8.1)"
      - "tests/test_infra_layout.py: 8 passed"
      - "full suite: 102 passed"
    terraform_fmt_check:
      status: "EXIT_3 — main.tf not fmt-clean vs terraform fmt; intentionally NOT reformatted to preserve byte-faithful mirror; acceptable per scoper EXP-02 boundary (byte-identical upstream rule)"
  decisions:
    - "Post-init removed infra/terraform/.terraform and .terraform.lock.hcl so layout tests pass on clean tree; both remain gitignored."
    - "random_password.db[0] documented as non-importable (no provider import); operator uses db_password tfvars or state migration."
    - "Import IDs use full ECR repo names (canon-systems-v2-dev/canon/...) to match live AWS."
    - "VPC resource is aws_vpc.this (not aws_vpc.main as anticipated in scoper); called out explicitly in README."
  next_actions:
    - "Operator (post-merge): choose backend, run imports per README manifest order, resolve random_password story, then terraform plan → zero changes."
    - "Optional: if team policy wants committed lockfile, a follow-up task can un-gitignore .terraform.lock.hcl (out of scope here)."
  open_questions:
    - "OQ-E0-T4-01..06 documented in docs/E0-T4-INFRA-IMPORT.md (none block E0-T4)."
END_HANDOFF_TO_QA
