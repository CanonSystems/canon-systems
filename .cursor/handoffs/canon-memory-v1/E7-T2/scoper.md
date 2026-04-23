# SCOPE_PACKET — E7-T2 sibling-repo deletion (documentation-only close)

## SCOPE_SUMMARY
Close out E7-T2 by marking `docs/DEPRECATIONS.md` FINAL and recording each
sibling's final disposition as a durable canonical event. No sibling
reached the `delete` label during v1; all `absorb` targets were folded
into `canon-systems` during Waves 3–6, so this task is **documentation
and canonical event emission only** — no filesystem deletions.

## Justification for documentation-only close
Audit of `docs/DEPRECATIONS.md` @ start of E7-T2 showed labels:
`canon-platform=keep`, `canon-systems-v2=keep (infra absorbed)`,
`mempalace=absorb`, `obsidian-mind=absorb`, `temporal=keep (vendor)`,
`total_recall=absorb`. No sibling carried `delete`. Operator explicitly
declined to re-label any `absorb` target as `delete`.

## Acceptance Criteria
1. `docs/DEPRECATIONS.md` marked FINAL with dated header.
2. Each sibling's final disposition recorded (`keep` / `absorbed` /
   `keep (vendor baseline)` as applicable).
3. One `sibling_disposition_finalized` canonical event per sibling
   appended to `.canon/memory/events.ndjson` (6 events total).
4. `tests/test_wave0_audit_docs.py::test_deprecations_covers_all_six_siblings_with_label`
   continues to pass (original `keep/absorb/delete` labels still visible
   near each sibling path).
5. No changes to sibling filesystem state.
6. Full `tests/` suite green.

## Files
- modify: `docs/DEPRECATIONS.md`
- append (runtime): `.canon/memory/events.ndjson`
- modify: `CHANGELOG.md`, `docs/SYSTEM-WORKFLOW.md`
