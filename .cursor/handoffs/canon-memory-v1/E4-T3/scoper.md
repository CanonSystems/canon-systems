# E4-T3 Scoper Packet — Stall watchdog + unblock event

## SCOPE_SUMMARY

E4-T3 ships `canon stall-watchdog scan`: a stdlib-only, monkeypatchable, **read-only-probe** CLI that scans a fixed list of `(task_id, workstream_id)` pairs (via `--tasks-file <path>` or `--handoffs-dir <path>` mirroring E4-T1), probes each target with `GET /state/checkpoint`, classifies any response whose nested `lease.expires_at <= now_epoch` as **STALLED**, and emits one canonical event per stall (`event_type = "lease_stall_detected"`) to an NDJSON event log (default `.canon/memory/events.ndjson`, overridable with `--event-log <path>`). The event payload carries `diagnostic` evidence plus a `suggested_next_step` copy-pasteable command sourced by importing `_resolution_hint("lease_held")` from `checkpoint_cli` (single source of truth, zero drift). Tests (`tests/test_stall_watchdog.py`, ≥13 cases) exercise the simulated-stall scenario, probe-owner-identity, degradation, and the `--dry-run` stderr NDJSON short-circuit — all against a monkeypatched `_http_request` seam; zero live state-api, zero `backend/**` edits, `CanonicalEvent` imported (never redefined) per Wave-3 discipline.

**Critical scoping correction vs. the parent task brief:** the brief suggested probing with `POST /state/lease/acquire` and examining 409 bodies. Reading `backend/state-api/state_api/leases.py:60` + `models.py:item_has_live_lease` shows this is unsound: the server treats `expires_at <= now_epoch` as *no live lease* and the acquire call **succeeds with 200**, silently stealing the expired token and destroying the stall evidence. The scoper decision is to use **GET /state/checkpoint** instead, because `models.lease_from_item()` returns the `LeaseInfo` block (with `expires_at`) regardless of live-ness — giving us a pure, idempotent, side-effect-free stall classifier that also aligns with `resume_engine._scan_task` (GET-only seam). See §Decisions below.

## SCOPE_PACKET

### Identifiers

- `handoff_id`: `handoff_20260423_e4t3_stall_watchdog`
- `company_id`: `IMC`
- `repository_id`: `innermost`
- `plan_id`: `canon-memory-v1`
- `task_id`: `E4-T3`
- `wave`: `4`
- `parallel_group`: `wave-4b`
- `branch`: `wave/4/canon-memory-v1` (tip `e4daacf` = post-E4-T2 merge)
- `depends_on`: `E4-T2`

### Story

- **title**: "Stall watchdog + unblock event"
- **userValue**: "Operators (and the release-orchestrator) can run a single idempotent command to detect any scoped task whose lease has expired without a clean release, producing a structured `lease_stall_detected` canonical event whose payload names the stale owner and a copy-pasteable command to unblock."

### Acceptance criteria (13)

