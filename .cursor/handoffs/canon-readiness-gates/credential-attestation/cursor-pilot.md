CURSOR_PILOT_PROMPT

<TASK>
Expose structured credential and Secrets Manager resolution attestation so Canon operators can diagnose credential failures from shared AWS secret resolution plus `canon doctor`, `canon preflight`, and `canon memory-health` without leaking secrets or changing deploy attestation.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: Shared AWS secret resolution exposes a structured, non-secret attestation object that includes effective AWS profile, region, resolved secret id, cache path/existence, cache hit/miss when known, and resolution status without leaking secret values or bearer tokens.
- AC2: The attestation design accounts for process-env versus repo-local env precedence, including the known case where process `AWS_PROFILE=canon-systems` can shadow repo-local `.canon/memory-layer.local.env` `AWS_PROFILE=canon-systems-v2`, and surfaces that mismatch as a warning/degraded credential-resolution signal.
- AC3: `canon doctor --json` includes the structured credential/Secrets Manager attestation and the human doctor output summarizes the effective profile, repo-local profile, resolved secret id, cache status, and actionable mismatch warning while preserving existing tenant, DNS, cache, and raw-IP diagnostics.
- AC4: `canon preflight` records credential/Secrets Manager attestation in `.canon/memory/context-latest.json` and summarizes non-secret credential status in `.canon/memory/context-latest.md` so failed or stale memory hydration shows why resolution degraded.
- AC5: `canon memory-health --json` includes credential/Secrets Manager attestation alongside backend health rows, and the existing exit-code contract remains backend-health driven unless a required backend is unhealthy or usage is invalid.
- AC6: Existing credential recovery, secret fetching, cache behavior, URL hydration, and readiness-gate behavior remain compatible; no deploy attestation, AWS writes, secret value logging, or plan-file edits are introduced.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-readiness-gates
- plan_id: canon_readiness_gates_c389cad8
- task_id: credential-attestation
- workstream_id: credential-attestation
- branch: feature/canon-run-ledger-readiness
- Do not edit `.cursor/plans/canon_readiness_gates_c389cad8.plan.md`.
- Do not leak secret values.
</CONTEXT>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - id: "ws1"
    goal: "Add shared non-secret credential attestation and env-precedence mismatch detection."
    depends_on: []
    can_run_parallel: true
  - id: "ws2"
    goal: "Expose credential attestation through `canon doctor` JSON and human output."
    depends_on: ["ws1"]
    can_run_parallel: true
  - id: "ws3"
    goal: "Persist and summarize credential attestation in preflight context artifacts."
    depends_on: ["ws1"]
    can_run_parallel: true
  - id: "ws4"
    goal: "Expose credential attestation in `canon memory-health --json` without changing health exit semantics."
    depends_on: ["ws1"]
    can_run_parallel: true
</PARALLELIZATION_PLAN>

<STOP_CONDITIONS>
Each stream emits HANDOFF_TO_QA_SHARD. Parent aggregates all shard outputs into one HANDOFF_TO_QA before qa-gate.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
