HANDOFF_TO_QA_SHARD
shard_id: ws3
task_id: deploy-attestation
workstream_id: ws3
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8

summary: |
  Extended release-orchestrator templates with deploy smoke evidence schema, stale verdict `environment_smoke_not_proof_of_branch`, and explicit deploy_gate PASS prerequisites including SHA/build parity and blocking promotion when environments lag branch tip. Workspace template synced byte-for-byte.

acceptance_criteria:
  - id: AC1
    status: satisfied
    evidence:
      - "src/canon_systems/templates/agents/release-orchestrator.md"
      - "tests/test_agent_templates.py::test_release_orchestrator_template_has_merge_and_deploy_gates"
  - id: AC2
    status: satisfied
    evidence:
      - "src/canon_systems/templates/agents/release-orchestrator.md"
      - "tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync"

artifacts:
  - src/canon_systems/templates/agents/release-orchestrator.md
  - .cursor/agents/release-orchestrator.md
  - tests/test_agent_templates.py

verification:
  command: "python3 -m pytest tests/test_agent_templates.py::test_release_orchestrator_template_has_merge_and_deploy_gates tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync -v"
  result: "2 passed"
END_HANDOFF_TO_QA_SHARD
