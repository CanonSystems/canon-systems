# E4-T4 Scoper Packet — Resume runbook + release gate

## SCOPE_SUMMARY

E4-T4 ships the operator-facing documentation layer for Wave 4's orchestrator-resilience tooling: a new `docs/runbooks/RESUME.md` one-page runbook that walks operators through the `canon resume` workflow with concrete invocations and sample output interpretations, plus an additive "## Resume check (E4-T4)" subsection in `src/canon_systems/templates/agents/release-orchestrator.md` that wires the resume check into the release-gate lifecycle (operators and the release-orchestrator subagent MUST consult `canon resume` output before advancing a merge gate). A new template-assertion test in `tests/test_agent_templates.py` (`test_release_orchestrator_template_resume_aware`) satisfies the backlog's done_signal ("Template test asserts resume-aware wording"). No production code changes; no new CLI; zero risk to the existing 363-test suite.

## SCOPE_PACKET

### Identifiers
- `handoff_id`: `handoff_20260423_e4t4_resume_runbook`
- `task_id`: `E4-T4`
- `wave`: `4`
- `parallel_group`: `wave-4c`
- `branch`: `wave/4/canon-memory-v1` (tip `6312576` = post-E4-T3)
- `depends_on`: `E4-T1`

### Story — acceptanceCriteria (8)

1. **New file `docs/runbooks/RESUME.md`** (one-page operator runbook). Required sections with specific content:
   - Title: `# Resume Runbook — canon resume` with a 2-3 line purpose statement.
   - `## When to use`: bullets describing the three common triggers (agent crash/restart, context-window rollover, post-merge sanity check before advancing waves).
   - `## Basic invocation`: a complete copy-pasteable `canon resume --plan-id <id> --company-id <c> --repository-id <r> --handoffs-dir .cursor/handoffs/<handoff_id>` example and a `--tasks-file` variant.
   - `## Interpreting the output`: a verbatim sample JSON envelope showing `resume_target = {"task_id": "E4-T2", "workstream_id": "ws-main", "phase": "implementer"}` and an operator decision matrix (target=null → fully complete; degraded_tasks populated → state-api issue; resume_available=false → conservative degrade).
   - `## Integration with the stall watchdog (E4-T3)`: a brief cross-reference showing the recommended ordering — `canon stall-watchdog scan` first (to detect stalled leases), then `canon resume` (to find the next actionable phase) — with a concrete 3-line shell example.
   - `## Release-gate integration`: a note that the release-orchestrator subagent now consults `canon resume` as part of the Merge-gate checklist (cross-reference to `src/canon_systems/templates/agents/release-orchestrator.md § Resume check (E4-T4)`).
   - `## Troubleshooting`: a 3-row table covering exit 4 (usage), exit 5 (transport), and the `resume_available: false` case.
   - `## See also`: cross-references to `canon resume --help`, `canon stall-watchdog scan --help`, `CHANGELOG.md` E4-T1/E4-T3, and `docs/SYSTEM-WORKFLOW.md` §3.
2. **Additive `## Resume check (E4-T4)` subsection in `src/canon_systems/templates/agents/release-orchestrator.md`**. Append AFTER the existing `## Checkpoint (read-before / write-after) contract` block (i.e., at the end of the file or in the Merge-gate area). Do NOT modify or reorder any existing line. Required wording anchors (these are the exact substrings asserted by the new template test):
   - Section header: `## Resume check (E4-T4)`
   - `canon resume`
   - `docs/runbooks/RESUME.md`
   - `resume_target`
   - `before advancing the merge gate`
3. **New template-assertion test in `tests/test_agent_templates.py`** named exactly `test_release_orchestrator_template_resume_aware`. Assertions:
   - `"## Resume check (E4-T4)" in body`
   - `"canon resume" in body`
   - `"docs/runbooks/RESUME.md" in body`
   - `"resume_target" in body`
   - `"before advancing the merge gate" in body`
   This is the done_signal: "Template test asserts resume-aware wording."
4. **A second new template-assertion test in `tests/test_agent_templates.py`** named exactly `test_resume_runbook_exists_and_covers_workflow`. Assertions: the file `docs/runbooks/RESUME.md` exists, contains the heading `# Resume Runbook — canon resume`, contains `canon resume --plan-id`, contains `resume_target`, contains `canon stall-watchdog`, and contains `docs/runbooks/RESUME.md` or references itself in the release-orchestrator context (e.g., "Release-gate integration" section). Test reads from repo root via `Path`.
5. **Living-spec additive edits**:
   - `CHANGELOG.md`: prepend E4-T4 bullet at the TOP of `## [Unreleased] ### Added`, above the existing E4-T3 bullet.
   - `docs/SYSTEM-WORKFLOW.md`: additive bullet in §3 adjacent to the existing Wave-4 bullets, describing the runbook + release-orchestrator resume check.
   - `README.md`: **skip** — no new CLI or flag (E4-T4 is documentation only).
6. **Backward-compat regression guard**: the existing `test_release_orchestrator_template_has_merge_and_deploy_gates` and `test_release_orchestrator_template_checkpoint_contract` and `test_release_orchestrator_template_retrieval_telemetry` tests (3 existing tests) MUST continue to pass. Any modification to `release-orchestrator.md` is strictly append-only; none of the pre-existing substrings asserted by these tests may be altered.
7. **Suite baseline**: the full pytest run must go from **363 passed** (post-E4-T3 tip) to **365 passed** (adding exactly 2 new template tests); no regressions.
8. **Forbidden-surface compliance**: no edits to `src/canon_systems/*.py`, `backend/**`, `infra/**`, `.cursor/rules/**`, `.cursor/plans/**`, or any template file other than `release-orchestrator.md`. No edits to any existing test file other than `tests/test_agent_templates.py` (which receives 2 new test functions, appended at the end).

