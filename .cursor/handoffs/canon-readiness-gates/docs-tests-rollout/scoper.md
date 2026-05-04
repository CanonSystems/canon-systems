HANDOFF_TO_CURSOR_PILOT
  scope_summary: Finalize the Canon Readiness Gates rollout by aligning public docs, packaged/workspace agent templates, and regression tests with the packet archive, run ledger, readiness, QA evidence, DoR telemetry, credential attestation, and deploy attestation work already completed. The task must also close any public CLI documentation drift, especially around `qa-validate`, `flow-audit`, checkpoint/readiness flags, and deploy-attestation behavior, without editing the reference plan file.
  scope_packet:
    identifiers:
      handoff_id: "canon-readiness-gates"
      task_id: "docs-tests-rollout"
      plan_id: "canon_readiness_gates_c389cad8"
      company_id: "CSC"
      repository_id: "canon-systems"
      repo_ref: "feature/canon-run-ledger-readiness@d3528041e391dc930c7634ff906a70eaa7561a14"
    story:
      title: "Document and regression-lock Canon Readiness Gates rollout"
      userValue: "Canon operators and downstream repos get one accurate, cross-repo rollout contract for readiness gates, so public CLI docs, agent behavior, and tests agree before this branch is merged or reused elsewhere."
      acceptanceCriteria:
        - "AC1: Public documentation accurately describes the implemented packet archive, run ledger, readiness check, QA validation, flow audit, credential attestation, and deploy attestation contracts, including command flags, exit codes, state-api boundaries, and explicit deferrals."
        - "AC2: The public `canon` CLI parser, command help, README command table, and workflow docs agree for `qa-validate`, `flow-audit`, `packet-archive`, `run-ledger`, and `readiness check`, including checkpoint and deploy-attestation flags where applicable."
        - "AC3: Packaged and workspace agent templates capture cross-repo rollout expectations for local packet persistence, S3 packet archive, run-ledger/readiness diagnostics, DoR telemetry, credential recovery, memory-health, deploy attestation, and release gates without conflicting with Canon Memory Platform v1 docs."
        - "AC4: Regression tests lock doc/template/CLI parity and cross-repo rollout behavior, including top-level `canon` forwarding for documented validator flags and byte-identity/sync expectations for packaged versus workspace release-orchestrator templates."
        - "AC5: Existing Canon Memory Platform docs and shipped readiness-gate behavior remain compatible: the reference plan file is not edited, secrets are not logged, local `.cursor/handoffs/...` packets remain required, readiness remains read-only/diagnostic, and archive/ledger/checkpoint storage boundaries remain distinct."
    repository:
      primaryLanguages: ["Python", "Markdown", "Terraform"]
      testFramework: "pytest; backend/state-api also uses pytest with moto-backed state-api tests"
      relevantFiles:
        - "README.md"
        - "CHANGELOG.md"
        - "docs/SYSTEM-WORKFLOW.md"
        - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
        - "docs/MEMORY-PLATFORM-PLAN.md"
        - "docs/ROADMAP.md"
        - "docs/CANON-PRIORITIZED-ROADMAP-2026.md"
        - "docs/CANON-SYSTEMS-ONE-PAGER-2026.md"
        - "docs/CANON-PRESENTATION-EVIDENCE.md"
        - "src/canon_systems/cli.py"
        - "src/canon_systems/qa_validate.py"
        - "src/canon_systems/flow_audit.py"
        - "src/canon_systems/readiness_cli.py"
        - "src/canon_systems/run_ledger_cli.py"
        - "src/canon_systems/packet_archive_cli.py"
        - "src/canon_systems/templates/agents/release-orchestrator.md"
        - ".cursor/agents/release-orchestrator.md"
        - "tests/test_agent_templates.py"
        - "tests/test_qa_validate.py"
        - "tests/test_flow_audit.py"
        - "tests/test_readiness_cli.py"
        - "tests/test_run_ledger_cli.py"
        - "tests/test_packet_archive_cli.py"
        - "tests/test_memory_health.py"
    constraints:
      dependencies:
        - "Prior readiness-gate tasks are treated as implemented in the current branch."
        - "Use the in-repo implementation and prior QA packets as evidence; do not edit the external reference plan."
      mustNotBreak:
        - "Do not edit the reference plan file named in the user request."
        - "Do not remove the requirement for local `.cursor/handoffs/<handoff_id>/<task_id>/...` packet files."
        - "Do not make `canon readiness check` mutate checkpoint, archive, or ledger state; it remains read-only and diagnostic."
        - "Do not merge packet bodies into run-ledger rows; ledger archive refs stay metadata-only."
        - "Do not weaken DoR telemetry, checkpoint, memory-health, credential recovery, or deploy attestation gates."
        - "Do not log or document secret values, bearer tokens, signed URLs, or credential payloads."
        - "Do not introduce conflicts with Canon Memory Platform v1 docs, rule distribution, or cross-repo wiring behavior."
    dor_checklist:
      repo_ref_verification: "pass: branch `feature/canon-run-ledger-readiness`, commit `d3528041e391dc930c7634ff906a70eaa7561a14`, remote `origin git@github.com:CanonSystems/canon-systems.git`"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "AC1: Public documentation accurately describes implemented readiness-gate contracts."
        implementation_targets: ["README.md", "CHANGELOG.md", "docs/SYSTEM-WORKFLOW.md", "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md", "docs/MEMORY-PLATFORM-PLAN.md", "docs/ROADMAP.md", "docs/CANON-PRIORITIZED-ROADMAP-2026.md", "docs/CANON-SYSTEMS-ONE-PAGER-2026.md"]
        verification_tests: ["tests/test_readiness_cli.py::test_readiness_check_help_documents_flags", "tests/test_memory_health.py::test_readme_row_present", "new doc parity tests as needed"]
      - criterion: "AC2: Public CLI parser/help/docs agree for qa-validate, flow-audit, packet-archive, run-ledger, and readiness check."
        implementation_targets: ["src/canon_systems/cli.py", "README.md", "docs/SYSTEM-WORKFLOW.md", "tests/test_qa_validate.py", "tests/test_flow_audit.py", "tests/test_readiness_cli.py", "tests/test_run_ledger_cli.py", "tests/test_packet_archive_cli.py"]
        verification_tests: ["new tests for `canon qa-validate --help` / `canon flow-audit --help` checkpoint flags", "tests/test_readiness_cli.py::test_canon_main_dispatches_readiness_check", "tests/test_run_ledger_cli.py::test_canon_main_dispatches_run_ledger_dry_run"]
      - criterion: "AC3: Agent templates capture cross-repo rollout expectations without replacing existing gates."
        implementation_targets: ["src/canon_systems/templates/agents/release-orchestrator.md", ".cursor/agents/release-orchestrator.md", "tests/test_agent_templates.py", "docs/SYSTEM-WORKFLOW.md", "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"]
        verification_tests: ["tests/test_agent_templates.py::test_release_orchestrator_template_has_merge_and_deploy_gates", "tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync", "new template rollout assertions"]
      - criterion: "AC4: Regression tests lock doc/template/CLI parity and cross-repo rollout behavior."
        implementation_targets: ["tests/test_agent_templates.py", "tests/test_qa_validate.py", "tests/test_flow_audit.py", "tests/test_readiness_cli.py", "tests/test_run_ledger_cli.py", "tests/test_packet_archive_cli.py", "src/canon_systems/cli.py"]
        verification_tests: ["tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync", "tests/test_flow_audit.py::test_public_cli_flow_audit_forwards_require_deploy_attestation", "new top-level checkpoint forwarding tests"]
      - criterion: "AC5: Existing docs and behavior remain compatible."
        implementation_targets: ["docs/SYSTEM-WORKFLOW.md", "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md", "docs/MEMORY-PLATFORM-PLAN.md", "src/canon_systems/readiness.py", "src/canon_systems/run_ledger.py", "src/canon_systems/packet_archive.py", "tests/test_readiness.py", "tests/test_run_ledger.py", "tests/test_packet_archive.py"]
        verification_tests: ["tests/test_readiness.py::test_readiness_snapshot_omits_body_fields", "tests/test_run_ledger.py::test_checkpoint_vs_ledger_keys_never_collide", "tests/test_packet_archive.py::test_packet_archived_event_payload_omits_unknown_keys", "new docs boundary assertions as needed"]
    risks_and_assumptions:
      assumptions:
        - "The dirty working tree is expected from prior tasks in this plan; implementation should preserve unrelated user/agent changes and avoid broad rewrites."
        - "Existing prior QA packets are authoritative evidence for already-completed behavior."
        - "Current docs already cover many readiness-gate concepts; this task should reconcile and regression-lock them."
        - "Potential drift exists: README/docs mention `--require-checkpoints`, and underlying validators support it, but top-level CLI parser forwarding may not."
      openQuestions: []
    prior_work_references:
      - artifact_id: "docs/FINAL_STANDUP_CHECKLIST.md"
        source: "mempalace"
        relevance: "Cross-repo rollout reminder from memory."
    retrieval_degradation_notes:
      - "Graph retrieval degraded because Secrets Manager credentials / AXON service configuration were unavailable."
      - "State checkpoint retrieval degraded because local state-api was not reachable."
      - "Canonical retrieval partially degraded because Secrets Manager credentials were unavailable, though one MemPalace hit was returned."
END_HANDOFF_TO_CURSOR_PILOT
