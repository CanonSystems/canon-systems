<!-- CURSOR_PILOT_PROMPT: E4-T2 lease + versioning enforcement -->

# E4-T2 Cursor-Pilot Prompt

## ROLE
You are the implementer for Canon Memory Platform v1, Wave 4, Task E4-T2 (Lease + versioning enforcement in CLI + templates). Work on branch `wave/4/canon-memory-v1` (tip `fce2971` = E4-T1).

## TASK
Enrich the four `canon checkpoint` mutating commands' 409 stderr envelopes with a new additive `resolution: {message, command}` key, preserving every existing key and exit code. Add `tests/test_checkpoint_concurrency.py` (≥12 tests) validating the acquire → write → renew → release flow and every 409 recovery path via a monkeypatched `_http_request` seam. Document the flow in `src/canon_systems/templates/agents/implementer.md` (new `### Conflict recovery (E4-T2)` subsection) and cross-reference in `release-orchestrator.md`. Update CHANGELOG and SYSTEM-WORKFLOW additively.

## CONTEXT

### Why this is additive-only

`backend/state-api` already rejects stale writes and lease-less mutations; the server-side enforcement is complete. E4-T2 is operator-ergonomics: when a 409 comes back, the client's stderr should TELL the operator the exact `canon checkpoint ...` command to run to recover. Exit codes stay stable (1 for version conflict, 2 for lease denied), existing stderr keys stay identical (many tests in `tests/test_checkpoint_cli.py` rely on them), and we only add a new `resolution` object alongside.

### Exit-code catalog (unchanged)

```
EXIT_OK = 0
EXIT_VERSION_CONFLICT = 1
EXIT_LEASE_DENIED = 2
EXIT_NOT_FOUND = 3
EXIT_USAGE = 4
EXIT_TRANSPORT = 5
```

### State-api 409 response shapes (reference, do not import)

- `PUT /state/checkpoint` with stale `state_version` → 409 `{"detail": {"error": "state_version_conflict", "expected": N, "actual": M}}`.
- `PUT /state/checkpoint` without valid lease → 409 with some error kind (server may label `"lease_invalid"` or `"lease_denied"`); the client treats any non-`state_version_conflict` 409 as lease-denied.
- `POST /state/lease/acquire` while another agent holds → 409 `{"detail": {"error": "lease_held", "owner_agent_run_id": "...", "expires_at": "..."}}`.
- `POST /state/lease/renew` with expired/rotated token → 409 `{"detail": {...}}`.
- `POST /state/lease/release` with stale token → 409 `{"detail": {...}}`.

## REPOSITORY

### Files to modify (5)
1. `src/canon_systems/checkpoint_cli.py` — add `_resolution_hint()` helper and weave into 4 × 409 branches.
2. `src/canon_systems/templates/agents/implementer.md` — append `### Conflict recovery (E4-T2)` subsection under the existing checkpoint contract block.
3. `src/canon_systems/templates/agents/release-orchestrator.md` — append single pointer bullet.
4. `CHANGELOG.md` — prepend E4-T2 bullet at top of `## [Unreleased] ### Added`.
5. `docs/SYSTEM-WORKFLOW.md` — append additive bullet in §3 or §5.1.

### Files to create (1)
6. `tests/test_checkpoint_concurrency.py` — new.

### Forbidden surfaces
- `backend/**`, `infra/**`, `.cursor/rules/**`, `.cursor/plans/**`.
- `src/canon_systems/*.py` except `checkpoint_cli.py`. **Do not touch `cli.py`, `resume_engine.py`, or any other module.**
- `templates/agents/*.md` except `implementer.md` and `release-orchestrator.md`.
- Any `tests/*.py` except the new `tests/test_checkpoint_concurrency.py`. **Do not modify `tests/test_checkpoint_cli.py`.**
- `README.md` — no new row needed; do not edit.

## IMPLEMENTATION SPECIFICATION

### 1. `src/canon_systems/checkpoint_cli.py` — add helper + weave

Add this helper near the top of the module (after the exit-code constants, before `_clamp_timeout`):

