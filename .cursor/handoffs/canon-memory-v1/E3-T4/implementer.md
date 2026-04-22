# E3-T4 implementer handoff

```yaml
HANDOFF_TO_QA:
  handoff_id: handoff_20260422_e3t4_graph_first_policy
  branch: wave/3/canon-memory-v1
  files_modified:
    - src/canon_systems/templates/rules/memory-layer-defaults.mdc
    - src/canon_systems/templates/agents/scoper.md
    - src/canon_systems/templates/agents/cursor-pilot.md
    - src/canon_systems/templates/agents/implementer.md
    - tests/test_agent_templates.py
    - CHANGELOG.md
    - README.md
    - docs/SYSTEM-WORKFLOW.md
  acceptance_criteria:
    - id: AC1
      description: "memory-layer-defaults.mdc ends with ## Retrieval policy (required) after ## Checkpoint contract (required), with graph/state/canonical/file steps and Fail-open fallback."
      status: MET
      evidence: "Appended block in src/canon_systems/templates/rules/memory-layer-defaults.mdc; closing line avoids duplicating the canonical arrow phrase so it appears once."
      run_result: "PASS (see suite_result)"
      covering_tests:
        - tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_policy
        - tests/test_agent_templates.py::test_retrieval_policy_order_is_stable
        - tests/test_agent_templates.py::test_memory_layer_defaults_checkpoint_contract
    - id: AC2
      description: "Exact substring `graph → state → canonical → file` appears exactly once in memory-layer-defaults.mdc (normative order)."
      status: MET
      evidence: "Single bold line **graph → state → canonical → file**; no duplicate backticked repeat at section end."
      run_result: "PASS (see suite_result)"
      covering_tests:
        - tests/test_agent_templates.py::test_retrieval_policy_order_is_stable
    - id: AC3
      description: "scoper.md contains ## Graph-first retrieval (required) adjacent to the Checkpoint contract; cites canon graph query, source_spans, fail-open, and memory-layer cross-ref."
      status: MET
      evidence: "New section before ## Checkpoint in src/canon_systems/templates/agents/scoper.md"
      run_result: "PASS (see suite_result)"
      covering_tests:
        - tests/test_agent_templates.py::test_scoper_template_graph_first_retrieval
        - tests/test_agent_templates.py::test_scoper_template_checkpoint_contract
    - id: AC4
      description: "cursor-pilot.md contains ## Graph-first retrieval (required) with canon graph query and canon graph impact; cites CURSOR_PILOT_PROMPT and memory-layer cross-ref."
      status: MET
      evidence: "New section before ## Checkpoint in src/canon_systems/templates/agents/cursor-pilot.md"
      run_result: "PASS (see suite_result)"
      covering_tests:
        - tests/test_agent_templates.py::test_cursor_pilot_template_graph_first_retrieval
        - tests/test_agent_templates.py::test_cursor_pilot_template_checkpoint_contract
    - id: AC5
      description: "implementer.md contains ## Graph-first retrieval (required) with graph query/impact for refactors, HANDOFF_TO_QA evidence guidance, fail-open, and memory-layer cross-ref."
      status: MET
      evidence: "New section before ## Checkpoint in src/canon_systems/templates/agents/implementer.md"
      run_result: "PASS (see suite_result)"
      covering_tests:
        - tests/test_agent_templates.py::test_implementer_template_graph_first_retrieval
        - tests/test_agent_templates.py::test_implementer_template_checkpoint_contract
    - id: AC6
      description: "tests/test_agent_templates.py adds exactly the five specified test functions; importlib.resources usage unchanged; no edits to pre-existing test bodies."
      status: MET
      evidence: "Five new defs appended at end of tests/test_agent_templates.py matching cursor-pilot spec."
      run_result: "PASS (see suite_result)"
      covering_tests:
        - tests/test_agent_templates.py
    - id: AC7
      description: "CHANGELOG.md [Unreleased] ### Added prepends the E3-T4 bullet at the top of Added (not appended)."
      status: MET
      evidence: "First bullet under ### Added documents E3-T4."
      run_result: "PASS (manual review)"
      covering_tests:
        - CHANGELOG.md
    - id: AC8
      description: "README.md gains one additive line on graph-first retrieval for coder-facing templates; no table reflow."
      status: MET
      evidence: "New bullet under What ships, after Subagent system block."
      run_result: "PASS (manual review)"
      covering_tests:
        - README.md
    - id: AC9
      description: "docs/SYSTEM-WORKFLOW.md §6 includes the retrieval policy (graph-first) bullet with fail-open and commands."
      status: MET
      evidence: "New first bullet under ## 6) Validation commands."
      run_result: "PASS (manual review)"
      covering_tests:
        - docs/SYSTEM-WORKFLOW.md
    - id: AC10
      description: "Focused pytest tests/test_agent_templates.py -q is green; count includes all prior tests plus five new."
      status: MET
      evidence: "19 passed in 0.04s"
      run_result: "PASS"
      covering_tests:
        - tests/test_agent_templates.py
    - id: AC11
      description: "Full repo pytest -q is green; no regressions."
      status: MET
      evidence: "298 passed in 4.19s"
      run_result: "PASS"
      covering_tests:
        - tests/
    - id: AC12
      description: "Edits limited to the eight allowlisted files; forbidden surfaces untouched."
      status: MET
      evidence: "No backend/infra/cli edits; .cursor/rules and .canon/memory not modified for this task."
      run_result: "PASS (scope check)"
      covering_tests:
        - tests/test_agent_templates.py
  suite_result:
    focused: "19 passed in 0.04s  (tests/test_agent_templates.py -q)"
    full: "298 passed in 4.19s  (pytest -q at repo root)"
  notes: "mdc fail-open lists AXON_SERVICE_URL/AXON_SERVICE_TOKEN; closing sentence reworded from pilot appendix to keep exactly one `graph → state → canonical → file` substring (AC2/test_retrieval_policy_order_is_stable)."
END_HANDOFF_TO_QA
```
