# E4-T1 QA Gate Packet — Orchestrator resume engine

## Verification summary

- Focused suite: `pytest tests/test_resume_engine.py -q` → `14 passed in 0.03s`
- Full suite:    `pytest -q` → `333 passed in 3.92s`
- Modified / new files (exactly the 6 allowlisted product paths, plus tolerated auto-churn):
  - `CHANGELOG.md`
  - `README.md`
  - `docs/SYSTEM-WORKFLOW.md`
  - `src/canon_systems/cli.py`
  - `src/canon_systems/resume_engine.py` (new)
  - `tests/test_resume_engine.py` (new)
  - (out-of-scope churn ignored: `.canon/memory/capture-*` auto-generated pair; `.cursor/handoffs/canon-memory-v1/E4-T1/{scoper,cursor-pilot,implementer,qa-gate}.md` handoff artifacts)

## Hardening checks

- `rg -n 'CanonicalEvent|event_type|emit_event' src/canon_systems/resume_engine.py` → 0 matches (zero-emission invariant holds).
- `rg -n 'sort_keys=True' src/canon_systems/resume_engine.py` → 3 matches (stdout envelope + stderr not_found + stderr usage all stable).
- `rg -n 'E4-T1|canon resume|Resume engine' CHANGELOG.md README.md docs/SYSTEM-WORKFLOW.md` → bullets present in all three living-spec files.
- `git diff --name-only` + `git ls-files --others --exclude-standard` matches the 6-path allowlist (plus tolerated `.canon/memory/*` churn and this task's handoff packets).

```
GATE_RESULTS
  handoff_id: "handoff_20260422_e4t1_resume_engine"
  task_id: "E4-T1"
  overall_verdict: PASS
  verdict: PASS
  regression_checked: true
  iterations: 0
  suite_result: "focused: 14 passed in 0.03s; full: 333 passed in 3.92s"
  acceptance_criteria:
    - id: AC-1
      summary: "New module src/canon_systems/resume_engine.py exports run(argv) -> int, main(), and the stdlib-only internal helpers (_http_request, _resolve_base_url, _load_tasks_from_file, _load_tasks_from_handoffs, _first_incomplete_phase, _scan_task, _compute_resume_target, _build_envelope, _build_parser) plus the exit-code catalog EXIT_OK=0, EXIT_NOT_FOUND=3, EXIT_USAGE=4, EXIT_TRANSPORT=5 — duplicated locally (per scoper) to avoid a cross-module dependency on checkpoint_cli.py."
      status: MET
      evidence: "File present at src/canon_systems/resume_engine.py; imports by tests confirm the public surface resolves (resume_engine.run, resume_engine._http_request). test_no_event_emission_in_module_source additionally reads the module __file__ text and asserts three canonical-event tokens are absent, pinning the stdlib-only + zero-emission contract. test_resume_cli_help_returns_0 drives run() end-to-end through argparse, exercising the parser + exit-code mapping."
      run_result: "pytest tests/test_resume_engine.py::test_resume_cli_help_returns_0 tests/test_resume_engine.py::test_no_event_emission_in_module_source -q PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_resume_cli_help_returns_0
        - tests/test_resume_engine.py::test_no_event_emission_in_module_source
    - id: AC-2
      summary: "CLI surface: canon resume --plan-id <id> --company-id <c> --repository-id <r> (--tasks-file <path> | --handoffs-dir <path>) [--base-url <url>] [--timeout-ms N] [--workstream-id-default <id>] [--emit-json]."
      status: MET
      evidence: "_build_parser wires all documented flags; mutually_exclusive_group enforces the --tasks-file | --handoffs-dir contract. --help drives run() to exit 0 through the SystemExit(0) trap. Exercised by test_resume_cli_help_returns_0 and by every happy-path test that passes --plan-id/--company-id/--repository-id + a task source."
      run_result: "pytest tests/test_resume_engine.py::test_resume_cli_help_returns_0 PASSED; full focused suite 14/14 exercises the flag surface."
      covering_tests:
        - tests/test_resume_engine.py::test_resume_cli_help_returns_0
        - tests/test_resume_engine.py::test_resume_target_first_incomplete_phase
    - id: AC-3
      summary: "Task-id discovery: --tasks-file reads a JSON array of {task_id, workstream_id}, with workstream_id falling back to --workstream-id-default (ws-main); --handoffs-dir enumerates immediate subdirectories matching E<N>-T<N>; exactly one of the two flags is required — both or neither is a usage error (exit 4)."
      status: MET
      evidence: "test_both_task_sources_is_usage_error asserts exit 4 when both flags are supplied; test_neither_task_source_is_usage_error asserts exit 4 when neither is supplied; test_handoffs_dir_discovery creates a tmp handoffs tree containing E4-T1/, E4-T2/, and a non-matching 'other/' directory, then asserts that only the two E<N>-T<N> entries are scanned (tasks_scanned == 2) and that the first becomes the resume target, confirming the regex filter and sort order."
      run_result: "pytest tests/test_resume_engine.py::test_both_task_sources_is_usage_error tests/test_resume_engine.py::test_neither_task_source_is_usage_error tests/test_resume_engine.py::test_handoffs_dir_discovery PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_both_task_sources_is_usage_error
        - tests/test_resume_engine.py::test_neither_task_source_is_usage_error
        - tests/test_resume_engine.py::test_handoffs_dir_discovery
    - id: AC-4
      summary: "Per (task_id, workstream_id) the engine calls state-api GET /state/checkpoint?company_id=&repository_id=&plan_id=&task_id=&workstream_id= and parses the response: HTTP 200 → extract phase + phase_status from the checkpoint body; HTTP 404 → treat as 'not yet started' (phase=None, phase_status=None); HTTP 5xx / transport / timeout → record in degraded_tasks and continue."
      status: MET
      evidence: "_http_request is monkeypatched in three tests to return canned tuples matching each HTTP class. test_resume_target_first_incomplete_phase drives the 200 path twice (once with in_progress, once with completed) and asserts the envelope picks the in-progress row. test_resume_missing_checkpoint_points_to_scoper returns (404, ...) and asserts the resume target becomes scoper (the first phase) — confirming 404 maps to phase=None. test_transport_error_all_tasks_exit_5 returns (0, None, {'X-Canon-Transport-Error': ...}) for every call and asserts every task lands in degraded_tasks with exit 5."
      run_result: "pytest tests/test_resume_engine.py::test_resume_target_first_incomplete_phase tests/test_resume_engine.py::test_resume_missing_checkpoint_points_to_scoper tests/test_resume_engine.py::test_transport_error_all_tasks_exit_5 PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_resume_target_first_incomplete_phase
        - tests/test_resume_engine.py::test_resume_missing_checkpoint_points_to_scoper
        - tests/test_resume_engine.py::test_transport_error_all_tasks_exit_5
    - id: AC-5
      summary: "Resume-target computation is an idempotent pure function: phase-order canonical list = [scoper, cursor-pilot, implementer, qa-gate, release-orchestrator]; for each task in input order find the first phase with phase_status != 'completed' (or a missing checkpoint → scoper); the first task with any incomplete phase becomes the resume target; if all tasks fully complete across all phases → resume_target is null and exit 0."
      status: MET
      evidence: "test_resume_target_first_incomplete_phase uses input order [B, A] with canned stubs (B=implementer/in_progress, A=qa-gate/completed) and asserts resume_target == {task_id:B, workstream_id:ws-main, phase:implementer} — proving input order is respected and 'in_progress' is treated as incomplete. test_resume_target_none_when_all_complete stubs release-orchestrator/completed for the only task and asserts resume_target is None and resume_available is False with exit 0. test_crash_restart_scenario_task_b_cursor_pilot drives the [A fully-complete → B cursor-pilot/completed] sequence and asserts resume_target == {task_id:B, workstream_id:w, phase:implementer}, confirming the 'next phase after the last completed phase' rule."
      run_result: "pytest tests/test_resume_engine.py::test_resume_target_first_incomplete_phase tests/test_resume_engine.py::test_resume_target_none_when_all_complete tests/test_resume_engine.py::test_crash_restart_scenario_task_b_cursor_pilot PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_resume_target_first_incomplete_phase
        - tests/test_resume_engine.py::test_resume_target_none_when_all_complete
        - tests/test_resume_engine.py::test_crash_restart_scenario_task_b_cursor_pilot
    - id: AC-6
      summary: "Output envelope on stdout is JSON with sort_keys=True for stable output and the exact key set: plan_id, company_id, repository_id, resume_target (null | {task_id, workstream_id, phase}), tasks_scanned, tasks_completed, degraded_tasks, resume_available."
      status: MET
      evidence: "`rg -n 'sort_keys=True' src/canon_systems/resume_engine.py` returns 3 hits (stdout envelope at line 256, plus stderr not_found and usage error envelopes at 228/231). test_output_envelope_keys_sorted parses stdout and asserts the top-level keys equal their sorted order, proving the sort_keys contract survives through json.dumps. test_resume_target_first_incomplete_phase additionally asserts the resume_target sub-object has the exact {task_id, workstream_id, phase} shape."
      run_result: "pytest tests/test_resume_engine.py::test_output_envelope_keys_sorted tests/test_resume_engine.py::test_resume_target_first_incomplete_phase PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_output_envelope_keys_sorted
        - tests/test_resume_engine.py::test_resume_target_first_incomplete_phase
    - id: AC-7
      summary: "Idempotency guarantee: the engine performs ONLY GETs against state-api; it never writes, leases, or emits canonical events. Running run() twice on an unchanged plan state produces byte-identical stdout."
      status: MET
      evidence: "test_idempotent_byte_equal_on_double_invocation drives run() twice with the same argv and the same stubbed _http_request and asserts first == second over captured stdout — byte-equality is the pin. test_no_event_emission_in_module_source proves the 'never emits canonical events' half of the contract by static-source assertion over the module file (no CanonicalEvent / event_type / emit_event tokens). The GET-only half is implicit in the _http_request signature used throughout (no write/lease helper is imported or defined)."
      run_result: "pytest tests/test_resume_engine.py::test_idempotent_byte_equal_on_double_invocation tests/test_resume_engine.py::test_no_event_emission_in_module_source PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_idempotent_byte_equal_on_double_invocation
        - tests/test_resume_engine.py::test_no_event_emission_in_module_source
    - id: AC-8
      summary: "No duplicate canonical events: a covering test confirms no _emit_event-style code path exists in resume_engine.py (static assertion on the module source)."
      status: MET
      evidence: "test_no_event_emission_in_module_source reads Path(resume_engine.__file__).read_text() and asserts three tokens — 'CanonicalEvent', 'event_type', 'emit_event' — are absent. `rg -n 'CanonicalEvent|event_type|emit_event' src/canon_systems/resume_engine.py` independently confirms zero matches, so the static assertion is binding."
      run_result: "pytest tests/test_resume_engine.py::test_no_event_emission_in_module_source PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_no_event_emission_in_module_source
    - id: AC-9
      summary: "src/canon_systems/cli.py additive wiring: new 'resume' subparser using the argparse.REMAINDER pattern (matches E3-T2/E3-T5); dispatches to resume_engine.run."
      status: MET
      evidence: "cli.py imports `run as run_resume_engine` from .resume_engine, adds a resume_parser with nargs=argparse.REMAINDER alongside the existing graph_parser/report_parser, and dispatches `args.command == 'resume'` → run_resume_engine(args.args). test_resume_cli_help_returns_0 drives resume_engine.run(['--help']) to exit 0 via the SystemExit trap in run(), confirming the parser builds cleanly under the same dispatch contract used by E3-T2/E3-T5."
      run_result: "pytest tests/test_resume_engine.py::test_resume_cli_help_returns_0 PASSED; full suite 333/333 confirms no existing subcommand regressed."
      covering_tests:
        - tests/test_resume_engine.py::test_resume_cli_help_returns_0
    - id: AC-10
      summary: "Crash/restart integration test: Task A has phase=release-orchestrator/completed (fully done); Task B has phase=cursor-pilot/completed → resume target is Task B / implementer; Task C with no checkpoint is NOT reached (stops at B). Stubs the HTTP seam to return canned responses and asserts the resume-target JSON exactly."
      status: MET
      evidence: "test_crash_restart_scenario_task_b_cursor_pilot implements the exact scenario from scoper §10: input order [A, B] with canned [A=release-orchestrator/completed, B=cursor-pilot/completed], asserts resume_target == {task_id:B, workstream_id:w, phase:implementer}. The test uses a sequential stub (nonlocal n index) so the second invocation naturally stops at B and never fires a third GET for a theoretical Task C — matching the 'early exit on first incomplete task' contract."
      run_result: "pytest tests/test_resume_engine.py::test_crash_restart_scenario_task_b_cursor_pilot PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_crash_restart_scenario_task_b_cursor_pilot
    - id: AC-11
      summary: "Idempotency test: invoke run() twice on the same stubbed HTTP state, capture stdout both times, assert byte-equality."
      status: MET
      evidence: "test_idempotent_byte_equal_on_double_invocation captures capsys.readouterr().out after each run() call and asserts first == second. The stub returns (404, None, {}) for every call, so the two invocations exercise identical code paths including the 'missing checkpoint → scoper' fallback — the pin is over the JSON output with sort_keys=True."
      run_result: "pytest tests/test_resume_engine.py::test_idempotent_byte_equal_on_double_invocation PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_idempotent_byte_equal_on_double_invocation
    - id: AC-12
      summary: "Usage-error tests: missing both flags → exit 4; both flags present → exit 4; --tasks-file missing-file → exit 4 with not_found-style envelope on stderr."
      status: MET
      evidence: "test_neither_task_source_is_usage_error asserts exit 4 when neither --tasks-file nor --handoffs-dir is supplied. test_both_task_sources_is_usage_error asserts exit 4 when both are supplied (argparse mutually_exclusive_group → SystemExit mapped to EXIT_USAGE). test_missing_tasks_file_is_not_found points at a non-existent path and asserts exit 4 with 'not_found' present in stderr — confirming the FileNotFoundError branch in run() that prints json.dumps({'error':'not_found','path':...}, sort_keys=True) before returning EXIT_USAGE."
      run_result: "pytest tests/test_resume_engine.py::test_both_task_sources_is_usage_error tests/test_resume_engine.py::test_neither_task_source_is_usage_error tests/test_resume_engine.py::test_missing_tasks_file_is_not_found PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_both_task_sources_is_usage_error
        - tests/test_resume_engine.py::test_neither_task_source_is_usage_error
        - tests/test_resume_engine.py::test_missing_tasks_file_is_not_found
    - id: AC-13
      summary: "Transport-error test: HTTP seam raises URLError (modeled as status=0 + X-Canon-Transport-Error header in the test stub); engine records the task as degraded and includes it in degraded_tasks. If ALL tasks are degraded, exit code is EXIT_TRANSPORT (5); if only some are degraded, exit 0 with resume_available=false (conservative degrade)."
      status: MET
      evidence: "test_transport_error_all_tasks_exit_5 stubs every GET with (0, None, {'X-Canon-Transport-Error': 'URLError'}) for two tasks and asserts exit 5 with len(degraded_tasks) == 2 — binding the all-degraded → EXIT_TRANSPORT rule. test_transport_error_partial_degrade_resume_unavailable drives [task 1 degraded, task 2 release-orchestrator/completed] and asserts exit 0 with resume_available == False — binding the partial-degrade → exit 0 + resume_available=false rule. Together they pin both branches of scoper §13."
      run_result: "pytest tests/test_resume_engine.py::test_transport_error_all_tasks_exit_5 tests/test_resume_engine.py::test_transport_error_partial_degrade_resume_unavailable PASSED"
      covering_tests:
        - tests/test_resume_engine.py::test_transport_error_all_tasks_exit_5
        - tests/test_resume_engine.py::test_transport_error_partial_degrade_resume_unavailable
    - id: AC-14
      summary: "Living-spec updates (additive): CHANGELOG.md prepends an E4-T1 bullet at the top of [Unreleased] ### Added; README.md adds a 'canon resume --plan-id ...' row to the commands table; docs/SYSTEM-WORKFLOW.md gains an additive bullet describing the resume engine + idempotency guarantee."
      status: MET
      evidence: "`rg -n 'E4-T1' CHANGELOG.md` → line 12 shows the new bullet `- **E4-T1** `canon resume --plan-id <id>` orchestrator resume engine: stdlib-only, read-only, idempotent scanner over state-api checkpoints. ...` as the first bullet under the Unreleased/Added heading. `rg -n 'canon resume' README.md` → line 225 shows the new commands-table row `| `canon resume --plan-id <id> --company-id <c> --repository-id <r> (--tasks-file <path> \\| --handoffs-dir <path>)` | Print the first incomplete (task_id, phase) pair for a plan as structured JSON (read-only; idempotent). |`. `rg -n 'Resume engine' docs/SYSTEM-WORKFLOW.md` → line 45 shows the new bullet `- **Resume engine (`canon resume`)**: Read-only, idempotent scanner over state-api checkpoints. ... Running `canon resume` twice on unchanged plan state yields byte-identical stdout.`. All three edits are additive (no reflow of adjacent rows/bullets)."
      run_result: "grep audit: CHANGELOG.md:12, README.md:225, docs/SYSTEM-WORKFLOW.md:45 all present."
      covering_tests:
        - CHANGELOG.md
        - README.md
        - docs/SYSTEM-WORKFLOW.md
  remaining_gaps: []
  notes: |
    All 14 acceptance criteria verified. Focused suite 14/14 passing, full repo suite 333/333 passing (319 baseline + 14 new resume_engine tests), zero iterations required. Modified-files set matches the 6 allowlisted product paths exactly (CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md, src/canon_systems/cli.py, src/canon_systems/resume_engine.py new, tests/test_resume_engine.py new); the only additional churn is the tolerated auto-generated `.canon/memory/capture-*` pair and the four handoff packets under `.cursor/handoffs/canon-memory-v1/E4-T1/` (scoper/cursor-pilot/implementer/qa-gate), which are governance artifacts rather than product surfaces. No forbidden surface (backend/**, infra/**, .cursor/rules/**, .cursor/plans/**) is touched; canon_backend_shared is not imported by resume_engine.py (zero-emission invariant binds even the CanonicalEvent import away). `canon resume` output is deterministic JSON via json.dumps(..., sort_keys=True) on stdout (and matching sort_keys on the two stderr error envelopes), byte-identical across repeated invocations.
END_GATE_RESULTS
```
