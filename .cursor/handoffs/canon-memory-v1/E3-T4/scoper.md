# E3-T4 Scoper Packet — Retrieval policy: graph-first in templates + rules

## SCOPE SUMMARY

E3-T4 codifies the graph-first retrieval policy from build plan §Wave 3 into the authoritative canon rule `memory-layer-defaults.mdc` and the three coder-facing agent templates (scoper, cursor-pilot, implementer). The retrieval order is fixed: **graph (axon) → state (checkpoints) → canonical (MemPalace + `.canon/memory/context-latest.md` + `canon ask`) → file reads**. Templates must cite the concrete `canon graph query` (and impact-where-appropriate) step as the first retrieval action before broad file reads for coding work. Additive-only to living specs. No backend changes.

## SCOPE PACKET

### Identifiers
- handoff_id: `handoff_20260422_e3t4_graph_first_policy`
- branch: `wave/3/canon-memory-v1` (tip 3e9093d)

### Story — acceptanceCriteria (12)
1. `src/canon_systems/templates/rules/memory-layer-defaults.mdc` gains a new `## Retrieval policy (required)` section (additive, appended; does not reflow existing §Before work / §During work / §Checkpoint contract sections).
2. That section names the four retrieval sources in order: graph → state → canonical → file. Each source is named with its concrete canon tool invocation: `canon graph query`, `canon checkpoint read`, `canon ask` / `.canon/memory/context-latest.md`, then raw file reads as the last resort.
3. Section explicitly forbids broad file reads (e.g., repo-wide greps, opening files not cited by graph/state/canonical) before the three RPC-based sources have been consulted for coding work.
4. Section documents the fail-open fallback: if `AXON_SERVICE_URL` / `AXON_SERVICE_TOKEN` are unset, or if `canon graph query` exits with code 2/3/4/5, agents fall back to state→canonical→file; no retrieval step is a hard blocker.
5. `src/canon_systems/templates/agents/scoper.md` — additive subsection under an existing checkpoint/retrieval hygiene area titled `## Graph-first retrieval (required)` that references `canon graph query --company-id <company_id> --repository-id <repository_id> --commit-sha <sha> --q <scope-question>` as the first retrieval step before repo exploration. Must cite `source_spans` as the evidence channel.
6. `src/canon_systems/templates/agents/cursor-pilot.md` — same `## Graph-first retrieval (required)` subsection, additionally referencing `canon graph impact --symbol <target>` for blast-radius checks before declaring the target surface in the cursor-pilot prompt.
7. `src/canon_systems/templates/agents/implementer.md` — same `## Graph-first retrieval (required)` subsection, instructing the implementer to run `canon graph query` (and `canon graph impact` when refactoring) BEFORE broad repo exploration, and to cite `source_spans` in the `HANDOFF_TO_QA` evidence channel where applicable.
8. `tests/test_agent_templates.py` gains ≥5 new assertions:
   - `test_memory_layer_defaults_retrieval_policy` — asserts the mdc contains `Retrieval policy (required)`, `graph → state → canonical → file`, `canon graph query`, `canon checkpoint read`, `canon ask`, and the fail-open clause mentioning `AXON_SERVICE_URL`.
   - `test_scoper_template_graph_first_retrieval` — asserts `Graph-first retrieval (required)`, `canon graph query`, and `source_spans` in scoper.md.
   - `test_cursor_pilot_template_graph_first_retrieval` — same in cursor-pilot.md plus `canon graph impact`.
   - `test_implementer_template_graph_first_retrieval` — same in implementer.md plus explicit "before broad repo exploration" clause.
   - `test_retrieval_policy_order_is_stable` — asserts the literal string `graph → state → canonical → file` appears exactly once in the mdc (order is a single canonical phrasing).
9. Existing agent-template tests continue to pass unchanged (no regressions in the 10+ existing assertions).
10. CHANGELOG additive: prepend E3-T4 bullet at TOP of `[Unreleased] ### Added`.
11. README additive: one-line note in the relevant agent/retrieval section linking graph-first to `canon graph query`; no table reflow.
12. `docs/SYSTEM-WORKFLOW.md` §6 additive bullet summarizing the 4-tier retrieval order.

### Forbidden surfaces
- backend/**, infra/**, src/canon_systems/cli.py, src/canon_systems/{checkpoint_cli,graph_indexer,flow_audit,qa_validate,memory_health,checkpoints}.py, .cursor/rules/**, .cursor/plans/**, tests outside test_agent_templates.py, template files other than the three above + memory-layer-defaults.mdc.

### Repository
- primaryLanguages: Markdown (policy), Python (tests)
- testFramework: pytest
- relevantFiles: src/canon_systems/templates/rules/memory-layer-defaults.mdc, src/canon_systems/templates/agents/{scoper,cursor-pilot,implementer}.md, tests/test_agent_templates.py, CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md

### Constraints
- dependencies: E3-T3 (canon graph query/impact), E2-T4 (template checkpoint sections exist and are load-bearing)
- mustNotBreak: existing agent-template test suite, canon qa-validate's token checks on template contents

### Prior work references
- peer:src/canon_systems/templates/rules/memory-layer-defaults.mdc (E2-T4 self-peer) — `## Checkpoint contract (required)` is the model for how to append a new required section.
- peer:src/canon_systems/templates/agents/scoper.md, cursor-pilot.md, implementer.md (E2-T4) — `## Checkpoint (read-before / write-after) contract` is the pattern for the new `## Graph-first retrieval (required)` subsection placement.
- peer:src/canon_systems/graph_indexer.py (E3-T3) — canonical CLI surface for `canon graph query`/`impact`.

### ac_traceability

| # | Target | Test |
|---|---|---|
| 1-4 | memory-layer-defaults.mdc | tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy, ::test_retrieval_policy_order_is_stable |
| 5 | scoper.md | tests/test_agent_templates.py::test_scoper_template_graph_first_retrieval |
| 6 | cursor-pilot.md | tests/test_agent_templates.py::test_cursor_pilot_template_graph_first_retrieval |
| 7 | implementer.md | tests/test_agent_templates.py::test_implementer_template_graph_first_retrieval |
| 8 | test file | pytest tests/test_agent_templates.py -q |
| 9 | no regressions | pytest -q (full suite) |
| 10 | CHANGELOG | grep |
| 11 | README | grep |
| 12 | SYSTEM-WORKFLOW | grep |

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: E3-T4 encodes graph-first retrieval policy in memory-layer-defaults.mdc + scoper/cursor-pilot/implementer agent templates. Additive sections only. 5+ new template-content tests in tests/test_agent_templates.py.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260422_e3t4_graph_first_policy"
    story:
      title: "Retrieval policy: graph-first in templates + rules"
      acceptanceCriteria:
        - "memory-layer-defaults.mdc gains ## Retrieval policy (required) section naming graph → state → canonical → file with fail-open fallback."
        - "scoper/cursor-pilot/implementer templates each gain ## Graph-first retrieval (required) subsection citing canon graph query."
        - "cursor-pilot.md additionally cites canon graph impact."
        - "tests/test_agent_templates.py has 5 new assertions covering the mdc + 3 templates + order-stability."
        - "No regressions to existing agent-template tests."
        - "Additive updates to CHANGELOG (top of Unreleased), README, SYSTEM-WORKFLOW §6."
        - "No edits to forbidden surfaces."
    constraints:
      dependencies: ["E3-T3", "E2-T4"]
      mustNotBreak: ["tests/test_agent_templates.py existing assertions"]
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
