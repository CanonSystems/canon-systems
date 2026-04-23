# E4-T2 Scoper Packet — Lease + versioning enforcement in CLI + templates

## SCOPE SUMMARY

E4-T2 hardens the existing `canon checkpoint` mutating surfaces (`write`, `lease-acquire`, `lease-renew`, `lease-release`) so that every 409 conflict (version mismatch or lease denial) emits an **actionable resolution envelope** on stderr while preserving the existing exit-code contract (`EXIT_VERSION_CONFLICT=1`, `EXIT_LEASE_DENIED=2`). The change is strictly additive to the stderr JSON (new `resolution` key carrying a human-readable message plus a concrete CLI recovery command); existing keys (`error`, `expected`, `actual`, `owner_agent_run_id`, `expires_at`) are preserved byte-for-byte. A new focused concurrency test suite (`tests/test_checkpoint_concurrency.py`) exercises the acquire → write → renew → release happy path and every 409 recovery path end-to-end against a monkeypatched `_http_request` seam (no live state-api). The acquire/renew/release flow is documented in `src/canon_systems/templates/agents/implementer.md` (and cross-referenced in `release-orchestrator.md`) with copy-pasteable commands. The "enforcement" is observational and operator-facing — the state-api server already rejects stale writes and lease-less mutations; E4-T2 makes the client's errors educate the caller about the exact next CLI invocation needed to recover.

## SCOPE PACKET

### Identifiers
- handoff_id: `handoff_20260423_e4t2_lease_version_enforcement`
- task_id: `E4-T2`
- wave: `4`
- branch: `wave/4/canon-memory-v1` (tip `fce2971`)

### Story — acceptanceCriteria (12)

1. `src/canon_systems/checkpoint_cli.py` gains a private helper `_resolution_hint(kind: str, scope: dict | None = None) -> dict[str, str]` that returns a `{"message": ..., "command": ...}` pair keyed by a fixed enum of conflict kinds: `"state_version_conflict"`, `"lease_held"`, `"lease_denied"`, `"lease_expired"`. The `command` string is a copy-pasteable `canon checkpoint ...` invocation using `<placeholders>` for fields the caller must substitute (never fabricates a real lease token or version number).
2. `_cmd_write` 409 `state_version_conflict` branch: stderr JSON continues to include `error`, `expected`, `actual` unchanged, and ADDS a `"resolution"` object `{"message": "...re-read current state_version and retry...", "command": "canon checkpoint read --company-id <c> ..."}`. Exit code remains `EXIT_VERSION_CONFLICT = 1`.
3. `_cmd_write` 409 non-version (lease) branch: stderr JSON adds `"resolution"` pointing at `canon checkpoint lease-acquire ...`. Exit code remains `EXIT_LEASE_DENIED = 2`. The existing `lease_token` scrub (line 300) is preserved.
4. `_cmd_lease_acquire` 409 `lease_held` branch: stderr JSON continues to include `error`, `owner_agent_run_id`, `expires_at`, and ADDS `"resolution"` whose `message` advises waiting for `expires_at` OR contacting the current `owner_agent_run_id`, with `command` = `canon checkpoint lease-acquire ...` (same invocation, retry-after guidance in message). Exit code remains `2`.
5. `_cmd_lease_renew` 409 branch: stderr JSON ADDS `"resolution"` pointing at `canon checkpoint lease-acquire ...` (renewal of an expired/rotated lease falls back to re-acquire). Exit code remains `2`.
6. `_cmd_lease_release` 409 branch: stderr JSON ADDS `"resolution"` noting the lease may already be released/rotated and advising re-acquire if a write is still pending. Exit code remains `2`.
7. **Backward compatibility**: every existing stderr key on every 409 path is preserved with the same spelling and type; only the new `resolution` key is added. A regression test asserts the original keys still exist alongside `resolution`.
8. New test file `tests/test_checkpoint_concurrency.py` (≥12 tests) monkeypatches `canon_systems.checkpoint_cli._http_request` to return canned `(status, body, headers)` tuples and validates:
   - Happy path: `lease-acquire` (200) → `write` (200) → `lease-renew` (200) → `lease-release` (200) returns `EXIT_OK` for every call and the lease token round-trips.
   - Version-conflict recovery: stale `write` returns 409 with `state_version_conflict`; envelope carries `expected`, `actual`, and `resolution.command` referencing `canon checkpoint read`.
   - Lease-held conflict: second `lease-acquire` while first holds returns 409 with `owner_agent_run_id`, `expires_at`, and `resolution` pointing at `canon checkpoint lease-acquire`.
   - `lease-renew` 409 → `resolution` points at `lease-acquire`.
   - `lease-release` 409 → `resolution` present; exit 2.
   - Two-client scenario: client A acquires (200), client B acquires (409 lease_held); both assertions in one test.
   - Version-conflict-then-reread-then-succeed: first write 409, second write 200 with new expected-version; asserts the sequencing.
