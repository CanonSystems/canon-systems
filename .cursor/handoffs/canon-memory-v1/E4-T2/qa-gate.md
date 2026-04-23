# E4-T2 QA Gate Packet — Lease + versioning enforcement in CLI + templates

## Verification summary

- Focused suite: `pytest tests/test_checkpoint_concurrency.py -q` → `17 passed in 0.04s` (≥12 target MET; 17 deterministic tests covering the 12 ACs, including parametrize variants for the backward-compat matrix).
- Tripwire:      `pytest tests/test_cli_checkpoint.py -q`       → `52 passed in 0.18s` (E2-T3 coverage intact).
- Full suite:    `pytest -q`                                    → `350 passed in 4.44s` (baseline 333 + 17 new; exceeds ≥345 target).

## Reconciliation

Changed surfaces (compared against `HANDOFF_TO_QA.files_modified`):

- `src/canon_systems/checkpoint_cli.py` — `_RESOLUTION_HINTS` constant + `_resolution_hint()` helper appended after the exit-code constants; `resolution` object attached on all four 409 stderr paths.
- `src/canon_systems/templates/agents/implementer.md` — appended `### Conflict recovery (E4-T2)` subsection.
- `src/canon_systems/templates/agents/release-orchestrator.md` — appended pointer bullet to implementer.md conflict-recovery.
- `CHANGELOG.md` — E4-T2 bullet prepended above E4-T1 in `[Unreleased] ### Added`.
- `docs/SYSTEM-WORKFLOW.md` — additive §3 bullet describing lease + versioning enforcement.
- `tests/test_checkpoint_concurrency.py` (new) — 17 tests (14 distinct `test_*` functions; 3 additional parametrize expansions).
- `tests/test_cli_checkpoint.py` — **justified deviation**: one assertion in `test_write_409_state_version_conflict_unwraps_detail_exit_1` was narrowed from a strict 3-key dict equality (`assert j == {"error": "state_version_conflict", "expected": 7, "actual": 8}`) to four per-key assertions that preserve every original key/value equality (`j["error"] == "state_version_conflict"`, `j["expected"] == 7`, `j["actual"] == 8`) and additionally require `j["resolution"]["message"]` and `j["resolution"]["command"]` to be truthy. Diff is 1 deletion + 6 additions confined to that single function; no other E2-T3 test was altered. This is the minimum change required to carry the additive-stderr contract forward without dropping a behavioral guarantee.
- Scoper packet referenced `tests/test_checkpoint_cli.py`; the real file is `tests/test_cli_checkpoint.py` (a naming miss in the packet, not a forbidden-surface violation). The 52-test tripwire run confirms E2-T3 coverage is preserved.

## Hardening checks

- `rg -n '^def test_' tests/test_checkpoint_concurrency.py` → 14 functions, matching the ac_traceability table (17 total node IDs after parametrize expansion).
- `git diff tests/test_cli_checkpoint.py` → +6 / −1 inside a single test body; all original key/value equality preserved.
- `pytest tests/test_checkpoint_concurrency.py::test_backward_compat_existing_keys_preserved -q` (run as part of the 17) confirms every pre-existing stderr key is retained across all four 409 paths.

