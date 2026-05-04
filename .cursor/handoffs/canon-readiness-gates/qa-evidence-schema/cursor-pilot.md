CURSOR_PILOT_PROMPT

<TASK>
Normalize QA evidence labels and actionable qa-validate diagnostics so release orchestrators and reviewers get reliable merge-gate validation because QA evidence is typed, parsed from the correct fields, and failures point to the exact packet line to fix.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: `canon qa-validate` parses `covering_tests` evidence only from acceptance-criterion `covering_tests:` blocks, preserving existing unprefixed pytest refs such as `tests/test_qa_validate.py::test_name`.
- AC2: `covering_tests` entries support explicit evidence kind labels for `pytest`, `manual`, `shell`, and `browser`; unknown or empty kinds fail validation with a message listing the allowed kinds.
- AC3: `pytest` evidence validates the referenced test file exists relative to the repository root, while `manual`, `shell`, and `browser` evidence require non-empty evidence text but do not require a filesystem path.
- AC4: Validation failures include actionable qa-gate packet line numbers for missing `covering_tests`, malformed evidence entries, unknown evidence kinds, and missing pytest files.
- AC5: Existing `qa-validate` merge-gate behavior remains compatible: `--require-pass`, `--require-dor-telemetry`, `--require-checkpoints`, exit codes `0/1/2`, and current successful qa-gate packets still work.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-readiness-gates
- plan_id: canon_readiness_gates_c389cad8
- task_id: qa-evidence-schema
- workstream_id: qa-evidence-schema
- branch: feature/canon-run-ledger-readiness
- Do not edit `/Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md`.
- Do not refactor shared DoR validation in this task.
</CONTEXT>

<PARALLELIZATION_PLAN>
- strategy: "sequential"
- workstreams:
  - id: "ws1"
    goal: "Implement scoped covering_tests parsing and evidence kind normalization."
    depends_on: []
    can_run_parallel: false
  - id: "ws2"
    goal: "Implement evidence validation rules and actionable line-number diagnostics while preserving merge-gate behavior."
    depends_on: ["ws1"]
    can_run_parallel: false
</PARALLELIZATION_PLAN>

<STOP_CONDITIONS>
Each workstream emits HANDOFF_TO_QA_SHARD. Parent aggregates shard outputs into one HANDOFF_TO_QA before qa-gate.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
