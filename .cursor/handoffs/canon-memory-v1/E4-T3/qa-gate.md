# E4-T3 QA Gate Packet — Stall watchdog + unblock event

## Verification summary

- Focused suite: `pytest tests/test_stall_watchdog.py -q` → `13 passed in 0.04s` (target ≥13 MET; every AC mapped to a covering test node ID).
- Full suite:    `pytest -q`                               → `363 passed in 3.88s` (baseline 350 + 13 new; exceeds ≥362 target).
- Spot-checks:
  - `rg -n "from canon_backend_shared.events import CanonicalEvent" src/canon_systems/stall_watchdog.py` → line 38 (verbatim import, Wave-3 discipline).
  - `rg -n "from .checkpoint_cli import _resolution_hint" src/canon_systems/stall_watchdog.py` → line 40 (single source of truth for `suggested_next_step`).
  - `rg -n "class CanonicalEvent" src/canon_systems/stall_watchdog.py` → no match (envelope type is never re-declared).
  - `rg -n "/state/lease/acquire|lease/acquire" src/canon_systems/stall_watchdog.py` → no match (GET-only probe; acquire-probe correctly rejected per scoper decision #1).
- Test surface: `rg -n "^def test_" tests/test_stall_watchdog.py` → 13 functions matching the ac_traceability table 1:1.

## Reconciliation

Changed surfaces (compared against `HANDOFF_TO_QA.files_modified`):

- `src/canon_systems/stall_watchdog.py` (new) — stdlib-only module implementing `run`, `main`, `_build_parser`, `_load_tasks_from_file`, `_load_tasks_from_handoffs`, `_scan_task`, `_classify_probe`, `build_lease_stall_event`, `_emit_event`, `_resolve_event_log_path`, `_build_envelope`. `CanonicalEvent` imported from `canon_backend_shared.events`; `_resolution_hint` imported from `canon_systems.checkpoint_cli`.
- `src/canon_systems/cli.py` — additive REMAINDER wiring: `from .stall_watchdog import run as run_stall_watchdog` import alongside peer imports; `stall-watchdog` subparser with REMAINDER capture; dispatch branch calling `run_stall_watchdog(remaining)`.
- `tests/test_stall_watchdog.py` (new) — 13 tests, all monkeypatching `canon_systems.stall_watchdog._http_request`; zero live network; zero sleeps.
- `CHANGELOG.md` — E4-T3 bullet prepended above E4-T2 in `[Unreleased] ### Added`.
- `README.md` — additive CLI table row for `canon stall-watchdog scan` after the `canon resume` row.
- `docs/SYSTEM-WORKFLOW.md` — additive §3 bullet describing GET-probe stall classifier + `lease_stall_detected` event.

No forbidden surface touched (no `backend/**`, no `infra/**`, no `.cursor/rules/**`, no `.cursor/plans/**`, no `src/canon_systems/*.py` other than `cli.py` and the new `stall_watchdog.py`, no template edits, no existing test file edits).

## Hardening checks

- Critical design decision (scoper §Decisions #1) held: module probes with `GET /state/checkpoint`, never `POST /state/lease/acquire`. Grep confirms zero occurrences of `lease/acquire` in the module body — the acquire-probe path is absent by construction.
- Canonical-event single-source discipline (Wave-3) held: `from canon_backend_shared.events import CanonicalEvent` present at line 38; no `class CanonicalEvent` anywhere in the module; `test_canonical_event_import_not_redefined` asserts both source-level facts.
- `_resolution_hint` is consumed, never duplicated: import at line 40; called inside `build_lease_stall_event` to populate `payload.suggested_next_step`.
- Exit-code contract (stricter than E4-T1 by design): 0 clean scan; 4 usage (mutually-exclusive discovery flags); 5 any degraded probe or event-log write failure. All three paths exercised by tests.
- Dry-run path asserted side-effect-free: `test_dry_run_writes_to_stderr_not_file` confirms no filesystem mutation when `--dry-run` is set.

```
GATE_RESULTS
  handoff_id: "handoff_20260423_e4t3_stall_watchdog"
  task_id: "E4-T3"
  verdict: PASS
  regression_checked: true
  iterations: 0
  suite_result: "focused: 13 passed in 0.04s; full: 363 passed in 3.88s"
  acceptance_criteria:
    - id: AC-01
      summary: "New src/canon_systems/stall_watchdog.py exposes run(argv)->int and main()->None; stdlib-only; CanonicalEvent imported verbatim from canon_backend_shared.events."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_single_stalled_task_emits_one_event
        - tests/test_stall_watchdog.py::test_canonical_event_import_not_redefined
      run_result: "pass — module executes end-to-end; source-scan confirms stdlib-only plus the required CanonicalEvent import."
    - id: AC-02
      summary: "canon stall-watchdog scan subcommand wired in src/canon_systems/cli.py using the REMAINDER pattern (additive only)."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_cli_wiring_passes_args_to_subcommand
      run_result: "pass — top-level canon stall-watchdog scan dispatch reaches stall_watchdog.run with captured REMAINDER args."
    - id: AC-03
      summary: "Flag surface: --company-id, --repository-id, --plan-id, mutually exclusive --tasks-file | --handoffs-dir, --workstream-id-default=ws-main, --base-url (env CANON_STATE_API_URL or http://localhost:8080), --timeout-ms (default 10000, clamp 100..60000), --event-log (default .canon/memory/events.ndjson), --dry-run, --probe-owner-suffix=canon-stall-watchdog."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_tasks_file_and_handoffs_dir_mutually_exclusive
        - tests/test_stall_watchdog.py::test_dry_run_writes_to_stderr_not_file
      run_result: "pass — mutual exclusion exits 4; --dry-run flag short-circuits to stderr NDJSON as specified."
    - id: AC-04
      summary: "Task discovery reuses E4-T1 conventions: _load_tasks_from_file (JSON array of {task_id, workstream_id?}) and _load_tasks_from_handoffs (regex ^E\\d+-T\\d+$ subdir scan)."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_handoffs_dir_discovers_e_t_subdirs
      run_result: "pass — only E<N>-T<N> subdirectories are enumerated; non-matching siblings are ignored."
    - id: AC-05
      summary: "Probe = GET /state/checkpoint. 200+lease.expires_at<=now_epoch -> STALLED (capture stale_owner, expires_at_utc, ttl_remaining_s); 200+no-lease or live lease -> not stalled; 404 -> not stalled; status 0 (transport) or 5xx -> degraded."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_single_stalled_task_emits_one_event
        - tests/test_stall_watchdog.py::test_scan_live_lease_emits_no_event
        - tests/test_stall_watchdog.py::test_scan_no_lease_emits_no_event
        - tests/test_stall_watchdog.py::test_scan_404_not_stalled_not_degraded
        - tests/test_stall_watchdog.py::test_scan_transport_error_degrades
        - tests/test_stall_watchdog.py::test_scan_5xx_degrades
      run_result: "pass — all five classifier branches exercised deterministically; zero calls to /state/lease/acquire (grep-verified)."
    - id: AC-06
      summary: "event_type = 'lease_stall_detected'; build_lease_stall_event(...) -> CanonicalEvent mirrors retrieval_telemetry.build_retrieval_breakdown_event shape with fixed agent_name='canon-stall-watchdog', synthetic agent_run_id/event_id, RFC3339Z timestamp."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_single_stalled_task_emits_one_event
      run_result: "pass — emitted event carries event_type 'lease_stall_detected' plus the mandated agent_name and id shapes."
    - id: AC-07
      summary: "Event payload = {diagnostic:{task_id, workstream_id, stale_owner_agent_run_id, expires_at_utc, observed_at_utc, ttl_remaining_s}, suggested_next_step:{message, command}} with suggested_next_step sourced verbatim from checkpoint_cli._resolution_hint('lease_held')."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_single_stalled_task_emits_one_event
      run_result: "pass — payload.diagnostic carries all six required keys; payload.suggested_next_step equals _resolution_hint('lease_held') output; zero duplication."
    - id: AC-08
      summary: "Event persistence: default append to .canon/memory/events.ndjson (auto-create parent dir, no truncation); --event-log overrides; --dry-run writes NDJSON to stderr with no filesystem mutation; I/O failure -> degraded reason=event_log_write -> exit 5."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_event_log_default_path_appends
        - tests/test_stall_watchdog.py::test_dry_run_writes_to_stderr_not_file
      run_result: "pass — sequential runs append rather than truncate; --dry-run produces stderr NDJSON only and leaves the event log absent."
    - id: AC-09
      summary: "stdout envelope JSON (sort_keys=True) includes plan_id, company_id, repository_id, tasks_scanned, stalls_detected, events_emitted, event_log_path, degraded_tasks[]."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_single_stalled_task_emits_one_event
        - tests/test_stall_watchdog.py::test_dry_run_writes_to_stderr_not_file
      run_result: "pass — envelope keys pinned and sorted; event_log_path resolves to absolute path in normal mode and '(stderr dry-run)' under --dry-run."
    - id: AC-10
      summary: "Exit codes: 0 clean; 4 usage (mutex flags); 5 any degraded probe or event-log write failure. No 3 (404 is not-an-error)."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_single_stalled_task_emits_one_event
        - tests/test_stall_watchdog.py::test_tasks_file_and_handoffs_dir_mutually_exclusive
        - tests/test_stall_watchdog.py::test_scan_transport_error_degrades
        - tests/test_stall_watchdog.py::test_scan_5xx_degrades
        - tests/test_stall_watchdog.py::test_scan_404_not_stalled_not_degraded
      run_result: "pass — exit 0 on clean scan (stall found, event emitted, no degradation); exit 4 on flag mutex; exit 5 on transport and http_500 degradation; 404 classifies as not-stalled-not-degraded with exit 0."
    - id: AC-11
      summary: "CanonicalEvent imported from canon_backend_shared.events, never re-declared. Source-scan regression test pins both facts."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_canonical_event_import_not_redefined
      run_result: "pass — source scan confirms the required import at line 38 and zero 'class CanonicalEvent' occurrences in the module body."
    - id: AC-12
      summary: "≥13 deterministic tests in tests/test_stall_watchdog.py monkeypatching canon_systems.stall_watchdog._http_request; covers single-stall, live lease, no lease, 404, transport error, 5xx, multi-task simulated stall, --dry-run, default-path append, mutex flags, handoffs-dir discovery, CanonicalEvent discipline, CLI wiring."
      status: MET
      covering_tests:
        - tests/test_stall_watchdog.py::test_scan_single_stalled_task_emits_one_event
        - tests/test_stall_watchdog.py::test_scan_live_lease_emits_no_event
        - tests/test_stall_watchdog.py::test_scan_no_lease_emits_no_event
        - tests/test_stall_watchdog.py::test_scan_404_not_stalled_not_degraded
        - tests/test_stall_watchdog.py::test_scan_transport_error_degrades
        - tests/test_stall_watchdog.py::test_scan_5xx_degrades
        - tests/test_stall_watchdog.py::test_done_signal_simulated_stall
        - tests/test_stall_watchdog.py::test_dry_run_writes_to_stderr_not_file
        - tests/test_stall_watchdog.py::test_event_log_default_path_appends
        - tests/test_stall_watchdog.py::test_tasks_file_and_handoffs_dir_mutually_exclusive
        - tests/test_stall_watchdog.py::test_handoffs_dir_discovers_e_t_subdirs
        - tests/test_stall_watchdog.py::test_canonical_event_import_not_redefined
        - tests/test_stall_watchdog.py::test_cli_wiring_passes_args_to_subcommand
      run_result: "pass — 13 deterministic tests; zero live state-api calls; zero unmocked network; zero sleeps > 100ms."
    - id: AC-13
      summary: "Living-spec additive edits: CHANGELOG top-of-Unreleased (above E4-T2 bullet); README CLI row after canon resume; docs/SYSTEM-WORKFLOW.md §3 bullet. No templates/runbooks (E4-T4 scope)."
      status: MET
      covering_tests:
        - CHANGELOG.md
        - README.md
        - docs/SYSTEM-WORKFLOW.md
      run_result: "pass — additive diff confined to three doc files; E4-T3 bullet sits above E4-T2 in [Unreleased] ### Added; README gains one CLI row after canon resume; SYSTEM-WORKFLOW §3 gains one bullet."
  remaining_gaps: []
  notes: |
    All 13 acceptance criteria verified. Focused suite 13/13, full repo suite 363/363, zero QA-iteration fixes required. The critical scoper decision — probe via GET /state/checkpoint rather than POST /state/lease/acquire — is enforced at the source level (grep-verified zero acquire calls) and at the semantic level (five classifier branches mapped to distinct tests). Canonical-event single-source discipline (Wave-3) is preserved: CanonicalEvent is imported verbatim from canon_backend_shared.events and never re-declared, and _resolution_hint is consumed from checkpoint_cli so unblock wording has a single source of truth. Exit-code contract (0/4/5) is stricter than E4-T1 by design per scoper decision #4. No forbidden surface touched.
END_GATE_RESULTS
```
