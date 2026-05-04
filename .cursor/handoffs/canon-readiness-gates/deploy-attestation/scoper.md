HANDOFF_TO_CURSOR_PILOT
  scope_summary: Add deployed commit/build attestation to release smoke evidence so browser smoke can prove the deployed environment is running the expected branch head, not merely that an older DEV build is healthy. Scope this to release-orchestrator evidence requirements, flow-audit validation, and CLI/template plumbing needed for that validation; do not implement unrelated docs rollout or edit the plan file.
  scope_packet:
    identifiers:
      handoff_id: "canon-readiness-gates"
      company_id: "CSC"
      repository_id: "canon-systems"
      plan_id: "canon_readiness_gates_c389cad8"
      task_id: "deploy-attestation"
      workstream_id: "deploy-attestation"
      branch: "feature/canon-run-ledger-readiness"
      repo_ref: "d3528041e391dc930c7634ff906a70eaa7561a14"
    story:
      title: "Add deployed commit/build verification to release smoke evidence"
      userValue: "Canon operators benefit because release smoke evidence distinguishes a healthy deployed environment from proof that the current branch/head is deployed, preventing stale DEV builds from being treated as merge-ready evidence."
      acceptanceCriteria:
        - "AC1: Release smoke evidence has a documented, structured, non-secret schema that records environment, URL, expected branch/head SHA, deployed commit SHA and/or build identifier, smoke verdict, checked timestamp, and evidence refs; stale or unverifiable deployments use the explicit verdict/reason `environment_smoke_not_proof_of_branch`."
        - "AC2: The release-orchestrator template requires deploy smoke evidence before marking `deploy_gate: PASS`, instructs agents to compare deployed commit/build against the expected branch/head SHA, and blocks promotion when DEV or another environment is on an older build."
        - "AC3: `canon flow-audit` can require deploy attestation evidence for a task and fails with actionable errors when the deployment smoke evidence file is missing, invalid JSON, missing required identity fields, missing deployed commit/build proof, or shows a deployed SHA/build that does not match the expected branch/head."
        - "AC4: The public `canon flow-audit` CLI forwards the new deploy-attestation requirement flag to `src/canon_systems.flow_audit.run` without regressing existing `--require-release-status`, `--require-memory-health`, `--require-checkpoints`, plan-file, DoR telemetry, or sampling behavior."
        - "AC5: Regression coverage proves stale deployed builds are not accepted as branch proof, while existing QA evidence parsing, memory-health gating, checkpoint gating, release template synchronization, and run-ledger/readiness metadata behavior remain compatible."
    repository:
      primaryLanguages: ["Python", "Markdown", "HCL/Terraform", "Shell"]
      testFramework: "pytest"
      relevantFiles:
        - "src/canon_systems/templates/agents/release-orchestrator.md"
        - ".cursor/agents/release-orchestrator.md"
        - "src/canon_systems/flow_audit.py"
        - "src/canon_systems/cli.py"
        - "tests/test_flow_audit.py"
        - "tests/test_agent_templates.py"
    constraints:
      dependencies:
        - "`src/canon_systems/templates/agents/release-orchestrator.md` and `.cursor/agents/release-orchestrator.md` are expected to stay byte-identical."
        - "`canon flow-audit` currently validates packet presence, DoR telemetry, optional memory-health evidence, checkpoint evidence, release-status evidence, and deterministic sampling."
      mustNotBreak:
        - "Do not edit `.cursor/plans/canon_readiness_gates_c389cad8.plan.md`."
        - "Do not implement unrelated docs rollout."
        - "Do not treat browser smoke success by itself as proof that the current branch/head is deployed."
        - "Do not log or persist secrets, bearer tokens, AWS credentials, or full opaque deployment provider payloads."
        - "Do not break existing `canon flow-audit` exit codes, sampling skip semantics, DoR telemetry validation, memory-health validation, checkpoint validation, or plan-file task lookup."
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "AC1: Release smoke evidence has a documented, structured, non-secret schema that records environment, URL, expected branch/head SHA, deployed commit SHA and/or build identifier, smoke verdict, checked timestamp, and evidence refs; stale or unverifiable deployments use the explicit verdict/reason `environment_smoke_not_proof_of_branch`."
        implementation_targets: ["src/canon_systems/templates/agents/release-orchestrator.md", ".cursor/agents/release-orchestrator.md", "src/canon_systems/flow_audit.py"]
        verification_tests: ["tests/test_agent_templates.py::test_release_orchestrator_template_requires_deploy_attestation_schema", "tests/test_flow_audit.py::test_deploy_attestation_accepts_current_deployed_sha"]
      - criterion: "AC2: The release-orchestrator template requires deploy smoke evidence before marking `deploy_gate: PASS`, instructs agents to compare deployed commit/build against the expected branch/head SHA, and blocks promotion when DEV or another environment is on an older build."
        implementation_targets: ["src/canon_systems/templates/agents/release-orchestrator.md", ".cursor/agents/release-orchestrator.md", "tests/test_agent_templates.py"]
        verification_tests: ["tests/test_agent_templates.py::test_release_orchestrator_template_blocks_stale_deployed_builds", "tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync"]
      - criterion: "AC3: `canon flow-audit` can require deploy attestation evidence for a task and fails with actionable errors when the deployment smoke evidence file is missing, invalid JSON, missing required identity fields, missing deployed commit/build proof, or shows a deployed SHA/build that does not match the expected branch/head."
        implementation_targets: ["src/canon_systems/flow_audit.py", "tests/test_flow_audit.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_passes_with_deploy_attestation_for_current_sha", "tests/test_flow_audit.py::test_flow_audit_fails_when_deploy_attestation_missing", "tests/test_flow_audit.py::test_flow_audit_fails_when_deployed_sha_differs_from_expected_sha", "tests/test_flow_audit.py::test_flow_audit_fails_when_deploy_attestation_lacks_build_or_sha"]
      - criterion: "AC4: The public `canon flow-audit` CLI forwards the new deploy-attestation requirement flag to `src/canon_systems.flow_audit.run` without regressing existing `--require-release-status`, `--require-memory-health`, `--require-checkpoints`, plan-file, DoR telemetry, or sampling behavior."
        implementation_targets: ["src/canon_systems/cli.py", "src/canon_systems/flow_audit.py", "tests/test_flow_audit.py"]
        verification_tests: ["tests/test_flow_audit.py::test_flow_audit_deploy_attestation_sampling_skip_does_not_validate_file", "tests/test_flow_audit.py::test_flow_audit_existing_memory_health_and_checkpoint_flags_still_pass"]
      - criterion: "AC5: Regression coverage proves stale deployed builds are not accepted as branch proof, while existing QA evidence parsing, memory-health gating, checkpoint gating, release template synchronization, and run-ledger/readiness metadata behavior remain compatible."
        implementation_targets: ["tests/test_flow_audit.py", "tests/test_agent_templates.py", "tests/test_qa_validate.py", "tests/test_readiness.py", "tests/test_run_ledger.py"]
        verification_tests: ["tests/test_flow_audit.py", "tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync", "tests/test_qa_validate.py::test_qa_validate_accepts_explicit_evidence_kinds", "tests/test_readiness.py::test_build_readiness_report_ready_when_packets_present", "tests/test_run_ledger.py::test_ac1_optional_verdict_validation_outcomes_commits_pr_deployment"]
    risks_and_assumptions:
      assumptions:
        - "The deploy smoke evidence file should live under `.cursor/handoffs/<handoff_id>/<task_id>/deployment-smoke.json` unless cursor-pilot finds an existing stronger local convention."
        - "A deployed commit SHA match is the preferred proof; a build identifier is acceptable only when the evidence also records the expected build identifier or a provider URL/artifact ref that unambiguously maps to the expected branch/head."
        - "`environment_smoke_not_proof_of_branch` should be treated as a failing deploy-attestation verdict for merge/promotion, even if browser smoke interactions themselves succeeded."
      openQuestions: []
END_HANDOFF_TO_CURSOR_PILOT
