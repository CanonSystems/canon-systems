# Infrastructure (`infra/`)

Top-level index for infrastructure-as-code and related material in this repo.

| Path | Purpose |
| --- | --- |
| [`terraform/`](terraform/) | **E0-T4** — Terraform root mirrored from `canon-systems-v2` @ `ebecb91`: VPC, ECR, baseline ECS Fargate, RDS, S3 artifacts, Secrets Manager placeholders for the dev plane (`project_name=canon-systems-v2`, `environment=dev`, `us-east-1`). Import-oriented; see [`terraform/README.md`](terraform/README.md) and [`docs/E0-T4-INFRA-IMPORT.md`](../docs/E0-T4-INFRA-IMPORT.md). |
| [`terraform/modules/dynamodb-canon-state/`](terraform/modules/dynamodb-canon-state/) | **E2-T1** — DynamoDB `canon-state` table module (PAY_PER_REQUEST, TTL on `lease_expires_at`, PITR, SSE) wired from the root; `terraform apply` deferred to operator follow-up. |
| [`terraform/modules/axon-snapshots/`](terraform/modules/axon-snapshots/) | **E3-T1** — S3 + DynamoDB stack for `backend/axon-service` per-commit graph snapshots and metadata; root module `axon_snapshots`; see [`terraform/README.md`](terraform/README.md#e3-t1--axon-snapshots-module-s3--dynamodb). |
| [`auth-ingress/`](auth-ingress/) | **Pre-existing / separate workstream** — Cognito and `canon-systems.com` ingress Terraform snippets; not wired from `terraform/` root. |