9. **`src/canon_systems/templates/agents/implementer.md` additive section** (append to the existing "## Checkpoint (read-before / write-after) contract" block): a new `### Conflict recovery (E4-T2)` subsection showing the precise recovery invocation for each of the three conflict kinds (version conflict, lease held, lease expired), matching the `_resolution_hint` messages verbatim so operators can cross-reference. Do not reflow existing lines.
10. **`src/canon_systems/templates/agents/release-orchestrator.md` additive pointer**: a one-line bullet referencing the new implementer.md section as the canonical conflict-recovery reference. No other template edits.
11. **Living-spec additive edits**:
    - `CHANGELOG.md`: prepend E4-T2 bullet at the TOP of `## [Unreleased] ### Added` (above the existing E4-T1 bullet).
    - `docs/SYSTEM-WORKFLOW.md` §3 or §5.1: additive bullet describing lease + versioning enforcement with actionable resolution envelopes.
    - `README.md`: **skip** — no new subcommand or flag, no new table row. If a row annotation is needed, it is append-only.
12. **Test suite baseline regression**: the full pytest run must pass with 333 + ≥12 = ≥345 tests (exact count TBD by implementer), and `tests/test_checkpoint_cli.py` (pre-existing E2-T3 coverage) must continue to pass unchanged.

### Done signal (per backlog)

- `tests/test_checkpoint_concurrency.py` PASS.

### Forbidden surfaces

- `backend/**` — state-api already rejects stale/lease-less writes; no server-side changes in E4-T2.
- `infra/**`
- `.cursor/rules/**`, `.cursor/plans/**`
- `src/canon_systems/*.py` OTHER THAN `checkpoint_cli.py`. In particular `resume_engine.py` (E4-T1 surface) and `cli.py` MUST NOT be modified — no new subcommands, no new flags.
- Templates other than `implementer.md` and `release-orchestrator.md`.
- Any test file other than the new `tests/test_checkpoint_concurrency.py`. Existing test files MUST NOT be edited.

### Repository
- primaryLanguages: Python (stdlib-only)
- testFramework: pytest
- relevantFiles:
  - Modify: `src/canon_systems/checkpoint_cli.py`, `src/canon_systems/templates/agents/implementer.md`, `src/canon_systems/templates/agents/release-orchestrator.md`, `CHANGELOG.md`, `docs/SYSTEM-WORKFLOW.md`
  - Create: `tests/test_checkpoint_concurrency.py`
  - Read-only reference: `tests/test_checkpoint_cli.py` (E2-T3 coverage patterns), `backend/state-api/state_api/checkpoints.py` (server 409 response shapes)

### Constraints
- dependencies: `E2-T3` (checkpoint CLI exists with exit-code catalog).
- mustNotBreak:
  - 333-test suite baseline (post-E4-T1 tip).
  - Existing `canon checkpoint` subcommand exit codes (0/1/2/3/4/5) unchanged.
  - Existing stderr JSON keys on all 409 paths unchanged (strictly additive).
  - No live state-api required for any test.

### Prior work references
- peer:`src/canon_systems/checkpoint_cli.py` (E2-T3) — the CLI being enriched; `_cmd_write` 409 branch at lines 291-304, `_cmd_lease_acquire` 409 at lines 358-375, `_cmd_lease_renew` 409 at lines 421-425, `_cmd_lease_release` 409 at lines 456-460.
- peer:`src/canon_systems/templates/agents/implementer.md` (E3-T4/E4 iterations) — the "## Checkpoint (read-before / write-after) contract" section at lines 102-132 is the anchor for the new `### Conflict recovery (E4-T2)` subsection.
- peer:`tests/test_checkpoint_cli.py` (E2-T3) — monkeypatch style for `_http_request` and exit-code assertions.

