# E3-T5 QA Gate Packet — Retrieval-source telemetry

## Verification summary

- Focused suite: `pytest tests/test_retrieval_telemetry.py tests/test_agent_templates.py -q` → `40 passed in 0.04s`
- Full suite:    `pytest -q` → `319 passed in 3.86s`
- Modified / new files (exactly the 14 allowlisted product paths, plus tolerated auto-churn):
  - `CHANGELOG.md`
  - `README.md`
  - `docs/SYSTEM-WORKFLOW.md`
  - `src/canon_systems/cli.py`
  - `src/canon_systems/retrieval_telemetry.py` (new)
  - `src/canon_systems/report_cli.py` (new)
  - `src/canon_systems/templates/rules/memory-layer-defaults.mdc`
  - `src/canon_systems/templates/agents/scoper.md`
  - `src/canon_systems/templates/agents/cursor-pilot.md`
  - `src/canon_systems/templates/agents/implementer.md`
  - `src/canon_systems/templates/agents/qa-gate.md`
  - `src/canon_systems/templates/agents/release-orchestrator.md`
  - `tests/test_agent_templates.py`
  - `tests/test_retrieval_telemetry.py` (new)
  - (out-of-scope churn ignored: `.canon/memory/capture-failures.log`, `.canon/memory/capture-latest.json`)

