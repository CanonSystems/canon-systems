```
CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
This prompt must be executed by that subagent (default model:
`composer-2-fast`), not by the parent planner agent. You write code and
tests only; you do NOT commit, push, or touch any other `task_id`.
</ROLE>

<TASK>
E1-T3 — Release gate: require memory-health PASS for critical backends.
Wire `canon memory-health` into release-orchestrator merge gates as a hard,
machine-checked gate: (a) teach the release-orchestrator template that
memory-health evidence is required and name the producer/consumer commands;
(b) add an opt-in `--require-memory-health` flag to `canon flow-audit` that
verifies the per-task evidence artifact
`.cursor/handoffs/<handoff_id>/<task_id>/memory-health.json` exists, parses
as JSON, and carries `schema_version=="1"` + `overall_status=="ok"`;
(c) extend tests to cover the new template text and three new flow-audit
paths (ok / missing / unhealthy) plus a back-compat lock; (d) mirror the
change into the living spec (CHANGELOG + SYSTEM-WORKFLOW §5/§6).
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: release-orchestrator.md gains a new bullet under `## Required governance` → `3. Merge gates (all required)` naming memory-health, evidence path `.cursor/handoffs/<handoff_id>/<task_id>/memory-health.json`, producer `canon memory-health --output <path>`, verifier `canon flow-audit --require-memory-health`.
- AC2: `flow_audit.py` adds `--require-memory-health` (store_true, default False). When set and task not sampled out, verifies evidence exists, parses as JSON, is object, has `schema_version=="1"` and `overall_status=="ok"`. Violations append error and exit 1.
- AC3: Evidence path is exactly `.cursor/handoffs/<handoff_id>/<task_id>/memory-health.json`.
- AC4: Back-compat — flag defaults off; without it, behavior unchanged.
- AC5: Five diagnostic substrings as specified.
- AC6: Sampling skip path unchanged.
- AC7: qa_validate.py NOT modified.
- AC8: .cursor/rules/memory-platform-build-discipline.mdc NOT modified.
- AC9: test_agent_templates.py asserts the four required tokens in template.
- AC10: test_flow_audit_passes_with_memory_health_evidence_ok.
- AC11: test_flow_audit_fails_when_memory_health_evidence_missing (stdout contains "missing memory-health evidence").
- AC12: test_flow_audit_fails_when_memory_health_overall_status_not_ok (stdout contains "overall_status='unhealthy' (expected 'ok')").
- AC13: test_flow_audit_passes_without_flag_when_memory_health_missing (back-compat lock).
- AC14: CHANGELOG `- E1-T3: ...` bullet ABOVE existing `- E1-T2:` bullet.
- AC15: SYSTEM-WORKFLOW §5 append-only sub-bullet after line 68 (`- required CI checks PASS`).
- AC16: SYSTEM-WORKFLOW §6 append-only sub-bullet after `canon dor-log` line 122.
- AC17: README.md + §1 of SYSTEM-WORKFLOW untouched.
- AC18: No forbidden-surface diffs.
- AC19: pytest -q exits 0 (138 expected); `canon flow-audit --help` shows new flag.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- company_id: canon-systems
- repository_id: canon-systems @ wave/1/canon-memory-v1 (E1-T1 @ 0d71319; E1-T2 just PASSED qa-gate, committing alongside this work)
- handoff_id: canon-memory-v1
- task_id: E1-T3
- parallel_task_status:
  - E1-T1 frozen (memory-health CLI)
  - E1-T2 frozen-for-this-work (mempalace fallback); shared-surface merges handled at commit
- prior_work_references:
  - `.cursor/handoffs/canon-memory-v1/E1-T1/*` — memory-health JSON schema (schema_version, overall_status, backends[], generated_at)
  - `.cursor/handoffs/canon-memory-v1/E1-T2/scoper.md` — shared-surface discipline precedent
  - `docs/MEMORY-PLATFORM-BACKLOG.md` row E1-T3
  - `.cursor/rules/memory-platform-build-discipline.mdc` §6 line 99
  - `docs/SYSTEM-WORKFLOW.md` §5 lines 60-68; §6 lines 114-122; §1 OUT OF SCOPE
  - `src/canon_systems/flow_audit.py` existing argparse + `_sample_selected` + `errors: list[str]` pattern
  - `src/canon_systems/templates/agents/release-orchestrator.md` `## Required governance` → `3. Merge gates`
  - `tests/test_flow_audit.py` `_write_task_artifacts` helper + `CANON_SYSTEMS_REPO_ROOT` monkeypatch pattern
</CONTEXT>

<REPOSITORY>
- primaryLanguages: Python (stdlib-only; 3.11+)
- testFramework: pytest
- relevantFiles:
  - src/canon_systems/flow_audit.py
  - src/canon_systems/templates/agents/release-orchestrator.md
  - tests/test_flow_audit.py
  - tests/test_agent_templates.py
  - CHANGELOG.md
  - docs/SYSTEM-WORKFLOW.md
