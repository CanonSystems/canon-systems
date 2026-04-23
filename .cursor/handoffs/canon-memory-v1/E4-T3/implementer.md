# E4-T3 implementer handoff

```yaml
HANDOFF_TO_QA:
  handoff_id: handoff_20260423_e4t3_stall_watchdog
  task_id: E4-T3
  branch: wave/4/canon-memory-v1
  files_modified:
    - src/canon_systems/stall_watchdog.py
    - tests/test_stall_watchdog.py
    - src/canon_systems/cli.py
    - CHANGELOG.md
    - README.md
    - docs/SYSTEM-WORKFLOW.md
  acceptance_criteria:
    - id: AC-01
      summary: Stall watchdog module — GET /state/checkpoint probe, lease_stall_detected CanonicalEvent, _resolution_hint import, exit 0/4/5
      status: MET
      evidence: src/canon_systems/stall_watchdog.py implements spec; CanonicalEvent from canon_backend_shared.events; suggested_next_step from checkpoint_cli._resolution_hint
      run_result: pytest tests/test_stall_watchdog.py -q — 13 passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_single_stalled_task_emits_one_event
    - id: AC-02
      summary: Live lease (expires_at > now) — no event, exit 0
      status: MET
      evidence: test_scan_live_lease_emits_no_event
      run_result: pytest tests/test_stall_watchdog.py::test_scan_live_lease_emits_no_event -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_live_lease_emits_no_event
    - id: AC-03
      summary: No lease (null / non-dict) — not stalled, exit 0
      status: MET
      evidence: test_scan_no_lease_emits_no_event
      run_result: pytest tests/test_stall_watchdog.py::test_scan_no_lease_emits_no_event -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_no_lease_emits_no_event
    - id: AC-04
      summary: HTTP 404 — not stalled, not degraded
      status: MET
      evidence: test_scan_404_not_stalled_not_degraded
      run_result: pytest tests/test_stall_watchdog.py::test_scan_404_not_stalled_not_degraded -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_404_not_stalled_not_degraded
    - id: AC-05
      summary: Transport failure (status 0) — degraded, exit 5
      status: MET
      evidence: test_scan_transport_error_degrades
      run_result: pytest tests/test_stall_watchdog.py::test_scan_transport_error_degrades -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_transport_error_degrades
    - id: AC-06
      summary: HTTP 5xx — degraded, exit 5
      status: MET
      evidence: test_scan_5xx_degrades
      run_result: pytest tests/test_stall_watchdog.py::test_scan_5xx_degrades -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_5xx_degrades
    - id: AC-07
      summary: Multi-task scan — stalled then live yields one event for stalled task only
      status: MET
      evidence: test_done_signal_simulated_stall
      run_result: pytest tests/test_stall_watchdog.py::test_done_signal_simulated_stall -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_done_signal_simulated_stall
    - id: AC-08
      summary: --dry-run writes NDJSON to stderr, no filesystem event log, events_emitted 0
      status: MET
      evidence: test_dry_run_writes_to_stderr_not_file
      run_result: pytest tests/test_stall_watchdog.py::test_dry_run_writes_to_stderr_not_file -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_dry_run_writes_to_stderr_not_file
    - id: AC-09
      summary: Default --event-log path appends across sequential runs
      status: MET
      evidence: test_event_log_default_path_appends
      run_result: pytest tests/test_stall_watchdog.py::test_event_log_default_path_appends -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_event_log_default_path_appends
    - id: AC-10
      summary: --tasks-file and --handoffs-dir mutually exclusive → exit 4
      status: MET
      evidence: test_tasks_file_and_handoffs_dir_mutually_exclusive
      run_result: pytest tests/test_stall_watchdog.py::test_tasks_file_and_handoffs_dir_mutually_exclusive -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_tasks_file_and_handoffs_dir_mutually_exclusive
    - id: AC-11
      summary: --handoffs-dir discovers only E<N>-T<N> subdirectories
      status: MET
      evidence: test_handoffs_dir_discovers_e_t_subdirs
      run_result: pytest tests/test_stall_watchdog.py::test_handoffs_dir_discovers_e_t_subdirs -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_handoffs_dir_discovers_e_t_subdirs
    - id: AC-12
      summary: CanonicalEvent imported from canon_backend_shared.events, not redefined in module
      status: MET
      evidence: test_canonical_event_import_not_redefined source scan
      run_result: pytest tests/test_stall_watchdog.py::test_canonical_event_import_not_redefined -q — passed
      covering_tests:
        - tests/test_stall_watchdog.py::test_canonical_event_import_not_redefined
    - id: AC-13
      summary: Top-level canon stall-watchdog REMAINDER dispatches to stall_watchdog.run
      status: MET
      evidence: cli.py additive import, subparser, dispatch; test_cli_wiring_passes_args_to_subcommand
      run_result: pytest tests/test_stall_watchdog.py::test_cli_wiring_passes_args_to_subcommand -q — passed; python3 -m canon_systems.cli stall-watchdog scan --help — exit 0
      covering_tests:
        - tests/test_stall_watchdog.py::test_cli_wiring_passes_args_to_subcommand
  suite_result:
    focused: 13 passed in 0.04s (tests/test_stall_watchdog.py)
    full: 363 passed in 4.23s (repo root pytest -q)
END_HANDOFF_TO_QA
```
