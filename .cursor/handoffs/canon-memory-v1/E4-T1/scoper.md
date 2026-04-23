# E4-T1 Scoper Packet — Orchestrator resume engine

## SCOPE SUMMARY

E4-T1 delivers `canon resume --plan-id <id>`: a stdlib-only local engine that queries the state-api over the existing `canon checkpoint read` surface (or a direct GET) to determine the first incomplete (task_id, phase) pair for a plan and prints a structured "resume target" payload. The engine is **read-only and idempotent** — running it twice on a quiescent plan prints identical output and emits zero canonical events (per AC §2: "idempotent re-entry; no duplicate canonical events"). Task enumeration is driven by an explicit `--tasks-file <path>` (JSON array of `{task_id, workstream_id}` records) OR by scanning a `--handoffs-dir <path>` for `<task_id>/` subdirectories. Fail-open when state-api is unreachable (prints a degraded envelope, exit code `5` via the existing checkpoint exit-code catalog). No backend changes; `canon_backend_shared` and `backend/state-api/**` remain untouched.

## SCOPE PACKET

### Identifiers
- handoff_id: `handoff_20260422_e4t1_resume_engine`
- branch: `wave/4/canon-memory-v1` (tip 58adaa3)

### Story — acceptanceCriteria (14)
1. New module `src/canon_systems/resume_engine.py` exports `run(argv) -> int`, `main()`, and internal helpers. Stdlib only. Reuses the checkpoint-CLI exit-code catalog: `EXIT_OK=0`, `EXIT_NOT_FOUND=3`, `EXIT_USAGE=4`, `EXIT_TRANSPORT=5`. (No conflict with the existing `checkpoint_cli` constants — duplicated here to avoid a cross-module dependency; the task scope forbids modifying `checkpoint_cli.py`.)
2. `canon resume --plan-id <id> --company-id <c> --repository-id <r> (--tasks-file <path> | --handoffs-dir <path>) [--base-url <url>] [--timeout-ms N] [--workstream-id-default <id>] [--emit-json]` is the CLI surface.
3. Task-id discovery:
   - If `--tasks-file <path>` given, read a JSON array of `{"task_id": "...", "workstream_id": "..."}` records; missing `workstream_id` falls back to `--workstream-id-default` (default `"ws-main"`).
   - If `--handoffs-dir <path>` given, enumerate immediate subdirectories matching `E<N>-T<N>` glob as `task_id` values; assign `--workstream-id-default` as their `workstream_id`.
   - Exactly one of the two flags must be supplied; supplying both or neither is a usage error (exit 4).
4. Per (task_id, workstream_id), call state-api `GET /state/checkpoint?company_id=&repository_id=&plan_id=&task_id=&workstream_id=` (reuses the known checkpoint schema). Parse the response:
   - HTTP 200 → extract `phase` and `phase_status` fields from the checkpoint body.
   - HTTP 404 → treat as "not yet started" (phase=None, phase_status=None).
   - HTTP 5xx / transport / timeout → degraded path; record for the final envelope but continue.
5. Resume-target computation (idempotent pure function):
   - Phase-order canonical list: `["scoper", "cursor-pilot", "implementer", "qa-gate", "release-orchestrator"]` (matches backlog §B union).
   - For each task in input order, find the first phase with `phase_status != "completed"` (or the task is missing a checkpoint entirely → first phase = `scoper`).
   - The first task with any incomplete phase becomes the resume target; earlier fully-completed tasks are skipped.
   - If all tasks are fully completed across all phases → resume-target is `null` and exit 0 (nothing to resume).
6. Output envelope on stdout (JSON, sort_keys=True for stable output):
   ```
   {
     "plan_id": "<id>",
     "company_id": "<c>",
     "repository_id": "<r>",
     "resume_target": null | {"task_id": "...", "workstream_id": "...", "phase": "<phase>"},
     "tasks_scanned": <int>,
     "tasks_completed": <int>,
     "degraded_tasks": [{"task_id": "...", "reason": "transport|http_500|..."}],
     "resume_available": true|false
   }
   ```
7. Idempotency guarantee: the engine performs ONLY GETs against state-api; it never writes, leases, or emits canonical events. Running it twice on an unchanged plan state produces byte-identical stdout. A covering test verifies byte-equality across two invocations.
8. No duplicate canonical events: a covering test confirms no `_emit_event`-style code path exists in `resume_engine.py` (static assertion on module source or a spy-based assertion).
9. `src/canon_systems/cli.py` additive wiring: new `resume` subparser using the `argparse.REMAINDER` pattern (matches E3-T2/E3-T5); dispatches to `resume_engine.run`.
10. Crash/restart integration test (done signal): `tests/test_resume_engine.py` includes a scenario where:
    - Task A has `phase=implementer`, `phase_status=completed` (fully done through release-orchestrator).
    - Task B has `phase=cursor-pilot`, `phase_status=completed` → resume target is Task B / `implementer`.
    - Task C has no checkpoint → NOT reached (stops at B).
    The test stubs the HTTP seam to return canned responses and asserts the resume-target JSON exactly.
