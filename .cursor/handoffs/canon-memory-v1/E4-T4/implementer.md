# E4-T4 Implementer packet — Resume runbook + release gate

## Summary

- **Created** `docs/runbooks/RESUME.md` — one-page operator runbook for `canon resume` (8 sections + See also). Added a one-line shell example containing the substring `canon resume --plan-id` so `test_resume_runbook_exists_and_covers_workflow` matches the pilot’s assertion (multiline-only examples do not include that contiguous substring).
- **Appended** `## Resume check (E4-T4)` to `src/canon_systems/templates/agents/release-orchestrator.md` (strict append only; no existing lines changed).
- **Appended** `test_release_orchestrator_template_resume_aware` and `test_resume_runbook_exists_and_covers_workflow` to `tests/test_agent_templates.py`.
- **Prepended** E4-T4 bullet at top of `CHANGELOG.md` `## [Unreleased]` → `### Added`.
- **Appended** E4-T4 Wave-4 bullet to `docs/SYSTEM-WORKFLOW.md` §3 after E4-T3.

## Verification

- `pytest tests/test_agent_templates.py -q` → **27 passed**
- `pytest -q` → **365 passed** (363 + 2)

## Production code

- **Zero** changes under `src/canon_systems/**/*.py` (documentation + template markdown + tests only).

```yaml
HANDOFF_TO_QA:
  handoff_id: handoff_20260423_e4t4_resume_runbook
  task_id: E4-T4
  branch: wave/4/canon-memory-v1
  files_modified:
    - docs/runbooks/RESUME.md
    - src/canon_systems/templates/agents/release-orchestrator.md
    - tests/test_agent_templates.py
    - CHANGELOG.md
    - docs/SYSTEM-WORKFLOW.md
  acceptance_criteria:
    - id: AC1
      description: "Runbook file exists at docs/runbooks/RESUME.md and covers 8 required sections."
      status: MET
      evidence: "docs/runbooks/RESUME.md includes When to use, Basic invocation, Interpreting the output, Integration with the stall watchdog (E4-T3), Release-gate integration, Troubleshooting, See also, plus title/purpose."
      run_result: "test_resume_runbook_exists_and_covers_workflow passed; file present on disk."
      covering_tests:
        - tests/test_agent_templates.py::test_resume_runbook_exists_and_covers_workflow
    - id: AC2
      description: "release-orchestrator.md carries all 5 anchor substrings."
      status: MET
      evidence: "Appended section contains ## Resume check (E4-T4), canon resume, docs/runbooks/RESUME.md, resume_target, before advancing the merge gate."
      run_result: "test_release_orchestrator_template_resume_aware passed."
      covering_tests:
        - tests/test_agent_templates.py::test_release_orchestrator_template_resume_aware
    - id: AC3
      description: "test_release_orchestrator_template_resume_aware passes (done_signal)."
      status: MET
      evidence: "Template body read via importlib.resources; five substring assertions green."
      run_result: "pytest tests/test_agent_templates.py::test_release_orchestrator_template_resume_aware PASSED"
      covering_tests:
        - tests/test_agent_templates.py::test_release_orchestrator_template_resume_aware
    - id: AC4
      description: "test_resume_runbook_exists_and_covers_workflow passes."
      status: MET
      evidence: "Path resolution to repo root; runbook headings and workflow anchors asserted."
      run_result: "pytest tests/test_agent_templates.py::test_resume_runbook_exists_and_covers_workflow PASSED"
      covering_tests:
        - tests/test_agent_templates.py::test_resume_runbook_exists_and_covers_workflow
    - id: AC5
      description: "Focused pytest (tests/test_agent_templates.py) = 27 passed."
      status: MET
      evidence: "25 prior + 2 new tests; no existing tests modified."
      run_result: "27 passed in 0.02s"
      covering_tests:
        - tests/test_agent_templates.py
    - id: AC6
      description: "Full pytest suite = 365 passed (delta +2 from 363)."
      status: MET
      evidence: "Full suite green; +2 tests only from E4-T4."
      run_result: "365 passed in 4.29s"
      covering_tests:
        - tests/test_agent_templates.py::test_release_orchestrator_template_resume_aware
        - tests/test_agent_templates.py::test_resume_runbook_exists_and_covers_workflow
  suite_result:
    total: 365
    passed: 365
    skipped: 0
END_HANDOFF_TO_QA
```