1. New module `src/canon_systems/stall_watchdog.py` exposing `run(argv: list[str] | None) -> int` and `main() -> None`, stdlib-only (`argparse`, `json`, `os`, `pathlib`, `socket`, `sys`, `urllib.error`, `urllib.request`, `urllib.parse`, `time`, `uuid`, `datetime`). No new third-party imports; `CanonicalEvent` imported verbatim from `canon_backend_shared.events` (Wave-3 discipline).
2. `canon stall-watchdog scan` subcommand wired in `src/canon_systems/cli.py` using the REMAINDER pattern (additive only — mirrors the existing `resume` block and dispatch). The `import` goes next to the other `run as run_*` imports. No edits to any other cli.py region.
3. Flags (all required unless noted): `--company-id`, `--repository-id`, `--plan-id` (required), exactly one of `--tasks-file <path>` | `--handoffs-dir <path>` (mutually exclusive, required), `--workstream-id-default` (default `ws-main`), `--base-url` (default env `CANON_STATE_API_URL` or `http://localhost:8080`), `--timeout-ms` (default `10000`, clamp `100..60000`), `--event-log <path>` (default `.canon/memory/events.ndjson`), `--dry-run` (flag; when set, emit would-be events to stderr as NDJSON and DO NOT open/append to the event log), `--probe-owner-suffix <str>` (default `canon-stall-watchdog`; reserved for future acquire-probe convention, plumbed through but unused by GET probe).
4. Task discovery reuses E4-T1 conventions verbatim: `_load_tasks_from_file` (JSON array of `{task_id, workstream_id?}` objects; missing `workstream_id` falls back to `--workstream-id-default`) and `_load_tasks_from_handoffs` (regex `^E\d+-T\d+$` subdir scan).
5. **Probe mechanism = `GET /state/checkpoint`**. Per-task scan steps: 200+`lease.expires_at<=now_epoch` → STALLED (capture stale_owner, expires_at_utc, ttl_remaining_s); 200+no-lease OR live lease → not stalled; 404 → not stalled; status 0 (transport) or 5xx or non-enumerated → degraded.
6. **`event_type = "lease_stall_detected"`**. Event constructed via helper `build_lease_stall_event(...) -> CanonicalEvent` mirroring `retrieval_telemetry.build_retrieval_breakdown_event` shape. Fixed values: `agent_name="canon-stall-watchdog"`, `agent_run_id="run-"+uuid.uuid4().hex[:16]`, `actor_id=""`, `handoff_id=""`, `model=""`, `parent_event_id=""`, `state_version=0`, `timestamp=observed_at_utc` (RFC3339Z), `event_id="ev-"+uuid.uuid4().hex`.
7. **Event payload** shape:
   ```
   {
     "diagnostic": {
       "task_id": "<id>", "workstream_id": "<ws>",
       "stale_owner_agent_run_id": "<...>",
       "expires_at_utc": "<RFC3339Z>",
       "observed_at_utc": "<RFC3339Z>",
       "ttl_remaining_s": <int, negative means expired>
     },
     "suggested_next_step": {"message": "...", "command": "canon checkpoint lease-acquire ..."}
   }
   ```
   `suggested_next_step` sourced verbatim by `from canon_systems.checkpoint_cli import _resolution_hint` → `_resolution_hint("lease_held")`. No duplication.
8. **Event persistence**: default append to `.canon/memory/events.ndjson` (auto-create parent dir; do not truncate); `--event-log` overrides; `--dry-run` writes NDJSON to stderr instead (no filesystem mutation); I/O failure → degraded with `reason="event_log_write"` → exit 5.
9. **stdout envelope** (JSON, sort_keys=True):
   ```
   {
     "plan_id": "...", "company_id": "...", "repository_id": "...",
     "tasks_scanned": N, "stalls_detected": N, "events_emitted": N,
     "event_log_path": "<resolved path or '(stderr dry-run)'>",
     "degraded_tasks": [{"task_id": "...", "reason": "transport|http_5xx|event_log_write"}]
   }
   ```
10. **Exit codes**: `0` clean scan; `4` usage errors; `5` **any** degraded probe OR event-log write failure (stricter than E4-T1 by design — document delta in module docstring). No `3` (404 on checkpoint is not-an-error).
11. **Canonical-event discipline compliance**: `CanonicalEvent` imported from `canon_backend_shared.events`, never re-declared. Source-scan regression test asserts `class CanonicalEvent` NOT in module and `from canon_backend_shared.events import CanonicalEvent` IS.
12. **Tests** (`tests/test_stall_watchdog.py`, ≥13 cases; new file only — no edits to any existing test file). All tests monkeypatch `canon_systems.stall_watchdog._http_request`. Required cases:
    1. `test_scan_single_stalled_task_emits_one_event`
    2. `test_scan_live_lease_emits_no_event`
    3. `test_scan_no_lease_emits_no_event`
    4. `test_scan_404_not_stalled_not_degraded`
    5. `test_scan_transport_error_degrades` (exit 5)
    6. `test_scan_5xx_degrades` (exit 5, reason `http_500`)
    7. `test_done_signal_simulated_stall` — Task A stalled + Task B live; exactly one event for A. **Backlog done_signal.**
    8. `test_dry_run_writes_to_stderr_not_file`
    9. `test_event_log_default_path_appends`
    10. `test_tasks_file_and_handoffs_dir_mutually_exclusive`
    11. `test_handoffs_dir_discovers_e_t_subdirs`
    12. `test_canonical_event_import_not_redefined`
    13. `test_cli_wiring_passes_args_to_subcommand`
13. **Living-spec additive edits** (zero reflow): CHANGELOG top-of-Unreleased (above E4-T2 bullet); README new CLI table row after `canon resume`; `docs/SYSTEM-WORKFLOW.md` §3 bullet. No edits to templates or runbooks (E4-T4 scope).

### Decisions (scoper-made)

