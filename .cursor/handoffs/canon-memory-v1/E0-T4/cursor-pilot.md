CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent. Execute E0-T4 byte-faithfully; no cloud, no commits, no pushes.
</ROLE>

<TASK>
E0-T4 — Stand up `canon-systems/infra/terraform/` by byte-faithfully mirroring the canon-systems-v2 Terraform root @ ebecb91 so the live AWS plane backing KNOWLEDGE_API_URL + KNOWLEDGE_WORKER_URL becomes declarative IaC. IMPORT-prep only: files must parse locally; per-resource import manifest must enumerate `terraform import <addr> <real_id>` commands. Branch `wave/0/canon-memory-v1` stays uncommitted.
</TASK>

<ACCEPTANCE_CRITERIA>
- infra/terraform/ is byte-faithful copy of canon-systems-v2/infra/terraform/ MINUS tfstate*, .terraform/, .terraform.lock.hcl.
- Six modules (vpc, ecr, ecs-fargate, rds-postgres, s3-artifacts, secrets) + six root files (main, variables, outputs, providers, versions, terraform.tfvars) present and unchanged from v2 @ ebecb91.
- `cd infra/terraform && terraform init -backend=false && terraform validate` exits 0.
- infra/terraform/README.md enumerates every resource addr + real AWS id + `terraform import` command (real IDs sourced from v2 tfstate READ-ONLY; tfstate NOT copied).
- docs/E0-T4-INFRA-IMPORT.md cites v2 SHA ebecb91, exclusion list, project_name/environment preservation rationale, "no cloud commands executed" statement.
- tests/test_infra_layout.py asserts file presence, tfstate/lock/cache absence, infra/auth-ingress/ unchanged.
- Root pytest stays green.
- Living-spec: README + CHANGELOG + SYSTEM-WORKFLOW §10 + DEPRECATIONS + .gitignore updated.
- No writes to backend/**, src/canon_systems/**, infra/auth-ingress/**, canon-systems-v2/**, Dockerfiles, deploy/**, .github/workflows/**.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- upstream_source_repo: /Users/edwardwalker/localwork/canon-systems-v2 (READ-ONLY)
- upstream_source_commit: ebecb91
- aws_account: 222274634742 us-east-1 (identifier only; never invoked)
- live_project_name: "canon-systems-v2" (preserve)
- live_environment: "dev" (preserve)
- non-blocking OQs to record in docs/E0-T4-INFRA-IMPORT.md: OQ-E0-T4-01..06 from scoper packet.
</CONTEXT>

<REPOSITORY>
- write_surface: infra/terraform/**, infra/README.md, docs/E0-T4-INFRA-IMPORT.md, tests/test_infra_layout.py (create) + README.md, CHANGELOG.md, docs/SYSTEM-WORKFLOW.md, docs/DEPRECATIONS.md, .gitignore (modify)
- forbidden_writes: backend/**, src/canon_systems/**, infra/auth-ingress/**, canon-systems-v2/**, pyproject.toml root, pytest.ini, Dockerfiles, deploy/**, .github/workflows/**
- permitted_commands: `terraform init -backend=false`, `terraform validate`, `terraform fmt -check`, `pytest`
- forbidden_commands: `terraform apply|destroy|import|refresh`, `aws *`, `aws-vault *`, `git commit`, `git push`
</REPOSITORY>

<REASONING>
Copy v2 HCL byte-faithfully (18 files). Read v2 terraform.tfstate to harvest real AWS IDs for the README manifest (NEVER copy tfstate). Validate via `terraform init -backend=false` + `terraform validate` (offline). Author structural pytest. Update living-spec narrative. The per-resource README manifest replaces the deferred zero-drift AC (OQ-E0-T4-01; operator executes post-merge).

AC → test mapping:
- AC1+AC2 → test_terraform_files_present + test_excluded_artifacts_absent
- AC3 → shell gate in qa-gate
- AC4 → test_import_manifest_exists + spot-check
- AC5 → test_migration_note_exists
- AC6 → test_auth_ingress_untouched
- AC7 → pytest -q
</REASONING>

<PARALLELIZATION_PLAN>
- ws1: mirror HCL (18 files)
- ws2: harvest real AWS IDs from v2 tfstate (read-only)
- ws3: author README import manifest (depends on ws1+ws2)
- ws4: author tests/test_infra_layout.py
- ws5: author infra/README.md + docs/E0-T4-INFRA-IMPORT.md
- ws6: living-spec edits
- ws7: run terraform init -backend=false + terraform validate + pytest (depends on ws1,3,4,5,6)

Wave 1 (parallel): ws1, ws2, ws4, ws5, ws6. Wave 2: ws3. Wave 3: ws7.
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Emit HANDOFF_TO_QA with acceptance_criteria_covered, changed_files (created/modified/deleted), how_to_run_tests, decisions, next_actions, open_questions.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
- No terraform apply/destroy/import/refresh.
- No aws/aws-vault/AWS SDK invocation.
- No git commit/push/branch change.
- No writes to forbidden paths.
- No copy of tfstate*, .terraform/, lock.hcl, *.tfplan.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
