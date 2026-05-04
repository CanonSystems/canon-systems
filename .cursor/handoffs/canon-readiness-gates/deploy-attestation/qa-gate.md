GATE_RESULTS
  handoff_id: "canon-readiness-gates"
  verdict: PASS
  acceptance_criteria:
    - criterion: "AC1: Release smoke evidence has a documented, structured, non-secret schema that records environment, URL, expected branch/head SHA, deployed commit SHA and/or build identifier, smoke verdict, checked timestamp, and evidence refs; stale or unverifiable deployments use the explicit verdict/reason `environment_smoke_not_proof_of_branch`."
      status: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_deploy_attestation_accepts_current_deployed_sha"
        - "tests/test_flow_audit.py::test_flow_audit_deploy_attestation_requires_expected_branch"
        - "tests/test_flow_audit.py::test_flow_audit_deploy_attestation_stale_verdict"
        - "tests/test_agent_templates.py::test_release_orchestrator_template_has_merge_and_deploy_gates"
      run_result: "pass: deployment-smoke schema is documented in flow_audit and release-orchestrator, requires branch/head identity, accepts matching deployed commit/build proof, and rejects stale verdicts."
    - criterion: "AC2: The release-orchestrator template requires deploy smoke evidence before marking `deploy_gate: PASS`, instructs agents to compare deployed commit/build against the expected branch/head SHA, and blocks promotion when DEV or another environment is on an older build."
      status: PASS
      covering_tests:
        - "tests/test_agent_templates.py::test_release_orchestrator_template_has_merge_and_deploy_gates"
        - "tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync"
      run_result: "pass: release-orchestrator template requires deploy attestation before deploy_gate PASS, blocks older deployed revisions, and packaged/workspace templates remain byte-identical."
    - criterion: "AC3: `canon flow-audit` can require deploy attestation evidence for a task and fails with actionable errors when the deployment smoke evidence file is missing, invalid JSON, missing required identity fields, missing deployed commit/build proof, or shows a deployed SHA/build that does not match the expected branch/head."
      status: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_passes_with_deploy_attestation_for_current_sha"
        - "tests/test_flow_audit.py::test_flow_audit_fails_when_deploy_attestation_missing"
        - "tests/test_flow_audit.py::test_flow_audit_deploy_attestation_invalid_json"
        - "tests/test_flow_audit.py::test_flow_audit_deploy_attestation_identity_mismatch"
        - "tests/test_flow_audit.py::test_flow_audit_deploy_attestation_requires_expected_branch"
        - "tests/test_flow_audit.py::test_flow_audit_fails_when_deploy_attestation_lacks_build_or_sha"
        - "tests/test_flow_audit.py::test_flow_audit_fails_when_deployed_sha_differs_from_expected_sha"
        - "tests/test_flow_audit.py::test_flow_audit_deploy_attestation_build_id_proof_passes"
      run_result: "pass: flow-audit requires deployment-smoke.json only when flagged and emits targeted failures for missing file, invalid JSON, identity gaps, missing proof, stale verdicts, SHA mismatch, and build mismatch conditions."
    - criterion: "AC4: The public `canon flow-audit` CLI forwards the new deploy-attestation requirement flag to `src/canon_systems.flow_audit.run` without regressing existing `--require-release-status`, `--require-memory-health`, `--require-checkpoints`, plan-file, DoR telemetry, or sampling behavior."
      status: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_public_cli_flow_audit_forwards_require_deploy_attestation"
        - "tests/test_flow_audit.py::test_public_cli_flow_audit_deploy_sampling_skip_does_not_validate_file"
        - "tests/test_flow_audit.py::test_flow_audit_deploy_attestation_sampling_skip_does_not_validate_file"
        - "tests/test_flow_audit.py::test_flow_audit_passes_for_valid_artifacts"
        - "tests/test_flow_audit.py::test_flow_audit_passes_with_memory_health_evidence_ok"
        - "tests/test_flow_audit.py::test_flow_audit_require_checkpoints_passes_when_all_five_valid"
      run_result: "pass: public CLI forwards --require-deploy-attestation, deterministic sampling still short-circuits deploy validation, and existing release-status, memory-health, checkpoint, plan-file, and DoR telemetry paths remain covered."
    - criterion: "AC5: Regression coverage proves stale deployed builds are not accepted as branch proof, while existing QA evidence parsing, memory-health gating, checkpoint gating, release template synchronization, and run-ledger/readiness metadata behavior remain compatible."
      status: PASS
      covering_tests:
        - "tests/test_flow_audit.py::test_flow_audit_deploy_attestation_stale_verdict"
        - "tests/test_flow_audit.py::test_flow_audit_fails_when_deployed_sha_differs_from_expected_sha"
        - "tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync"
        - "tests/test_qa_validate.py"
        - "tests/test_memory_health.py"
        - "tests/test_readiness.py"
        - "tests/test_run_ledger.py"
        - "tests/test_readiness_cli.py"
        - "tests/test_run_ledger_cli.py"
      run_result: "pass: python3 -m pytest tests/test_flow_audit.py tests/test_agent_templates.py tests/test_qa_validate.py tests/test_memory_health.py tests/test_readiness.py tests/test_run_ledger.py tests/test_readiness_cli.py tests/test_run_ledger_cli.py -q --tb=short -> 177 passed in 0.32s."
  iterations: 1
  regression_checked: true
  remaining_gaps: []
  notes: "QA found and fixed a schema parity gap between the release-orchestrator deployment-smoke contract and flow-audit validation. Checkpoint read was skipped because CANON_STATE_API_URL is unset in this environment; no plan file was edited."
END_GATE_RESULTS