### ac_traceability

| # | Target | Test |
|---|---|---|
| 1 | `_resolution_hint` helper | `tests/test_checkpoint_concurrency.py::test_resolution_hint_kinds_enum` |
| 2 | write version-conflict resolution | `tests/test_checkpoint_concurrency.py::test_write_version_conflict_includes_resolution` |
| 3 | write lease-denied resolution | `tests/test_checkpoint_concurrency.py::test_write_lease_denied_includes_resolution` |
| 4 | acquire lease-held resolution | `tests/test_checkpoint_concurrency.py::test_acquire_lease_held_includes_owner_and_resolution` |
| 5 | renew 409 resolution | `tests/test_checkpoint_concurrency.py::test_renew_409_includes_resolution` |
| 6 | release 409 resolution | `tests/test_checkpoint_concurrency.py::test_release_409_includes_resolution` |
| 7 | backward compat (no keys dropped) | `tests/test_checkpoint_concurrency.py::test_backward_compat_existing_keys_preserved` |
| 8 | acquire→write→renew→release happy path + scenarios | `tests/test_checkpoint_concurrency.py::test_acquire_write_renew_release_happy_path`, `::test_two_clients_second_acquire_denied`, `::test_version_conflict_then_reread_then_succeed` |
| 9 | implementer.md conflict-recovery section | `tests/test_checkpoint_concurrency.py::test_implementer_template_documents_conflict_recovery` |
| 10 | release-orchestrator.md pointer | `tests/test_checkpoint_concurrency.py::test_release_orchestrator_template_references_conflict_recovery` |
| 11 | CHANGELOG + SYSTEM-WORKFLOW additive | `tests/test_checkpoint_concurrency.py::test_changelog_has_e4t2_bullet`, `::test_system_workflow_documents_enforcement` |
| 12 | Regression: full suite still passes | pytest full run (suite-level, not per-test) |

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: E4-T2 enriches canon checkpoint 409 stderr envelopes with a new additive `resolution` key carrying copy-pasteable recovery commands; adds tests/test_checkpoint_concurrency.py (≥12 tests) over a monkeypatched _http_request; documents acquire/renew/release flow in templates/agents/implementer.md and release-orchestrator.md. Exit codes and existing stderr keys preserved byte-for-byte.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260423_e4t2_lease_version_enforcement"
      task_id: "E4-T2"
      wave: 4
      branch: "wave/4/canon-memory-v1"
    story:
      title: "Lease + versioning enforcement in CLI + templates"
      acceptanceCriteria:
        - "_resolution_hint helper returns {message, command} for each of 4 conflict kinds."
        - "write 409 state_version_conflict stderr gains `resolution` (keeps error/expected/actual)."
        - "write 409 non-version (lease) stderr gains `resolution`."
        - "lease-acquire 409 lease_held stderr gains `resolution` (keeps owner_agent_run_id/expires_at)."
        - "lease-renew 409 stderr gains `resolution`."
        - "lease-release 409 stderr gains `resolution`."
        - "Backward-compat: all existing stderr keys preserved on every 409 path."
        - "tests/test_checkpoint_concurrency.py exercises happy path + every 409 recovery path via monkeypatched _http_request."
        - "implementer.md gains `### Conflict recovery (E4-T2)` subsection with copy-pasteable commands."
        - "release-orchestrator.md gains pointer bullet to implementer.md conflict-recovery."
        - "Additive CHANGELOG + SYSTEM-WORKFLOW edits (no README change)."
        - "Full pytest suite green (333 + ≥12 new)."
    constraints:
      dependencies: ["E2-T3"]
      mustNotBreak:
        - "333-test suite baseline"
        - "canon checkpoint exit codes 0/1/2/3/4/5"
        - "existing stderr JSON keys on all 409 paths"
    forbidden_surfaces:
      - "backend/**"
      - "infra/**"
      - ".cursor/rules/**"
      - ".cursor/plans/**"
      - "src/canon_systems/*.py except checkpoint_cli.py"
      - "templates/agents/*.md except implementer.md and release-orchestrator.md"
      - "tests/*.py except the new tests/test_checkpoint_concurrency.py"
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
      prior_work_references: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