```python
_RESOLUTION_HINTS: dict[str, dict[str, str]] = {
    "state_version_conflict": {
        "message": (
            "Your expected state_version is stale. Re-read the current checkpoint "
            "to get the latest state_version, then retry the write with "
            "--expected-version <new_value>."
        ),
        "command": (
            "canon checkpoint read --company-id <c> --repository-id <r> "
            "--plan-id <p> --task-id <t> --workstream-id <w>"
        ),
    },
    "lease_held": {
        "message": (
            "Another agent currently holds the lease. Wait until expires_at, "
            "or coordinate with owner_agent_run_id, then re-run lease-acquire."
        ),
        "command": (
            "canon checkpoint lease-acquire --company-id <c> --repository-id <r> "
            "--plan-id <p> --task-id <t> --workstream-id <w> "
            "--owner-agent-run-id <run_id> --owner-actor-id <actor_id> --ttl-seconds 300"
        ),
    },
    "lease_denied": {
        "message": (
            "Your lease_token is missing, stale, or unauthorized for this scope. "
            "Acquire a fresh lease, then retry the mutating call with the new lease_token."
        ),
        "command": (
            "canon checkpoint lease-acquire --company-id <c> --repository-id <r> "
            "--plan-id <p> --task-id <t> --workstream-id <w> "
            "--owner-agent-run-id <run_id> --owner-actor-id <actor_id> --ttl-seconds 300"
        ),
    },
    "lease_expired": {
        "message": (
            "The lease_token has expired or been rotated. Re-acquire the lease "
            "(renewal of a dead token is not supported) and retry."
        ),
        "command": (
            "canon checkpoint lease-acquire --company-id <c> --repository-id <r> "
            "--plan-id <p> --task-id <t> --workstream-id <w> "
            "--owner-agent-run-id <run_id> --owner-actor-id <actor_id> --ttl-seconds 300"
        ),
    },
}


def _resolution_hint(kind: str) -> dict[str, str]:
    """Return the {message, command} recovery hint for a known conflict kind.

    Unknown kinds return the conservative `lease_denied` hint (re-acquire lease).
    """
    if kind in _RESOLUTION_HINTS:
        return dict(_RESOLUTION_HINTS[kind])
    return dict(_RESOLUTION_HINTS["lease_denied"])
```

Then modify each 409 branch:

**`_cmd_write` state_version_conflict branch** (currently lines ~291-297):

```python
    if st == 409:
        raw = j if isinstance(j, dict) else {}
        d = _unwrap_detail(raw)
        if isinstance(d, dict) and d.get("error") == "state_version_conflict":
            o = {k: d[k] for k in ("error", "expected", "actual") if k in d}
            o["resolution"] = _resolution_hint("state_version_conflict")
            _emit_stderr_json(o)
            return EXIT_VERSION_CONFLICT
        if isinstance(d, dict):
            o = {k: v for k, v in d.items() if k != "lease_token"}
            o["resolution"] = _resolution_hint("lease_denied")
            _emit_stderr_json(o)
            return EXIT_LEASE_DENIED
        _emit_stderr_json({"error": "conflict", "detail": d, "resolution": _resolution_hint("lease_denied")})
        return EXIT_LEASE_DENIED
```

**`_cmd_lease_acquire` 409 branch** (currently lines ~358-375):

```python
    if st == 409:
        raw = j if isinstance(j, dict) else {}
        d = _unwrap_detail(raw)
        if isinstance(d, dict) and d.get("error") == "lease_held":
            _emit_stderr_json(
                {
                    "error": "lease_held",
                    "owner_agent_run_id": d.get("owner_agent_run_id"),
                    "expires_at": d.get("expires_at"),
                    "resolution": _resolution_hint("lease_held"),
                }
            )
            return EXIT_LEASE_DENIED
        if isinstance(d, dict):
            o = {k: v for k, v in d.items() if k != "lease_token"}
            o["resolution"] = _resolution_hint("lease_denied")
            _emit_stderr_json(o)
            return EXIT_LEASE_DENIED
        _emit_stderr_json({"error": "lease_denied", "detail": d, "resolution": _resolution_hint("lease_denied")})
        return EXIT_LEASE_DENIED
```

**`_cmd_lease_renew` 409 branch** (currently lines ~421-425):

```python
    if st == 409:
        raw = j if isinstance(j, dict) else {}
        d = _unwrap_detail(raw)
        out = d if isinstance(d, dict) else {"detail": d}
        out = dict(out)
        out["resolution"] = _resolution_hint("lease_expired")
        _emit_stderr_json(out)
        return EXIT_LEASE_DENIED
```

**`_cmd_lease_release` 409 branch** (currently lines ~456-460):

