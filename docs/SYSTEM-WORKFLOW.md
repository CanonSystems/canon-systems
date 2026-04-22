# Canon System Workflow (Living Spec)

This document is the current source of truth for how Canon works end-to-end.
Update it on every meaningful Canon iteration (new command, gate, agent
contract, hook behavior, memory behavior, or rollout policy).

## 1) Runtime model

- Canon ships as one CLI package: `canon-systems` (binary: `canon`).
- Scope is tenant-bound by `company_id` + `repository_id`.
- Memory is AWS-backed and loaded from layered env + Secrets Manager.
- Cursor hooks run per turn:
  - preflight context hydration
  - post-response memory capture
- Failed or unreachable MemPalace `/memory/search` calls are classified (`mempalace_status` in preflight + `canon ask --json`); non-ok outcomes are logged to a local JSONL queue (`.canon/memory/mempalace-retry-queue.jsonl`) for later replay — exit codes stay healthy unless another failure applies.

## 2) Core execution chain

For non-trivial work, expected chain:

`project-planner -> scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator`

Key contracts:

- `project-planner` emits `PROJECT_EXECUTION_PLAN` with task graph.
- `scoper` emits `HANDOFF_TO_CURSOR_PILOT` (or `HANDOFF_NOT_READY`).
- `cursor-pilot` emits `CURSOR_PILOT_PROMPT` (or `HANDOFF_NOT_READY`).
- `implementer` emits `HANDOFF_TO_QA` / `HANDOFF_TO_QA_SHARD`.
- `qa-gate` emits `GATE_RESULTS`.
- `release-orchestrator` emits `RELEASE_STATUS`.

## 3) Persistence contract (required)

Packets must be file-backed, not chat-only:

- `.cursor/handoffs/<handoff_id>/<task_id>/scoper.md`
- `.cursor/handoffs/<handoff_id>/<task_id>/cursor-pilot.md`
- `.cursor/handoffs/<handoff_id>/<task_id>/qa-gate.md`
- `.cursor/handoffs/<handoff_id>/<task_id>/release-status.md`

Plan state file:

- `.cursor/plans/<plan-id>.plan.md` updated on every task status transition.

## 4) DoR rejection telemetry contract

When `scoper` or `cursor-pilot` returns `HANDOFF_NOT_READY`, parent orchestration
must persist and send telemetry artifacts:

- Rejection packet:
  - `.cursor/handoffs/<handoff_id>/<task_id>/handoff-not-ready/<stage>-<timestamp>.md`
- Telemetry event payload:
  - `.cursor/handoffs/<handoff_id>/<task_id>/dor-failure/<stage>-<timestamp>.json`
- Telemetry send status:
  - `.cursor/handoffs/<handoff_id>/<task_id>/dor-failure/<stage>-<timestamp>.status`
  - Must include `exit_code:`
- Send command:
  - `canon dor-log --event-file <payload-json> --quiet`

## 5) Merge/release gates

Before merge, require all:

- `qa-gate` verdict PASS
- `canon qa-validate --file ... --require-pass`
- `canon qa-validate ... --handoff-id <id> --task-id <id> --require-dor-telemetry`
- sampled `canon flow-audit --handoff-id <id> --task-id <id> --sample-rate 0.2`
- required CI checks PASS
  - `canon flow-audit --handoff-id <id> --task-id <id> --require-memory-health` (optional in Wave 0; required by release-orchestrator from Wave 1+) verifies on-disk per-task `memory-health.json` evidence (schema v1, overall_status ok) before merge

Before deploy promotion:

- environment smoke checks PASS
- promotion order respected (`dev -> staging -> production/TestFlight`)

### 5.1) Auto-branching + per-task commits + PR-at-wave-close

For multi-wave initiatives (e.g. the Canon Memory Platform v1 build), the
parent orchestrator operates an auto-branching commit/PR protocol on top of
the merge/release gates above. The authoritative contract lives in
`.cursor/rules/memory-platform-build-discipline.mdc` §§9-10; the summary below
exists solely to keep this living spec honest per §G of the backlog.

