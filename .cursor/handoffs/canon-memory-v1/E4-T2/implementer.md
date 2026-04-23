# E4-T2 Implementer Handoff

## Summary of work

- **`src/canon_systems/checkpoint_cli.py`:** Added `_RESOLUTION_HINTS` constant and `_resolution_hint()` helper after the exit-code constants; attached the `resolution` object on all four 409 stderr paths (`_cmd_write` version + lease branches, `_cmd_lease_acquire`, `_cmd_lease_renew`, `_cmd_lease_release`). Exit codes unchanged. All pre-existing stderr keys preserved byte-for-byte.
- **`src/canon_systems/templates/agents/implementer.md`:** Appended `### Conflict recovery (E4-T2)` subsection at end of file.
- **`src/canon_systems/templates/agents/release-orchestrator.md`:** Appended single pointer bullet at end of file.
- **`CHANGELOG.md`:** Prepended E4-T2 bullet at the top of `## [Unreleased] ### Added`, above the existing E4-T1 bullet.
- **`docs/SYSTEM-WORKFLOW.md`:** Appended additive bullet in §3 describing the lease + versioning enforcement.
- **`tests/test_checkpoint_concurrency.py` (new):** 17 tests covering the 12 logical ACs (some have multiple parametrize variants for backward-compat coverage).

### Justified deviation

- **`tests/test_cli_checkpoint.py`** (the actual E2-T3 tripwire file; the packet referenced `tests/test_checkpoint_cli.py` which does not exist in this repo): one assertion at line 400 used `assert j == {"error": "state_version_conflict", "expected": 7, "actual": 8}` — a byte-exact dict equality that would fail once the new additive `resolution` key was added. The implementer narrowly relaxed this to four per-key assertions that still verify all three original keys with identical values AND require `resolution.message` + `resolution.command` to be truthy. The diff is 1 deletion + 6 additions, all confined to one test function. No other E2-T3 test was touched. This is the minimum change required to carry the additive contract forward without dropping any behavioral guarantee from E2-T3.

## Pytest results

- Focused: `pytest tests/test_checkpoint_concurrency.py -q` → **17 passed in 0.06s**.
- Tripwire: `pytest tests/test_cli_checkpoint.py -q` → **52 passed**.
- Full: `pytest -q` → **350 passed in 5.18s** (baseline 333 + 17 new; exceeds ≥345 target).

## HANDOFF_TO_QA

```yaml
HANDOFF_TO_QA:
  handoff_id: handoff_20260423_e4t2_lease_version_enforcement
  task_id: E4-T2
  branch: wave/4/canon-memory-v1
  files_modified:
    - src/canon_systems/checkpoint_cli.py
    - src/canon_systems/templates/agents/implementer.md
    - src/canon_systems/templates/agents/release-orchestrator.md
    - CHANGELOG.md
    - docs/SYSTEM-WORKFLOW.md
    - tests/test_checkpoint_concurrency.py
    - tests/test_cli_checkpoint.py
  notes: |
    Narrow backward-compat relax of one assertion in tests/test_cli_checkpoint.py
    (previously asserted exact 3-key dict equality; now asserts subset-match +
    truthy resolution.message/command). The packet referenced tests/test_checkpoint_cli.py
    which does not exist in this repo; the real E2-T3 tripwire is tests/test_cli_checkpoint.py
    (52 tests, all green). Nothing committed.
  suite_result:
    focused: "17 passed in 0.06s  (pytest tests/test_checkpoint_concurrency.py -q)"
    tripwire: "52 passed  (pytest tests/test_cli_checkpoint.py -q)"
    full: "350 passed in 5.18s  (pytest -q at repo root)"
  acceptance_criteria:
    - id: AC1
      status: MET
      evidence: "_RESOLUTION_HINTS and _resolution_hint() after exit codes; unknown kinds map to lease_denied."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_resolution_hint_kinds_enum
    - id: AC2
      status: MET
      evidence: "write 409 state_version_conflict: error/expected/actual + resolution; exit 1; command prefix 'canon checkpoint read'."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_write_version_conflict_includes_resolution
        - tests/test_checkpoint_concurrency.py::test_version_conflict_then_reread_then_succeed
    - id: AC3
      status: MET
      evidence: "write 409 non-version (lease_invalid): original error retained + lease_denied resolution; exit 2."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_write_lease_denied_includes_resolution
    - id: AC4
      status: MET
      evidence: "lease-acquire 409 lease_held: error/owner_agent_run_id/expires_at preserved + resolution; exit 2; second client denied."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_acquire_lease_held_includes_owner_and_resolution
        - tests/test_checkpoint_concurrency.py::test_two_clients_second_acquire_denied
    - id: AC5
      status: MET
      evidence: "lease-renew 409: detail preserved + lease_expired resolution; exit 2."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_renew_409_includes_resolution
    - id: AC6
      status: MET
      evidence: "lease-release 409: detail preserved + resolution; exit 2."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_release_409_includes_resolution
    - id: AC7
      status: MET
      evidence: "All 4 × 409 paths: pre-existing stderr keys retained alongside new resolution key."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_backward_compat_existing_keys_preserved
    - id: AC8
      status: MET
      evidence: "Stateful acquire → write → renew → release; all 200; lease token reuse."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_acquire_write_renew_release_happy_path
    - id: AC9
      status: MET
      evidence: "implementer.md gains '### Conflict recovery (E4-T2)' with canon checkpoint read, canon checkpoint lease-acquire, exit codes 1 and 2."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_implementer_template_documents_conflict_recovery
    - id: AC10
      status: MET
      evidence: "release-orchestrator.md references Conflict recovery and implementer.md."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_release_orchestrator_template_references_conflict_recovery
    - id: AC11
      status: MET
      evidence: "CHANGELOG [Unreleased] has **E4-T2** bullet before **E4-T1** bullet."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_changelog_has_e4t2_bullet
    - id: AC12
      status: MET
      evidence: "SYSTEM-WORKFLOW.md §3 bullet mentions E4-T2 + resolution; full pytest suite green at 350 passed."
      run_result: PASS
      covering_tests:
        - tests/test_checkpoint_concurrency.py::test_system_workflow_documents_enforcement
        - tests/test_cli_checkpoint.py
END_HANDOFF_TO_QA
```
