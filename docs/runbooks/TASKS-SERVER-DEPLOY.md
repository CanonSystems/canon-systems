# Runbook: server-authoritative `canon task` (state-api task plane)

This runbook wires **`STATE_TASKS_TABLE_NAME`** on the running **state-api** process
and backfills local FMO (or other) task ledgers to the server. It complements
[`TASKS-ROLLOUT.md`](TASKS-ROLLOUT.md) (CLI auto-update) and ships with **canon-systems 3.7.0+**.

## Prerequisites

- **canon-systems ≥ 3.7.0** on state-api hosts and developer machines (`pipx upgrade canon-systems`).
- AWS credentials for the target environment (same profile used for other Canon infra).
- Clients already use **`CANON_STATE_API_URL`** (often the same base as `KNOWLEDGE_API_URL`, e.g. `https://memory.canon-systems.com`). No separate URL is required unless you run a dedicated state-api host.

## 1. Provision the DynamoDB table (Terraform)

From `infra/terraform/` with the correct workspace / `-var-file` for **dev**, **staging**, or **prod**:

```bash
cd infra/terraform
terraform plan   # expect new aws_dynamodb_table.tasks
terraform apply
```

Table name pattern: **`${project_name}-${environment}-canon-tasks`**  
(e.g. `canon-systems-v2-dev-canon-tasks`).

**Import** if the table already exists:

```bash
terraform import 'module.state_table.aws_dynamodb_table.tasks' 'canon-systems-v2-dev-canon-tasks'
```

Capture outputs:

```bash
terraform output -raw state_tasks_table_name
terraform output -raw state_tasks_table_arn
```

## 2. Configure state-api (server env)

On every process that serves **`/state/tasks`** (ECS task definition, App Runner, or sidecar), set:

| Variable | Value |
|----------|--------|
| `STATE_TASKS_TABLE_NAME` | `terraform output -raw state_tasks_table_name` |
| `AWS_REGION` | Same region as the table (e.g. `us-east-1`) |
| `STATE_TABLE_NAME` | *(unchanged)* checkpoint table |
| `STATE_RUN_LEDGER_TABLE_NAME` | *(unchanged)* run-ledger table |
| `STATE_ARTIFACT_BUCKET` | *(unchanged)* archive bucket |

**IAM (task role):** grant DynamoDB on the tasks table ARN (same actions as run-ledger):

- `dynamodb:GetItem`, `PutItem`, `Query` on `state_tasks_table_arn` and `state_tasks_table_arn/index/*`

Redeploy state-api after setting env vars so the new routes are live.

## 3. Verify the task plane

Replace `BASE` with your `CANON_STATE_API_URL` (no trailing slash):

```bash
BASE=https://memory.canon-systems.com
curl -sS "$BASE/healthz"
curl -sS "$BASE/state/tasks?company_id=FMO&limit=5"
# expect 200 {"events":[],"count":0} — not 404, not 503 tasks_table_unset
```

Optional smoke POST (idempotent `event_id`):

```bash
curl -sS -X POST "$BASE/state/tasks/events" -H 'Content-Type: application/json' -d '{
  "schema_version": 1,
  "event_type": "task_created",
  "event_id": "evt_deploy_smoke_001",
  "task_ref": "tsk_deploy_smoke",
  "timestamp": "2026-06-02T12:00:00Z",
  "actor_id": "operator",
  "company_id": "FMO",
  "scope": "company",
  "fields": {"title": "deploy smoke", "status": "open"}
}'
```

## 4. Backfill local ledgers to the server

From any **wired** repo for that `company_id` (e.g. FMO showtrail):

```bash
cd ~/localwork/go.showtrail.website
canon task sync --scan-localwork
```

`--scan-localwork` unions events from:

- the current repo's `.canon/tasks/ledger.ndjson`,
- `~/.canon/tasks/<company_id>/ledger.ndjson`,
- every `~/localwork/*/.canon/tasks/ledger.ndjson` (multi-repo imports).

Then confirm:

```bash
canon task list --all-repos --json | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"
canon task next --json
```

## 5. Developer machines after deploy

1. `pipx upgrade canon-systems` (or rely on auto-update on next `canon` call).
2. `canon doctor --fix-cache` if URLs changed.
3. `canon task sync --scan-localwork` once per company after the server is live.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| `GET /state/tasks` → **404** | Gateway or image predates 3.7.0 routes | Deploy state-api build with `/state/tasks`; confirm path routing to state-api |
| **503** `tasks_table_unset` | `STATE_TASKS_TABLE_NAME` unset on server | Set env + redeploy; verify with `curl` |
| `canon task sync`: all pushes **failed** | Server unreachable or table/IAM missing | Fix §2–3, retry sync |
| Tasks visible locally but not on another machine | Server backfill not run | `canon task sync --scan-localwork` from a wired repo |
| `canon task next` empty | No open tasks for `--mine` in this repo | `canon task list --all-repos` or `canon task next --any` |