- **Wave branch:** one long-lived branch per wave, named
  `wave/<N>/<handoff_id>` (e.g. `wave/0/canon-memory-v1`), cut from `main` at
  wave start, before any pre-flight chore commit.
- **Pre-flight chore commit:** orchestration artifacts needed before the first
  task (rule install, backlog rewrites, plan copies, living-spec mirrors like
  this subsection) land on the wave branch as a single
  `chore(memory-platform-v1): <brief>` commit.
- **Per-task commit:** on `verdict: READY_TO_MERGE` in a task's
  `release-status.md`, the parent MUST stage the task's artifacts plus its
  packet quartet (`scoper.md`, `cursor-pilot.md`, `qa-gate.md`,
  `release-status.md`) and commit with a Conventional Commit message carrying
  `handoff_id`, `plan_id`, and `workstream_id` trailers. One commit per task,
  no squashing, no amending once pushed.
- **PR at wave close:** after the last task in the wave lands, parent pushes
  the wave branch and opens a PR with a per-task summary table, base `main`,
  title `wave/<N>: <epic title>`.
- **Auto-merge:** permitted only if every task commit has qa-gate PASS,
  qa-validate PASS, and flow-audit PASS packets on disk; required CI is green;
  and either `CANON_AUTO_MERGE=1` is set or a required-reviewer approval is
  present. From Wave 1 onward, `canon memory-health` must also exit 0. If any
  gate is missing, the PR stays open for human review and the parent proceeds
  to the next wave branch rather than blocking.
- **Cross-wave sequencing:** the next wave's branch is cut from `main` after
  the prior wave's PR merges (not from the prior wave branch). If the parent
  speculatively cuts the next wave while the prior PR is still open, it MUST
  rebase onto `main` once the prior merges.
- **Never automatic:** force-push, rewriting pushed commits, merging to `main`
  without CI+approval or `CANON_AUTO_MERGE=1`, or deleting non-wave branches.

See rule §§9-10 for authoritative wording.

## 6) Validation commands

- QA packet validator:
  - `canon qa-validate --file <qa-gate.md> --require-pass`
- Process audit validator:
  - `canon flow-audit --handoff-id <id> --task-id <id> --plan-file <plan>`
- Memory health probe: `canon memory-health [--required <csv>] [--timeout-ms <int>]`
- Graph retrieval plane: [`backend/axon-service`](../backend/axon-service/README.md) exposes `/axon/{company_id}/{repository_id}/index`, `/query`, `/impact`, and `/healthz`. `canon memory-health` treats **graph** as optional by default; it probes the axon service at **`AXON_SERVICE_URL`** (append `/healthz`) when that env is set.
- State checkpoint/lease: `canon checkpoint ...` (read/write/lease) against a deployed `state-api` (JSON over HTTP; use `--base-url` or `CANON_STATE_API_URL`)
- Phase-boundary hydration: agents run `canon checkpoint read` before their phase work and `canon checkpoint write` after, via `state-api`; when `CANON_STATE_API_URL` is unset, skip checkpoint HTTP gracefully (local dev, sandbox, or CI without a reachable state plane).
- DoR telemetry sender (with queue fallback):
  - `canon dor-log --event-file <event.json>`
  - **memory-health evidence (Wave 1+):** `canon memory-health --output .cursor/handoffs/<handoff_id>/<task_id>/memory-health.json` to persist; `canon flow-audit ... --require-memory-health` to enforce at merge (release-orchestrator contract).
- On-disk per-phase checkpoint files: merge gates may run `canon flow-audit --require-checkpoints` and `canon qa-validate --require-checkpoints` (with handoff/task ids) to block integration when any of the five phase checkpoint artifacts is missing or invalid.

## 7) Automation and propagation

- Self-update checks are automatic (throttled).
- Repo/user wiring auto-refreshes when installed version is newer than pinned.
- Global auto-rewire updates previously wired repos under configured roots.