```python
    if st == 409:
        raw = j if isinstance(j, dict) else {}
        d = _unwrap_detail(raw)
        out = d if isinstance(d, dict) else {"detail": d}
        out = dict(out)
        out["resolution"] = _resolution_hint("lease_expired")
        _emit_stderr_json(out)
        return EXIT_LEASE_DENIED
```

**CRITICAL backward-compat rules:**
- The key `"resolution"` is the ONLY new key. Do not rename `error`, `expected`, `actual`, `owner_agent_run_id`, `expires_at`, `detail`.
- Do NOT change any 200/404/422/5xx branch output.
- Do NOT change exit codes.
- Do NOT change `_cmd_read` (read has no 409 path).

### 2. `tests/test_checkpoint_concurrency.py` — new file

Write ≥12 tests. All tests monkeypatch `canon_systems.checkpoint_cli._http_request` to return canned tuples. Use `capsys` for stdout/stderr capture. Do NOT spawn subprocesses. Follow the style of `tests/test_checkpoint_cli.py`.

Mandatory tests (exact names for AC traceability):

```python
# 1. test_resolution_hint_kinds_enum
#    Call _resolution_hint for each of: state_version_conflict, lease_held, lease_denied, lease_expired.
#    Assert each returns a dict with non-empty "message" and "command" strings.
#    Assert unknown kind falls back to lease_denied.

# 2. test_write_version_conflict_includes_resolution
#    Seed _http_request to return (409, {"detail": {"error": "state_version_conflict", "expected": 5, "actual": 7}}, {}).
#    Invoke run(["write", ... --expected-version 5 ...]).
#    Assert exit code == 1, stderr JSON has keys {error, expected, actual, resolution},
#    and resolution.command starts with "canon checkpoint read".

# 3. test_write_lease_denied_includes_resolution
#    Seed _http_request to return (409, {"detail": {"error": "lease_invalid"}}, {}).
#    Assert exit == 2, stderr JSON has `resolution` with command starting with "canon checkpoint lease-acquire".
#    Also assert the original "error" key survives.

# 4. test_acquire_lease_held_includes_owner_and_resolution
#    Seed (409, {"detail": {"error": "lease_held", "owner_agent_run_id": "run-abc", "expires_at": "2026-04-23T00:00:00Z"}}, {}).
#    Invoke run(["lease-acquire", ...]).
#    Assert exit == 2, stderr has {error, owner_agent_run_id, expires_at, resolution},
#    resolution.command contains "lease-acquire".

# 5. test_renew_409_includes_resolution
#    Seed (409, {"detail": {"error": "lease_expired"}}, {}).
#    Invoke run(["lease-renew", ...]).
#    Assert exit == 2, stderr has `resolution` with command containing "lease-acquire".

# 6. test_release_409_includes_resolution
#    Seed (409, {"detail": {"error": "lease_expired"}}, {}).
#    Invoke run(["lease-release", ...]).
#    Assert exit == 2, stderr has `resolution`.

# 7. test_backward_compat_existing_keys_preserved
#    Parametrize over the four 409 paths (write-version, write-lease, acquire, renew) and
#    assert that every PRE-EXISTING stderr key (error, expected/actual OR owner_agent_run_id/expires_at)
#    is still present alongside the new `resolution` key. Use tests/test_checkpoint_cli.py
#    E2-T3 expected-shapes as the source of truth for original keys.

# 8. test_acquire_write_renew_release_happy_path
#    Seed _http_request with a stateful queue returning (200, ...) bodies in sequence:
#      [0] acquire → returns {"lease_token": "tok-1", "expires_at": "..."}
#      [1] write   → returns {"state_version": 1, "last_event_id": "ev-1"}
#      [2] renew   → returns {"lease_token": "tok-1", "expires_at": "..."}
#      [3] release → returns {"released": true}
#    Call run() four times sequentially; assert all return 0 and lease_token round-trips.

# 9. test_two_clients_second_acquire_denied
#    Stateful queue: first acquire 200, second acquire 409 lease_held.
#    Assert first returns 0, second returns 2 with resolution + owner_agent_run_id present.

# 10. test_version_conflict_then_reread_then_succeed
#     Stateful queue: first write 409 state_version_conflict (expected=5, actual=7),
#     second write 200 (the "retry with --expected-version 7" path).
#     Call run(["write", ... --expected-version 5 ...]) → exit 1.
#     Call run(["write", ... --expected-version 7 ...]) → exit 0.
#     Assert both stderr + stdout shapes.

# 11. test_implementer_template_documents_conflict_recovery
#     Read src/canon_systems/templates/agents/implementer.md.
#     Assert it contains the header "### Conflict recovery (E4-T2)".
#     Assert the section references all three of: "canon checkpoint read",
#     "canon checkpoint lease-acquire", and exit codes 1 and 2.

# 12. test_release_orchestrator_template_references_conflict_recovery
#     Read src/canon_systems/templates/agents/release-orchestrator.md.
#     Assert it contains a reference to "Conflict recovery" and "implementer.md".

# 13. test_changelog_has_e4t2_bullet
#     Read CHANGELOG.md, assert it contains "**E4-T2**" in the [Unreleased] block
#     and that the E4-T2 bullet appears BEFORE the existing E4-T1 bullet.

# 14. test_system_workflow_documents_enforcement
#     Read docs/SYSTEM-WORKFLOW.md, assert it contains "E4-T2" and "resolution"
#     (or "enforcement") in an additive bullet.
```