### Done signal

- Backlog: `Template test asserts resume-aware wording.` → satisfied by `tests/test_agent_templates.py::test_release_orchestrator_template_resume_aware`.

### Forbidden surfaces

- `backend/**`, `infra/**`, `.cursor/rules/**`, `.cursor/plans/**`.
- `src/canon_systems/**/*.py` — no production-code changes (E4-T4 is documentation + template).
- Any template file under `src/canon_systems/templates/` except `release-orchestrator.md`.
- Any test file except `tests/test_agent_templates.py` (new test functions appended only; no existing test may be edited).
- `README.md` — no new CLI, no new row.

### Repository
- primaryLanguages: Markdown + Python test additions.
- testFramework: pytest.
- relevantFiles:
  - Create: `docs/runbooks/RESUME.md`.
  - Modify (additive): `src/canon_systems/templates/agents/release-orchestrator.md`, `tests/test_agent_templates.py` (append 2 new test functions), `CHANGELOG.md`, `docs/SYSTEM-WORKFLOW.md`.
  - Read-only reference: `src/canon_systems/resume_engine.py`, `src/canon_systems/stall_watchdog.py`, `docs/runbooks/auth-migration-rollback.md` (style template for other runbook).

### Constraints
- dependencies: `E4-T1` (runbook documents the `canon resume` CLI shipped there).
- mustNotBreak:
  - 363-test suite baseline.
  - 3 existing `test_release_orchestrator_template_*` tests (any rewording in release-orchestrator.md must be strictly additive).
  - Wave-4 waiver (no live state-api).

### Prior work references
- peer:`src/canon_systems/resume_engine.py` (E4-T1) — CLI shape, flag surface, output envelope shape; runbook examples draw from this.
- peer:`src/canon_systems/stall_watchdog.py` (E4-T3) — cross-reference for combined workflow section.
- peer:`src/canon_systems/templates/agents/release-orchestrator.md` — append point after the `## Checkpoint (read-before / write-after) contract` section (ends around line 191).
- peer:`tests/test_agent_templates.py` — style reference: `importlib.resources`-based template body reads + substring assertions; lines 26-53 show the existing `test_release_orchestrator_template_has_merge_and_deploy_gates` pattern.
- peer:`docs/runbooks/auth-migration-rollback.md` — existing runbook for style/format reference.
- peer:`.cursor/handoffs/canon-memory-v1/E4-T1/scoper.md` — `canon resume` AC reference.
- peer:`.cursor/handoffs/canon-memory-v1/E4-T3/scoper.md` — stall watchdog cross-reference source.

### ac_traceability

| # | Target | Test |
|---|---|---|
| 1 | docs/runbooks/RESUME.md exists + structure | `tests/test_agent_templates.py::test_resume_runbook_exists_and_covers_workflow` |
| 2 | release-orchestrator.md resume-aware wording | `tests/test_agent_templates.py::test_release_orchestrator_template_resume_aware` |
| 3 | Template test exists (done_signal) | same as #2 |
| 4 | Runbook content test exists | same as #1 |
| 5 | CHANGELOG + SYSTEM-WORKFLOW additive | QA gate flow-audit content check (manual review; no dedicated test) |
| 6 | Backward-compat on existing release-orchestrator template tests | existing 3 tests continue to pass: `test_release_orchestrator_template_has_merge_and_deploy_gates`, `test_release_orchestrator_template_checkpoint_contract`, `test_release_orchestrator_template_retrieval_telemetry` |
| 7 | Full suite green at 365 | pytest -q suite |
| 8 | Forbidden surfaces | QA gate diff allowlist check |

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E4-T4 ships docs/runbooks/RESUME.md (one-page operator runbook for canon resume) + an additive '## Resume check (E4-T4)' section in release-orchestrator.md wiring resume into the merge gate + 2 new template-assertion tests in tests/test_agent_templates.py (the done_signal test)."
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260423_e4t4_resume_runbook"
      task_id: "E4-T4"
      wave: 4
      branch: "wave/4/canon-memory-v1"
    story:
      title: "Resume runbook + release gate"
      acceptanceCriteria:
        - "docs/runbooks/RESUME.md exists with canon resume examples (8 required sections)."
        - "release-orchestrator.md gains '## Resume check (E4-T4)' section with required anchors (canon resume, docs/runbooks/RESUME.md, resume_target, 'before advancing the merge gate')."
        - "tests/test_agent_templates.py::test_release_orchestrator_template_resume_aware asserts the wording (done_signal)."
        - "tests/test_agent_templates.py::test_resume_runbook_exists_and_covers_workflow asserts runbook content."
        - "Existing 3 release-orchestrator template tests continue to pass (strict append-only)."
        - "Suite goes from 363 to 365 passed."
        - "CHANGELOG top-of-Unreleased + SYSTEM-WORKFLOW §3 additive bullets; no README edits."
        - "Zero edits to src/canon_systems/**/*.py, backend/**, infra/**, .cursor/rules/**, .cursor/plans/**."
    constraints:
      dependencies: ["E4-T1"]
      mustNotBreak:
        - "363-test baseline"
        - "existing release-orchestrator template tests"
        - "Wave-4 waiver"
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
      prior_work_references: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
