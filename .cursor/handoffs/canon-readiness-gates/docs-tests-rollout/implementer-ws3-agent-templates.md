HANDOFF_TO_QA_SHARD
shard_id: ws3-agent-templates
task_id: docs-tests-rollout
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8

summary: |
  Release-orchestrator packaged and workspace templates gained an additive cross-repo
  rollout section covering local packets, packet archive, run-ledger/readiness diagnostics,
  DoR telemetry, credential recovery, memory-health, deploy attestation, and release gates.
  Templates remain byte-synced and pytest locks the rollout expectations.

files_touched:
  - src/canon_systems/templates/agents/release-orchestrator.md
  - .cursor/agents/release-orchestrator.md
  - tests/test_agent_templates.py

acceptance_criteria:
  - id: AC3
    status: satisfied
    evidence:
      - "Template section names local packet quartet, `canon packet-archive`, `canon run-ledger`, read-only `canon readiness check`, DoR telemetry, `canon secrets`, memory-health, deploy attestation, and release gates."
      - "Packaged and workspace templates are byte-identical."
  - id: AC4
    status: satisfied
    evidence:
      - "tests/test_agent_templates.py::test_release_orchestrator_template_cross_repo_rollout_expectations"
      - "tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync"
  - id: AC5
    status: satisfied
    evidence:
      - "Template changes are additive and preserve existing gates."

verification:
  - "python3 -m pytest tests/test_agent_templates.py::test_release_orchestrator_template_cross_repo_rollout_expectations tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync tests/test_agent_templates.py::test_release_orchestrator_template_has_merge_and_deploy_gates -q -> 3 passed"

notes: |
  Graph retrieval and checkpoint hydrate degraded in the sandbox. The reference plan file was not edited.

END_HANDOFF_TO_QA_SHARD
