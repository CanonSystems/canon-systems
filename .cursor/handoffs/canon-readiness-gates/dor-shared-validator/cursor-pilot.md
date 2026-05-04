CURSOR_PILOT_PROMPT

<TASK>
Extract shared DoR telemetry validation so release governance gets one consistent rejection telemetry artifact contract across `canon qa-validate --require-dor-telemetry` and `canon flow-audit`.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: `canon qa-validate --require-dor-telemetry` and `canon flow-audit` both call a shared DoR telemetry validation helper rather than maintaining separate rejection telemetry validation loops.
- AC2: For every `.cursor/handoffs/<handoff_id>/<task_id>/handoff-not-ready/<stem>.md` packet, both commands require `.cursor/handoffs/<handoff_id>/<task_id>/dor-failure/<stem>.json` and `<stem>.status`, reject invalid/non-object telemetry JSON, and report missing artifacts using actionable paths.
- AC3: The shared helper validates telemetry identity consistently: payload `handoff_id` must match the CLI handoff id, `stage` must be non-empty, and `task_id` must match when present or when the caller opts into requiring task identity.
- AC4: The shared helper validates each telemetry status file contains an `exit_code:` marker, and both commands preserve existing exit-code behavior (`0` pass, `1` validation failure, `2` usage/file errors).
- AC5: Existing non-DoR behavior remains unchanged: qa-gate evidence parsing, checkpoint validation, memory-health validation, release-status checks, plan-file checks, credential handling, and deploy attestation are not refactored or semantically changed.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-readiness-gates
- plan_id: canon_readiness_gates_c389cad8
- task_id: dor-shared-validator
- workstream_id: dor-shared-validator
- branch: feature/canon-run-ledger-readiness
- Do not edit `.cursor/plans/canon_readiness_gates_c389cad8.plan.md`.
- Do not change credential, secret, deploy attestation, memory-health, run-ledger, packet-archive, or readiness behavior.
</CONTEXT>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - id: "ws1"
    goal: "Create shared DoR telemetry validation helper and focused helper-level behavior through CLI-facing tests."
    depends_on: []
    can_run_parallel: false
  - id: "ws2"
    goal: "Refactor qa-validate to use the shared helper while preserving qa-gate and checkpoint behavior."
    depends_on: ["ws1"]
    can_run_parallel: true
  - id: "ws3"
    goal: "Refactor flow-audit to use the shared helper while preserving sampling and non-DoR artifact checks."
    depends_on: ["ws1"]
    can_run_parallel: true
  - id: "ws4"
    goal: "Run focused regression checks and ensure no credential/deploy attestation surface changed."
    depends_on: ["ws2", "ws3"]
    can_run_parallel: false
</PARALLELIZATION_PLAN>

<STOP_CONDITIONS>
Each workstream emits HANDOFF_TO_QA_SHARD. Parent aggregates shard outputs into one HANDOFF_TO_QA before qa-gate.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
