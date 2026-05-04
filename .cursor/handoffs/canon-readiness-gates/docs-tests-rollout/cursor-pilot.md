CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
</ROLE>

<TASK>
Document and regression-lock the Canon Readiness Gates rollout so operators and downstream repos have one accurate cross-repo contract for packet archive, run ledger, readiness, QA validation, flow audit, DoR telemetry, credential attestation, deploy attestation, and release gates before this branch is merged or reused.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: Public documentation accurately describes the implemented packet archive, run ledger, readiness check, QA validation, flow audit, credential attestation, and deploy attestation contracts, including command flags, exit codes, state-api boundaries, and explicit deferrals.
- AC2: The public `canon` CLI parser, command help, README command table, and workflow docs agree for `qa-validate`, `flow-audit`, `packet-archive`, `run-ledger`, and `readiness check`, including checkpoint and deploy-attestation flags where applicable.
- AC3: Packaged and workspace agent templates capture cross-repo rollout expectations for local packet persistence, S3 packet archive, run-ledger/readiness diagnostics, DoR telemetry, credential recovery, memory-health, deploy attestation, and release gates without conflicting with Canon Memory Platform v1 docs.
- AC4: Regression tests lock doc/template/CLI parity and cross-repo rollout behavior, including top-level `canon` forwarding for documented validator flags and byte-identity/sync expectations for packaged versus workspace release-orchestrator templates.
- AC5: Existing Canon Memory Platform docs and shipped readiness-gate behavior remain compatible: the reference plan file is not edited, secrets are not logged, local `.cursor/handoffs/...` packets remain required, readiness remains read-only/diagnostic, and archive/ledger/checkpoint storage boundaries remain distinct.
</ACCEPTANCE_CRITERIA>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- wave_1:
  - id: "ws1-docs"
    goal: "Align public docs and command tables with implemented readiness-gate contracts."
    depends_on: []
    can_run_parallel: true
  - id: "ws2-cli-parity"
    goal: "Make public `canon` parser/help/forwarding agree with validator and readiness subcommands."
    depends_on: []
    can_run_parallel: true
  - id: "ws3-agent-templates"
    goal: "Update packaged and workspace release-orchestrator templates for rollout expectations while preserving sync."
    depends_on: []
    can_run_parallel: true
  - id: "ws4-compatibility-regression"
    goal: "Lock shipped readiness-gate behavior and storage-boundary compatibility."
    depends_on: []
    can_run_parallel: true
- wave_2:
  - id: "ws5-integration-sweep"
    goal: "Run focused test suite and resolve parity gaps after docs, CLI, template, and compatibility shards land."
    depends_on: ["ws1-docs", "ws2-cli-parity", "ws3-agent-templates", "ws4-compatibility-regression"]
    can_run_parallel: false
</PARALLELIZATION_PLAN>

<CONSTRAINTS>
- Do not edit the reference plan file named in the user request.
- Do not remove the requirement for local `.cursor/handoffs/<handoff_id>/<task_id>/...` packet files.
- Do not make `canon readiness check` mutate checkpoint, archive, or ledger state; it remains read-only and diagnostic.
- Do not merge packet bodies into run-ledger rows; ledger archive refs stay metadata-only.
- Do not weaken DoR telemetry, checkpoint, memory-health, credential recovery, deploy attestation, or release gates.
- Do not log or document secret values, bearer tokens, signed URLs, or credential payloads.
</CONSTRAINTS>

<STOP_CONDITIONS>
Each wave-1 stream emits `HANDOFF_TO_QA_SHARD`. Parent aggregates shards and runs ws5 before invoking qa-gate.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
