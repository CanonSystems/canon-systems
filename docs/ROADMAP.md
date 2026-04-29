# Roadmap — future work (unordered)

This file collects **future** initiatives. **Order is not priority.** Pull items into plans or tickets when you are ready to execute.

- **AWS naming debt — `canon-systems-v2` → `canon-systems`:** Today many live resources still use the historical prefix `canon-systems-v2-dev` (and related names) because Terraform `project_name` and imported state came from the sibling `canon-systems-v2` repo. The Git monorepo is **`canon-systems`**; aligning **cloud** names (S3 buckets, DynamoDB tables, ECR repository namespace segments, optional IAM path labels, documentation examples) with `canon-systems-<env>` would reduce confusion. **Requires** a deliberate migration (create parallel resources or rename where supported, update secrets and clients, cut over, retire old names) — not a find/replace in code alone.

- **Terraform remote state** for roots under `infra/` (including `infra/axon-only/` and the main `infra/terraform/` stack) so teams share one state backend instead of local `terraform.tfstate`.

- **Stricter E2E / CI gate** optionally treating **graph** (and/or **state**) as required in `canon e2e-check` for tenants that mandate the full four-plane stack.

- **Rotate / externalize** long-lived bearer tokens (e.g. graph, shared `CANON_HTTP_BEARER_TOKEN`) via short-lived credentials or per-service auth where product requirements allow.

- **Single “operator runbook”** for greenfield AWS: order of apply (VPC, data planes, App Runner/ECS, secrets, smoke tests) generated from the same sources as docs to avoid drift.

- **Structured resume + task memory layer, with later Jira-like workflow integration:** Add first-class Canon artifacts for `session_handoff`, `plan`, `epic`, `task`, `task_update`, and `decision` so new chats can resume from durable rationale and tasks can be looked up by id. Keep this inside Canon first because it is agent execution context, crash recovery, and memory retrieval; later integrate with Jira/Linear-style systems only for portfolio workflow concerns. Detailed plan: [STRUCTURED-RESUME-TASK-MEMORY-PLAN.md](STRUCTURED-RESUME-TASK-MEMORY-PLAN.md).

(Add more bullets anytime; keep them self-contained one-liners.)
