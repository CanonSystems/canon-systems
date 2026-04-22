# E3-T5 Scoper Packet — Retrieval-source telemetry

## SCOPE SUMMARY

E3-T5 delivers a stdlib-only `retrieval_breakdown` canonical event emitter that every agent phase can invoke to record per-source `tokens_in`/`tokens_out` counts (buckets: `graph`, `state`, `canonical`, `file`). Ships a new `src/canon_systems/retrieval_telemetry.py` module built on the shared `CanonicalEvent` envelope (`backend/shared/canon_backend_shared/events.py`), a `canon report` CLI stub that reads NDJSON event files and renders a per-phase breakdown (Wave-6 stub, per backlog), and `tests/test_retrieval_telemetry.py` asserting emitter shape, template wiring, and report stub output. Agent templates gain a `## Retrieval-source telemetry (required)` subsection instructing each phase to emit one `retrieval_breakdown` event.

## SCOPE PACKET

### Identifiers
- handoff_id: `handoff_20260422_e3t5_retrieval_telemetry`
- branch: `wave/3/canon-memory-v1` (tip 6594063)

### Story — acceptanceCriteria (18)
1. New module `src/canon_systems/retrieval_telemetry.py` exports:
   - `RETRIEVAL_SOURCES = ("graph", "state", "canonical", "file")` — the fixed bucket order (aligned with E3-T4's graph→state→canonical→file policy).
   - `@dataclass(frozen=True) class SourceCounts` with fields `tokens_in: int = 0`, `tokens_out: int = 0` (non-negative ints; `__post_init__` raises `ValueError` on negatives).
   - `@dataclass class RetrievalBreakdown` with `graph: SourceCounts`, `state: SourceCounts`, `canonical: SourceCounts`, `file: SourceCounts` (defaults = empty `SourceCounts()`).
   - `build_retrieval_breakdown_event(*, event_id, parent_event_id, company_id, repository_id, plan_id, task_id, handoff_id, agent_name, agent_run_id, actor_id, model, timestamp, state_version, breakdown: RetrievalBreakdown) -> CanonicalEvent` — returns a `CanonicalEvent` with `event_type="retrieval_breakdown"` and `payload={"sources": {"graph": {"tokens_in": ..., "tokens_out": ...}, "state": {...}, "canonical": {...}, "file": {...}}, "totals": {"tokens_in": ..., "tokens_out": ...}}`.
   - `sum_breakdown(breakdown) -> SourceCounts` — returns totals across all 4 sources.
2. The emitter reuses `CanonicalEvent` from `backend/shared/canon_backend_shared/events.py` — NO redefinition or shadow dataclass.
3. `canon report` CLI stub (new subcommand wired to existing `canon` CLI):
   - `src/canon_systems/report_cli.py` (new): `run(argv) -> int` implements `canon report --events <path.ndjson> [--by phase|agent|source] [--plan-id X] [--task-id Y]`.
   - Reads the NDJSON file line-by-line (one `CanonicalEvent` JSON per line), filters to `event_type == "retrieval_breakdown"`, optionally filters by `plan_id`/`task_id`.
   - Aggregates `tokens_in`/`tokens_out` by the selected dimension; prints a deterministic JSON summary to stdout (NOT a pretty table — Wave 6 will polish).
   - Exit codes: `0` success, `2` usage error, `3` file not found, `4` malformed NDJSON line.
4. `src/canon_systems/cli.py` is additively updated to expose a `report` subparser that delegates to `report_cli.run` via `argparse.REMAINDER`, mirroring the E3-T2 `graph` subparser wiring pattern.
5. `canon report --help` exits 0; `canon report --events <missing>` exits 3; `canon report --events <malformed>` exits 4; `canon report` with no `--events` exits 2.
6. `tests/test_retrieval_telemetry.py` (new) — ≥12 tests:
   - `test_source_counts_non_negative` — negative `tokens_in` raises `ValueError`.
   - `test_retrieval_breakdown_defaults_zero` — default `RetrievalBreakdown()` has all 4 buckets at `SourceCounts(0, 0)`.
   - `test_build_event_canonical_shape` — output is a `CanonicalEvent` with `event_type="retrieval_breakdown"` and `schema_version=1`.
   - `test_build_event_payload_sources_keys` — payload contains `sources` with exactly 4 keys in `RETRIEVAL_SOURCES` order; each has `tokens_in`/`tokens_out`.
   - `test_build_event_payload_totals_sum` — payload `totals.tokens_in` equals sum of all sources' `tokens_in`; same for `tokens_out`.
   - `test_sum_breakdown_zero_for_default` — returns `SourceCounts(0, 0)`.
   - `test_sum_breakdown_sums_all_sources` — given non-trivial input, sums correctly.
   - `test_event_roundtrip_via_to_dict_from_dict` — `to_dict` → `from_dict` roundtrip preserves payload.
7. `tests/test_retrieval_telemetry.py` — continued:
   - `test_report_cli_aggregates_by_source` — given a fixture NDJSON with 2 events, prints a JSON summary grouped by source.
   - `test_report_cli_aggregates_by_phase` — groups by `agent_name` when `--by phase` is passed.
   - `test_report_cli_filters_by_plan_id` — `--plan-id` filters correctly.
   - `test_report_cli_missing_file_exit_3` — nonexistent path returns exit 3.
   - `test_report_cli_malformed_line_exit_4` — invalid JSON line returns exit 4.
   - `test_report_cli_missing_events_flag_exit_2` — no `--events` returns exit 2.
   - `test_cli_graph_and_report_help` — both `canon report --help` and the existing `canon graph --help` continue to return 0 (regression guard for cli.py wiring).
8. Agent templates (`scoper.md`, `cursor-pilot.md`, `implementer.md`, `qa-gate.md`, `release-orchestrator.md`) each gain a `## Retrieval-source telemetry (required)` subsection instructing the phase to emit one `retrieval_breakdown` canonical event at phase end with `payload.sources` keyed by the 4-bucket contract. The subsection must reference `src/canon_systems/retrieval_telemetry.py::build_retrieval_breakdown_event` as the canonical constructor.
9. `memory-layer-defaults.mdc` gains a `## Retrieval-source telemetry (required)` section mirroring the template clause: every agent phase emits a `retrieval_breakdown` canonical event; payload.sources = `{graph,state,canonical,file}`; totals are derived; skip-on-degraded when axon is unreachable (zero counts are acceptable; the event is still emitted).
10. `tests/test_agent_templates.py` gains ≥6 new assertions (one per affected template + one for memory-layer-defaults.mdc) verifying the telemetry subsection's presence and the 4 bucket names.
11. `CHANGELOG.md` — prepend E3-T5 bullet at TOP of `[Unreleased] ### Added`.
12. `README.md` — additive row in the canon commands table for `canon report` (short description + "Wave-6 stub" annotation).
13. `docs/SYSTEM-WORKFLOW.md` §6 — additive bullet on retrieval-source telemetry with the 4 buckets and fail-open note.
14. `canon report` output is stable JSON: keys sorted, integer counts, deterministic for a given NDJSON input (snapshot-friendly).
15. No dependency on `canon graph query` at runtime for the emitter or report CLI — this is a pure local event-shaping + NDJSON-reading module (no HTTP).
16. `canon_backend_shared` is NOT modified. The emitter simply imports `CanonicalEvent` from it.
17. Forbidden surfaces: backend/**, infra/**, .cursor/rules/**, .cursor/plans/**, any `src/canon_systems/*.py` other than `cli.py` (additive) and the two new modules (`retrieval_telemetry.py`, `report_cli.py`).
18. Full pytest suite passes (no regressions).

### Repository
- primaryLanguages: Python (stdlib + dataclasses), Markdown (templates)
- testFramework: pytest
- relevantFiles: src/canon_systems/{retrieval_telemetry.py,report_cli.py,cli.py,templates/rules/memory-layer-defaults.mdc,templates/agents/{scoper,cursor-pilot,implementer,qa-gate,release-orchestrator}.md}, tests/{test_retrieval_telemetry.py,test_agent_templates.py}, CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md, backend/shared/canon_backend_shared/events.py (READ-ONLY reference)

### Constraints
- dependencies: E3-T4 (graph-first policy cements the 4-source order), E2-T2 (CanonicalEvent lives in backend/shared from Wave 2)
- mustNotBreak: existing 298-test suite; cli.py must retain all existing subcommands unchanged.

### Prior work references
- peer:backend/shared/canon_backend_shared/events.py (E2-T2) — CanonicalEvent shape + schema_version=1 invariant.
- peer:src/canon_systems/cli.py (E3-T2) — graph-subparser REMAINDER pattern for delegating to a submodule.
- peer:src/canon_systems/graph_indexer.py (E3-T2) — stdlib-only CLI with exit-code catalog (0/2/3/4 mapping reused).
- peer:src/canon_systems/templates/rules/memory-layer-defaults.mdc (E3-T4) — Retrieval policy section; Retrieval-source telemetry section sits adjacent.

### ac_traceability

| # | Target | Test |
|---|---|---|
| 1-2 | retrieval_telemetry.py | tests/test_retrieval_telemetry.py::test_source_counts_non_negative, ::test_retrieval_breakdown_defaults_zero, ::test_build_event_canonical_shape, ::test_build_event_payload_sources_keys, ::test_build_event_payload_totals_sum, ::test_sum_breakdown_zero_for_default, ::test_sum_breakdown_sums_all_sources, ::test_event_roundtrip_via_to_dict_from_dict |
| 3-5 | report_cli.py | tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_source, ::test_report_cli_aggregates_by_phase, ::test_report_cli_filters_by_plan_id, ::test_report_cli_missing_file_exit_3, ::test_report_cli_malformed_line_exit_4, ::test_report_cli_missing_events_flag_exit_2 |
| 4 | cli.py | tests/test_retrieval_telemetry.py::test_cli_graph_and_report_help |
| 6-7 | test file | full run |
| 8-10 | templates + mdc | tests/test_agent_templates.py::test_<role>_template_retrieval_telemetry (6 new) |
| 11-13 | CHANGELOG/README/SYSTEM-WORKFLOW | grep |
| 14 | stable JSON | tests/test_retrieval_telemetry.py::test_report_cli_aggregates_by_source (snapshot assertion on sorted keys) |
| 15 | no HTTP | tests/test_retrieval_telemetry.py (no seam needed) |
| 16 | backend/shared untouched | git diff --name-only |
| 17 | forbidden surfaces | git diff --name-only |
| 18 | full suite | pytest -q |

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: E3-T5 delivers retrieval_breakdown event emitter (src/canon_systems/retrieval_telemetry.py), canon report CLI stub (src/canon_systems/report_cli.py + cli.py wiring), agent-template + mdc clauses requiring per-phase emission, and 18+ tests.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260422_e3t5_retrieval_telemetry"
    story:
      title: "Retrieval-source telemetry"
      acceptanceCriteria:
        - "retrieval_telemetry.py exposes RETRIEVAL_SOURCES, SourceCounts, RetrievalBreakdown, build_retrieval_breakdown_event, sum_breakdown."
        - "Emitter reuses CanonicalEvent from backend/shared/canon_backend_shared/events.py; no shadow dataclass."
        - "canon report CLI reads NDJSON, filters by plan/task, groups by phase/agent/source, JSON output, exit codes 0/2/3/4."
        - "cli.py adds report subparser using REMAINDER pattern."
        - "All 5 coder-facing agent templates + memory-layer-defaults.mdc gain ## Retrieval-source telemetry (required) subsection."
        - "tests/test_retrieval_telemetry.py ≥14 tests; tests/test_agent_templates.py ≥6 new assertions."
        - "CHANGELOG prepended; README + SYSTEM-WORKFLOW additive."
        - "No edits to backend/shared, backend/*, infra/*, .cursor/rules/*, .cursor/plans/*, or src/canon_systems/*.py other than cli.py + the two new modules."
    constraints:
      dependencies: ["E3-T4", "E2-T2"]
      mustNotBreak: ["298-test suite baseline", "all existing canon CLI subcommands"]
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