11. Idempotency test: invoke `run()` twice on the same stubbed HTTP state, capture stdout both times, assert byte-equality.
12. Usage-error tests: missing both flags → exit 4; both flags present → exit 4; `--plan-id` missing → argparse exit 4; `--tasks-file` missing-file → exit 4 with `not_found`-style envelope on stderr.
13. Transport-error test: HTTP seam raises `URLError`; engine records the task as degraded and includes it in `degraded_tasks`; if ALL tasks degraded, exit code is `EXIT_TRANSPORT` (5); if only some are degraded, exit 0 with `resume_available=false` (because we can't prove completion either way — conservative degrade). The exact semantics are defined by the test assertions.
14. Living-spec updates (additive): `CHANGELOG.md` prepend E4-T1 bullet at top of `[Unreleased] ### Added`; `README.md` additive row `canon resume --plan-id ...`; `docs/SYSTEM-WORKFLOW.md` §5.1 (or §3) additive bullet describing the resume engine + idempotency guarantee.

### Forbidden surfaces
- backend/** (including backend/shared — only `CanonicalEvent` may be IMPORTED, but resume_engine must not emit events, so even the import is unnecessary)
- infra/**
- .cursor/rules/**, .cursor/plans/**
- src/canon_systems/*.py OTHER THAN `cli.py` (additive) and `resume_engine.py` (new)
- Template files (E4-T4 separately handles template + runbook wiring)

### Repository
- primaryLanguages: Python (stdlib-only)
- testFramework: pytest
- relevantFiles: src/canon_systems/{resume_engine.py (new), cli.py}, tests/test_resume_engine.py (new), CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md, src/canon_systems/checkpoint_cli.py (READ-ONLY reference for HTTP seam + exit codes)

### Constraints
- dependencies: E2-T3 (canon checkpoint CLI → establishes the HTTP seam shape), E2-T5 (flow-audit checkpoint enforcement)
- mustNotBreak: 319-test suite baseline; existing `canon checkpoint` subcommands unchanged.

### Prior work references
- peer:src/canon_systems/checkpoint_cli.py (E2-T3) — GET /state/checkpoint seam, exit-code catalog, base-url resolution pattern.
- peer:src/canon_systems/graph_indexer.py (E3-T2) — stdlib-only CLI shape with `_http_request` seam.
- peer:src/canon_systems/report_cli.py (E3-T5) — stub CLI module wired via `argparse.REMAINDER` in cli.py.

### ac_traceability

| # | Target | Test |
|---|---|---|
| 1-5 | resume_engine.py | tests/test_resume_engine.py::test_resume_target_first_incomplete_phase, ::test_resume_target_none_when_all_complete, ::test_resume_missing_checkpoint_points_to_scoper |
| 6 | stdout envelope | tests/test_resume_engine.py::test_output_envelope_keys_sorted, ::test_output_envelope_exact_shape |
| 7 | idempotency | tests/test_resume_engine.py::test_idempotent_byte_equal_on_double_invocation |
| 8 | no duplicate events | tests/test_resume_engine.py::test_no_event_emission_in_module_source |
| 9 | cli wiring | tests/test_resume_engine.py::test_resume_cli_help_returns_0 |
| 10 | crash/restart | tests/test_resume_engine.py::test_crash_restart_scenario_task_b_cursor_pilot |
| 11 | idempotency (dup) | tests/test_resume_engine.py::test_idempotent_byte_equal_on_double_invocation |
| 12 | usage errors | tests/test_resume_engine.py::test_both_task_sources_is_usage_error, ::test_neither_task_source_is_usage_error, ::test_missing_tasks_file_is_not_found |
| 13 | transport | tests/test_resume_engine.py::test_transport_error_all_tasks_exit_5, ::test_transport_error_partial_degrade_resume_unavailable |
| 14 | living-spec | grep (CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md) |

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: E4-T1 delivers canon resume --plan-id engine as stdlib-only src/canon_systems/resume_engine.py + cli.py wiring. Read-only + idempotent (no canonical events). Outputs JSON envelope with resume_target = first incomplete (task_id, phase) pair.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260422_e4t1_resume_engine"
    story:
      title: "Orchestrator resume engine"
      acceptanceCriteria:
        - "canon resume --plan-id <id> scans checkpoints (via state-api GET) and prints JSON resume target."
        - "Idempotent: double invocation on unchanged state yields byte-identical stdout."
        - "No canonical events emitted (static source check)."
        - "Task discovery via --tasks-file (JSON) or --handoffs-dir (subdirectory scan); exactly one required."
        - "Phase-order: scoper, cursor-pilot, implementer, qa-gate, release-orchestrator."
        - "Missing checkpoint (404) ⇒ task needs scoper."
        - "Transport error: degraded if partial, exit 5 if all tasks degraded."
        - "cli.py additive resume subparser using REMAINDER pattern."
        - "≥12 tests in tests/test_resume_engine.py."
        - "Additive CHANGELOG/README/SYSTEM-WORKFLOW."
    constraints:
      dependencies: ["E2-T3", "E2-T5"]
      mustNotBreak: ["319-test suite baseline", "canon checkpoint subcommands"]
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