**Test-seam pattern** (match `tests/test_checkpoint_cli.py` if it exists; otherwise use):

```python
import json
from canon_systems import checkpoint_cli


def _scope_args(extra: list[str] | None = None) -> list[str]:
    base = [
        "--company-id", "c-1", "--repository-id", "r-1",
        "--plan-id", "p-1", "--task-id", "t-1",
        "--workstream-id", "ws-1",
    ]
    return base + (extra or [])


def test_write_version_conflict_includes_resolution(monkeypatch, capsys):
    def _fake(method, url, body, timeout_ms):
        return (409, {"detail": {"error": "state_version_conflict", "expected": 5, "actual": 7}}, {})
    monkeypatch.setattr(checkpoint_cli, "_http_request", _fake)

    rc = checkpoint_cli.run(["write"] + _scope_args([
        "--handoff-id", "h", "--phase", "implementer", "--phase-status", "completed",
        "--expected-version", "5", "--lease-token", "tok-1",
    ]))
    assert rc == checkpoint_cli.EXIT_VERSION_CONFLICT
    err = capsys.readouterr().err.strip()
    payload = json.loads(err)
    assert payload["error"] == "state_version_conflict"
    assert payload["expected"] == 5
    assert payload["actual"] == 7
    assert "resolution" in payload
    assert payload["resolution"]["command"].startswith("canon checkpoint read")
```

For stateful queues (tests 8, 9, 10):

```python
def _queue(*responses):
    it = iter(responses)
    def _fake(method, url, body, timeout_ms):
        return next(it)
    return _fake
```

### 3. `src/canon_systems/templates/agents/implementer.md` — append subsection

Append this block at the END of the file (after the existing `**Dev/sandbox skip:** ...` paragraph at line 132). Do not reflow or reorder existing lines.

```markdown

### Conflict recovery (E4-T2)

When `canon checkpoint` returns exit `1` or `2`, the stderr JSON now includes a `resolution` object with a concrete recovery command. Handle each kind as follows:

- **Exit 1 — `state_version_conflict`** (stale `--expected-version`):
  1. Re-read the current checkpoint: `canon checkpoint read --company-id <c> --repository-id <r> --plan-id <p> --task-id <t> --workstream-id <w>`.
  2. Read the returned `state_version`; retry the `write` with `--expected-version <new_value>`.

- **Exit 2 — `lease_held`** (another agent owns the lease): wait until the returned `expires_at`, or coordinate with `owner_agent_run_id`, then re-run `canon checkpoint lease-acquire`.

- **Exit 2 — `lease_denied` / `lease_expired`** (your `--lease-token` is missing/stale/rotated): re-run `canon checkpoint lease-acquire` to obtain a fresh token, then retry the mutating call with the new `--lease-token`.

Renewal (`lease-renew`) of an expired token is not supported — always fall back to `lease-acquire`. The `resolution.command` field in the stderr envelope is copy-pasteable with `<placeholder>` substitutions for scope IDs.
```

### 4. `src/canon_systems/templates/agents/release-orchestrator.md` — append pointer

Append ONE bullet at the end of the file (do not reflow existing lines):

```markdown

- **Conflict recovery:** when any `canon checkpoint` mutating call returns exit `1` or `2`, consult the `### Conflict recovery (E4-T2)` section of `src/canon_systems/templates/agents/implementer.md` for the canonical recovery flow. The stderr `resolution` object contains the exact `canon checkpoint ...` command to re-run.
```

### 5. `CHANGELOG.md` — prepend E4-T2 bullet

Insert a new bullet at the TOP of the `## [Unreleased] ### Added` block, immediately after the `### Added` heading and BEFORE the existing E4-T1 bullet:

