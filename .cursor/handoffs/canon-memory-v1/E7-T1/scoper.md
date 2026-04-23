# SCOPE_PACKET — E7-T1 hard-lock rule distribution via `canon wire`

## SCOPE_SUMMARY
Copy the workspace hard-lock rule
`.cursor/rules/memory-platform-build-discipline.mdc` into the canon-systems
template tree so `canon wire` (`canon setup enable-repo` / `install_user_scope`)
distributes it byte-identically to every wired repo.

## Non-goals
- No changes to the rule's content; it must stay byte-identical.
- No new CLI command; we extend the existing installer.
- No migration for already-wired repos other than re-running `canon setup`.

## Acceptance Criteria
1. `src/canon_systems/templates/rules/memory-platform-build-discipline.mdc`
   exists and is byte-identical to the workspace rule.
2. `enable_repo(repo)` copies the rule into `<repo>/.cursor/rules/`.
3. `install_user_scope()` copies the rule into `~/.cursor/rules/`.
4. Repeated `enable_repo` is idempotent (byte-identical bytes).
5. `tests/test_wire_distribution.py` covers all four assertions plus the
   package-resource lookup itself.
6. Full `tests/` suite green.

## Files
- add:    `src/canon_systems/templates/rules/memory-platform-build-discipline.mdc`
- modify: `src/canon_systems/repo_enable.py`
- add:    `tests/test_wire_distribution.py`
- modify: `CHANGELOG.md`, `README.md`, `docs/SYSTEM-WORKFLOW.md`
