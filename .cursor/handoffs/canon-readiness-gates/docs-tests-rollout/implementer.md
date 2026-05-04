HANDOFF_TO_QA
task_id: docs-tests-rollout
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
workstream_id: docs-tests-rollout

summary: |
  Finalized cross-repo rollout documentation, CLI parity, agent-template guidance, and
  regression coverage for Canon Readiness Gates. Public docs now describe the implemented
  packet archive, run ledger, readiness check, QA/flow audit, credential attestation, and
  deploy attestation surfaces; top-level CLI forwarding and template sync are regression-locked.

acceptance_criteria:
  - id: AC1
    status: satisfied
    evidence:
      - "README.md command table and readiness scope language"
      - "CHANGELOG.md Unreleased readiness/doctor/flow-audit notes"
      - "docs/SYSTEM-WORKFLOW.md section 6"
      - "docs/MEMORY-PLATFORM-PLAN.md storage boundary and v1 archive/ledger language"
      - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md no-secret credential attestation language"
      - "docs/ROADMAP.md and product/strategy docs updated for v1 rollout vs future productization"
  - id: AC2
    status: satisfied
    evidence:
      - "src/canon_systems/cli.py forwards `--require-checkpoints` for qa-validate and flow-audit"
      - "src/canon_systems/flow_audit.py documents checkpoint flag behavior"
      - "tests/test_qa_validate.py and tests/test_flow_audit.py public CLI parity tests"
      - "tests/test_readiness_cli.py, tests/test_run_ledger_cli.py, tests/test_packet_archive_cli.py help/dispatch coverage"
  - id: AC3
    status: satisfied
    evidence:
      - "src/canon_systems/templates/agents/release-orchestrator.md additive cross-repo rollout section"
      - ".cursor/agents/release-orchestrator.md byte-synced workspace copy"
      - "tests/test_agent_templates.py::test_release_orchestrator_template_cross_repo_rollout_expectations"
  - id: AC4
    status: satisfied
    evidence:
      - "CLI forwarding/help parity tests"
      - "agent template sync and rollout expectation tests"
      - "storage boundary docs/tests for readiness, run-ledger, and packet archive"
  - id: AC5
    status: satisfied
    evidence:
      - "tests/test_readiness.py read-only diagnostics and snapshot body omissions"
      - "tests/test_run_ledger.py metadata-only archive refs and checkpoint-vs-ledger key separation"
      - "tests/test_packet_archive.py packet_archived allowlist and credential/body omissions"
      - "Docs preserve required local packets and separate checkpoint/ledger/archive stores"

files_touched:
  - README.md
  - CHANGELOG.md
  - docs/SYSTEM-WORKFLOW.md
  - docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md
  - docs/MEMORY-PLATFORM-PLAN.md
  - docs/ROADMAP.md
  - docs/CANON-PRIORITIZED-ROADMAP-2026.md
  - docs/CANON-SYSTEMS-ONE-PAGER-2026.md
  - docs/CANON-PRESENTATION-EVIDENCE.md
  - src/canon_systems/cli.py
  - src/canon_systems/flow_audit.py
  - src/canon_systems/templates/agents/release-orchestrator.md
  - .cursor/agents/release-orchestrator.md
  - tests/test_agent_templates.py
  - tests/test_qa_validate.py
  - tests/test_flow_audit.py
  - tests/test_readiness_cli.py
  - tests/test_run_ledger_cli.py
  - tests/test_packet_archive_cli.py
  - tests/test_readiness.py
  - tests/test_run_ledger.py
  - tests/test_packet_archive.py

verification:
  - "python3 -m pytest tests/test_agent_templates.py tests/test_qa_validate.py tests/test_flow_audit.py tests/test_readiness_cli.py tests/test_run_ledger_cli.py tests/test_packet_archive_cli.py tests/test_memory_health.py tests/test_readiness.py tests/test_run_ledger.py tests/test_packet_archive.py -q --tb=short -> 200 passed"

notes:
  - "Graph retrieval degraded due missing AXON/AWS configuration; state checkpoint reads were skipped/degraded when state-api was unavailable."
  - "The user-provided reference plan file was not edited."

shards:
  - .cursor/handoffs/canon-readiness-gates/docs-tests-rollout/implementer-ws1-docs.md
  - .cursor/handoffs/canon-readiness-gates/docs-tests-rollout/implementer-ws2-cli-parity.md
  - .cursor/handoffs/canon-readiness-gates/docs-tests-rollout/implementer-ws3-agent-templates.md
  - .cursor/handoffs/canon-readiness-gates/docs-tests-rollout/implementer-ws4-compatibility-regression.md
  - .cursor/handoffs/canon-readiness-gates/docs-tests-rollout/implementer-ws5-integration-sweep.md

END_HANDOFF_TO_QA