```markdown
- **E4-T2** Lease + versioning enforcement in CLI + templates: `canon checkpoint write | lease-acquire | lease-renew | lease-release` now emit an additive `resolution: {message, command}` object on every 409 stderr envelope carrying the copy-pasteable recovery command (`canon checkpoint read` for stale versions, `canon checkpoint lease-acquire` for lease conflicts). Exit codes (`1` = version conflict, `2` = lease denied) and all pre-existing stderr keys preserved byte-for-byte. New `tests/test_checkpoint_concurrency.py` validates the acquire → write → renew → release happy path and every 409 recovery path via a monkeypatched `_http_request` seam. `src/canon_systems/templates/agents/implementer.md` gains a `### Conflict recovery (E4-T2)` subsection; `release-orchestrator.md` cross-references it.
```

### 6. `docs/SYSTEM-WORKFLOW.md` — append additive bullet

Append a single bullet in §3 (or §5.1 if more appropriate, depending on which section already covers checkpoint/lease mechanics). Do not reorder or reflow other bullets. Example shape:

```markdown
- **E4-T2 lease + versioning enforcement (CLI):** every `canon checkpoint` mutating command (`write`, `lease-acquire`, `lease-renew`, `lease-release`) now emits an additive `resolution: {message, command}` object on 409 stderr envelopes, carrying the exact `canon checkpoint ...` recovery invocation. Exit codes remain `1` (version conflict) and `2` (lease denied). Operators (and orchestrator agents) can parse `resolution.command` to drive automated recovery. See `src/canon_systems/templates/agents/implementer.md § Conflict recovery (E4-T2)`.
```

## REASONING

1. Read the current `src/canon_systems/checkpoint_cli.py` to locate the four 409 branches and confirm line numbers.
2. Read `tests/test_checkpoint_cli.py` (READ-ONLY) to match the monkeypatch signature `(method, url, body, timeout_ms) -> (status, body_json, headers)`.
3. Read `src/canon_systems/templates/agents/implementer.md` to confirm the append point (after the "Dev/sandbox skip" paragraph).
4. Read `src/canon_systems/templates/agents/release-orchestrator.md` to confirm the append point.
5. Apply the 5 modifications + 1 new file.
6. Run `pytest tests/test_checkpoint_concurrency.py -q` — expect ≥12 passes.
7. Run `pytest tests/test_checkpoint_cli.py -q` — expect ZERO regressions (the E2-T3 suite is the tripwire for backward compat).
8. Run `pytest -q` at repo root — expect ≥345 passes (333 baseline + ≥12 new).
9. Smoke-test via the existing CLI: no new subcommand means no new smoke test required, but verify `python3 -m canon_systems.cli checkpoint --help` still shows all 5 subcommands.
10. Emit `HANDOFF_TO_QA` to `.cursor/handoffs/canon-memory-v1/E4-T2/implementer.md`.

## OUTPUT FORMAT

Write the full implementer packet to `.cursor/handoffs/canon-memory-v1/E4-T2/implementer.md`. It MUST include a `HANDOFF_TO_QA` block with:

- `handoff_id: handoff_20260423_e4t2_lease_version_enforcement`
- `task_id: E4-T2`
- `branch: wave/4/canon-memory-v1`
- `files_modified:` exact list (6 paths: 1 new test + 5 modified)
- `acceptance_criteria:` 12 ACs each with `status: MET`, `evidence:`, `run_result:`, and `covering_tests:` (YAML block-style list of pytest node ids / file paths — NO `shell::` / `grep::` / `manual::` prefixes, only bare node IDs or file paths)
- `suite_result:` pytest summary lines for both the focused `test_checkpoint_concurrency.py` run AND the full-suite run
- `notes:` any degradations or observations

## STOP CONDITIONS

Stop and surface a blocker (do not improvise) if:
- `src/canon_systems/checkpoint_cli.py` has been restructured away from the `_cmd_write` / `_cmd_lease_*` layout.
- Any pre-existing test in `tests/test_checkpoint_cli.py` fails — this means a backward-compat violation was introduced.
- `cli.py` or `resume_engine.py` would need editing (they must not).
- The `_unwrap_detail` helper behavior has changed in a way that breaks the `d.get("error") == "state_version_conflict"` check.
- README.md would need a new row (no new subcommand/flag in E4-T2, so this should never happen).
