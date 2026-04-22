# E2-T5 Scoper Packet

**Task:** Enforce checkpoint artifacts in flow-audit + qa-validate
**Wave branch:** `wave/2/canon-memory-v1`
**Produced by:** scoper subagent (ID 95c7f4b2-692a-4fc2-93e2-e9253a17a77e)

---

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: E2-T5 adds an opt-in `--require-checkpoints` flag to both `canon flow-audit` and `canon qa-validate` so merge gates can fail when per-phase JSON checkpoint artifacts are missing or invalid under `.cursor/handoffs/<handoff_id>/<task_id>/checkpoints/`. Validation logic lives in a single shared helper `_collect_checkpoint_errors(*, root, handoff_id, task_id) -> list[str]`; tests only exercise the filesystem; living-spec updates document the new flags while respecting forbidden surfaces and verbatim preservation of existing tests.
  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      company_id: "IMC"
      repository_id: "innermost"
    story:
      title: "E2-T5: Enforce checkpoint artifacts in flow-audit + qa-validate"
      userValue: "Release and merge governance consumers can block integration when any of the five §B phase checkpoint files is missing, malformed, or inconsistent with the active handoff/task, reducing silent phase-boundary gaps before merge."
      acceptanceCriteria:
        - "`canon flow-audit` adds a `--require-checkpoints` boolean flag."
        - "When `--require-checkpoints` is set, the audit requires files at `.cursor/handoffs/<handoff_id>/<task_id>/checkpoints/scoper.json`, `cursor-pilot.json`, `implementer.json`, `qa-gate.json`, and `release-orchestrator.json`."
        - "Each required checkpoint file MUST be valid JSON with a JSON object at the top level (not an array, string, or primitive-only root)."
        - "Each object MUST include `schema_version` exactly equal to the string `\"1\"`."
        - "Each object MUST include `phase` exactly equal to the filename stem (e.g. `scoper.json` ⇒ `phase` is `scoper`)."
        - "Each object MUST include `task_id` exactly equal to the CLI `--task-id` value."
        - "Each object MUST include `handoff_id` exactly equal to the CLI `--handoff-id` value."
        - "Each object MUST include `state_version` as an integer with value >= 1 (must fail when missing, non-integer, or 0)."
        - "On any checkpoint validation failure, `flow-audit` exits `1`, prints `flow-audit: FAILED`, and prints one `- <descriptive error>` line per issue."
        - "When `--require-checkpoints` is NOT set, `flow-audit` MUST NOT read or assert on the `checkpoints/` directory; all prior default behavior is unchanged."
        - "`canon qa-validate` adds a `--require-checkpoints` boolean flag."
        - "When `--require-checkpoints` is set, both `--handoff-id` and `--task-id` MUST be present and non-empty after strip; otherwise exit `2` with a usage line mirroring the `--require-dor-telemetry` pattern."
        - "With `--require-checkpoints`, `qa-validate` validates the same five paths and the same field rules as `flow-audit` using the shared helper only."
        - "Checkpoint errors MUST be appended to the existing `errors` list after prior gate and DoR telemetry collection (additive error list)."
        - "On any non-empty `errors` list, `qa-validate` exits `1`, prints `qa-validate: FAILED`, and prints one `- <error>` line per accumulated error."
        - "A single shared function `_collect_checkpoint_errors(*, root: Path, handoff_id: str, task_id: str) -> list[str]` holds all per-field checkpoint rules (implemented in a new `src/canon_systems/checkpoints.py` or exported from `flow_audit.py`)."
        - "`flow_audit` and `qa_validate` import and call that shared function; there is no duplicated validation logic between the two CLIs."
        - "New code paths are stdlib-only (e.g. `json`, `argparse`, `pathlib`); do not add dependencies or change `pyproject.toml` / `requirements-dev.txt`."
        - "All pre-existing test functions and bodies in `tests/test_flow_audit.py` and `tests/test_qa_validate.py` remain unchanged verbatim (append-only new tests only)."
        - "`flow-audit` exit contract remains: `0` pass, `1` fail, `2` reserved for usage/argparse as today."
        - "`qa-validate` exit contract remains: `0` pass, `1` fail, `2` usage or unrecoverable packet errors as today."
        - "Add `test_flow_audit_require_checkpoints_passes_when_all_five_valid`: `--require-checkpoints` exit `0` when all five files are valid."
        - "Add `test_flow_audit_require_checkpoints_fails_when_phase_file_missing`: exit `1` and descriptive error when one of five is absent."
        - "Add `test_flow_audit_require_checkpoints_fails_when_schema_version_not_one`: exit `1` when `schema_version` is not string `\"1\"`."
        - "Add `test_flow_audit_require_checkpoints_fails_when_phase_field_mismatch`: exit `1` when `phase` does not match stem."
        - "Add `test_flow_audit_require_checkpoints_fails_when_handoff_id_mismatch`: exit `1` when JSON `handoff_id` ≠ CLI."
        - "Add `test_flow_audit_require_checkpoints_fails_when_task_id_mismatch`: exit `1` when JSON `task_id` ≠ CLI."
        - "Add `test_flow_audit_require_checkpoints_fails_when_state_version_missing_or_zero`: exit `1` for invalid `state_version`."
        - "Add `test_flow_audit_passes_without_require_checkpoints_without_checkpoints_dir`: no `--require-checkpoints` does not require `checkpoints/` (backward compatibility)."
        - "Add `test_qa_validate_require_checkpoints_passes_on_valid_artifacts`: exit `0` on valid gate packet + valid checkpoints with `--require-checkpoints`."
        - "Add `test_qa_validate_require_checkpoints_fails_on_missing_checkpoint_file`: exit `1` with expected failure output."
        - "Add `test_qa_validate_require_checkpoints_exits_2_without_handoff_or_task_id`: exit `2` with usage line if ids missing when flag set."
        - "Add `test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry`: exit `0` when gate, DOR, and checkpoints all valid."
        - "CHANGELOG.md: prepend one bullet at the TOP of `[Unreleased]` → `### Added` (above the E2-T4 bullet) with the exact E2-T5 text from the task brief."
        - "README.md: one additive mention of `--require-checkpoints` in the `canon` commands table or adjacent prose; do not reflow the table."
        - "docs/SYSTEM-WORKFLOW.md §6: add one additive bullet tying per-phase checkpoint file enforcement to merge gates."
        - "Do not modify: `backend/**`, `infra/**`, `.cursor/rules/**`, `.cursor/plans/**`, `.github/workflows/**`, `pyproject.toml`, `pytest.ini`, `requirements-dev.txt`, `scripts/**`, `src/canon_systems/templates/**`, `src/canon_systems/hooks/**`, or `src/canon_systems/checkpoint_cli.py`."
    repository:
      primaryLanguages: ["Python"]
      testFramework: "pytest"
      relevantFiles:
        - "src/canon_systems/flow_audit.py"
        - "src/canon_systems/qa_validate.py"
        - "src/canon_systems/checkpoints.py"
        - "tests/test_flow_audit.py"
        - "tests/test_qa_validate.py"
        - "CHANGELOG.md"
        - "README.md"
        - "docs/SYSTEM-WORKFLOW.md"
    constraints:
      dependencies: ["E2-T4 completed: templates reference checkpoint read/write; this task only enforces on-disk files in CLIs."]
      mustNotBreak: ["Default CLI behavior without new flags; all existing tests; exit-code semantics for successful and failing runs."]
    invariants:
      - "Checkpoint validation runs only when `--require-checkpoints` is passed."
      - "The five required phase stems are: scoper, cursor-pilot, implementer, qa-gate, release-orchestrator."
      - "Single shared `_collect_checkpoint_errors` is the only source of field rules."
    non_goals:
      - "Network calls to `state-api` or hooks that write `checkpoints/*.json` (later work)."
      - "Any change to `checkpoint_cli.py` or HTTP wire protocol."
    done_signals:
      - "`pytest -q` green (~237+ tests passed)."
      - "`SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh` green."
      - "`canon qa-validate` on the E2-T5 `qa-gate` packet with `--require-pass` exits `0`."
    forbidden_surfaces:
      - "backend/**"
      - "infra/**"
      - ".cursor/rules/**"
      - ".cursor/plans/**"
      - ".github/workflows/**"
      - "pyproject.toml"
      - "pytest.ini"
      - "requirements-dev.txt"
      - "scripts/**"
      - "src/canon_systems/templates/**"
      - "src/canon_systems/hooks/**"
      - "src/canon_systems/checkpoint_cli.py"
    dor_checklist:
      repo_ref_verification: "pass — base branch `wave/2/canon-memory-v1` at tip `f1525b6` (re-verify after any rebase)."
      ac_traceability: "pass — each AC below maps to code targets and a named test or explicit doc/verification path."
    ac_traceability:
      - criterion: "`canon flow-audit` adds `--require-checkpoints`."
        implementation_targets: ["src/canon_systems/flow_audit.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid"]
      - criterion: "Five `checkpoints/<phase>.json` files required when flag is set."
        implementation_targets: ["src/canon_systems/flow_audit.py", "src/canon_systems/checkpoints.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid", "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_file_missing"]
      - criterion: "Top-level JSON object; parse failures produce descriptive errors."
        implementation_targets: ["src/canon_systems/checkpoints.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_file_missing"]
      - criterion: "`schema_version` string `\"1\"` required."
        implementation_targets: ["src/canon_systems/checkpoints.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_schema_version_not_one"]
      - criterion: "`phase` matches filename stem."
        implementation_targets: ["src/canon_systems/checkpoints.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_field_mismatch"]
      - criterion: "`task_id` in JSON matches CLI."
        implementation_targets: ["src/canon_systems/checkpoints.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_task_id_mismatch"]
      - criterion: "`handoff_id` in JSON matches CLI."
        implementation_targets: ["src/canon_systems/checkpoints.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_handoff_id_mismatch"]
      - criterion: "`state_version` int >= 1."
        implementation_targets: ["src/canon_systems/checkpoints.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_state_version_missing_or_zero"]
      - criterion: "flow-audit: exit `1`, `flow-audit: FAILED`, `-` lines on checkpoint failure."
        implementation_targets: ["src/canon_systems/flow_audit.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_require_checkpoints_fails_when_phase_file_missing"]
      - criterion: "Without flag, no checkpoint assertions."
        implementation_targets: ["src/canon_systems/flow_audit.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_passes_without_require_checkpoints_without_checkpoints_dir"]
      - criterion: "`canon qa-validate` adds `--require-checkpoints`."
        implementation_targets: ["src/canon_systems/qa_validate.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_require_checkpoints_passes_on_valid_artifacts"]
      - criterion: "`--require-checkpoints` requires both ids; else exit `2`."
        implementation_targets: ["src/canon_systems/qa_validate.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_require_checkpoints_exits_2_without_handoff_or_task_id"]
      - criterion: "Same five paths and fields; errors appended to list."
        implementation_targets: ["src/canon_systems/qa_validate.py", "src/canon_systems/checkpoints.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_require_checkpoints_fails_on_missing_checkpoint_file", "tests/test_qa_validate.py::test_qa_validate_require_checkpoints_composable_with_require_pass_and_require_dor_telemetry"]
      - criterion: "qa-validate: exit `1`, `qa-validate: FAILED`, `-` lines when errors."
        implementation_targets: ["src/canon_systems/qa_validate.py"]
        verification_tests: ["tests/test_qa_validate.py::test_qa_validate_require_checkpoints_fails_on_missing_checkpoint_file"]
      - criterion: "Single `_collect_checkpoint_errors`; no duplicated rules."
        implementation_targets: ["src/canon_systems/checkpoints.py"]
        verification_tests: ["tests/test_flow_audit.py and tests/test_qa_validate.py both exercise shared errors"]
      - criterion: "Stdlib-only; no new deps."
        implementation_targets: ["src/canon_systems/checkpoints.py", "src/canon_systems/flow_audit.py", "src/canon_systems/qa_validate.py"]
        verification_tests: ["review: no changes to pyproject.toml / requirements-dev.txt"]
      - criterion: "Existing tests verbatim."
        implementation_targets: ["tests/test_flow_audit.py", "tests/test_qa_validate.py"]
        verification_tests: ["git diff: no edits inside pre-E2-T5 test bodies"]
      - criterion: "Exit codes preserved for both CLIs."
        implementation_targets: ["src/canon_systems/flow_audit.py", "src/canon_systems/qa_validate.py"]
        verification_tests: ["all new + existing tests assert return codes"]
      - criterion: "CHANGELOG prepended E2-T5 Added bullet (exact spec wording)."
        implementation_targets: ["CHANGELOG.md"]
        verification_tests: ["reviewer: first Added bullet is E2-T5 string"]
      - criterion: "README additive `--require-checkpoints` mention; no reflow."
        implementation_targets: ["README.md"]
        verification_tests: ["reviewer: single-line or additive diff only in commands section"]
      - criterion: "SYSTEM-WORKFLOW.md §6 one bullet for merge-gate checkpoint enforcement."
        implementation_targets: ["docs/SYSTEM-WORKFLOW.md"]
        verification_tests: ["reviewer: §6 contains new bullet"]
      - criterion: "Forbidden surfaces list honored."
        implementation_targets: ["repository"]
        verification_tests: ["git diff name-only: zero paths under forbidden globs"]
    risks_and_assumptions:
      assumptions:
        - "On-disk `schema_version` is the string `\"1\"` (task spec); `docs/MEMORY-PLATFORM-BACKLOG.md` §B example uses numeric `1` for DynamoDB — file artifact contract for this task follows the E2-T5 spec."
        - "`company_id` and `repository_id` in identifiers come from `.canon/memory/context-latest.md` because `.canon/memory-layer.local.env` was not found in-repo at scoping time."
      openQuestions: []
    prior_work_references: []
END_HANDOFF_TO_CURSOR_PILOT
```
