# E4-T1 implementer handoff

```
HANDOFF_TO_QA
  handoff_id: handoff_20260422_e4t1_resume_engine
  branch: wave/4/canon-memory-v1
  files_modified:
    - src/canon_systems/resume_engine.py
    - tests/test_resume_engine.py
    - src/canon_systems/cli.py
    - CHANGELOG.md
    - README.md
    - docs/SYSTEM-WORKFLOW.md
  acceptance_criteria:
    - id: AC1
      criterion: "resume_engine: stdlib-only read-only run(); stdout is json.dumps(..., sort_keys=True); no writes except stdio; API surface (PHASE_ORDER, _http_request, _resolve_base_url, _load_tasks_from_file, _load_tasks_from_handoffs, _first_incomplete_phase, _scan_task, _compute_resume_target, _build_envelope, _build_parser, run, main) and exit constants EXIT_OK/EXIT_NOT_FOUND/EXIT_USAGE/EXIT_TRANSPORT"
      status: MET
      evidence: "New module implements GET checkpoint scanning and envelope; run() only prints JSON to stdout and JSON errors to stderr"
      run_result: "pytest tests/test_resume_engine.py -q: 14 passed; pytest -q: 333 passed"
      covering_tests:
        - tests/test_resume_engine.py::test_output_envelope_keys_sorted
        - tests/test_resume_engine.py::test_idempotent_byte_equal_on_double_invocation
    - id: AC2
      criterion: "CLI: import run_resume_engine; resume subparser with REMAINDER; dispatch args.command == resume to run_resume_engine"
      status: MET
      evidence: "cli.py additive import after report_cli; resume_parser after report_parser; dispatch after report block"
      run_result: "pytest -q: 333 passed; python3 -m canon_systems.cli resume --help exited 0"
      covering_tests:
        - tests/test_resume_engine.py::test_resume_cli_help_returns_0
    - id: AC3
      criterion: "Mutually exclusive --tasks-file vs --handoffs-dir required; both or neither → exit 4 (EXIT_USAGE)"
      status: MET
      evidence: "argparse mutually_exclusive_group; SystemExit mapped to EXIT_USAGE in run()"
      run_result: "pytest tests/test_resume_engine.py -q: 14 passed"
      covering_tests:
        - tests/test_resume_engine.py::test_both_task_sources_is_usage_error
        - tests/test_resume_engine.py::test_neither_task_source_is_usage_error
    - id: AC4
      criterion: "Missing --tasks-file path: stderr JSON with not_found, exit 4"
      status: MET
      evidence: "FileNotFoundError from Path.read_text; stderr {\"error\": \"not_found\", \"path\": ...}"
      run_result: "pytest tests/test_resume_engine.py::test_missing_tasks_file_is_not_found: passed"
      covering_tests:
        - tests/test_resume_engine.py::test_missing_tasks_file_is_not_found
    - id: AC5
      criterion: "First resumable task in list order (non-degraded scans only): A qa-gate completed then B implementer in progress (B listed first) → resume_target B at implementer"
      status: MET
      evidence: "Monkeypatched _http_request returns canned 200 bodies; _compute_resume_target ignores degraded entries only (first incomplete among valid scans)"
      run_result: "pytest tests/test_resume_engine.py::test_resume_target_first_incomplete_phase: passed"
      covering_tests:
        - tests/test_resume_engine.py::test_resume_target_first_incomplete_phase
    - id: AC6
      criterion: "All tasks at release-orchestrator completed → resume_target null, resume_available false, exit 0"
      status: MET
      evidence: "Envelope from _build_envelope; _first_incomplete_phase returns None for terminal completed state"
      run_result: "pytest tests/test_resume_engine.py::test_resume_target_none_when_all_complete: passed"
      covering_tests:
        - tests/test_resume_engine.py::test_resume_target_none_when_all_complete
    - id: AC7
      criterion: "404 checkpoint → treat as no phase; first incomplete phase scoper"
      status: MET
      evidence: "_scan_task returns (None, None, None) for 404; _first_incomplete_phase(None, None) → scoper"
      run_result: "pytest tests/test_resume_engine.py::test_resume_missing_checkpoint_points_to_scoper: passed"
      covering_tests:
        - tests/test_resume_engine.py::test_resume_missing_checkpoint_points_to_scoper
    - id: AC8
      criterion: "A fully complete (release-orchestrator completed); B cursor-pilot completed → next phase implementer for B"
      status: MET
      evidence: "Sequential _http_request stubs; second task selected after first returns fully complete"
      run_result: "pytest tests/test_resume_engine.py::test_crash_restart_scenario_task_b_cursor_pilot: passed"
      covering_tests:
        - tests/test_resume_engine.py::test_crash_restart_scenario_task_b_cursor_pilot
    - id: AC9
      criterion: "Idempotency: two run() with same argv and same stub → identical stdout bytes"
      status: MET
      evidence: "test captures capsys.readouterr twice"
      run_result: "pytest tests/test_resume_engine.py::test_idempotent_byte_equal_on_double_invocation: passed"
      covering_tests:
        - tests/test_resume_engine.py::test_idempotent_byte_equal_on_double_invocation
    - id: AC10
      criterion: "No CanonicalEvent, event_type, or emit_event literals in resume_engine.py source (static test)"
      status: MET
      evidence: "test_no_event_emission_in_module_source reads __file__ text"
      run_result: "pytest tests/test_resume_engine.py::test_no_event_emission_in_module_source: passed"
      covering_tests:
        - tests/test_resume_engine.py::test_no_event_emission_in_module_source
    - id: AC11
      criterion: "All tasks transport-degraded → exit 5; envelope includes degraded_tasks for each task"
      status: MET
      evidence: "status 0 from _http_request → degrade transport; all_degraded path returns EXIT_TRANSPORT"
      run_result: "pytest tests/test_resume_engine.py::test_transport_error_all_tasks_exit_5: passed"
      covering_tests:
        - tests/test_resume_engine.py::test_transport_error_all_tasks_exit_5
    - id: AC12
      criterion: "Partial transport: one task degraded, one fully complete → exit 0, resume_available false, no resume_target from incomplete stub data"
      status: MET
      evidence: "Degraded scans skipped in _compute_resume_target; remaining task complete yields null target; resume_available false"
      run_result: "pytest tests/test_resume_engine.py::test_transport_error_partial_degrade_resume_unavailable: passed"
      covering_tests:
        - tests/test_resume_engine.py::test_transport_error_partial_degrade_resume_unavailable
    - id: AC13
      criterion: "--handoffs-dir: only E<N>-T<N> subdirectories (regex), sorted; default workstream for entries"
      status: MET
      evidence: "_load_tasks_from_handoffs filters dirs; test uses E4-T1, E4-T2, other"
      run_result: "pytest tests/test_resume_engine.py::test_handoffs_dir_discovery: passed"
      covering_tests:
        - tests/test_resume_engine.py::test_handoffs_dir_discovery
    - id: AC14
      criterion: "CHANGELOG prepended (E4-T1); README commands table row; docs/SYSTEM-WORKFLOW.md §3 bullet for resume engine"
      status: MET
      evidence: "Additive text per cursor-pilot strings"
      run_result: "File inspection; full suite 333 passed"
      covering_tests:
        - tests/test_resume_engine.py
  suite_result:
    focused: "pytest tests/test_resume_engine.py -q: 14 passed in 0.03s"
    full: "pytest -q: 333 passed in 4.34s"
```
