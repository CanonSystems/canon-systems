# E2-T5 QA Gate Packet

**Task:** Enforce checkpoint artifacts in flow-audit + qa-validate
**Branch:** `wave/2/canon-memory-v1`
**Verdict:** PASS

## Reconciliation
Tracked diffs (excluding `.canon/memory/*` churn) touch `CHANGELOG.md`, `README.md`, `docs/SYSTEM-WORKFLOW.md`, `src/canon_systems/flow_audit.py`, `src/canon_systems/qa_validate.py`, and both test files. `src/canon_systems/checkpoints.py` is new and untracked. Matches the implementer handoff. Forbidden-surface check: no paths under `backend/**`, `infra/**`, `scripts/**`, templates, hooks, `checkpoint_cli.py`, `cli.py`, `.cursor/rules/**`, `.cursor/plans/**`, `pyproject.toml`, `pytest.ini`, `requirements-dev.txt`, or `.github/**`.

## Commands
- `pytest -q` → **241 passed** in ~2.7s.
- `SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh` → **exit 0** (build, pytest 220 passed / 21 skipped, terraform skipped).

## Code review
- `REQUIRED_PHASES` has five stems (`scoper`, `cursor-pilot`, `implementer`, `qa-gate`, `release-orchestrator`).
- `_collect_checkpoint_errors` enforces path existence, JSON parse, dict root, `schema_version == "1"`, `phase` vs stem, `task_id` / `handoff_id` vs CLI, and `state_version` as `int` (excluding `bool`) `>= 1`.
- `flow_audit.py` registers `--require-checkpoints` and calls `_collect_checkpoint_errors` only inside `if args.require_checkpoints:`, after memory-health/plan/artifact/DoR checks, before the final `if errors:`.
- `qa_validate.py` registers the flag, returns **2** with the expected usage line when ids are missing, and appends checkpoint errors after gate parsing and optional DoR telemetry.
- Tests: 9 new `test_flow_audit_require_*`/backward-compat functions; 4 new `test_qa_validate_require_checkpoints_*`. Diffs in test files are append-only plus imports; no pre-existing test bodies were rewritten.

## Docs
- CHANGELOG: E2-T5 is the first bullet under `[Unreleased] ### Added` (above E2-T4).
- README: `canon` commands table rows for `qa-validate` and `flow-audit` include `[--require-checkpoints]` (in-place cell updates; table structure unchanged).
- `docs/SYSTEM-WORKFLOW.md` §6: on-disk per-phase checkpoint / merge-gate bullet added.

## Fix iterations
0.

