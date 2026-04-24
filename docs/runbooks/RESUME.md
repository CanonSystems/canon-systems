# Resume Runbook — canon resume

This runbook is the one-page operator path for resuming a stalled or interrupted Canon Memory Platform build using `canon resume`. It complements `canon stall-watchdog scan` (E4-T3) and is referenced by the `release-orchestrator` template's merge-gate checklist.

## When to use

- **Agent crash or forced restart**: an implementer/qa-gate/release-orchestrator subagent was interrupted mid-phase and you need to determine which `(task_id, phase)` pair to re-invoke.
- **Context-window rollover**: a parent orchestrator hit its context budget mid-wave and needs to hand off to a fresh conversation with the correct resume target.
- **Post-merge sanity check**: before advancing a wave PR, verify every task reached `release-orchestrator` / `completed` with no gaps.

## Basic invocation

Discovery via the on-disk handoff directory (recommended — tasks self-describe):

```shell
canon resume \
  --plan-id canon-memory-v1 \
  --company-id <c> --repository-id <r> \
  --handoffs-dir .cursor/handoffs/canon-memory-v1
```

Equivalent one line (no continuations):

```shell
canon resume --plan-id canon-memory-v1 --company-id <c> --repository-id <r> --handoffs-dir .cursor/handoffs/canon-memory-v1
```

Discovery via an explicit JSON task list:

```shell
canon resume \
  --plan-id canon-memory-v1 \
  --company-id <c> --repository-id <r> \
  --tasks-file plan/tasks.json
```

where `plan/tasks.json` is a JSON array of `{"task_id": "E4-T1", "workstream_id": "ws-main"}` objects.

Optional enriched entries (for **experimental** parent-session multilane planning only) may add `depends_on` (JSON array of `task_id` strings), `parallel_group` (string), and `can_run_parallel` (boolean). Those fields are ignored unless you pass **`--lanes`** (see below).

## Experimental multilane mode (`--lanes`, `--tasks-file` only)

**Opt-in:** set **`CANON_EXPERIMENTAL_MULTILANE_ORCHESTRATION=1`** on the parent orchestrator and use an enriched manifest. The hard-lock build rule (**`memory-platform-build-discipline.mdc` §11**) describes policy; this section is the operator summary.

```shell
canon resume \
  --plan-id canon-memory-v1 \
  --company-id <c> --repository-id <r> \
  --tasks-file plan/tasks.json \
  --lanes
```

**Constraints:**

- **`--lanes` requires `--tasks-file`**. It is **not** supported with `--handoffs-dir` (exit `4`).
- Adds **`experimental_lanes`: true** plus **`runnable_targets`**, **`active_targets`**, **`blocked_targets`**, and **`task_threads`** to the JSON envelope. **`resume_target`**, exit codes, and checkpoint I/O are unchanged from the serial engine (first incomplete task in file order with a readable checkpoint).
- **Merge-gate and release sweeps** should keep using **legacy serial discovery** (`--handoffs-dir` or a plain tasks-file **without** relying on lane-only fields) so incomplete work is not missed when experimental scheduling is off.

## Interpreting the output

A typical envelope on stdout:

```json
{
  "company_id": "<c>",
  "degraded_tasks": [],
  "plan_id": "canon-memory-v1",
  "repository_id": "<r>",
  "resume_available": true,
  "resume_target": {"phase": "implementer", "task_id": "E4-T2", "workstream_id": "ws-main"},
  "tasks_completed": 1,
  "tasks_scanned": 4
}
```

Operator decision matrix:

- `resume_target != null` → re-invoke that agent phase for that task_id. The phase value is one of the canonical 5: `scoper`, `cursor-pilot`, `implementer`, `qa-gate`, `release-orchestrator`.
- `resume_target == null` AND `resume_available == false` → all tasks fully completed (nothing to resume).
- `degraded_tasks` non-empty → state-api is unreachable or returning 5xx for some tasks. Resolve the transport issue first, then re-run.
- `resume_available == false` with non-empty `degraded_tasks` → conservative degrade: the engine cannot prove completion, so it refuses to advance. Fix state-api and re-run.

Exit codes: `0` (clean or degraded-partial), `4` (usage error), `5` (all tasks transport-degraded).

## Integration with the stall watchdog (E4-T3)

Recommended ordering before any resume action:

```shell
canon stall-watchdog scan \
  --plan-id canon-memory-v1 --company-id <c> --repository-id <r> \
  --handoffs-dir .cursor/handoffs/canon-memory-v1 \
  --dry-run
canon resume \
  --plan-id canon-memory-v1 --company-id <c> --repository-id <r> \
  --handoffs-dir .cursor/handoffs/canon-memory-v1
```

The stall watchdog surfaces any lease whose `expires_at <= now_epoch`; resolve those (via `canon checkpoint lease-acquire` per the `suggested_next_step` in the emitted `lease_stall_detected` event) before acting on the resume target.

## Release-gate integration

The `release-orchestrator` subagent consults `canon resume` as part of the Merge-gate checklist (see `src/canon_systems/templates/agents/release-orchestrator.md § Resume check (E4-T4)`). A wave PR must not be advanced to merge unless `canon resume` reports `resume_target == null` for the plan — i.e., every task has reached `release-orchestrator` / `completed`.

## Troubleshooting

| Exit | Meaning | Recovery |
|---|---|---|
| `4` | Usage error (missing flag, both `--tasks-file` and `--handoffs-dir`, bad JSON) | Re-read `canon resume --help`; supply exactly one of the two discovery flags. |
| `5` | All tasks transport-degraded (state-api unreachable) | Check `CANON_STATE_API_URL`; verify state-api health; re-run. |
| `0` + `resume_available: false` + empty `degraded_tasks` | All tasks complete | No action — wave is ready for PR/merge. |
| `0` + `resume_available: false` + non-empty `degraded_tasks` | Conservative degrade | Resolve degraded-task transport issues first, then re-run. |

## See also

- `canon resume --help`
- `canon stall-watchdog scan --help`
- `CHANGELOG.md` entries E4-T1 (resume engine) and E4-T3 (stall watchdog)
- `docs/SYSTEM-WORKFLOW.md` §3 (Wave-4 resilience surfaces)
