CURSOR_PILOT_PROMPT

<TASK>
Add deployed commit/build verification to release smoke evidence so Canon operators can prove that the deployed environment is running the expected branch/head, not merely that an older healthy environment passed browser smoke.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: Release smoke evidence has a documented, structured, non-secret schema that records environment, URL, expected branch/head SHA, deployed commit SHA and/or build identifier, smoke verdict, checked timestamp, and evidence refs; stale or unverifiable deployments use the explicit verdict/reason `environment_smoke_not_proof_of_branch`.
- AC2: The release-orchestrator template requires deploy smoke evidence before marking `deploy_gate: PASS`, instructs agents to compare deployed commit/build against the expected branch/head SHA, and blocks promotion when DEV or another environment is on an older build.
- AC3: `canon flow-audit` can require deploy attestation evidence for a task and fails with actionable errors when the deployment smoke evidence file is missing, invalid JSON, missing required identity fields, missing deployed commit/build proof, or shows a deployed SHA/build that does not match the expected branch/head.
- AC4: The public `canon flow-audit` CLI forwards the new deploy-attestation requirement flag to `src/canon_systems.flow_audit.run` without regressing existing `--require-release-status`, `--require-memory-health`, `--require-checkpoints`, plan-file, DoR telemetry, or sampling behavior.
- AC5: Regression coverage proves stale deployed builds are not accepted as branch proof, while existing QA evidence parsing, memory-health gating, checkpoint gating, release template synchronization, and run-ledger/readiness metadata behavior remain compatible.
</ACCEPTANCE_CRITERIA>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - id: "ws1"
    goal: "Add deploy attestation validation to flow-audit"
    depends_on: []
    can_run_parallel: true
  - id: "ws2"
    goal: "Add public CLI flag forwarding"
    depends_on: ["ws1"]
    can_run_parallel: false
  - id: "ws3"
    goal: "Update release-orchestrator deploy evidence requirements"
    depends_on: []
    can_run_parallel: true
  - id: "ws4"
    goal: "Run compatibility regressions for existing gates"
    depends_on: ["ws1", "ws2", "ws3"]
    can_run_parallel: false
</PARALLELIZATION_PLAN>

<STOP_CONDITIONS>
Each stream emits HANDOFF_TO_QA_SHARD. Parent aggregates all shard outputs into one HANDOFF_TO_QA before qa-gate.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
