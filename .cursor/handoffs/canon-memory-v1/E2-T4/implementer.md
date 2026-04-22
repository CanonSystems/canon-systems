# E2-T4 Implementer Packet

**Task:** Agent templates hydrate + checkpoint at phase boundaries
**Wave branch:** `wave/2/canon-memory-v1`
**Produced by:** implementer subagent (ID b8024769-f0e9-40a9-b880-8182ccd03cef)

---

```
HANDOFF_TO_QA
  task_id: E2-T4
  title: "Agent templates hydrate + checkpoint at phase boundaries"
  branch: wave/2/canon-memory-v1
  summary: >-
    Appended checkpoint read-before/write-after contract to five core agent templates,
    checkpoint propagation note to project-planner, required checkpoint block to
    memory-layer-defaults.mdc, seven additive template tests, and living-spec bullets
    in CHANGELOG/README/SYSTEM-WORKFLOW. No Python/src changes. pytest + smoke green;
    git diff matches E2-T4 allowlist only.

  files_changed:
    - src/canon_systems/templates/agents/scoper.md
    - src/canon_systems/templates/agents/cursor-pilot.md
    - src/canon_systems/templates/agents/implementer.md
    - src/canon_systems/templates/agents/qa-gate.md
    - src/canon_systems/templates/agents/release-orchestrator.md
    - src/canon_systems/templates/agents/project-planner.md
    - src/canon_systems/templates/rules/memory-layer-defaults.mdc
    - tests/test_agent_templates.py
    - CHANGELOG.md
    - README.md
    - docs/SYSTEM-WORKFLOW.md

  verification_commands:
    - "pytest -q  # 228 passed"
    - "SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh  # exit 0"
    - "git diff --name-only  # equals allowlist (11 paths)"

  notes:
    - "72 new assert lines in tests/test_agent_templates.py (≥15 required)."
    - "Incidental .canon/memory/*.log|.json edits were git-restored so git diff matches the E2-T4 allowlist."
END_HANDOFF_TO_QA
```
