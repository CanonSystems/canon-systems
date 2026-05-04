RELEASE_STATUS
  initiative: "Canon Readiness Gates"
  task_id: "deploy-attestation"
  verdict: "READY_TO_MERGE"
  branch: "feature/canon-run-ledger-readiness"
  head_sha: "d3528041e391dc930c7634ff906a70eaa7561a14"
  pr_url: "pending"
  qa_gate: "PASS"
  ci_gate: "PASS"
  merge_gate: "PASS"
  environment: "none"
  deploy_gate: "PENDING"
  rollback_ref: "d3528041e391dc930c7634ff906a70eaa7561a14"
  checked_at: "2026-05-04T17:28:00Z"
  evidence:
    - "qa-gate.md verdict PASS with 5/5 acceptance criteria passing"
    - "canon qa-validate --file .cursor/handoffs/canon-readiness-gates/deploy-attestation/qa-gate.md --require-pass -> PASS"
    - "canon qa-validate --file .cursor/handoffs/canon-readiness-gates/deploy-attestation/qa-gate.md --require-pass --handoff-id canon-readiness-gates --task-id deploy-attestation --require-dor-telemetry -> PASS"
    - "canon flow-audit --handoff-id canon-readiness-gates --task-id deploy-attestation --plan-file .cursor/plans/canon_readiness_gates_c389cad8.plan.md --sample-rate 1.0 -> PASS"
    - "python3 -m pytest tests/test_flow_audit.py tests/test_agent_templates.py tests/test_qa_validate.py tests/test_memory_health.py tests/test_readiness.py tests/test_run_ledger.py tests/test_readiness_cli.py tests/test_run_ledger_cli.py -q --tb=short -> 177 passed in 0.31s"
    - "canon memory-health --output .cursor/handoffs/canon-readiness-gates/deploy-attestation/memory-health.json -> overall_status ok"
    - "canon flow-audit --handoff-id canon-readiness-gates --task-id deploy-attestation --plan-file .cursor/plans/canon_readiness_gates_c389cad8.plan.md --sample-rate 1.0 --require-memory-health -> PASS"
  notes:
    - "CANON_STATE_API_URL was unset, so checkpoint read was skipped per the release-orchestrator sandbox skip rule."
    - "The installed canon flow-audit command does not accept --require-dor-telemetry; DoR telemetry-aware validation was enforced through qa-validate."
    - "No push, PR creation, deployment promotion, or plan-file edit was performed."
  blockers: []
  next_action: "Stage and commit deploy-attestation artifacts when the parent orchestrator is ready."
END_RELEASE_STATUS