## 8) Living update checklist (required per iteration)

When Canon behavior changes, update in the same PR:

1. This file (`docs/SYSTEM-WORKFLOW.md`)
2. `README.md` command/behavior docs
3. Relevant agent templates/rules
4. Tests that enforce the new behavior
5. `CHANGELOG.md`

If any of the five are missing, iteration is incomplete.

## 9) Forward plan

The live architectural direction is tracked in:

- `docs/MEMORY-PLATFORM-PLAN.md` (target architecture + why)
- `docs/MEMORY-PLATFORM-BACKLOG.md` (executable `PROJECT_EXECUTION_PLAN` that
  the `scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator`
  chain runs task-by-task)

When changing the workflow, update this file and the backlog in the same PR.

## 10) Backend monorepo layout

Python backend services and the stdlib-only shared library (`canon_backend_shared`
under `backend/shared/`) are colocated in `backend/` as setuptools packages, with
`synthesis-web/` reserved for a future UI entrypoint (see E5-T4). Use
`uv sync --all-packages` or `bash scripts/backend/install-workspace.sh` from the
repo root to install the workspace. **`knowledge-api`** (flat `app/` + Alembic),
**`knowledge-worker`**, and **`memory-adapter`** use the consolidated sources from
`sibling` `canon-systems-v2` documented in
[`docs/E0-T3-MIGRATION-NOTES.md`](E0-T3-MIGRATION-NOTES.md) (git history waived
there in favor of a per-file map). The same migration brought **`knowledge-schema`**,
**`knowledge-policy`**, and **`knowledge-client`** into `backend/` so `pip install -e`
does not depend on a v2-style `libs/` checkout. For a quick CI-oriented check, run
`bash scripts/backend/build-services.sh` after `pip`/`uv` resolves deps — it
installs `backend/shared` and each leaf Python package, then import-smokes
`*.main.app`. Details: `backend/README.md`.

**AWS plane (declarative):** `infra/terraform/` is now the in-repo Terraform root
mirrored from `canon-systems-v2` (VPC, ECR, baseline ECS Fargate, RDS, S3
artifacts, Secrets Manager placeholders for the `canon-systems-v2` / `dev` stack in
`us-east-1`). It is **import-prep only** in Wave 0: operators reconcile remote state
and run `terraform plan` until zero drift (see [`docs/E0-T4-INFRA-IMPORT.md`](E0-T4-INFRA-IMPORT.md)
and [`infra/terraform/README.md`](../infra/terraform/README.md)). **`infra/auth-ingress/`**
remains a separate workstream (Cognito / public ingress), not wired from this root.

- **DynamoDB `canon-state` (E2-T1):** [`infra/terraform/modules/dynamodb-canon-state/`](../infra/terraform/modules/dynamodb-canon-state/) defines the per-environment `canon-state` table (composite keys `pk`/`sk`, TTL on `lease_expires_at`, PITR, SSE); E2-T1 did not run `terraform apply` (operator follow-up; see [`infra/terraform/README.md`](../infra/terraform/README.md)).
- **`state-api` (E2-T2):** the [`backend/state-api/`](../backend/state-api/README.md) FastAPI service is the **operational-state plane** endpoint for checkpoint reads/writes and lease acquire/renew/release against that table (REST §B shapes + canonical `checkpoint_write` events).

**Consolidation smoke (Wave 0):** `bash scripts/smoke-test.sh` proves the monorepo still
builds, passes the full Python test run, and passes `terraform` validate (local init
with `-backend=false`, no `apply`) from a dev or CI shell. The workflow
**Canon Smoke Test** in `.github/workflows/ci.yml` runs the same script on
`pull_request` and on `push` to `main` and `wave/**`. It does not invoke the `canon`
CLI or call live service URLs; operator follow-up for end-to-end live checks is tracked
in [`docs/WAVE-0-CLOSEOUT.md`](WAVE-0-CLOSEOUT.md) (including OQ-E0-T4-01 and
OQ-E0-T5-01).
