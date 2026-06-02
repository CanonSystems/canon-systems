# DynamoDB Canon state plane (Terraform module)

## Purpose

Provisions DynamoDB tables for the **Canon Memory Platform** operational-state plane per [`docs/MEMORY-PLATFORM-BACKLOG.md`](../../../docs/MEMORY-PLATFORM-BACKLOG.md) §B and later additions:

| Resource | Table suffix | Used by |
|----------|--------------|---------|
| `aws_dynamodb_table.this` | `-canon-state` | Checkpoints + leases (`STATE_TABLE_NAME`) |
| `aws_dynamodb_table.run_ledger` | `-canon-run-ledger` | Run ledger (`STATE_RUN_LEDGER_TABLE_NAME`) |
| `aws_dynamodb_table.tasks` | `-canon-tasks` | Assignable tasks (`STATE_TASKS_TABLE_NAME`, canon-systems ≥ 3.7.0) |

E2-T1 did **not** run `terraform apply`; creation/import in AWS is an operator follow-up. See root [`README.md`](../README.md) and [`docs/runbooks/TASKS-SERVER-DEPLOY.md`](../../../docs/runbooks/TASKS-SERVER-DEPLOY.md).

## Per-environment isolation

The root module passes `name_prefix = "${var.project_name}-${var.environment}"`. For `project_name = canon-systems-v2`:

| `environment` | Checkpoint table | Run ledger | Tasks |
| --- | --- | --- | --- |
| `dev` | `canon-systems-v2-dev-canon-state` | `...-canon-run-ledger` | `...-canon-tasks` |
| `staging` | `canon-systems-v2-staging-canon-state` | `...` | `...` |
| `prod` | `canon-systems-v2-prod-canon-state` | `...` | `...` |

## Input

| Name | Description |
| --- | --- |
| `name_prefix` | String prefix for table names (`project_name` + `environment`). |

## Outputs

| Name | Description |
| --- | --- |
| `table_name` / `table_arn` | Checkpoint/lease table |
| `run_ledger_table_name` / `run_ledger_table_arn` | Run ledger table |
| `tasks_table_name` / `tasks_table_arn` | Assignable-task event table |

## Key schemas

**Checkpoint (`-canon-state`):**

- **`pk` (S)** — `company_id#repository_id`
- **`sk` (S)** — `plan_id#task_id#workstream_id`
- **TTL:** `lease_expires_at`

**Run ledger (`-canon-run-ledger`):** same `pk`/`sk` pattern; keys use `#run_ledger` partition suffix per `canon_backend_shared.run_ledger`.

**Tasks (`-canon-tasks`):**

- **`pk` (S)** — `{company_id}#tasks`
- **`sk` (S)** — `{task_ref}#evt#{event_id}`

## Billing and features

All three tables: **PAY_PER_REQUEST**, **PITR**, **SSE** (AWS-owned key), **deletion protection**. Only the checkpoint table enables **TTL** on `lease_expires_at`.

## Example (root-style invocation)

```hcl
module "state_table" {
  source      = "./modules/dynamodb-canon-state"
  name_prefix = "${var.project_name}-${var.environment}"
}
```