1. **Probe mechanism = `GET /state/checkpoint`** (NOT acquire-probe). `models.item_has_live_lease` treats `expires_at<=now_epoch` as *no live lease* → `POST /state/lease/acquire` on a stalled lease **succeeds with 200**, silently stealing the token and destroying the stall evidence. GET is pure, idempotent, side-effect-free; `lease_from_item` returns `LeaseInfo` unconditionally when `lease_token` is set, so expired `expires_at` is visible verbatim.
2. **Event type = `"lease_stall_detected"`** (NOT `"unblock_suggested"`). Observation-form noun-phrase matches existing canonical types (`retrieval_breakdown`, `checkpoint_write`); `suggested_next_step` inside `payload` carries the action wording.
3. **`_resolution_hint` = imported from `checkpoint_cli`** (intra-package underscore-prefixed import; documented as intentional cross-module private import). Zero duplication; single source of truth.
4. **Exit-code on any partial degradation = 5** (stricter than E4-T1): a missed probe could hide the actual stall; safety story differs from resume-target.
5. **Default event-log path = `.canon/memory/events.ndjson`**. Aligned with `.canon/memory/` runtime artifacts; NDJSON matches `report_cli._load_events`; enables Wave-6 telemetry aggregation.
6. **`--probe-owner-suffix` default `canon-stall-watchdog`**. Plumbed through but unused by GET probe in E4-T3; reserved for future acquire-diagnostic variant so a future scoper does not re-debate it.

### Forbidden surfaces

- `backend/**` (READ-ONLY; `CanonicalEvent` importable and REQUIRED to be imported).
- `infra/**`
- `.cursor/rules/**`, `.cursor/plans/**`
- `src/canon_systems/*.py` other than `cli.py` (additive only) and the NEW `stall_watchdog.py`.
- `src/canon_systems/templates/**` (E4-T4 owns template/runbook wiring).
- Any existing `tests/*.py` file (only new `tests/test_stall_watchdog.py`).
- `docs/runbooks/**` (E4-T4).
- Live AWS / docker-compose.

### Repository
- primaryLanguages: Python 3.11+ (stdlib-only new module).
- testFramework: pytest.
- relevantFiles:
  - Create: `src/canon_systems/stall_watchdog.py`, `tests/test_stall_watchdog.py`.
  - Modify (additive): `src/canon_systems/cli.py` (3 insertion points), `CHANGELOG.md`, `README.md`, `docs/SYSTEM-WORKFLOW.md`.
  - Read-only reference: `src/canon_systems/{resume_engine,checkpoint_cli,retrieval_telemetry}.py`, `backend/shared/canon_backend_shared/events.py`, `backend/state-api/state_api/{leases,models}.py`.

### Constraints
- dependencies: `E4-T2` (imports `_resolution_hint`); `E3-T5` (event-emission pattern); `E4-T1` (CLI shape + discovery).
- mustNotBreak:
  - 350-test baseline (tip `e4daacf`); target ≥362 after E4-T3.
  - All existing `canon *` subcommands unchanged.
  - `_resolution_hint` return shape (read-only consumption).
  - Wave-3 canonical-event single-source discipline.
  - Wave-4 no-live-state-api waiver.

### Prior work references
- peer:`src/canon_systems/resume_engine.py` — CLI shape + `_http_request` seam + task discovery + exit codes.
- peer:`src/canon_systems/checkpoint_cli.py` — `_resolution_hint` import target + lease HTTP shape.
- peer:`src/canon_systems/retrieval_telemetry.py` — canonical-event emitter pattern.
- peer:`src/canon_systems/cli.py` — REMAINDER subparser wiring at `cli.py:16` / `:311-318` / `:525-532`.
- backend:`backend/state-api/state_api/leases.py` + `models.py` — probe-semantics evidence for the GET-probe decision (acquire-on-expired succeeds).
- peer:`.cursor/handoffs/canon-memory-v1/E4-T1/scoper.md` — discovery-flag + exit-code precedent.
- peer:`.cursor/handoffs/canon-memory-v1/E4-T2/scoper.md` — packet-format precedent.

### ac_traceability

