# E0-T4 — Terraform root migration (infra/terraform)

**Date:** 2026-04-22

## Upstream reference

- **Sibling repo:** `canon-systems-v2` (read-only on this workstation).
- **Git SHA:** `ebecb91` (exact; Terraform HCL mirrored from `infra/terraform/` at this revision).

## Git-history waiver

Same pattern as E0-T3: `canon-systems-v2` carries a minimal commit history for this
tree; this repo adopts a **copy-based mirror** of the HCL at `ebecb91` rather than
`git subtree`/`filter-repo` history replay. Provenance is this document + the SHA
above.

## Exclusions from the mirror

The following were **not** copied into `canon-systems/infra/terraform/`:

- `terraform.tfstate` and `terraform.tfstate.backup` (and any `terraform.tfstate*`)
- `.terraform/` (provider and module plugin cache)
- `.terraform.lock.hcl` (regenerated per machine via `terraform init`)
- `*.tfplan`

Real resource IDs for the import manifest were **read** from v2 `terraform.tfstate`
only; that file is **not** committed here.

## Preservation rationale

These values match the live stack and **must not** change casually:

| Setting | Value |
| --- | --- |
| `project_name` | `canon-systems-v2` |
| `environment` | `dev` |
| Region | `us-east-1` |
| Account (identifier) | `222274634742` |

Renaming `project_name` or `environment` would imply resource replacement or a
state move playbook, not an in-place edit (see OQ-E0-T4-03).

## Cloud execution boundary

**E0-T4 executed no cloud commands.** `terraform apply`, `terraform destroy`,
`terraform import`, `terraform refresh`, and `aws *` CLI (or AWS SDK) calls were
**never** invoked as part of this task. Only local file operations, documentation,
layout tests, and (when available) `terraform init -backend=false` + `terraform validate`
were in scope.

## Open questions (OQ)

| ID | Question | Proposed resolution | Blocking for this task |
| --- | --- | --- | --- |
| OQ-E0-T4-01 | Zero-drift AC (`terraform plan` clean against production) cannot be verified without AWS creds and imported state. | Defer to operator follow-up post-merge; E0-T4 done signal is “HCL parses + import manifest ready”. | no |
| OQ-E0-T4-02 | Does `MEMORY_ADAPTER_URL` get a runtime AWS resource in Wave 0? | Carried; E1-T2 owns the decision. | no |
| OQ-E0-T4-03 | Rename `project_name` from `canon-systems-v2` to `canon-systems`? | No in this task (would cause delete/recreate); defer to state-move playbook. | no |
| OQ-E0-T4-04 | Prune `jira-bridge`, `temporal-runtime` from the ECR list? | No (would destroy live resources); keep verbatim; Wave 7 may revisit. | no |
| OQ-E0-T4-05 | Declare S3 + DynamoDB remote backend now? | Defer to Wave 2 (E2-T1 introduces DynamoDB). | no |
| OQ-E0-T4-06 | Copy `.terraform.lock.hcl`? | No (machine-dependent); operator regenerates with `terraform init`. | no |