```yaml
GATE_RESULTS
  handoff_id: "E2-T5"
  verdict: PASS
  acceptance_criteria_all_pass: true
  regression_checked: true
  iterations: 0
  acceptance_criteria:
    - id: AC-01
      criterion: "`canon flow-audit` adds a `--require-checkpoints` boolean flag."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid"
      run_result: "Pytest run passes; `flow_audit.py` registers `add_argument('--require-checkpoints', action='store_true')`."
    - id: AC-02
      criterion: "When `--require-checkpoints` is set, the audit requires the five `checkpoints/<phase>.json` files."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_file_missing"
      run_result: "Pass test writes all five; missing-file test asserts failure mentioning missing checkpoint path."
    - id: AC-03
      criterion: "Each file must be valid JSON with a top-level object."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_invalid_json_fails"
      run_result: "Non-object root yields descriptive error; pytest green."
    - id: AC-04
      criterion: "schema_version must be string '1'."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_schema_version_not_one"
      run_result: "Failure output includes schema_version mismatch."
    - id: AC-05
      criterion: "phase must equal filename stem."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_field_mismatch"
      run_result: "Mismatched phase fails with phase mismatch in output."
    - id: AC-06
      criterion: "task_id in JSON must match CLI --task-id."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_task_id_mismatch"
      run_result: "Asserted `task_id mismatch` in CLI output; exit 1."
    - id: AC-07
      criterion: "handoff_id in JSON must match CLI --handoff-id."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_handoff_id_mismatch"
      run_result: "Asserted `handoff_id mismatch` in output."
    - id: AC-08
      criterion: "state_version must be integer >= 1."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_state_version_missing_or_zero"
      run_result: "0 and missing key both produce state_version invalid errors."
    - id: AC-09
      criterion: "flow-audit exits 1 with FAILED banner and per-error lines."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_file_missing"
      run_result: "Test asserts return code 1, `flow-audit: FAILED`, and `- ` error lines."
    - id: AC-10
      criterion: "Without --require-checkpoints, flow-audit unchanged (no checkpoints/ required)."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_passes_without_require_checkpoints_without_checkpoints_dir"
      run_result: "PASS with no checkpoints/ directory when flag omitted."
    - id: AC-11
      criterion: "canon qa-validate adds --require-checkpoints."
      verdict: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_passes_on_valid_artifacts"
      run_result: "Parser and tests exercise the flag; pytest passes."
    - id: AC-12
      criterion: "--require-checkpoints without both ids → exit 2 and usage line."
      verdict: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_exits_2_without_handoff_or_task_id"
      run_result: "Exit 2 and message `qa-validate: --require-checkpoints requires --handoff-id and --task-id`."
    - id: AC-13
      criterion: "qa-validate uses same five paths/fields via shared helper."
      verdict: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_fails_on_missing_checkpoint_file"
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry"
      run_result: "Both import _collect_checkpoint_errors from checkpoints.py."
    - id: AC-14
      criterion: "Checkpoint errors appended after gate + DoR telemetry collection."
      verdict: PASS
      covering_tests:
        - "src/canon_systems/qa_validate.py"
      run_result: "Code order: gate errors, optional DoR telemetry, then _collect_checkpoint_errors into same errors list."
    - id: AC-15
      criterion: "qa-validate non-empty errors → exit 1 + FAILED banner + - lines."
      verdict: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_fails_on_missing_checkpoint_file"
      run_result: "Test asserts exit 1, failure banner, hyphen-prefixed errors."
    - id: AC-16
      criterion: "Single _collect_checkpoint_errors in src/canon_systems/checkpoints.py."
      verdict: PASS
      covering_tests:
        - "src/canon_systems/checkpoints.py"
      run_result: "Single implementation; flow_audit and qa_validate import it."
    - id: AC-17
      criterion: "No duplicated per-field rules across CLIs."
      verdict: PASS
      covering_tests:
        - "src/canon_systems/flow_audit.py"
        - "src/canon_systems/qa_validate.py"
        - "src/canon_systems/checkpoints.py"
      run_result: "Both call imported helper; no local copies."
    - id: AC-18
      criterion: "Stdlib-only, no new deps."
      verdict: PASS
      covering_tests:
        - "src/canon_systems/checkpoints.py"
      run_result: "Uses json/pathlib only; no pyproject/requirements changes."
    - id: AC-19
      criterion: "Existing tests unchanged (append-only)."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py"
        - "tests/test_qa_validate.py"
      run_result: "Diffs show imports + appended EOF functions only."
    - id: AC-20
      criterion: "flow-audit exit contract 0/1/2 preserved."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_file_missing"
      run_result: "Tests assert 0/1; argparse error path unchanged; full suite green."
    - id: AC-21
      criterion: "qa-validate exit contract 0/1/2 preserved."
      verdict: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_passes_on_valid_artifacts"
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_fails_on_missing_checkpoint_file"
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_exits_2_without_handoff_or_task_id"
      run_result: "Tests assert 0/1/2 respectively."
    - id: AC-22
      criterion: "Named flow-audit checkpoint tests present."
      verdict: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_file_missing"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_schema_version_not_one"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_field_mismatch"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_handoff_id_mismatch"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_task_id_mismatch"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_state_version_missing_or_zero"
        - "tests/test_flow_audit.py::test_flow_audit_passes_without_require_checkpoints_without_checkpoints_dir"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_invalid_json_fails"
      run_result: "All nine present and passing."
    - id: AC-23
      criterion: "Named qa-validate checkpoint tests present."
      verdict: PASS
      covering_tests:
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_passes_on_valid_artifacts"
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_fails_on_missing_checkpoint_file"
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_exits_2_without_handoff_or_task_id"
        - "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry"
      run_result: "All four present; pytest node IDs match scoper."
    - id: AC-24
      criterion: "CHANGELOG E2-T5 bullet at top of [Unreleased] ### Added."
      verdict: PASS
      covering_tests:
        - "CHANGELOG.md"
      run_result: "E2-T5 bullet is first; E2-T4 follows."
    - id: AC-25
      criterion: "README mentions --require-checkpoints (no reflow)."
      verdict: PASS
      covering_tests:
        - "README.md"
      run_result: "qa-validate and flow-audit rows updated in place with [--require-checkpoints]."
    - id: AC-26
      criterion: "SYSTEM-WORKFLOW §6 adds merge-gate bullet referencing checkpoints."
      verdict: PASS
      covering_tests:
        - "docs/SYSTEM-WORKFLOW.md"
      run_result: "§6 includes merge-gate / --require-checkpoints line."
    - id: AC-27
      criterion: "Forbidden surfaces untouched; .canon churn out of scope."
      verdict: PASS
      covering_tests:
        - "src/canon_systems/checkpoints.py"
        - "src/canon_systems/flow_audit.py"
        - "src/canon_systems/qa_validate.py"
      run_result: "No intersection with forbidden globs."
  remaining_gaps: []
  notes: "Full pytest (241) and smoke (exit 0) are green."
END_GATE_RESULTS
```
