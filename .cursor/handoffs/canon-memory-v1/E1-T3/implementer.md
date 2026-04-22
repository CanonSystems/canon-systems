```
HANDOFF_TO_QA
  task_id: E1-T3
  handoff_id: canon-memory-v1
  branch: wave/1/canon-memory-v1

  summary: "E1-T3 adds opt-in --require-memory-health flag to canon flow-audit that verifies per-task .cursor/handoffs/<handoff_id>/<task_id>/memory-health.json evidence (schema_version='1', overall_status='ok'), teaches the release-orchestrator template to name memory-health as a required merge gate, and mirrors the change into CHANGELOG + SYSTEM-WORKFLOW §5/§6. 7-file diff after parent-approved cli.py plumb amendment for AC19."

  scope_amendments:
    - "cli.py plumb (2 edits) for AC19: fa.add_argument('--require-memory-health', ...) + forward block. Parent-approved via rule §5 gate-driven iteration (cursor-pilot's cli.py ban was an oversight given AC19 literal requirement)."

  verification_commands_ran:
    - "pytest -q" → 138 passed
    - "PYTHONPATH=src python3 -c 'from canon_systems.flow_audit import _collect_memory_health_errors; print(\"ok\")'" → ok
    - "python3 main(['flow-audit','--help']) via canon_systems.cli with redirect_stdout" → contains '--require-memory-health'
    - "git diff --name-only" → 7 files

  diff_files (7):
    - CHANGELOG.md
    - docs/SYSTEM-WORKFLOW.md
    - src/canon_systems/cli.py
    - src/canon_systems/flow_audit.py
    - src/canon_systems/templates/agents/release-orchestrator.md
    - tests/test_agent_templates.py
    - tests/test_flow_audit.py

  ac_evidence:
    AC1: "src/canon_systems/templates/agents/release-orchestrator.md" — new bullet under Merge gates with memory-health, evidence path, producer (canon memory-health --output), verifier (canon flow-audit --require-memory-health).
    AC2: "src/canon_systems/flow_audit.py" — `parser.add_argument('--require-memory-health', action='store_true')`; when set (and not sample-skipped), `_collect_memory_health_errors(base)` appends errors; exit 1 on any violation.
    AC3: "src/canon_systems/flow_audit.py" — evidence file `base / 'memory-health.json'` where base = root/.cursor/handoffs/<handoff_id>/<task_id>.
    AC4: Default flag off; test_flow_audit_passes_without_flag_when_memory_health_missing passes without flag and without evidence.
    AC5: _collect_memory_health_errors emits: missing, invalid JSON, not object, schema_version mismatch (with got repr), overall_status mismatch (with quoted value).
    AC6: Sampling unchanged; early return still applies; memory-health sits below skip path.
    AC7: "qa_validate.py" not in git diff.
    AC8: ".cursor/rules/memory-platform-build-discipline.mdc" not modified.
    AC9: "tests/test_agent_templates.py" — test asserts four tokens: memory-health, evidence path, --require-memory-health, canon memory-health --output.
    AC10: "tests/test_flow_audit.py::test_flow_audit_passes_with_memory_health_evidence_ok"
    AC11: "tests/test_flow_audit.py::test_flow_audit_fails_when_memory_health_evidence_missing" (stdout contains 'missing memory-health evidence')
    AC12: "tests/test_flow_audit.py::test_flow_audit_fails_when_memory_health_overall_status_not_ok" (stdout contains "overall_status='unhealthy' (expected 'ok')")
    AC13: "tests/test_flow_audit.py::test_flow_audit_passes_without_flag_when_memory_health_missing"
    AC14: "CHANGELOG.md" — E1-T3 Added bullet immediately above E1-T2
    AC15: "docs/SYSTEM-WORKFLOW.md" §5 — sub-bullet after "- required CI checks PASS"
    AC16: "docs/SYSTEM-WORKFLOW.md" §6 — sub-bullet after canon dor-log line
    AC17: "README.md" and SYSTEM-WORKFLOW §1 not in git diff
    AC18: Only the seven allowed paths changed; no forbidden-surface touches (memory_health.py, memory_queue.py, context_preload.py, ask_hybrid.py, qa_validate.py, tests/test_mempalace_fallback.py, tests/test_memory_health.py, rules/**, plans/**, README.md, §1, backend/**, infra/**, pyproject.toml, etc all untouched).
    AC19: FULL — cli.py plumb exposes --require-memory-health via subparser; main(['flow-audit','--help']) output contains the flag; pytest -q 138 passed.

  commit: "Do not commit — parent runs qa-gate first."
END_HANDOFF_TO_QA
```
