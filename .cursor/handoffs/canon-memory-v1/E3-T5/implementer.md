# E3-T5 implementer handoff

```
HANDOFF_TO_QA
  handoff_id: handoff_20260422_e3t5_retrieval_telemetry
  branch: wave/3/canon-memory-v1
  files_modified:
    - src/canon_systems/retrieval_telemetry.py
    - src/canon_systems/report_cli.py
    - src/canon_systems/cli.py
    - src/canon_systems/templates/rules/memory-layer-defaults.mdc
    - src/canon_systems/templates/agents/scoper.md
    - src/canon_systems/templates/agents/cursor-pilot.md
    - src/canon_systems/templates/agents/implementer.md
    - src/canon_systems/templates/agents/qa-gate.md
    - src/canon_systems/templates/agents/release-orchestrator.md
    - tests/test_retrieval_telemetry.py
    - tests/test_agent_templates.py
    - CHANGELOG.md
    - README.md
    - docs/SYSTEM-WORKFLOW.md
  acceptance_criteria:
    - id: AC1
      criterion: "retrieval_telemetry.py exports RETRIEVAL_SOURCES, SourceCounts, RetrievalBreakdown, sum_breakdown, build_retrieval_breakdown_event with fixed 4-bucket order"
      status: MET
      evidence: "New module implements spec dataclasses, RETRIEVAL_SOURCES tuple, and CanonicalEvent construction"
      run_result: "pytest tests/test_retrieval_telemetry.py -q: 15 passed"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_source_counts_non_negative
        - tests/test_retrieval_telemetry.py::test_retrieval_breakdown_defaults_zero
        - tests/test_retrieval_telemetry.py::test_build_event_canonical_shape
        - tests/test_retrieval_telemetry.py::test_build_event_payload_sources_keys
        - tests/test_retrieval_telemetry.py::test_build_event_payload_totals_sum
        - tests/test_retrieval_telemetry.py::test_sum_breakdown_zero_for_default
        - tests/test_retrieval_telemetry.py::test_sum_breakdown_sums_all_sources
    - id: AC2
      criterion: "Emitter reuses CanonicalEvent from canon_backend_shared.events; no local shadow envelope"
      status: MET
      evidence: "Single import; test_build_event_canonical_shape and roundtrip use CanonicalEvent"
      run_result: "pytest tests/test_retrieval_telemetry.py -q: 15 passed"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_build_event_canonical_shape
        - tests/test_retrieval_telemetry.py::test_event_roundtrip_via_to_dict_from_dict
    - id: AC3
      criterion: "report_cli.run: NDJSON read, filter retrieval_breakdown, aggregate by --by, plan/task filters, JSON stdout, exit 0/2/3/4"
      status: MET
      evidence: "report_cli.py matches cursor-pilot skeleton; tests cover success and error exits"
      run_result: "pytest tests/test_retrieval_telemetry.py -q: 15 passed"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_source
        - tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_phase
        - tests/test_retrieval_telemetry.py::test_report_cli_filters_by_plan_id
        - tests/test_retrieval_telemetry.py::test_report_cli_missing_file_exit_3
        - tests/test_retrieval_telemetry.py::test_report_cli_malformed_line_exit_4
        - tests/test_retrieval_telemetry.py::test_report_cli_missing_events_flag_exit_2
    - id: AC4
      criterion: "cli.py adds report subparser with REMAINDER and dispatches to run_report_cli"
      status: MET
      evidence: "Import, report_parser, and args.command==report block added adjacent to graph"
      run_result: "pytest tests/test_retrieval_telemetry.py::test_cli_graph_and_report_help: passed"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_cli_graph_and_report_help
    - id: AC5
      criterion: "canon report --help exits 0; missing file exits 3; malformed NDJSON exits 4; no --events exits 2"
      status: MET
      evidence: "covered by run_report and CLI help test; main(report,--help) raises SystemExit(0) per argparse"
      run_result: "pytest tests/test_retrieval_telemetry.py -q: 15 passed; python3 -m canon_systems.cli report --help exited 0 in smoke"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_cli_graph_and_report_help
        - tests/test_retrieval_telemetry.py::test_report_cli_missing_file_exit_3
        - tests/test_retrieval_telemetry.py::test_report_cli_malformed_line_exit_4
        - tests/test_retrieval_telemetry.py::test_report_cli_missing_events_flag_exit_2
    - id: AC6
      criterion: "tests/test_retrieval_telemetry.py: ≥14 tests for emitter, sum, roundtrip, report aggregation, exit codes, CLI help regression"
      status: MET
      evidence: "15 tests in file"
      run_result: "pytest tests/test_retrieval_telemetry.py -q: 15 passed"
      covering_tests:
        - tests/test_retrieval_telemetry.py
    - id: AC7
      criterion: "tests/test_agent_templates.py: 6 new template/mdc assertion tests"
      status: MET
      evidence: "test_memory_layer_defaults_retrieval_telemetry and five agent template tests"
      run_result: "pytest tests/test_agent_templates.py -q: 25 passed"
      covering_tests:
        - tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_telemetry
        - tests/test_agent_templates.py::test_scoper_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_cursor_pilot_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_implementer_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_qa_gate_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_release_orchestrator_template_retrieval_telemetry
    - id: AC8
      criterion: "Five agent templates: ## Retrieval-source telemetry (required) with markers and build_retrieval_breakdown_event"
      status: MET
      evidence: "Subsections added (scoper/cursor-pilot/implementer adjacent to Graph-first; qa-gate before Checkpoint; release-orchestrator before Output format)"
      run_result: "pytest tests/test_agent_templates.py: 6 new tests passed"
      covering_tests:
        - tests/test_agent_templates.py
    - id: AC9
      criterion: "memory-layer-defaults.mdc: ## Retrieval-source telemetry (required) mirroring 4-bucket + emission rule"
      status: MET
      evidence: "Section after Fail-open under Retrieval policy"
      run_result: "pytest tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_telemetry: passed"
      covering_tests:
        - tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_telemetry
    - id: AC10
      criterion: "CHANGELOG: E3-T5 prepended under [Unreleased] Added"
      status: MET
      evidence: "Top bullet documents modules, report stub, templates, tests"
      run_result: "File inspection"
      covering_tests: []
    - id: AC11
      criterion: "README: additive canon report row in commands table"
      status: MET
      evidence: "Row after can graph impact for canon report with --events/--by/--plan-id/--task-id"
      run_result: "File inspection"
      covering_tests: []
    - id: AC12
      criterion: "docs/SYSTEM-WORKFLOW.md §6: additive bullet on retrieval-source telemetry and canon report stub"
      status: MET
      evidence: "New bullet after Retrieval policy bullet in section 6"
      run_result: "File inspection"
      covering_tests: []
    - id: AC13
      criterion: "canon report output: deterministic JSON with sort_keys=True"
      status: MET
      evidence: "test_report_cli_aggregates_by_source asserts re-serialized output matches sorted form"
      run_result: "pytest tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_source: passed"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_source
    - id: AC14
      criterion: "No HTTP/graph query dependency in emitter or report (stdlib + file read only)"
      status: MET
      evidence: "retrieval_telemetry and report_cli use no urllib/requests; tests are local fixtures"
      run_result: "Code review; pytest tests/test_retrieval_telemetry.py: 15 passed"
      covering_tests:
        - tests/test_retrieval_telemetry.py
    - id: AC15
      criterion: "backend/shared and forbidden surfaces not modified in this change set"
      status: MET
      evidence: "Edits limited to 13 allowlisted product paths; import-only for canon_backend_shared"
      run_result: "git status / diff review at implementation time"
      covering_tests: []
    - id: AC16
      criterion: "RETRIEVAL_SOURCES order graph → state → canonical → file in emitter payload iteration"
      status: MET
      evidence: "RETRIEVAL_SOURCES tuple and test_build_event_payload_sources_keys"
      run_result: "pytest tests/test_retrieval_telemetry.py::test_build_event_payload_sources_keys: passed"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_build_event_payload_sources_keys
    - id: AC17
      criterion: "Full pytest suite green (no regressions)"
      status: MET
      evidence: "319 passed at repo root"
      run_result: "pytest -q: 319 passed in ~4s"
      covering_tests: []
    - id: AC18
      criterion: "Public API matches spec: report exit catalog 0/2/3/4; bucket key order; event_type retrieval_breakdown"
      status: MET
      evidence: "EXIT_* constants, sorted bucket keys in aggregation, build_retrieval_breakdown event_type"
      run_result: "pytest tests/test_retrieval_telemetry.py: 15 passed"
      covering_tests:
        - tests/test_retrieval_telemetry.py
  suite_result:
    focused: "tests/test_retrieval_telemetry.py tests/test_agent_templates.py: 40 passed in ~0.07s"
    full: "pytest -q: 319 passed in ~3.98s"
END_HANDOFF_TO_QA
```
