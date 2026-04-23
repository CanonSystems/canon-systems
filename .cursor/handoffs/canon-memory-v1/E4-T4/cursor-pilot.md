<!-- CURSOR_PILOT_PROMPT: E4-T4 resume runbook + release gate -->

# E4-T4 Cursor-Pilot Prompt

## ROLE
You are the implementer for Canon Memory Platform v1, Wave 4, Task E4-T4 (Resume runbook + release gate). Work on branch `wave/4/canon-memory-v1` (tip `6312576` = E4-T3).

## TASK
Create `docs/runbooks/RESUME.md` (one-page operator runbook) and add an additive `## Resume check (E4-T4)` subsection to `src/canon_systems/templates/agents/release-orchestrator.md` that wires `canon resume` into the merge-gate lifecycle. Add 2 new template-assertion tests in `tests/test_agent_templates.py` (the done_signal test + a runbook-content test). No production code changes. Full suite must go from 363 → 365 passed.

## REPOSITORY

### Files to create (1)
1. `docs/runbooks/RESUME.md`

### Files to modify (additive only, 4)
2. `src/canon_systems/templates/agents/release-orchestrator.md` — append `## Resume check (E4-T4)` section at the END of the file (after the existing `## Checkpoint (read-before / write-after) contract` block, which ends around line 191).
3. `tests/test_agent_templates.py` — append 2 new test functions at the END of the file.
4. `CHANGELOG.md` — prepend E4-T4 bullet at the TOP of `## [Unreleased] ### Added`, above the existing E4-T3 bullet.
5. `docs/SYSTEM-WORKFLOW.md` — additive bullet in §3 adjacent to existing Wave-4 bullets.

### Forbidden surfaces
- `backend/**`, `infra/**`, `.cursor/rules/**`, `.cursor/plans/**`.
- `src/canon_systems/**/*.py` — NO production-code changes (E4-T4 is documentation + template only).
- Any template file under `src/canon_systems/templates/` except `release-orchestrator.md`.
- Any test file except `tests/test_agent_templates.py` (append new test functions only; do NOT edit existing tests).
- `README.md` — no new CLI, no new row.

## IMPLEMENTATION SPECIFICATION

### 1. `docs/runbooks/RESUME.md` (NEW)

Full required content (copy exactly, adjust only whitespace/formatting preferences):

```markdown
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

Discovery via an explicit JSON task list:

```shell
canon resume \
  --plan-id canon-memory-v1 \
  --company-id <c> --repository-id <r> \
  --tasks-file plan/tasks.json
```

where `plan/tasks.json` is a JSON array of `{"task_id": "E4-T1", "workstream_id": "ws-main"}` objects.

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
```

### 2. `src/canon_systems/templates/agents/release-orchestrator.md` — append section

Append at the END of the file (after the existing last bullet about Conflict recovery, which ends around line 191). Use this exact block so the 5 required anchors are present:

```markdown

## Resume check (E4-T4)

Before advancing the merge gate, run `canon resume` to verify every task in the plan has reached `release-orchestrator` / `completed`:

```shell
canon resume \
  --plan-id <plan_id> --company-id <company_id> --repository-id <repository_id> \
  --handoffs-dir .cursor/handoffs/<handoff_id>
```

Interpret the stdout envelope:

- `resume_target == null` AND `resume_available == false` AND empty `degraded_tasks` → wave is complete; merge gate MAY advance.
- `resume_target != null` → at least one task has an incomplete phase. Do NOT advance the merge gate. Re-invoke the indicated agent phase for the indicated `task_id`.
- `degraded_tasks` non-empty → state-api transport issue; resolve before advancing.

This check is required **before advancing the merge gate**; operators consult `docs/runbooks/RESUME.md` for the full operator workflow (including stall-watchdog cross-reference and troubleshooting).
```

**Required anchor substrings** (enforced by the new template test — keep verbatim):
- `## Resume check (E4-T4)`
- `canon resume`
- `docs/runbooks/RESUME.md`
- `resume_target`
- `before advancing the merge gate`

Do NOT modify or reorder any existing line. Do NOT edit any other template file.

### 3. `tests/test_agent_templates.py` — append 2 new test functions at END of file

Append at the very end of the file (after the existing `test_release_orchestrator_template_retrieval_telemetry` test function):

