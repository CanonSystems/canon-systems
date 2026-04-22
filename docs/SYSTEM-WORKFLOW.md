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
- DoR telemetry sender (with queue fallback):
  - `canon dor-log --event-file <event.json>`

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
