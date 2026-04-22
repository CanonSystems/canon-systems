# E2-T5 Implementer Packet

**Task:** Enforce checkpoint artifacts in flow-audit + qa-validate
**Branch:** `wave/2/canon-memory-v1`
**Model:** composer-2-fast

---

```
HANDOFF_TO_QA
task: E2-T5 — Enforce checkpoint artifacts in flow-audit + qa-validate
branch: wave/2/canon-memory-v1 (tip f1525b6)

files_changed:
  - src/canon_systems/checkpoints.py (NEW): REQUIRED_PHASES tuple; _collect_checkpoint_errors helper
  - src/canon_systems/flow_audit.py (ADDITIVE): import + --require-checkpoints argparse flag + errors.extend(...) gate
  - src/canon_systems/qa_validate.py (ADDITIVE): import + --require-checkpoints argparse flag + handoff/task id guard (exit 2) + errors.extend(...) gate
  - tests/test_flow_audit.py (APPEND): _write_checkpoints helper + 9 new tests
  - tests/test_qa_validate.py (APPEND): _write_minimal_gate_packet + _write_valid_checkpoints helpers + 4 new tests
  - CHANGELOG.md: prepended E2-T5 bullet at top of [Unreleased] ### Added
  - README.md: additive row/sentence mentioning --require-checkpoints for flow-audit + qa-validate (no reflow)
  - docs/SYSTEM-WORKFLOW.md: additive bullet in §6 tying checkpoint enforcement to merge gates

verification:
  - pytest -q → 241 passed (baseline before change was 228; +13 new tests)
  - SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh → exit 0
  - python3 -c "from canon_systems.checkpoints import REQUIRED_PHASES, _collect_checkpoint_errors; assert len(REQUIRED_PHASES)==5" → exit 0
  - No forbidden-surface edits (backend/**, infra/**, templates/**, hooks/**, scripts/**, pyproject.toml, pytest.ini, checkpoint_cli.py, cli.py, .cursor/rules/**, .cursor/plans/**): ∅
  - Existing test bodies unchanged (verified via git diff tests/test_flow_audit.py tests/test_qa_validate.py — only appends)

acceptance_criteria (mapping scoper ACs → covering tests):
  - flow-audit flag present → src/canon_systems/flow_audit.py (argparse) + tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid
  - Five phase paths resolved correctly → tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid, ::test_flow_audit_require_checkpoints_fails_when_phase_file_missing
  - Top-level JSON object + parse errors → tests/test_flow_audit.py::test_flow_audit_require_checkpoints_invalid_json_fails
  - schema_version=="1" → tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_schema_version_not_one
  - phase==stem → tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_field_mismatch
  - task_id matches CLI → tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_task_id_mismatch
  - handoff_id matches CLI → tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_handoff_id_mismatch
  - state_version int>=1 → tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_state_version_missing_or_zero
  - flow-audit exit 1 + FAILED lines → assertions in the six failure tests above
  - Backward compat (no flag → no checkpoint reads) → tests/test_flow_audit.py::test_flow_audit_passes_without_require_checkpoints_without_checkpoints_dir
  - qa-validate flag present → tests/test_qa_validate.py::test_qa_validate_require_checkpoints_passes_on_valid_artifacts
  - qa-validate missing ids → exit 2 → tests/test_qa_validate.py::test_qa_validate_require_checkpoints_exits_2_without_handoff_or_task_id
  - Shared validation, errors appended, exit 1 → tests/test_qa_validate.py::test_qa_validate_require_checkpoints_fails_on_missing_checkpoint_file
  - Composable with --require-pass + --require-dor-telemetry → tests/test_qa_validate.py::test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry
  - Single _collect_checkpoint_errors, no rule duplication → src/canon_systems/checkpoints.py (sole owner); both flow_audit.py + qa_validate.py import it
  - Stdlib-only, no dep changes → pyproject.toml unchanged; checkpoints.py uses json/pathlib
  - Existing tests unchanged → git diff shows only appends
  - Exit codes preserved → 0/1/2 asserted across new tests
  - CHANGELOG/README/SYSTEM-WORKFLOW additive → see files_changed

blockers: none
note: src/canon_systems/checkpoints.py is untracked (new file); parent will stage on commit.
END_HANDOFF_TO_QA
```
