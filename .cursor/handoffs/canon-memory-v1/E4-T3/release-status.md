# E4-T3 Release Status — Stall watchdog + unblock event

## Summary

E4-T3 ships `canon stall-watchdog scan`: a stdlib-only, idempotent, read-only
CLI that probes scoped tasks via `GET /state/checkpoint`, classifies any
response whose `lease.expires_at <= now_epoch` as **STALLED**, and emits one
canonical `lease_stall_detected` event per stall to `.canon/memory/events.ndjson`
(override via `--event-log`; `--dry-run` redirects to stderr NDJSON). The event
payload carries a `suggested_next_step` sourced by importing
`_resolution_hint("lease_held")` from `checkpoint_cli` — single source of truth,
zero duplication. `CanonicalEvent` is imported verbatim from
`canon_backend_shared.events` (Wave-3 discipline).

The scoper's critical decision #1 (probe via GET rather than
`POST /state/lease/acquire`) is enforced by construction: `models.item_has_live_lease`
treats expired leases as *no live lease*, so acquire would silently steal the
expired token and destroy the stall evidence. Grep confirms zero
`lease/acquire` references inside the module body.

## Verification

- Focused suite: `pytest tests/test_stall_watchdog.py -q` → **13 passed** in 0.04s.
- Full suite: `pytest -q` → **363 passed** in 3.88s (baseline 350 + 13 new; target ≥362 exceeded).
- QA-gate iterations: **0** (PASS on first run).
- flow-audit: PASS (`canon flow-audit --handoff-id canon-memory-v1 --task-id E4-T3 --require-release-status`).
- Commit sits on top of `e4daacf` (post-E4-T2) on `wave/4/canon-memory-v1`;
  no push (parent handles wave PR at wave close per rule §10).

## Commit scope (per-task, additive only)

Staged:

- `src/canon_systems/stall_watchdog.py` (new)
- `src/canon_systems/cli.py` (3 additive insertion points: import, subparser, dispatch)
- `tests/test_stall_watchdog.py` (new; 13 deterministic tests)
- `CHANGELOG.md` (E4-T3 bullet prepended above E4-T2 in `[Unreleased] ### Added`)
- `README.md` (new CLI row after `canon resume`)
- `docs/SYSTEM-WORKFLOW.md` (additive §3 bullet)
- `.cursor/handoffs/canon-memory-v1/E4-T3/{scoper,cursor-pilot,implementer,qa-gate,release-status}.md`

Explicitly NOT staged (precedent §4): `.canon/memory/capture-failures.log`,
`.canon/memory/capture-latest.json` (auto-churn from capture hooks).

```
RELEASE_STATUS
  initiative: "Canon Memory Platform v1"
  task_id: "E4-T3"
  branch: "wave/4/canon-memory-v1"
  pr_url: "pending (wave-close per rule §10)"
  new_commit_sha: "1b8f500"
  flow_audit_result: "PASS"
  qa_gate: "PASS"
  qa_gate_verdict: "PASS"
  ci_gate: "PENDING"
  merge_gate: "PENDING"
  suite_result: "363 passed"
  environment: "none"
  deploy_gate: "PENDING"
  rollback_ref: "e4daacf"
  blockers: []
  verdict: "RELEASED"
  next_action: "Await wave-4 close; parent opens wave PR (rule §10)."
END_RELEASE_STATUS
```
