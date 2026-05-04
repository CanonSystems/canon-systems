HANDOFF_TO_QA_SHARD
shard_id: ws4
task_id: deploy-attestation
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
workstream_id: ws4

summary: |
  Ran focused compatibility regressions for deploy-attestation without code changes.
  Stale deploy and SHA/proof failures remain covered; qa-validate, memory-health,
  checkpoint, release template sync, and run-ledger/readiness tests all pass together.

acceptance_criteria:
  - id: AC5
    status: satisfied
    evidence:
      - command: "python3 -m pytest tests/test_flow_audit.py tests/test_agent_templates.py tests/test_qa_validate.py tests/test_memory_health.py tests/test_readiness.py tests/test_run_ledger.py tests/test_readiness_cli.py tests/test_run_ledger_cli.py -q --tb=short"
        result: "176 passed in 0.30s"
      - path: tests/test_flow_audit.py
        note: "Covers stale deploy verdict, expected/deployed SHA mismatch, missing deploy proof, memory-health gating, and checkpoint gating."
      - path: tests/test_agent_templates.py
        note: "Release-orchestrator template parity remains green."
      - path: tests/test_qa_validate.py
        note: "QA evidence parsing remains compatible."
      - path: tests/test_memory_health.py
        note: "memory-health behavior remains compatible."
      - path: tests/test_readiness.py
      - path: tests/test_run_ledger.py
      - path: tests/test_readiness_cli.py
      - path: tests/test_run_ledger_cli.py

retrieval_breakdown_event: |
  {"schema_version":1,"event_id":"retrieval_ws4_deploy_attestation_20260504","parent_event_id":"implementer_parent_deploy_attestation","event_type":"retrieval_breakdown","company_id":"CSC","repository_id":"canon-systems","plan_id":"canon_readiness_gates_c389cad8","task_id":"deploy-attestation","handoff_id":"canon-readiness-gates","agent_name":"implementer","agent_run_id":"implementer-ws4-compat","actor_id":"cursor-subagent","model":"composer-2-fast","timestamp":"2026-05-04T17:22:45Z","state_version":0,"payload":{"sources":{"graph":{"tokens_in":95,"tokens_out":0},"state":{"tokens_in":0,"tokens_out":0},"canonical":{"tokens_in":1200,"tokens_out":320},"file":{"tokens_in":14200,"tokens_out":6100}},"totals":{"tokens_in":15495,"tokens_out":6420}}}

notes: |
  Graph query failed with exit 5 / SSL verification failure. Checkpoint read failed
  with exit 5 / localhost refused; no checkpoint write. The plan file was not edited.

files_touched: []

verification:
  command: "python3 -m pytest tests/test_flow_audit.py tests/test_agent_templates.py tests/test_qa_validate.py tests/test_memory_health.py tests/test_readiness.py tests/test_run_ledger.py tests/test_readiness_cli.py tests/test_run_ledger_cli.py -q --tb=short"
  result: "176 passed"

END_HANDOFF_TO_QA_SHARD
