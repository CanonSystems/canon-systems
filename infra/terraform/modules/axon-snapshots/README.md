# axon-snapshots

Terraform module for the **graph retrieval (Axon) plane**: one versioned, encrypted, private S3 bucket for per-tenant gzip JSON snapshots, plus a DynamoDB table for metadata index rows.

## Purpose

- **S3** — stores objects at `{company_id}/{repository_id}/{commit_sha}.json.gz` (application code; not created by this module).
- **DynamoDB** — `pk` (string, hash), `sk` (string, range) for snapshot metadata; PAY_PER_REQUEST, PITR, deletion protection, SSE.

## Cloud apply

`terraform apply` in the target account/environment is **operator-run** and **out of band** for this repository’s automation. No in-task cloud commands are performed here (waived).

## Inputs

| Name | Type | Description |
| --- | --- | --- |
| `name_prefix` | string | Prefix for resource names, e.g. `project-env`. Produces `*-axon-snapshots` and `*-axon-snapshots-meta`. |

## Outputs

| Name | Description |
| --- | --- |
| `snapshots_bucket_name` | S3 bucket name |
| `snapshots_bucket_arn` | S3 bucket ARN |
| `meta_table_name` | DynamoDB table name |
| `meta_table_arn` | DynamoDB table ARN |

## Key schema (meta table)

- **pk** — `company_id#repository_id`
- **sk** — `commit_sha`

Attributes are written by `backend/axon-service` (`uploaded_at`, `size_bytes`, `node_count`, `edge_count`, `snapshot_key`, …).

## Import (existing resources)

From `infra/terraform/` after configuring backend and credentials (replace IDs with real values):

```bash
terraform import 'module.axon_snapshots.aws_s3_bucket.snapshots' 'myproj-dev-axon-snapshots'
terraform import 'module.axon_snapshots.aws_dynamodb_table.meta' 'myproj-dev-axon-snapshots-meta'
```
