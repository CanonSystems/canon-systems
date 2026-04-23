# SCOPE_PACKET — E7-T3 final five-file living-spec refresh + release sign-off

## SCOPE_SUMMARY
Refresh the five living-spec files so they accurately describe the final
shipped Canon Memory Platform v1 (Waves 0–7). Emit the v1 release
sign-off packet as the closing artifact of the plan.

## Acceptance Criteria
1. `CHANGELOG.md` has at least one entry per epic E0–E7.
2. `README.md` has a dated "Canon Memory Platform v1 — shipped" summary
   section describing all seven waves.
3. `docs/MEMORY-PLATFORM-PLAN.md §9 (Implementation Waves)` reflects the
   final state of each wave (SHIPPED).
4. `docs/MEMORY-PLATFORM-BACKLOG.md` header notes v1 completion.
5. `docs/SYSTEM-WORKFLOW.md` header notes v1 completion.
6. Full `tests/` suite green.
7. Final `RELEASE_STATUS` artefact recorded at
   `.cursor/handoffs/canon-memory-v1/E7-T3/release-status.md`.

## Files
- modify: `README.md`, `docs/MEMORY-PLATFORM-PLAN.md`,
  `docs/MEMORY-PLATFORM-BACKLOG.md`, `docs/SYSTEM-WORKFLOW.md`,
  `CHANGELOG.md` (entry for E7-T3 itself).
- add: `.cursor/handoffs/canon-memory-v1/E7-T3/{scoper,implementer,qa-gate,release-status}.md`.