```python


def test_release_orchestrator_template_resume_aware() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("release-orchestrator.md").read_text(
        encoding="utf-8"
    )
    assert "## Resume check (E4-T4)" in body
    assert "canon resume" in body
    assert "docs/runbooks/RESUME.md" in body
    assert "resume_target" in body
    assert "before advancing the merge gate" in body


def test_resume_runbook_exists_and_covers_workflow() -> None:
    from pathlib import Path
    # Resolve relative to repo root: this test file lives at tests/test_agent_templates.py
    repo_root = Path(__file__).resolve().parent.parent
    runbook = repo_root / "docs" / "runbooks" / "RESUME.md"
    assert runbook.is_file(), f"Resume runbook missing at {runbook}"
    body = runbook.read_text(encoding="utf-8")
    assert "# Resume Runbook — canon resume" in body
    assert "canon resume --plan-id" in body
    assert "resume_target" in body
    assert "canon stall-watchdog" in body
    assert "Release-gate integration" in body
```

Do NOT modify any existing test function in this file.

### 4. `CHANGELOG.md` — prepend E4-T4 bullet

Insert at the TOP of `## [Unreleased] ### Added`, above the existing E4-T3 bullet:

```markdown
- **E4-T4** Resume runbook + release-gate integration: new `docs/runbooks/RESUME.md` one-page operator runbook for `canon resume` with basic invocation examples, output interpretation decision matrix, stall-watchdog cross-reference, release-gate integration pointer, and a troubleshooting table. New `## Resume check (E4-T4)` section in `src/canon_systems/templates/agents/release-orchestrator.md` wires the resume check into the merge-gate checklist (operators must confirm `resume_target == null` before advancing the merge gate). Two new template-assertion tests in `tests/test_agent_templates.py` (`test_release_orchestrator_template_resume_aware` satisfies the backlog done_signal; `test_resume_runbook_exists_and_covers_workflow` locks in the runbook structure). Documentation-only task; zero production-code changes; suite goes 363 → 365 passed.
```

### 5. `docs/SYSTEM-WORKFLOW.md` — append additive bullet in §3

Append a bullet adjacent to existing Wave-4 bullets in §3:

```markdown
- **E4-T4 resume runbook + release-gate integration:** new `docs/runbooks/RESUME.md` gives operators a one-page path for `canon resume`. The `release-orchestrator` template now requires a `canon resume` check before advancing the merge gate (`resume_target == null` AND empty `degraded_tasks`). Cross-references the E4-T3 stall watchdog for the combined "scan-then-resume" operator workflow.
```

## REASONING

1. Read `src/canon_systems/templates/agents/release-orchestrator.md` to confirm the append point (after the existing Conflict recovery bullet, near line 191).
2. Read `tests/test_agent_templates.py` to confirm style (importlib.resources body read + substring assertions); confirm exact function naming convention (`test_*`).
3. Write `docs/runbooks/RESUME.md` with the 8 required sections.
4. Append `## Resume check (E4-T4)` block to `release-orchestrator.md` with the 5 required anchor substrings.
5. Append 2 new test functions to `tests/test_agent_templates.py`.
6. Prepend CHANGELOG bullet; append SYSTEM-WORKFLOW bullet.
7. Run `pytest tests/test_agent_templates.py -q` → expect all existing tests + 2 new ones to pass (from 25 → 27).
8. Run `pytest -q` at repo root → expect 365 passed (363 + 2).
9. Emit `HANDOFF_TO_QA` to `.cursor/handoffs/canon-memory-v1/E4-T4/implementer.md`.

## OUTPUT FORMAT

Write full implementer packet with a `HANDOFF_TO_QA` block:
- `handoff_id: handoff_20260423_e4t4_resume_runbook`
- `task_id: E4-T4`
- `branch: wave/4/canon-memory-v1`
- `files_modified:` 5 paths exactly (1 new + 4 modified).
- `acceptance_criteria:` 8 ACs each with `status: MET`, `evidence`, `run_result`, `covering_tests` (bare pytest node IDs or file paths; NO prefixes; every AC ≥1 entry; block-style YAML).
- `suite_result:` pytest summary (focused + full).

## STOP CONDITIONS

Stop and surface a blocker if:
- Modifying `release-orchestrator.md` would require editing any existing line (it must be strict append).
- Any existing `test_release_orchestrator_template_*` test starts failing — that means the append leaked backward-compat.
- Adding any test requires production-code changes.
- The existing `docs/runbooks/auth-migration-rollback.md` style clashes with the required runbook structure (unlikely — they're independent files).