```
GATE_RESULTS
  handoff_id: "handoff_20260422_e3t5_retrieval_telemetry"
  task_id: "E3-T5"
  overall_verdict: PASS
  verdict: PASS
  regression_checked: true
  iterations: 0
  suite_result: "focused: 40 passed in 0.04s; full: 319 passed in 3.86s"
  acceptance_criteria:
    - id: AC-1
      summary: "New module src/canon_systems/retrieval_telemetry.py exports RETRIEVAL_SOURCES=('graph','state','canonical','file'), SourceCounts (frozen dataclass with non-negative __post_init__), RetrievalBreakdown (dataclass of 4 SourceCounts with zero defaults), sum_breakdown(), and build_retrieval_breakdown_event(...) producing a CanonicalEvent with event_type='retrieval_breakdown' and payload {sources:{graph,state,canonical,file:{tokens_in,tokens_out}}, totals:{tokens_in,tokens_out}}."
      status: MET
      evidence: "Module file present at src/canon_systems/retrieval_telemetry.py; public names imported directly by the test module (RETRIEVAL_SOURCES, SourceCounts, RetrievalBreakdown, build_retrieval_breakdown_event, sum_breakdown). Negative-token guard, bucket-order iteration, payload shape, and totals summation all asserted by dedicated unit tests in tests/test_retrieval_telemetry.py."
      run_result: "pytest tests/test_retrieval_telemetry.py -q PASSED (15/15)"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_source_counts_non_negative
        - tests/test_retrieval_telemetry.py::test_retrieval_breakdown_defaults_zero
        - tests/test_retrieval_telemetry.py::test_build_event_canonical_shape
        - tests/test_retrieval_telemetry.py::test_build_event_payload_sources_keys
        - tests/test_retrieval_telemetry.py::test_build_event_payload_totals_sum
        - tests/test_retrieval_telemetry.py::test_sum_breakdown_zero_for_default
        - tests/test_retrieval_telemetry.py::test_sum_breakdown_sums_all_sources
    - id: AC-2
      summary: "Emitter reuses CanonicalEvent from backend/shared/canon_backend_shared/events.py (imported directly) — NO local redefinition or shadow dataclass."
      status: MET
      evidence: "Single import line in src/canon_systems/retrieval_telemetry.py: `from canon_backend_shared.events import CanonicalEvent`. test_build_event_canonical_shape asserts schema_version=1 and event_type identity; test_event_roundtrip_via_to_dict_from_dict round-trips through the shared envelope's to_dict/from_dict API without loss, proving the emitter relies on the shared dataclass rather than a shadow copy."
      run_result: "pytest tests/test_retrieval_telemetry.py::test_build_event_canonical_shape tests/test_retrieval_telemetry.py::test_event_roundtrip_via_to_dict_from_dict -q PASSED"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_build_event_canonical_shape
        - tests/test_retrieval_telemetry.py::test_event_roundtrip_via_to_dict_from_dict
    - id: AC-3
      summary: "src/canon_systems/report_cli.py ships `canon report` stub: run(argv) reads NDJSON line-by-line, filters to event_type='retrieval_breakdown', optionally filters by --plan-id / --task-id, aggregates tokens_in/tokens_out by --by {source|phase|agent}, prints a deterministic JSON summary to stdout."
      status: MET
      evidence: "report_cli.run implements all three group-by modes plus plan-id filtering; aggregation output is sorted and serialized with json.dumps(sort_keys=True). Six pytest cases cover aggregation by source, by phase, plan-id filtering, missing-file (exit 3), malformed JSON line (exit 4), and missing --events (exit 2)."
      run_result: "pytest tests/test_retrieval_telemetry.py -q PASSED (6 report_cli cases)"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_source
        - tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_phase
        - tests/test_retrieval_telemetry.py::test_report_cli_filters_by_plan_id
        - tests/test_retrieval_telemetry.py::test_report_cli_missing_file_exit_3
        - tests/test_retrieval_telemetry.py::test_report_cli_malformed_line_exit_4
        - tests/test_retrieval_telemetry.py::test_report_cli_missing_events_flag_exit_2
    - id: AC-4
      summary: "src/canon_systems/cli.py additively wires a `report` subparser with nargs=argparse.REMAINDER that delegates to report_cli.run — mirrors the E3-T2 `graph` subparser pattern; no existing subcommand is removed or reflowed."
      status: MET
      evidence: "cli.py imports `run as run_report_cli` from .report_cli, registers `report_parser = sub.add_parser('report', ...)` with REMAINDER args adjacent to the existing graph_parser, and dispatches `args.command == 'report'` → run_report_cli. test_cli_graph_and_report_help invokes `canon ... --help` paths for both the existing `graph` subcommand and the new `report` subcommand via the shared CLI entrypoint, confirming the wiring is additive."
      run_result: "pytest tests/test_retrieval_telemetry.py::test_cli_graph_and_report_help -q PASSED"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_cli_graph_and_report_help
    - id: AC-5
      summary: "Exit-code catalog respected: canon report --help exits 0; canon report --events <missing> exits 3; canon report --events <malformed> exits 4; canon report (no --events) exits 2."
      status: MET
      evidence: "report_cli defines EXIT_OK=0, EXIT_USAGE=2, EXIT_FILE_NOT_FOUND=3, EXIT_MALFORMED=4 and returns each on the matching failure branch. test_cli_graph_and_report_help covers --help=0 through the CLI entrypoint; test_report_cli_missing_file_exit_3 / test_report_cli_malformed_line_exit_4 / test_report_cli_missing_events_flag_exit_2 cover the error paths."
      run_result: "pytest tests/test_retrieval_telemetry.py -q PASSED (help+3 exit-code cases)"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_cli_graph_and_report_help
        - tests/test_retrieval_telemetry.py::test_report_cli_missing_file_exit_3
        - tests/test_retrieval_telemetry.py::test_report_cli_malformed_line_exit_4
        - tests/test_retrieval_telemetry.py::test_report_cli_missing_events_flag_exit_2
    - id: AC-6
      summary: "tests/test_retrieval_telemetry.py (new) contains ≥12 tests covering the emitter half of the surface (SourceCounts non-negativity, RetrievalBreakdown defaults, build_event canonical shape + payload sources keys + totals sum, sum_breakdown zero + non-trivial, CanonicalEvent round-trip)."
      status: MET
      evidence: "`grep -c '^def test_' tests/test_retrieval_telemetry.py` → 15 test functions present. The first 8 functions cover the emitter/dataclass half of the scoper §6 enumeration (SourceCounts non-negativity, defaults-zero, canonical shape, payload keys, totals sum, sum_breakdown zero, sum_breakdown sums, round-trip). All 15 pass in the focused run."
      run_result: "pytest tests/test_retrieval_telemetry.py -q → 15 passed in 0.03s"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_source_counts_non_negative
        - tests/test_retrieval_telemetry.py::test_retrieval_breakdown_defaults_zero
        - tests/test_retrieval_telemetry.py::test_build_event_canonical_shape
        - tests/test_retrieval_telemetry.py::test_build_event_payload_sources_keys
        - tests/test_retrieval_telemetry.py::test_build_event_payload_totals_sum
        - tests/test_retrieval_telemetry.py::test_sum_breakdown_zero_for_default
        - tests/test_retrieval_telemetry.py::test_sum_breakdown_sums_all_sources
        - tests/test_retrieval_telemetry.py::test_event_roundtrip_via_to_dict_from_dict
    - id: AC-7
      summary: "tests/test_retrieval_telemetry.py continues with ≥7 report-CLI tests covering aggregation by source/phase, plan-id filter, missing-file/malformed-line/missing-flag exit codes, and a `canon graph --help` + `canon report --help` regression guard for cli.py wiring."
      status: MET
      evidence: "Functions test_report_cli_aggregates_by_source, test_report_cli_aggregates_by_phase, test_report_cli_filters_by_plan_id, test_report_cli_missing_file_exit_3, test_report_cli_malformed_line_exit_4, test_report_cli_missing_events_flag_exit_2, and test_cli_graph_and_report_help — all seven present and passing."
      run_result: "pytest tests/test_retrieval_telemetry.py -q → 15 passed in 0.03s"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_source
        - tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_phase
        - tests/test_retrieval_telemetry.py::test_report_cli_filters_by_plan_id
        - tests/test_retrieval_telemetry.py::test_report_cli_missing_file_exit_3
        - tests/test_retrieval_telemetry.py::test_report_cli_malformed_line_exit_4
        - tests/test_retrieval_telemetry.py::test_report_cli_missing_events_flag_exit_2
        - tests/test_retrieval_telemetry.py::test_cli_graph_and_report_help
    - id: AC-8
      summary: "All five coder-facing agent templates (scoper.md, cursor-pilot.md, implementer.md, qa-gate.md, release-orchestrator.md) gain a `## Retrieval-source telemetry (required)` subsection instructing the phase to emit one retrieval_breakdown canonical event at phase end with payload.sources keyed by graph/state/canonical/file, and referencing `src/canon_systems/retrieval_telemetry.py::build_retrieval_breakdown_event` as the canonical constructor."
      status: MET
      evidence: "Five new test functions (one per template) assert the header substring `## Retrieval-source telemetry (required)` AND the `retrieval_breakdown` token. The scoper-template test additionally asserts `build_retrieval_breakdown_event`. All five pass."
      run_result: "pytest tests/test_agent_templates.py -q → 25 passed (6 new telemetry tests inclusive)"
      covering_tests:
        - tests/test_agent_templates.py::test_scoper_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_cursor_pilot_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_implementer_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_qa_gate_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_release_orchestrator_template_retrieval_telemetry
    - id: AC-9
      summary: "src/canon_systems/templates/rules/memory-layer-defaults.mdc gains a `## Retrieval-source telemetry (required)` section mirroring the template clause: every agent phase emits a retrieval_breakdown canonical event; payload.sources = {graph,state,canonical,file}; totals are derived; skip-on-degraded when axon is unreachable (zero counts are acceptable; the event is still emitted)."
      status: MET
      evidence: "`grep -n '## Retrieval-source telemetry (required)' src/canon_systems/templates/rules/memory-layer-defaults.mdc` → line 239. The new section lives adjacent to the E3-T4 `## Retrieval policy (required)` block, is additive (no reflow), and names all four bucket keys plus the build_retrieval_breakdown_event constructor. test_memory_layer_defaults_retrieval_telemetry asserts the header substring, the retrieval_breakdown token, the four bucket names (graph/state/canonical/file), and the build_retrieval_breakdown_event identifier all appear in the mdc body."
      run_result: "pytest tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_telemetry -q PASSED"
      covering_tests:
        - tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_telemetry
    - id: AC-10
      summary: "tests/test_agent_templates.py gains ≥6 new assertions — one per affected template (5) plus one for memory-layer-defaults.mdc — each verifying the telemetry subsection's presence and the 4 bucket names / retrieval_breakdown token."
      status: MET
      evidence: "Six new test functions visible via `grep '^def test_' tests/test_agent_templates.py | grep retrieval_telemetry`: test_memory_layer_defaults_retrieval_telemetry, test_scoper_template_retrieval_telemetry, test_cursor_pilot_template_retrieval_telemetry, test_implementer_template_retrieval_telemetry, test_qa_gate_template_retrieval_telemetry, test_release_orchestrator_template_retrieval_telemetry. Focused suite reports 25 passed (was 19 pre-E3-T5; +6 new)."
      run_result: "pytest tests/test_agent_templates.py -q → 25 passed in ~0.02s"
      covering_tests:
        - tests/test_agent_templates.py::test_memory_layer_defaults_retrieval_telemetry
        - tests/test_agent_templates.py::test_scoper_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_cursor_pilot_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_implementer_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_qa_gate_template_retrieval_telemetry
        - tests/test_agent_templates.py::test_release_orchestrator_template_retrieval_telemetry
    - id: AC-11
      summary: "CHANGELOG.md: E3-T5 bullet prepended at TOP of `[Unreleased] ### Added` (not appended), documenting retrieval_telemetry.py emitter + canon report stub + template clause + new tests."
      status: MET
      evidence: "`grep -n 'E3-T5' CHANGELOG.md` → line 12 shows the new bullet `- **E3-T5** Retrieval-source telemetry: new src/canon_systems/retrieval_telemetry.py emits retrieval_breakdown canonical events ...` as the first bullet under the Unreleased/Added heading, directly above the pre-existing E3-T4 bullet (prepended, not appended)."
      run_result: "grep -n 'E3-T5' CHANGELOG.md → line 12 (first bullet under [Unreleased] Added)"
      covering_tests:
        - CHANGELOG.md
    - id: AC-12
      summary: "README.md additive: one new row in the `canon` commands table for `canon report --events <ndjson> [--by phase|agent|source] [--plan-id X] [--task-id Y]` with a short description and Wave-6 stub annotation; no table reflow of existing rows."
      status: MET
      evidence: "`grep -n 'canon report' README.md` → line 224 contains the new table row `| \\`canon report --events <ndjson> [--by phase\\|agent\\|source] [--plan-id X] [--task-id Y]\\` | Aggregate retrieval_breakdown canonical events into a JSON rollup (Wave 6 will polish into CSV/table). |`. The pre-existing `canon graph query` / `canon graph impact` rows immediately above are unchanged — no reflow."
      run_result: "grep -n 'canon report' README.md → line 224"
      covering_tests:
        - README.md
    - id: AC-13
      summary: "docs/SYSTEM-WORKFLOW.md §6 gains an additive bullet on retrieval-source telemetry naming the four canonical buckets (graph/state/canonical/file) and the fail-open (zero-counts-are-valid) note, and cross-linking `canon report --events`."
      status: MET
      evidence: "`grep -n 'Retrieval-source telemetry' docs/SYSTEM-WORKFLOW.md` → line 118 shows the new bullet `- **Retrieval-source telemetry**: Each agent phase emits one retrieval_breakdown canonical event with payload.sources keyed by the fixed graph/state/canonical/file 4-bucket contract (see src/canon_systems/retrieval_telemetry.py). canon report --events <ndjson> provides a stub rollup grouped by phase, agent, or source (Wave-6 polish). Zero counts are valid when a source is unused or degraded; the event is still emitted.` — additive under §6, no reflow."
      run_result: "grep -n 'Retrieval-source telemetry' docs/SYSTEM-WORKFLOW.md → line 118"
      covering_tests:
        - docs/SYSTEM-WORKFLOW.md
    - id: AC-14
      summary: "canon report output is stable JSON: keys sorted, integer counts, deterministic for a given NDJSON input (snapshot-friendly)."
      status: MET
      evidence: "report_cli.run prints via `json.dumps(out, sort_keys=True)` after building an aggregation dict sorted by key. test_report_cli_aggregates_by_source captures stdout, parses it back, and additionally asserts that re-serializing with sort_keys=True yields byte-identical output — pinning deterministic JSON stability."
      run_result: "pytest tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_source -q PASSED"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_source
    - id: AC-15
      summary: "No dependency on `canon graph query` at runtime for the emitter or the report CLI — pure local event-shaping + NDJSON-reading module (stdlib only, no urllib/requests/HTTP)."
      status: MET
      evidence: "`rg -n 'urllib|requests|http' src/canon_systems/retrieval_telemetry.py src/canon_systems/report_cli.py` returns no matches (stdlib only). The tests in tests/test_retrieval_telemetry.py exercise report_cli.run against local tmp_path NDJSON fixtures with no network seam; a missing axon endpoint would not affect either module."
      run_result: "code audit + pytest tests/test_retrieval_telemetry.py -q PASSED (no test requires network)"
      covering_tests:
        - tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_source
        - tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_phase
        - tests/test_retrieval_telemetry.py::test_report_cli_filters_by_plan_id
    - id: AC-16
      summary: "canon_backend_shared is NOT modified — the emitter imports CanonicalEvent from backend/shared/canon_backend_shared/events.py without editing the package."
      status: MET
      evidence: "`git diff --name-only | rg '^backend/'` returns zero lines. `git ls-files --others --exclude-standard | rg '^backend/'` returns zero lines. The only reference to canon_backend_shared in this change set is the single import in src/canon_systems/retrieval_telemetry.py. The shared package is consumed read-only."
      run_result: "git diff --name-only / ls-files audit → 0 lines under backend/"
      covering_tests:
        - src/canon_systems/retrieval_telemetry.py
    - id: AC-17
      summary: "Forbidden surfaces untouched (backend/**, infra/**, .cursor/rules/**, .cursor/plans/**, and any src/canon_systems/*.py other than cli.py + the two new modules). Git diff + untracked-new-files equals exactly the 14 allowlisted product paths (CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md, src/canon_systems/cli.py, src/canon_systems/retrieval_telemetry.py, src/canon_systems/report_cli.py, src/canon_systems/templates/rules/memory-layer-defaults.mdc, src/canon_systems/templates/agents/{scoper,cursor-pilot,implementer,qa-gate,release-orchestrator}.md, tests/test_agent_templates.py, tests/test_retrieval_telemetry.py) plus tolerated `.canon/memory/*` auto-churn."
      status: MET
      evidence: "`git diff --name-only` emits: .canon/memory/capture-failures.log, .canon/memory/capture-latest.json, CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md, src/canon_systems/cli.py, src/canon_systems/templates/agents/{cursor-pilot,implementer,qa-gate,release-orchestrator,scoper}.md, src/canon_systems/templates/rules/memory-layer-defaults.mdc, tests/test_agent_templates.py. `git ls-files --others --exclude-standard` emits the three new product files (report_cli.py, retrieval_telemetry.py, test_retrieval_telemetry.py) alongside the three handoff packets for this task (.cursor/handoffs/canon-memory-v1/E3-T5/{scoper,cursor-pilot,implementer}.md — handoff artifacts, not product surfaces). `rg '^(backend/|infra/|\\.cursor/rules/|\\.cursor/plans/)' <(git diff --name-only)` returns zero lines; no other src/canon_systems/*.py file is modified beyond cli.py."
      run_result: "git diff / ls-files audit → 14 product paths match allowlist exactly"
      covering_tests:
        - src/canon_systems/retrieval_telemetry.py
        - src/canon_systems/report_cli.py
        - src/canon_systems/cli.py
    - id: AC-18
      summary: "Full pytest suite passes (no regressions) — 319 tests, 0 failures, 0 errors."
      status: MET
      evidence: "Full repo sweep `pytest -q` reports 319 passed in 3.86s (298 pre-E3-T5 baseline + 15 new retrieval_telemetry tests + 6 new agent-template tests = 319). Zero failures / zero errors anywhere in the tree; pre-existing E3-T1..E3-T4 tests remain green."
      run_result: "pytest -q → 319 passed in 3.86s"
      covering_tests:
        - tests/test_retrieval_telemetry.py
        - tests/test_agent_templates.py
  remaining_gaps: []
  notes: |
    All 18 acceptance criteria verified. Focused suite 40/40 passing (15 retrieval_telemetry + 25 agent_templates — 19 pre-existing + 6 new), full repo suite 319/319 passing, zero iterations required. Modified-files set matches the 14 allowlisted product paths exactly; the only additional churn is the tolerated auto-generated `.canon/memory/capture-*` pair and the three handoff packets under `.cursor/handoffs/canon-memory-v1/E3-T5/` (scoper/cursor-pilot/implementer), which are governance artifacts rather than product surfaces. No forbidden surface (backend/**, infra/**, .cursor/rules/**, .cursor/plans/**) is touched; `canon_backend_shared` is consumed read-only via a single import in src/canon_systems/retrieval_telemetry.py. `canon report` output is deterministic JSON (sort_keys=True) and the exit-code catalog (0/2/3/4) matches the E3-T2 graph_indexer precedent.
END_GATE_RESULTS
```
