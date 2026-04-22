# E3-T4 QA Gate Packet — Retrieval policy: graph-first in templates + rules

## Verification summary

- Focused suite: `pytest tests/test_agent_templates.py -q` → `19 passed in 0.01s`
- Full suite:    `pytest -q` → `298 passed in 3.87s`
- Modified files (exactly the 8 allowlisted, plus tolerated auto-churn):
  - `CHANGELOG.md`
  - `README.md`
  - `docs/SYSTEM-WORKFLOW.md`
  - `src/canon_systems/templates/rules/memory-layer-defaults.mdc`
  - `src/canon_systems/templates/agents/scoper.md`
  - `src/canon_systems/templates/agents/cursor-pilot.md`
  - `src/canon_systems/templates/agents/implementer.md`
  - `tests/test_agent_templates.py`
  - (out-of-scope churn ignored: `.canon/memory/capture-failures.log`, `.canon/memory/capture-latest.json`)

```
GATE_RESULTS
  handoff_id: "handoff_20260422_e3t4_graph_first_policy"
  task_id: "E3-T4"
  overall_verdict: PASS
  verdict: PASS
  regression_checked: true
  iterations: 0
  suite_result: "focused: 19 passed in 0.01s; full: 298 passed in 3.87s"
  acceptance_criteria:
    - id: AC-1
      summary: "memory-layer-defaults.mdc gains additive `## Retrieval policy (required)` section appended after `## Checkpoint contract (required)`; existing sections are not reflowed."
      status: MET
      evidence: "Section header present at line 207 of src/canon_systems/templates/rules/memory-layer-defaults.mdc, appended after the existing Checkpoint contract block; test_memory_layer_defaults_retrieval_policy asserts the header substring and test_memory_layer_defaults_checkpoint_contract still passes (no reflow)."
      run_result: "pytest tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy -q PASSED"
      covering_tests:
        - tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy
        - tests/test_agent_templates.py::test_memory_layer_defaults_checkpoint_contract
    - id: AC-2
      summary: "Section names the four retrieval sources in order (graph → state → canonical → file) with concrete canon tool invocations: canon graph query, canon checkpoint read, canon ask, then raw file reads as last resort."
      status: MET
      evidence: "Section body lists graph/state/canonical/file as steps 1-4 and references `canon graph query`, `canon graph impact`, `canon checkpoint read`, `canon ask`, and `.canon/memory/context-latest.md`. test_memory_layer_defaults_retrieval_policy asserts each of the canon tool substrings; test_retrieval_policy_order_is_stable asserts the canonical order phrase appears exactly once."
      run_result: "pytest tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy tests/test_agent_templates.py::test_retrieval_policy_order_is_stable -q PASSED"
      covering_tests:
        - tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy
        - tests/test_agent_templates.py::test_retrieval_policy_order_is_stable
    - id: AC-3
      summary: "Section forbids broad file reads (speculative repo-wide greps, opening files not cited by graph/state/canonical) before the three RPC-based sources have been consulted for coding work."
      status: MET
      evidence: "Step 4 of the section reads `File reads — last resort. Only open files that were cited by steps 1-3, or whose existence was explicitly required by the user prompt. Broad repo-wide greps or speculative `ls -R` are discouraged when steps 1-3 return usable evidence.` test_memory_layer_defaults_retrieval_policy anchors the section via the `## Retrieval policy (required)` header assertion."
      run_result: "pytest tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy -q PASSED"
      covering_tests:
        - tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy
    - id: AC-4
      summary: "Section documents the fail-open fallback: if AXON_SERVICE_URL / AXON_SERVICE_TOKEN are unset, or if canon graph query exits with code 2/3/4/5, agents fall back to state → canonical → file; no retrieval step is a hard blocker."
      status: MET
      evidence: "Subsection `### Fail-open fallback` names `AXON_SERVICE_URL` / `AXON_SERVICE_TOKEN`, cites exit codes 2/3/4/5, and records fallback to `state → canonical → file`. test_memory_layer_defaults_retrieval_policy asserts the `AXON_SERVICE_URL` and `Fail-open fallback` substrings."
      run_result: "pytest tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy -q PASSED"
      covering_tests:
        - tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy
    - id: AC-5
      summary: "scoper.md gains `## Graph-first retrieval (required)` subsection citing `canon graph query --company-id ... --repository-id ... --commit-sha ... --q ...` as the first retrieval step and `source_spans` as the evidence channel."
      status: MET
      evidence: "New subsection inserted before `## Checkpoint` in src/canon_systems/templates/agents/scoper.md; test_scoper_template_graph_first_retrieval asserts the header, `canon graph query`, and `source_spans` substrings; test_scoper_template_checkpoint_contract remains green (no reflow)."
      run_result: "pytest tests/test_agent_templates.py::test_scoper_template_graph_first_retrieval tests/test_agent_templates.py::test_scoper_template_checkpoint_contract -q PASSED"
      covering_tests:
        - tests/test_agent_templates.py::test_scoper_template_graph_first_retrieval
        - tests/test_agent_templates.py::test_scoper_template_checkpoint_contract
    - id: AC-6
      summary: "cursor-pilot.md gains the same `## Graph-first retrieval (required)` subsection, additionally referencing `canon graph impact --symbol <target>` for blast-radius checks before declaring the target surface in the CURSOR_PILOT_PROMPT."
      status: MET
      evidence: "New subsection inserted before `## Checkpoint` in src/canon_systems/templates/agents/cursor-pilot.md; test_cursor_pilot_template_graph_first_retrieval asserts the header, `canon graph query`, and `canon graph impact` substrings; test_cursor_pilot_template_checkpoint_contract remains green."
      run_result: "pytest tests/test_agent_templates.py::test_cursor_pilot_template_graph_first_retrieval tests/test_agent_templates.py::test_cursor_pilot_template_checkpoint_contract -q PASSED"
      covering_tests:
        - tests/test_agent_templates.py::test_cursor_pilot_template_graph_first_retrieval
        - tests/test_agent_templates.py::test_cursor_pilot_template_checkpoint_contract
    - id: AC-7
      summary: "implementer.md gains the same `## Graph-first retrieval (required)` subsection, instructing the implementer to run `canon graph query` (and `canon graph impact` when refactoring) BEFORE broad repo exploration, and to cite `source_spans` in HANDOFF_TO_QA evidence where applicable."
      status: MET
      evidence: "New subsection inserted before `## Checkpoint` in src/canon_systems/templates/agents/implementer.md; test_implementer_template_graph_first_retrieval asserts the header, `canon graph query`, and the lowercase `broad repo exploration` clause; test_implementer_template_checkpoint_contract remains green."
      run_result: "pytest tests/test_agent_templates.py::test_implementer_template_graph_first_retrieval tests/test_agent_templates.py::test_implementer_template_checkpoint_contract -q PASSED"
      covering_tests:
        - tests/test_agent_templates.py::test_implementer_template_graph_first_retrieval
        - tests/test_agent_templates.py::test_implementer_template_checkpoint_contract
    - id: AC-8
      summary: "tests/test_agent_templates.py gains five new assertions: test_memory_layer_defaults_retrieval_policy, test_retrieval_policy_order_is_stable, test_scoper_template_graph_first_retrieval, test_cursor_pilot_template_graph_first_retrieval, test_implementer_template_graph_first_retrieval."
      status: MET
      evidence: "All five new test functions present in tests/test_agent_templates.py (lines 265, 278, 285, 292, 301) and all five pass in the focused suite run (19 passed total — 14 pre-existing + 5 new)."
      run_result: "pytest tests/test_agent_templates.py -q → 19 passed in 0.01s"
      covering_tests:
        - tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy
        - tests/test_agent_templates.py::test_retrieval_policy_order_is_stable
        - tests/test_agent_templates.py::test_scoper_template_graph_first_retrieval
        - tests/test_agent_templates.py::test_cursor_pilot_template_graph_first_retrieval
        - tests/test_agent_templates.py::test_implementer_template_graph_first_retrieval
    - id: AC-9
      summary: "Existing agent-template tests (10+ pre-existing assertions) continue to pass unchanged; no regressions anywhere in the repo suite."
      status: MET
      evidence: "Focused suite shows 19 passed (14 pre-existing + 5 new — pre-existing count unchanged). Full repo sweep `pytest -q` shows 298 passed with zero failures / zero errors, confirming no regressions elsewhere. AC-9 order-stability is additionally covered by test_retrieval_policy_order_is_stable which pins the canonical phrase `graph → state → canonical → file` to exactly one occurrence in the mdc."
      run_result: "pytest -q → 298 passed in 3.87s; pytest tests/test_agent_templates.py -q → 19 passed in 0.01s"
      covering_tests:
        - tests/test_agent_templates.py::test_retrieval_policy_order_is_stable
        - tests/test_agent_templates.py::test_memory_layer_defaults_checkpoint_contract
        - tests/test_agent_templates.py::test_scoper_template_checkpoint_contract
        - tests/test_agent_templates.py::test_cursor_pilot_template_checkpoint_contract
        - tests/test_agent_templates.py::test_implementer_template_checkpoint_contract
    - id: AC-10
      summary: "CHANGELOG.md additive: E3-T4 bullet prepended at TOP of [Unreleased] ### Added (not appended)."
      status: MET
      evidence: "CHANGELOG.md shows `- **E3-T4** Retrieval policy codified as graph-first ...` as the first bullet immediately under `## [Unreleased]` / `### Added`, directly above the pre-existing E3-T3 bullet (prepended, not appended)."
      run_result: "grep -n 'E3-T4' CHANGELOG.md → first bullet under [Unreleased] Added"
      covering_tests:
        - CHANGELOG.md
    - id: AC-11
      summary: "README.md additive: one-line note in the relevant agent/retrieval section linking graph-first to `canon graph query`; no table reflow."
      status: MET
      evidence: "README.md line 18 contains new bullet `- Graph-first retrieval is the default for all coder-facing agent templates (scoper/cursor-pilot/implementer). See \\`## Retrieval policy (required)\\` in \\`src/canon_systems/templates/rules/memory-layer-defaults.mdc\\`.` Pre-existing `canon graph query` / `canon graph impact` command-table rows (lines 222-223) are unchanged — no table reflow."
      run_result: "grep -n 'Graph-first retrieval is the default' README.md → line 18"
      covering_tests:
        - README.md
    - id: AC-12
      summary: "docs/SYSTEM-WORKFLOW.md §6 additive bullet summarizing the 4-tier retrieval order (graph → state → canonical → file) with canon tool invocations and fail-open fallback."
      status: MET
      evidence: "docs/SYSTEM-WORKFLOW.md line 117 contains new bullet `- **Retrieval policy (graph-first)**: Coder-facing templates (scoper/cursor-pilot/implementer) consult memory sources in a fixed order — \\`graph → state → canonical → file\\`. Graph reads via \\`canon graph query\\`/\\`canon graph impact\\`, state via \\`canon checkpoint read\\`, canonical via \\`.canon/memory/context-latest.md\\` + \\`canon ask\\`. Fail-open when axon is unset or returns 2/3/4/5; degradation is recorded in the HANDOFF_TO_QA \\`notes:\\` field.` under `## 6) Validation commands` — additive, does not reflow pre-existing §6 graph-retrieval plane bullets (lines 123-125)."
      run_result: "grep -n 'Retrieval policy (graph-first)' docs/SYSTEM-WORKFLOW.md → line 117"
      covering_tests:
        - docs/SYSTEM-WORKFLOW.md
  remaining_gaps: []
  notes: |
    All 12 acceptance criteria verified. Focused suite 19/19 passing (14 pre-existing + 5 new template-content assertions), full repo suite 298/298 passing, zero iterations required. Modified-files set matches the 8 allowlisted paths exactly (CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md, src/canon_systems/templates/rules/memory-layer-defaults.mdc, src/canon_systems/templates/agents/{scoper,cursor-pilot,implementer}.md, tests/test_agent_templates.py); tolerated out-of-scope churn (.canon/memory/capture-failures.log, .canon/memory/capture-latest.json) is auto-generated and does not constitute a forbidden-surface violation. The canonical phrase `graph → state → canonical → file` appears exactly once in src/canon_systems/templates/rules/memory-layer-defaults.mdc (AC-9 order-stability, covered by test_retrieval_policy_order_is_stable).
END_GATE_RESULTS
```
