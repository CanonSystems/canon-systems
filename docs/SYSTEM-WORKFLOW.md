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