- mustNotBreak (DO NOT EDIT):
  - src/canon_systems/memory_health.py (E1-T1 frozen)
  - src/canon_systems/memory_queue.py (E1-T2 frozen)
  - src/canon_systems/context_preload.py (E1-T2 frozen)
  - src/canon_systems/ask_hybrid.py (E1-T2 frozen)
  - src/canon_systems/qa_validate.py (AC7)
  - src/canon_systems/cli.py (already registers both commands)
  - tests/test_mempalace_fallback.py (E1-T2 frozen)
  - tests/test_memory_health.py (E1-T1 frozen)
  - .cursor/rules/memory-platform-build-discipline.mdc (AC8)
  - .cursor/plans/**, frozen Wave-0 docs
  - README.md (E1-T2 owns this wave)
  - docs/SYSTEM-WORKFLOW.md §1 (E1-T2 owns)
  - Any agent template except release-orchestrator.md
  - backend/**, infra/**, canon-systems-v2/**
  - pyproject.toml, pytest.ini, requirements-dev.txt, .github/workflows/**
  - .cursor/handoffs/canon-memory-v1/E0-*/**
- No new helper modules, no new runtime deps, no live HTTP, no git ops.
</REPOSITORY>

<REASONING>
Swimlanes (file-disjoint, parallel-reviewable):
1. ws1-code: flow_audit.py inline helper `_collect_memory_health_errors(base) -> list[str]` + arg wiring.
2. ws2-template: release-orchestrator.md one new bullet.
3. ws3-tests: 4 new flow-audit cases + extended template-token asserts.
4. ws4-living-spec: CHANGELOG + SYSTEM-WORKFLOW §5/§6 additive edits.

Helper logic:
- Path = base / "memory-health.json"; emit `missing memory-health evidence: <path>` when absent.
- Parse JSON; on JSONDecodeError → `invalid JSON in memory-health evidence: <path>`.
- If not dict → `memory-health evidence payload must be object: <path>`.
- If schema_version != "1" → `memory-health evidence schema_version mismatch (got <v>, expected '1'): <path>`.
- If overall_status != "ok" → `memory-health evidence overall_status='<s>' (expected 'ok'): <path>`.
- Wire-in AFTER existing `required` loop + `rejection_packets` block, BEFORE `if args.plan_file:`. Sampling `_sample_selected` short-circuits above, so sampled-out tasks naturally skip.

Risks:
- Shared CHANGELOG ordering with E1-T2 — resolved: E1-T3 bullet inserted above E1-T2 bullet.
- SYSTEM-WORKFLOW §1 is E1-T2 territory — do not touch.
- stdlib-only — json + pathlib already imported in flow_audit.py.
</REASONING>

<PARALLELIZATION_PLAN>
workstreams:
  - id: ws1-code
    targets: [src/canon_systems/flow_audit.py]
    tests: [tests/test_flow_audit.py::test_flow_audit_passes_with_memory_health_evidence_ok,
            tests/test_flow_audit.py::test_flow_audit_fails_when_memory_health_evidence_missing,
            tests/test_flow_audit.py::test_flow_audit_fails_when_memory_health_overall_status_not_ok,
            tests/test_flow_audit.py::test_flow_audit_passes_without_flag_when_memory_health_missing]
    can_run_parallel: true
  - id: ws2-template
    targets: [src/canon_systems/templates/agents/release-orchestrator.md]
    tests: [tests/test_agent_templates.py::test_release_orchestrator_template_has_merge_and_deploy_gates (extended)]
    can_run_parallel: true
  - id: ws3-tests
    targets: [tests/test_flow_audit.py, tests/test_agent_templates.py]
    depends_on: [ws1-code, ws2-template]
  - id: ws4-living-spec
    targets: [CHANGELOG.md, docs/SYSTEM-WORKFLOW.md]
    depends_on: [ws1-code, ws2-template]
execution_waves:
  - wave 1: [ws1-code, ws2-template]
  - wave 2: [ws3-tests, ws4-living-spec]
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
1) flow_audit.py: add argparse flag, add module-level helper `_collect_memory_health_errors(base: Path) -> list[str]`, wire in `if args.require_memory_health: errors.extend(_collect_memory_health_errors(base))` after required loop, before plan_file check.

2) release-orchestrator.md: inside Merge gates, append ONE bullet after the existing `canon flow-audit ... --sample-rate 0.2` line containing all four tokens: `memory-health`, `.cursor/handoffs/<handoff_id>/<task_id>/memory-health.json`, `--require-memory-health`, `canon memory-health --output`.

3) test_agent_templates.py: extend `test_release_orchestrator_template_has_merge_and_deploy_gates` with 4 new assertions.

4) test_flow_audit.py: add helper `_write_memory_health_evidence(root, *, handoff_id, task_id, overall_status="ok", schema_version="1")`, add 4 new tests (names above) using `CANON_SYSTEMS_REPO_ROOT` monkeypatch + capsys.

5) CHANGELOG.md: insert `- E1-T3: \`canon flow-audit --require-memory-health\` release-gate flag that verifies per-task .cursor/handoffs/<handoff_id>/<task_id>/memory-health.json evidence (schema_version='1', overall_status='ok'); release-orchestrator template now names memory-health as a required merge gate.` ABOVE existing `- E1-T2:` bullet under `[Unreleased] ### Added`.

6) docs/SYSTEM-WORKFLOW.md §5: append ONE sub-bullet after line 68 `- required CI checks PASS` documenting `canon flow-audit --require-memory-health` enforcement.
   docs/SYSTEM-WORKFLOW.md §6: append ONE sub-bullet after `canon dor-log` (line 122) with producer/enforcer commands.

No other edits; no new modules, no config changes, no forbidden-surface diffs.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
Emit HANDOFF_TO_QA block with per-AC evidence mapping. Do NOT commit, push, or touch other task_ids.

Failure modes requiring STOP and REPORT:
- Forbidden-surface touch
- pytest -q fails or regresses
- AC lacks implementation OR test
- Non-additive CHANGELOG or SYSTEM-WORKFLOW edit
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
```
