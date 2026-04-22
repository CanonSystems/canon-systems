# DynamoDB `canon-state` table (Terraform module)

## Purpose

Provisions the **Canon Memory Platform** operational-state plane DynamoDB table per [`docs/MEMORY-PLATFORM-BACKLOG.md`](../../../docs/MEMORY-PLATFORM-BACKLOG.md) §B: leased checkpoints, version checks, and resume/concurrency data for Wave 2+ (state-api, checkpoint CLI) and later waves.

E2-T1 did **not** run `terraform apply`; creation/import in AWS is an operator follow-up. See root [`README.md`](../README.md) E2-T1 section.

## Per-environment isolation

The root module passes `name_prefix = "${var.project_name}-${var.environment}"` (same pattern as S3, Secrets, RDS, and other modules). The table name is `"${var.name_prefix}-canon-state"`, so for `project_name = canon-systems-v2`:

| `environment` | Table name |
| --- | --- |
| `dev` | `canon-systems-v2-dev-canon-state` |
| `staging` | `canon-systems-v2-staging-canon-state` |
| `prod` | `canon-systems-v2-prod-canon-state` |

Switching `environment` (e.g. via separate `-var-file` or workspace practice) addresses a different physical table.

## Input

| Name | Description |
| --- | --- |
| `name_prefix` | String prefix for the table name; must match `project_name` + `environment` convention from the root (see table above). |

## Outputs

| Name | Description |
| --- | --- |
| `table_name` | DynamoDB table name. |
| `table_arn` | DynamoDB table ARN. |

## Key schema

- **`pk` (S)** — `company_id#repository_id`
- **`sk` (S)** — `plan_id#task_id#workstream_id`

## Billing and features

- **Billing mode:** `PAY_PER_REQUEST`
- **TTL:** attribute `lease_expires_at` (Number, epoch seconds). Items expire automatically after that time; this enforces Backlog §B lease semantics.
- **PITR, SSE (AWS-owned key), deletion protection** are enabled in `main.tf`.

## Example (root-style invocation)

```hcl
module "state_table" {
  source      = "./modules/dynamodb-canon-state"
  name_prefix = "${var.project_name}-${var.environment}"
}
```
