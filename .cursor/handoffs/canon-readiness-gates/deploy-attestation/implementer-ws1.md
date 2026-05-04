HANDOFF_TO_QA_SHARD
shard_id: ws1
task_id: deploy-attestation
handoff_id: canon-readiness-gates

summary: |
  Implemented deploy smoke attestation validation in `flow_audit.run` behind `--require-deploy-attestation`, reading `.cursor/handoffs/<handoff>/<task>/deployment-smoke.json`. Added schema v1 in module docstring, validation for identity, required fields, stale verdict `environment_smoke_not_proof_of_branch`, deployed SHA vs expected SHA, and build-id proof.

acceptance_criteria:
  - id: AC1
    status: SATISFIED
    evidence:
      - "src/canon_systems/flow_audit.py deployment-smoke schema"
      - "tests/test_flow_audit.py::test_deploy_attestation_accepts_current_deployed_sha"
  - id: AC3
    status: SATISFIED
    evidence:
      - "src/canon_systems/flow_audit.py::_collect_deploy_attestation_errors"
      - "tests/test_flow_audit.py::test_flow_audit_passes_with_deploy_attestation_for_current_sha"
      - "tests/test_flow_audit.py::test_flow_audit_fails_when_deploy_attestation_missing"
      - "tests/test_flow_audit.py::test_flow_audit_fails_when_deployed_sha_differs_from_expected_sha"
      - "tests/test_flow_audit.py::test_flow_audit_fails_when_deploy_attestation_lacks_build_or_sha"

verification:
  command: "python3 -m pytest tests/test_flow_audit.py -v --tb=short -q"
  result: "35 passed"
END_HANDOFF_TO_QA_SHARD