| # | Criterion | Target | Test |
|---|---|---|---|
| 1 | New module run/main | `stall_watchdog.py::run/main` | `test_scan_single_stalled_task_emits_one_event` |
| 2 | cli.py additive wiring | `cli.py` 3 insertion points | `test_cli_wiring_passes_args_to_subcommand` |
| 3 | Full flag surface | `stall_watchdog.py::_build_parser` | `test_tasks_file_and_handoffs_dir_mutually_exclusive`, `test_dry_run_writes_to_stderr_not_file` |
| 4 | E4-T1-style discovery | `_load_tasks_from_file/_handoffs` | `test_handoffs_dir_discovers_e_t_subdirs` |
| 5 | GET-probe classifier | `_scan_task`, `_classify_probe` | `test_scan_single_stalled_task_emits_one_event`, `::_live_lease`, `::_no_lease`, `::_404_not_stalled`, `::_transport_degrades`, `::_5xx_degrades` |
| 6 | event_type + helper shape | `build_lease_stall_event` | `test_scan_single_stalled_task_emits_one_event` |
| 7 | Payload shape | `build_lease_stall_event` payload | `test_scan_single_stalled_task_emits_one_event` |
| 8 | Event persistence + dry-run | `_emit_event`, `_resolve_event_log_path` | `test_event_log_default_path_appends`, `test_dry_run_writes_to_stderr_not_file` |
| 9 | stdout envelope | `_build_envelope` | `test_scan_single_stalled_task_emits_one_event` |
| 10 | Exit codes 0/4/5 | `run` | `test_scan_transport_error_degrades`, `test_tasks_file_and_handoffs_dir_mutually_exclusive`, `test_scan_single_stalled_task_emits_one_event` |
| 11 | CanonicalEvent not redefined | source-level | `test_canonical_event_import_not_redefined` |
| 12 | Simulated-stall done_signal | full loop | `test_done_signal_simulated_stall` |
| 13 | Living-spec additive edits | CHANGELOG/README/SYSTEM-WORKFLOW | QA flow-audit diff/content checks |

### DoR checklist
- repo_ref_verification: **pass**
- ac_traceability: **pass**
- prior_work_references: **pass**

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E4-T3 ships canon stall-watchdog scan: stdlib-only CLI probing state-api via GET /state/checkpoint (NOT acquire-probe — server silently steals expired leases on acquire), classifies lease.expires_at<=now_epoch as STALLED, emits lease_stall_detected canonical event per stall to .canon/memory/events.ndjson with suggested_next_step from _resolution_hint('lease_held'). New module stall_watchdog.py + tests/test_stall_watchdog.py (≥13 cases) + additive cli.py REMAINDER wiring. Zero backend edits; CanonicalEvent imported. Exit 5 on any degraded probe."
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260423_e4t3_stall_watchdog"
      task_id: "E4-T3"
      wave: 4
      branch: "wave/4/canon-memory-v1"
    story:
      title: "Stall watchdog + unblock event"
      acceptanceCriteria:
        - "New src/canon_systems/stall_watchdog.py stdlib-only; imports CanonicalEvent from canon_backend_shared.events."
        - "cli.py additive REMAINDER wiring for `canon stall-watchdog scan`."
        - "Full flag surface incl. --tasks-file/--handoffs-dir (mutually exclusive), --event-log, --dry-run, --probe-owner-suffix."
        - "E4-T1-style task discovery."
        - "Probe = GET /state/checkpoint. 200+lease.expires_at<=now→STALLED; 200 no-lease/live→not stalled; 404→not stalled; transport/5xx→degraded."
        - "event_type='lease_stall_detected'; build_lease_stall_event mirrors retrieval_telemetry pattern."
        - "Payload {diagnostic, suggested_next_step} with suggested_next_step = _resolution_hint('lease_held') imported from checkpoint_cli."
        - "Event persistence: default .canon/memory/events.ndjson append; --event-log override; --dry-run → stderr NDJSON (no fs mutation)."
        - "stdout envelope JSON sort_keys with tasks_scanned/stalls_detected/events_emitted/event_log_path/degraded_tasks."
        - "Exit: 0 clean; 4 usage; 5 any degraded probe or event-log write failure."
        - "≥13 tests in tests/test_stall_watchdog.py monkeypatching _http_request."
        - "CanonicalEvent imported never redefined (source-scan test)."
        - "Additive CHANGELOG top-of-Unreleased + README CLI row + SYSTEM-WORKFLOW §3 bullet."
    constraints:
      dependencies: ["E4-T2", "E3-T5", "E4-T1"]
      mustNotBreak:
        - "350-test baseline"
        - "all existing canon subcommands"
        - "_resolution_hint return shape"
        - "Wave-3 CanonicalEvent single source"
        - "Wave-4 no-live-state-api"
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
      prior_work_references: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
