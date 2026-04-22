# Infrastructure (`infra/`)

Top-level index for infrastructure-as-code and related material in this repo.

| Path | Purpose |
| --- | --- |
| [`terraform/`](terraform/) | **E0-T4** — Terraform root mirrored from `canon-systems-v2` @ `ebecb91`: VPC, ECR, baseline ECS Fargate, RDS, S3 artifacts, Secrets Manager placeholders for the dev plane (`project_name=canon-systems-v2`, `environment=dev`, `us-east-1`). Import-oriented; see [`terraform/README.md`](terraform/README.md) and [`docs/E0-T4-INFRA-IMPORT.md`](../docs/E0-T4-INFRA-IMPORT.md). |
| [`auth-ingress/`](auth-ingress/) | **Pre-existing / separate workstream** — Cognito and `canon-systems.com` ingress Terraform snippets; not wired from `terraform/` root. |