```
GATE_RESULTS
  handoff_id: "handoff_20260423_e4t2_lease_version_enforcement"
  task_id: "E4-T2"
  verdict: PASS
  regression_checked: true
  iterations: 0
  suite_result: "focused: 17 passed in 0.04s; tripwire: 52 passed in 0.18s; full: 350 passed in 4.44s"
  acceptance_criteria:
    - id: AC-1
      summary: "_resolution_hint(kind, scope=None) helper returns {message, command} pair keyed by fixed enum of 4 conflict kinds (state_version_conflict, lease_held, lease_denied, lease_expired); command string is a copy-pasteable canon checkpoint ... invocation using <placeholders>."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_resolution_hint_kinds_enum
      run_result: "pass — enum coverage of all 4 kinds plus the unknown-kind fallback asserted."
    - id: AC-2
      summary: "_cmd_write 409 state_version_conflict: stderr keeps error/expected/actual byte-for-byte and adds resolution pointing at canon checkpoint read; exit code remains EXIT_VERSION_CONFLICT=1."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_write_version_conflict_includes_resolution
        - tests/test_checkpoint_concurrency.py::test_version_conflict_then_reread_then_succeed
      run_result: "pass — expected/actual preserved; resolution.command begins with 'canon checkpoint read'; exit 1."
    - id: AC-3
      summary: "_cmd_write 409 non-version (lease) branch: stderr adds resolution pointing at canon checkpoint lease-acquire; exit remains EXIT_LEASE_DENIED=2; existing lease_token scrub preserved."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_write_lease_denied_includes_resolution
      run_result: "pass — original error key retained, lease_denied resolution attached, exit 2."
    - id: AC-4
      summary: "_cmd_lease_acquire 409 lease_held: stderr keeps error/owner_agent_run_id/expires_at and adds resolution advising wait-for-expiry or contact owner; command = canon checkpoint lease-acquire ...; exit remains 2."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_acquire_lease_held_includes_owner_and_resolution
        - tests/test_checkpoint_concurrency.py::test_two_clients_second_acquire_denied
      run_result: "pass — owner_agent_run_id and expires_at intact; two-client scenario confirms second acquire denied with identical envelope shape."
    - id: AC-5
      summary: "_cmd_lease_renew 409 branch: stderr adds resolution pointing at canon checkpoint lease-acquire (expired/rotated lease falls back to re-acquire); exit remains 2."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_renew_409_includes_resolution
      run_result: "pass — lease_expired resolution attached with lease-acquire command; exit 2."
    - id: AC-6
      summary: "_cmd_lease_release 409 branch: stderr adds resolution noting the lease may already be released/rotated and advising re-acquire if a write is still pending; exit remains 2."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_release_409_includes_resolution
      run_result: "pass — resolution present; exit 2; prior detail keys preserved."
    - id: AC-7
      summary: "Backward compatibility: every existing stderr key on every 409 path is preserved with the same spelling and type; only the new resolution key is added."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_backward_compat_existing_keys_preserved
        - tests/test_cli_checkpoint.py::test_write_409_state_version_conflict_unwraps_detail_exit_1
      run_result: "pass — concurrency suite asserts key preservation across all 4 × 409 paths; E2-T3 tripwire (52/52) re-run confirms no other regression, and the narrowly relaxed assertion still pins the three original keys by value."
    - id: AC-8
      summary: "tests/test_checkpoint_concurrency.py (≥12 tests) monkeypatches canon_systems.checkpoint_cli._http_request and exercises happy path (acquire→write→renew→release, lease token round-trip), version-conflict recovery, lease-held conflict, renew/release 409 paths, two-client scenario, and version-conflict-then-reread-then-succeed sequencing."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_acquire_write_renew_release_happy_path
        - tests/test_checkpoint_concurrency.py::test_two_clients_second_acquire_denied
        - tests/test_checkpoint_concurrency.py::test_version_conflict_then_reread_then_succeed
      run_result: "pass — 17 tests total, all deterministic via monkeypatched _http_request; no live state-api, no unmocked network."
    - id: AC-9
      summary: "src/canon_systems/templates/agents/implementer.md gains additive ### Conflict recovery (E4-T2) subsection showing precise recovery invocations for each conflict kind (version, lease held, lease expired), matching _resolution_hint messages verbatim."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_implementer_template_documents_conflict_recovery
      run_result: "pass — template assertion confirms canon checkpoint read, canon checkpoint lease-acquire, and exit codes 1 and 2 all appear under the new subsection."
    - id: AC-10
      summary: "src/canon_systems/templates/agents/release-orchestrator.md gains one-line pointer bullet referencing the new implementer.md conflict-recovery section."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_release_orchestrator_template_references_conflict_recovery
      run_result: "pass — template references both 'Conflict recovery' and 'implementer.md'."
    - id: AC-11
      summary: "Additive living-spec edits: CHANGELOG.md prepends an E4-T2 bullet above the existing E4-T1 bullet in [Unreleased] ### Added; docs/SYSTEM-WORKFLOW.md gains an additive bullet in §3 describing lease + versioning enforcement + resolution envelopes; README.md is intentionally unchanged."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_changelog_has_e4t2_bullet
        - tests/test_checkpoint_concurrency.py::test_system_workflow_documents_enforcement
      run_result: "pass — CHANGELOG assertion pins E4-T2 appearing before E4-T1; SYSTEM-WORKFLOW assertion pins §3 bullet mentioning E4-T2 + resolution."
    - id: AC-12
      summary: "Suite-level regression: full pytest run passes with 333 baseline + ≥12 new = ≥345 tests; tests/test_cli_checkpoint.py (E2-T3 tripwire) continues to pass with no functional regression (one assertion relaxed from dict-equality to subset-match is the documented, justified deviation)."
      status: MET
      covering_tests:
        - tests/test_checkpoint_concurrency.py
        - tests/test_cli_checkpoint.py
      run_result: "pass — full suite 350/350; tripwire 52/52; focused 17/17."
  remaining_gaps: []
  notes: |
    All 12 acceptance criteria verified. Focused suite 17/17, tripwire 52/52, full repo suite 350/350, zero QA-iteration fixes required. The only deviation from the scoper packet is a narrow, bounded relaxation of one assertion in tests/test_cli_checkpoint.py (moving from strict dict-equality to subset-match while preserving every original key/value equality and additionally asserting resolution.message/command truthiness); the scoper packet misnamed this file as tests/test_checkpoint_cli.py, and the deviation was necessary because the additive resolution key intentionally breaks strict-equality while preserving behavioral compatibility. No forbidden surface touched (no backend/**, no infra/**, no .cursor/rules/**, no .cursor/plans/**, no src/canon_systems/*.py except checkpoint_cli.py, no templates other than implementer.md and release-orchestrator.md, and no test file other than the new tests/test_checkpoint_concurrency.py plus the one-function tripwire relax in tests/test_cli_checkpoint.py). Exit-code contract (0/1/2/3/4/5) preserved; stderr JSON is strictly additive on every 409 path.
END_GATE_RESULTS
```
