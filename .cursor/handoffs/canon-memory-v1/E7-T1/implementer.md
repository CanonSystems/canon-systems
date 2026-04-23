# HANDOFF_TO_QA — E7-T1 hard-lock rule distribution

## Status
READY_FOR_QA

## Changes
- Copied workspace rule to
  `src/canon_systems/templates/rules/memory-platform-build-discipline.mdc`
  (byte-identical).
- Extended `repo_enable.enable_repo()` and
  `repo_enable.install_user_scope()` to install the new rule alongside
  `memory-layer-defaults.mdc`.
- Added `tests/test_wire_distribution.py` — 5 tests covering packaging,
  byte-identity with the workspace rule, installation via `enable_repo`,
  idempotence, and user-scope installation.

## Test evidence
- `tests/test_wire_distribution.py` — 5/5 passed.
- `tests/test_repo_enable.py` — 3/3 passed (pre-existing enable_repo contract).
- Full `tests/` suite — 440/440 passed.

## AC coverage
- AC1 template present + byte-identical: `test_template_rule_is_packaged`,
  `test_template_rule_byte_identical_to_workspace`.
- AC2 installed into repo: `test_enable_repo_installs_hard_lock_rule`.
- AC3 user scope install: `test_install_user_scope_installs_hard_lock_rule`.
- AC4 idempotent: `test_enable_repo_install_is_idempotent`.
- AC5 test suite exists: this test file.
- AC6 full suite green: see test evidence.

## Deviations
None.
