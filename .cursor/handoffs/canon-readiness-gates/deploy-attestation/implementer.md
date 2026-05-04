HANDOFF_TO_QA
task_id: deploy-attestation
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
workstream_id: deploy-attestation

summary: |
  Implemented deployed commit/build verification for release smoke evidence.
  `canon flow-audit` can now require `.cursor/handoffs/<handoff_id>/<task_id>/deployment-smoke.json`
  and rejects missing, invalid, stale, or mismatched deploy proof. The public CLI
  forwards `--require-deploy-attestation`, and release-orchestrator templates now require
  deploy attestation before `deploy_gate: PASS`.

acceptance_criteria:
  - id: AC1
    status: satisfied
    evidence:
      - "src/canon_systems/flow_audit.py deployment-smoke schema"
      - "src/canon_systems/templates/agents/release-orchestrator.md deploy smoke evidence schema"
      - "tests/test_flow_audit.py::test_deploy_attestation_accepts_current_deployed_sha"
      - "tests/test_agent_templates.py::test_release_orchestrator_template_has_merge_and_deploy_gates"
  - id: AC2
    status: satisfied
    evidence:
      - "src/canon_systems/templates/agents/release-orchestrator.md deploy gate requirements"
      - ".cursor/agents/release-orchestrator.md synced template"
      - "tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync"
  - id: AC3
    status: satisfied
    evidence:
      - "src/canon_systems/flow_audit.py::_collect_deploy_attestation_errors"
      - "tests/test_flow_audit.py::test_flow_audit_passes_with_deploy_attestation_for_current_sha"
      - "tests/test_flow_audit.py::test_flow_audit_fails_when_deploy_attestation_missing"
      - "tests/test_flow_audit.py::test_flow_audit_fails_when_deployed_sha_differs_from_expected_sha"
      - "tests/test_flow_audit.py::test_flow_audit_fails_when_deploy_attestation_lacks_build_or_sha"
      - "tests/test_flow_audit.py::test_flow_audit_deploy_attestation_stale_verdict"
  - id: AC4
    status: satisfied
    evidence:
      - "src/canon_systems/cli.py flow-audit --require-deploy-attestation forwarding"
      - "tests/test_flow_audit.py::test_public_cli_flow_audit_forwards_require_deploy_attestation"
      - "tests/test_flow_audit.py::test_public_cli_flow_audit_deploy_sampling_skip_does_not_validate_file"
  - id: AC5
    status: satisfied
    evidence:
      - "python3 -m pytest tests/test_flow_audit.py tests/test_agent_templates.py tests/test_qa_validate.py tests/test_memory_health.py tests/test_readiness.py tests/test_run_ledger.py tests/test_readiness_cli.py tests/test_run_ledger_cli.py -q --tb=short -> 176 passed"

files_touched:
  - src/canon_systems/flow_audit.py
  - src/canon_systems/cli.py
  - src/canon_systems/templates/agents/release-orchestrator.md
  - .cursor/agents/release-orchestrator.md
  - tests/test_flow_audit.py
  - tests/test_agent_templates.py

verification:
  - command: "python3 -m pytest tests/test_flow_audit.py -q"
    result: "37 passed"
  - command: "python3 -m pytest tests/test_agent_templates.py::test_release_orchestrator_template_has_merge_and_deploy_gates tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync -v"
    result: "2 passed"
  - command: "python3 -m pytest tests/test_flow_audit.py tests/test_agent_templates.py tests/test_qa_validate.py tests/test_memory_health.py tests/test_readiness.py tests/test_run_ledger.py tests/test_readiness_cli.py tests/test_run_ledger_cli.py -q --tb=short"
    result: "176 passed"

notes: |
  Graph retrieval degraded with SSL verification failures. State checkpoint reads degraded
  because the local state-api was not reachable; no checkpoint writes were attempted.
  The attached plan file was not edited.

shards:
  - .cursor/handoffs/canon-readiness-gates/deploy-attestation/implementer-ws1.md
  - .cursor/handoffs/canon-readiness-gates/deploy-attestation/implementer-ws2.md
  - .cursor/handoffs/canon-readiness-gates/deploy-attestation/implementer-ws3.md
  - .cursor/handoffs/canon-readiness-gates/deploy-attestation/implementer-ws4.md

END_HANDOFF_TO_QA
