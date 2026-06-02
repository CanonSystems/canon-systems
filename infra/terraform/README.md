# Terraform — canon-systems-v2 dev plane (us-east-1)

## Overview

This root declares the AWS footprint that backs the **three-URL** knowledge plane
(`KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, and related VPC/RDS/S3/Secrets/ECR/ECS
baseline) for project **`canon-systems-v2`**, environment **`dev`**, in account
**`222274634742`**, region **`us-east-1`**.

**Owned here:** VPC (including subnets, IGW, NAT, EIPs, route tables, associations),
ECR repositories (four names from `terraform.tfvars`), baseline ECS Fargate cluster /
task / service / IAM, RDS PostgreSQL, S3 artifacts bucket + encryption / versioning /
public-access block, and placeholder Secrets Manager secrets.

**Not owned here:**

- **`infra/auth-ingress/`** — Cognito and `canon-systems.com` ingress; separate
  workstream, not wired from this root.
- **`memory-adapter`** — no dedicated ECS service or ECR repository in this stack
  (Wave 0 audit); localhost-only in dev unless a later task adds runtime IaC.

Mirrored byte-for-byte from sibling repo `canon-systems-v2` at commit **`ebecb91`**,
excluding state, lock file, provider cache, and plan files (see
[`docs/E0-T4-INFRA-IMPORT.md`](../../docs/E0-T4-INFRA-IMPORT.md)).

**Note:** The VPC resource in code is `aws_vpc.this` (not `main`).

## Prerequisites

- **Terraform** >= 1.5 (operator install; not performed by E0-T4 automation).
- **AWS credentials** with rights to plan/import the resources below (operator
  responsibility; E0-T4 did not invoke AWS APIs).

## Local validation

From repository root:

```bash
cd infra/terraform
terraform init -backend=false
terraform validate
```

## Import manifest

Use this table after configuring a **remote or local backend** and AWS credentials.
Commands assume run from `infra/terraform/`. Addresses match this repo’s module
paths (`module.ecs_baseline`, `module.artifacts_bucket`, `module.placeholders`).

**Real IDs** were read from `canon-systems-v2`’s `terraform.tfstate` at migration
time (state was **not** copied into this repo).

| address | real_id | import_command |
| --- | --- | --- |
| `random_password.db[0]` | *(not importable — see note below)* | *(N/A — `random_password` has no import in the Random provider; supply `db_password` in `terraform.tfvars` and align state manually, or migrate state from v2.)* |
| `module.vpc.aws_vpc.this` | `vpc-00e2f24eb25629746` | `terraform import 'module.vpc.aws_vpc.this' vpc-00e2f24eb25629746` |
| `module.vpc.aws_subnet.public[0]` | `subnet-0582c25e509a21086` | `terraform import 'module.vpc.aws_subnet.public[0]' subnet-0582c25e509a21086` |
| `module.vpc.aws_subnet.public[1]` | `subnet-01fe2e2a150d2d999` | `terraform import 'module.vpc.aws_subnet.public[1]' subnet-01fe2e2a150d2d999` |
| `module.vpc.aws_subnet.private[0]` | `subnet-016f14bb41af99e0f` | `terraform import 'module.vpc.aws_subnet.private[0]' subnet-016f14bb41af99e0f` |
| `module.vpc.aws_subnet.private[1]` | `subnet-0ddf4e8d1eb19f8f2` | `terraform import 'module.vpc.aws_subnet.private[1]' subnet-0ddf4e8d1eb19f8f2` |
| `module.vpc.aws_internet_gateway.this` | `igw-0f33875078b492da4` | `terraform import 'module.vpc.aws_internet_gateway.this' igw-0f33875078b492da4` |
| `module.vpc.aws_eip.nat[0]` | `eipalloc-0792ff970017ecc03` | `terraform import 'module.vpc.aws_eip.nat[0]' eipalloc-0792ff970017ecc03` |
| `module.vpc.aws_nat_gateway.this[0]` | `nat-0ebfe10f6d85a6239` | `terraform import 'module.vpc.aws_nat_gateway.this[0]' nat-0ebfe10f6d85a6239` |
| `module.vpc.aws_route_table.public` | `rtb-0043df114caef5de8` | `terraform import 'module.vpc.aws_route_table.public' rtb-0043df114caef5de8` |
| `module.vpc.aws_route_table.private[0]` | `rtb-0f0574784df576c6c` | `terraform import 'module.vpc.aws_route_table.private[0]' rtb-0f0574784df576c6c` |
| `module.vpc.aws_route_table.private[1]` | `rtb-0bf2f178f478b0f5d` | `terraform import 'module.vpc.aws_route_table.private[1]' rtb-0bf2f178f478b0f5d` |
| `module.vpc.aws_route_table_association.public[0]` | `subnet-0582c25e509a21086/rtb-0043df114caef5de8` | `terraform import 'module.vpc.aws_route_table_association.public[0]' subnet-0582c25e509a21086/rtb-0043df114caef5de8` |
| `module.vpc.aws_route_table_association.public[1]` | `subnet-01fe2e2a150d2d999/rtb-0043df114caef5de8` | `terraform import 'module.vpc.aws_route_table_association.public[1]' subnet-01fe2e2a150d2d999/rtb-0043df114caef5de8` |
| `module.vpc.aws_route_table_association.private[0]` | `subnet-016f14bb41af99e0f/rtb-0f0574784df576c6c` | `terraform import 'module.vpc.aws_route_table_association.private[0]' subnet-016f14bb41af99e0f/rtb-0f0574784df576c6c` |
| `module.vpc.aws_route_table_association.private[1]` | `subnet-0ddf4e8d1eb19f8f2/rtb-0bf2f178f478b0f5d` | `terraform import 'module.vpc.aws_route_table_association.private[1]' subnet-0ddf4e8d1eb19f8f2/rtb-0bf2f178f478b0f5d` |
| `module.ecr.aws_ecr_repository.this["canon/jira-bridge"]` | `canon-systems-v2-dev/canon/jira-bridge` | `terraform import 'module.ecr.aws_ecr_repository.this["canon/jira-bridge"]' canon-systems-v2-dev/canon/jira-bridge` |
| `module.ecr.aws_ecr_repository.this["canon/knowledge-api"]` | `canon-systems-v2-dev/canon/knowledge-api` | `terraform import 'module.ecr.aws_ecr_repository.this["canon/knowledge-api"]' canon-systems-v2-dev/canon/knowledge-api` |
| `module.ecr.aws_ecr_repository.this["canon/knowledge-worker"]` | `canon-systems-v2-dev/canon/knowledge-worker` | `terraform import 'module.ecr.aws_ecr_repository.this["canon/knowledge-worker"]' canon-systems-v2-dev/canon/knowledge-worker` |
| `module.ecr.aws_ecr_repository.this["canon/temporal-runtime"]` | `canon-systems-v2-dev/canon/temporal-runtime` | `terraform import 'module.ecr.aws_ecr_repository.this["canon/temporal-runtime"]' canon-systems-v2-dev/canon/temporal-runtime` |
| `module.ecr.aws_ecr_lifecycle_policy.this["canon/jira-bridge"]` | `canon-systems-v2-dev/canon/jira-bridge` | `terraform import 'module.ecr.aws_ecr_lifecycle_policy.this["canon/jira-bridge"]' canon-systems-v2-dev/canon/jira-bridge` |
| `module.ecr.aws_ecr_lifecycle_policy.this["canon/knowledge-api"]` | `canon-systems-v2-dev/canon/knowledge-api` | `terraform import 'module.ecr.aws_ecr_lifecycle_policy.this["canon/knowledge-api"]' canon-systems-v2-dev/canon/knowledge-api` |
| `module.ecr.aws_ecr_lifecycle_policy.this["canon/knowledge-worker"]` | `canon-systems-v2-dev/canon/knowledge-worker` | `terraform import 'module.ecr.aws_ecr_lifecycle_policy.this["canon/knowledge-worker"]' canon-systems-v2-dev/canon/knowledge-worker` |
| `module.ecr.aws_ecr_lifecycle_policy.this["canon/temporal-runtime"]` | `canon-systems-v2-dev/canon/temporal-runtime` | `terraform import 'module.ecr.aws_ecr_lifecycle_policy.this["canon/temporal-runtime"]' canon-systems-v2-dev/canon/temporal-runtime` |
| `module.artifacts_bucket.random_id.suffix` | `SVLyVw` | `terraform import 'module.artifacts_bucket.random_id.suffix' SVLyVw` |
| `module.artifacts_bucket.aws_s3_bucket.artifacts` | `canon-systems-v2-dev-artifacts-4952f257` | `terraform import 'module.artifacts_bucket.aws_s3_bucket.artifacts' canon-systems-v2-dev-artifacts-4952f257` |
| `module.artifacts_bucket.aws_s3_bucket_versioning.artifacts` | `canon-systems-v2-dev-artifacts-4952f257` | `terraform import 'module.artifacts_bucket.aws_s3_bucket_versioning.artifacts' canon-systems-v2-dev-artifacts-4952f257` |
| `module.artifacts_bucket.aws_s3_bucket_server_side_encryption_configuration.artifacts` | `canon-systems-v2-dev-artifacts-4952f257` | `terraform import 'module.artifacts_bucket.aws_s3_bucket_server_side_encryption_configuration.artifacts' canon-systems-v2-dev-artifacts-4952f257` |
| `module.artifacts_bucket.aws_s3_bucket_public_access_block.artifacts` | `canon-systems-v2-dev-artifacts-4952f257` | `terraform import 'module.artifacts_bucket.aws_s3_bucket_public_access_block.artifacts' canon-systems-v2-dev-artifacts-4952f257` |
| `module.placeholders.aws_secretsmanager_secret.placeholder["memory-layer__fmo__github-com-canonsystems-canon-systems-v2"]` | `canon-systems-v2-dev/memory-layer__fmo__github-com-canonsystems-canon-systems-v2` | `terraform import 'module.placeholders.aws_secretsmanager_secret.placeholder["memory-layer__fmo__github-com-canonsystems-canon-systems-v2"]' canon-systems-v2-dev/memory-layer__fmo__github-com-canonsystems-canon-systems-v2` |
| `module.placeholders.aws_secretsmanager_secret.placeholder["memory-layer__fmo__github-com-familyoneinc-familyonewebsite"]` | `canon-systems-v2-dev/memory-layer__fmo__github-com-familyoneinc-familyonewebsite` | `terraform import 'module.placeholders.aws_secretsmanager_secret.placeholder["memory-layer__fmo__github-com-familyoneinc-familyonewebsite"]' canon-systems-v2-dev/memory-layer__fmo__github-com-familyoneinc-familyonewebsite` |
| `module.ecs_baseline.aws_ecs_cluster.this` | `canon-systems-v2-dev-cluster` | `terraform import 'module.ecs_baseline.aws_ecs_cluster.this' canon-systems-v2-dev-cluster` |
| `module.ecs_baseline.aws_cloudwatch_log_group.this` | `/ecs/canon-systems-v2-dev` | `terraform import 'module.ecs_baseline.aws_cloudwatch_log_group.this' /ecs/canon-systems-v2-dev` |
| `module.ecs_baseline.aws_security_group.tasks` | `sg-0ee63ae6eb859760b` | `terraform import 'module.ecs_baseline.aws_security_group.tasks' sg-0ee63ae6eb859760b` |
| `module.ecs_baseline.aws_iam_role.execution` | `canon-systems-v2-dev-ecs-exec-20260413191631345300000001` | `terraform import 'module.ecs_baseline.aws_iam_role.execution' canon-systems-v2-dev-ecs-exec-20260413191631345300000001` |
| `module.ecs_baseline.aws_iam_role.task` | `canon-systems-v2-dev-ecs-task-20260413191631346000000002` | `terraform import 'module.ecs_baseline.aws_iam_role.task' canon-systems-v2-dev-ecs-task-20260413191631346000000002` |
| `module.ecs_baseline.aws_iam_role_policy_attachment.execution_managed` | `canon-systems-v2-dev-ecs-exec-20260413191631345300000001/arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy` | `terraform import 'module.ecs_baseline.aws_iam_role_policy_attachment.execution_managed' canon-systems-v2-dev-ecs-exec-20260413191631345300000001/arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy` |
| `module.ecs_baseline.aws_iam_role_policy.task` | `canon-systems-v2-dev-ecs-task-20260413191631346000000002:canon-systems-v2-dev-task-inline` | `terraform import 'module.ecs_baseline.aws_iam_role_policy.task' canon-systems-v2-dev-ecs-task-20260413191631346000000002:canon-systems-v2-dev-task-inline` |
| `module.ecs_baseline.aws_ecs_task_definition.baseline` | `canon-systems-v2-dev-baseline:2` | `terraform import 'module.ecs_baseline.aws_ecs_task_definition.baseline' canon-systems-v2-dev-baseline:2` |
| `module.ecs_baseline.aws_ecs_service.baseline` | `canon-systems-v2-dev-cluster/canon-systems-v2-dev-baseline` | `terraform import 'module.ecs_baseline.aws_ecs_service.baseline' canon-systems-v2-dev-cluster/canon-systems-v2-dev-baseline` |
| `module.rds.aws_db_subnet_group.this` | `canon-systems-v2-dev-db` | `terraform import 'module.rds.aws_db_subnet_group.this' canon-systems-v2-dev-db` |
| `module.rds.aws_security_group.rds` | `sg-099f857abab0afe70` | `terraform import 'module.rds.aws_security_group.rds' sg-099f857abab0afe70` |
| `module.rds.aws_db_instance.this` | `canon-systems-v2-dev-postgres` | `terraform import 'module.rds.aws_db_instance.this' canon-systems-v2-dev-postgres` |

Data sources (`data.aws_availability_zones.available`, `data.aws_region.current`,
`data.aws_caller_identity.current`, `data.aws_iam_policy_document.task`) require no
import.

## Reconciliation procedure

1. Configure backend and credentials (out of scope for E0-T4).
2. Run imports in an order that respects dependencies (VPC and `random_id` / S3
   before dependents; ECS after IAM and log group; RDS after VPC).
3. Resolve the **`random_password.db[0]`** gap (password variable vs. state
   migration) so `module.rds` can converge.
4. Run **`terraform plan`**. After a full import, **plan must show zero diffs**
   (operator acceptance; deferred from E0-T4 per OQ-E0-T4-01).

## Preserved identifiers + rationale

| Key | Value | Rationale |
| --- | --- | --- |
| `project_name` | `canon-systems-v2` | Matches live resource name prefixes; renaming would force replace (OQ-E0-T4-03). |
| `environment` | `dev` | Matches deployed stack. |
| `aws_region` | `us-east-1` | Live region. |
| AWS account | `222274634742` | Identifier only in docs; parity with v2 state. |

## Deferred items

- **Remote state backend** — not declared in this root yet (OQ-E0-T4-05).
- **Rename** `project_name` / resources to `canon-systems` — follow-up playbook
  only (OQ-E0-T4-03).
- **memory-adapter** runtime — no ECS/ECR here; E1-T2 (OQ-E0-T4-02).
- **ECR prune** — keep all four repos verbatim; do not drop `jira-bridge` /
  `temporal-runtime` while live (OQ-E0-T4-04).
- **`.terraform.lock.hcl`** — regenerate with `terraform init` locally
  (OQ-E0-T4-06).

## E2-T1 — DynamoDB canon-state table

**E2-T1 executed zero cloud commands** (no `terraform apply`, `terraform import`, `terraform plan`, or AWS API/CLI calls in-task).

The module [`modules/dynamodb-canon-state/`](modules/dynamodb-canon-state/) declares one DynamoDB table per Terraform configuration, named `"${var.project_name}-${var.environment}-canon-state"`. For `project_name = canon-systems-v2`, that is `canon-systems-v2-dev-canon-state`, `canon-systems-v2-staging-canon-state`, and `canon-systems-v2-prod-canon-state` when `environment` is `dev`, `staging`, and `prod` respectively.

**Operator apply (post-merge / when credentials and backend are configured):** from `infra/terraform/`:

```bash
terraform apply
```

**Import (if a table already exists and should be adopted into state):** from `infra/terraform/`, after selecting the correct workspace or `-var-file` for the target environment:

```bash
terraform import 'module.state_table.aws_dynamodb_table.this' 'canon-systems-v2-dev-canon-state'
terraform import 'module.state_table.aws_dynamodb_table.this' 'canon-systems-v2-staging-canon-state'
terraform import 'module.state_table.aws_dynamodb_table.this' 'canon-systems-v2-prod-canon-state'
```

Equivalent form using variable interpolation (resolve `project_name` and `environment` for the target stack; one import per environment/state):

```text
terraform import 'module.state_table.aws_dynamodb_table.this' "${var.project_name}-${var.environment}-canon-state"
```

### Run ledger + assignable tasks tables (same module)

The [`dynamodb-canon-state`](modules/dynamodb-canon-state/) module also declares:

- **`${var.project_name}-${var.environment}-canon-run-ledger`** — set **`STATE_RUN_LEDGER_TABLE_NAME`** on state-api.
- **`${var.project_name}-${var.environment}-canon-tasks`** — set **`STATE_TASKS_TABLE_NAME`** on state-api (canon-systems ≥ 3.7.0).

Import when adopting existing tables:

```bash
terraform import 'module.state_table.aws_dynamodb_table.run_ledger' 'canon-systems-v2-dev-canon-run-ledger'
terraform import 'module.state_table.aws_dynamodb_table.tasks' 'canon-systems-v2-dev-canon-tasks'
```

Root outputs: `state_run_ledger_table_name`, `state_tasks_table_name` (and ARNs). Operator runbook: [`docs/runbooks/TASKS-SERVER-DEPLOY.md`](../../docs/runbooks/TASKS-SERVER-DEPLOY.md).

## E3-T1 — axon-snapshots module (S3 + DynamoDB)

**E3-T1 executed zero cloud commands** in-task (waiver: operator `terraform apply` / AWS calls only with credentials and backend outside CI).

The module [`modules/axon-snapshots/`](modules/axon-snapshots/) adds one S3 bucket (`${var.project_name}-${var.environment}-axon-snapshots`) and one DynamoDB table (`...-axon-snapshots-meta`) for the graph retrieval plane (`backend/axon-service`). See the module [README](modules/axon-snapshots/README.md) for the key schema.

### Local validate / plan

From the repository root (requires Terraform >= 1.5 on `PATH`):

```bash
cd infra/terraform
terraform init -backend=false
terraform validate
terraform plan
```

**Apply** (operator; not run in this repo’s smoke by default without credentials):

```bash
cd infra/terraform
terraform apply
```

**Import** (adopt pre-existing resources; replace names with the real bucket and table for the target environment):

```bash
cd infra/terraform
terraform import 'module.axon_snapshots.aws_s3_bucket.snapshots' 'canon-systems-v2-dev-axon-snapshots'
terraform import 'module.axon_snapshots.aws_dynamodb_table.meta' 'canon-systems-v2-dev-axon-snapshots-meta'
```

Equivalent with variables:

```text
terraform import 'module.axon_snapshots.aws_s3_bucket.snapshots' "${var.project_name}-${var.environment}-axon-snapshots"
terraform import 'module.axon_snapshots.aws_dynamodb_table.meta' "${var.project_name}-${var.environment}-axon-snapshots-meta"
```

## Optional stable ingress for `ecs_baseline` (target group attachment)

This root keeps existing **`module.ecs_baseline`** naming and import addresses. Optional variables wire the baseline Fargate service to an **operator-provisioned** load balancer target group without creating ACM certificates or Route53 records here.

| Variable | Purpose |
| --- | --- |
| `ecs_ingress_enabled` | When `true`, add a `load_balancer` block on `aws_ecs_service.baseline` |
| `ecs_ingress_target_group_arn` | ARN of the existing target group (required when ingress is enabled) |
| `ecs_ingress_source_security_group_ids` | SGs allowed to reach `ecs_container_port` on the task ENIs (e.g. ALB SG); optional if you manage rules elsewhere |
| `memory_plane_stable_dns_hostname` | Bookkeeping only: echoed in `memory_plane_stable_dns_hostname` output for runbooks (not applied as a resource) |

**Outputs:** `ecs_ingress_enabled`, `ecs_ingress_target_group_arn`, `memory_plane_stable_dns_hostname`.

**CSC dev secret cutover** (`canon-memory-dev/memory-layer__csc__canon-systems`): after ingress and DNS/TLS work in AWS, update the secret JSON to stable `https://` bases for `KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, `MEMORY_ADAPTER_URL`, and `CANON_STATE_API_URL`; clear `~/.canon/memory-layer-aws-cache.json` or run `canon doctor --fix-cache`; validate with `scripts/validate_memory_endpoints.py` and `canon memory-health`. **Rollback:** restore the prior secret version in Secrets Manager, clear the cache again, re-validate. See `docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md` §1.2c.
