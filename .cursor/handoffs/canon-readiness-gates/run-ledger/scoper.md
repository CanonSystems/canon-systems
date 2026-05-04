HANDOFF_TO_CURSOR_PILOT
  scope_summary: Define and implement the DynamoDB-backed run ledger for Canon readiness gates as the durable index that connects plans, tasks, phases, archived packet/evidence URIs, validation outcomes, commits, and deployments. Build directly on the packet-archive records already produced by `POST /state/archive` / `canon packet-archive`, keep ledger state separate from mutable checkpoint/lease state, and stop before implementing `canon readiness check`.
  scope_packet:
    identifiers:
      handoff_id: "canon-readiness-gates"
      company_id: "CSC"
      repository_id: "canon-systems"
      plan_id: "canon_readiness_gates_c389cad8"
      task_id: "run-ledger"
      workstream_id: "run-ledger"
      repo_ref: "feature/canon-run-ledger-readiness@d3528041e391dc930c7634ff906a70eaa7561a14"
    story:
      title: "Define DynamoDB-backed run ledger"
      userValue: "Canon operators and future readiness checks get a queryable, durable run record that ties each plan/task/phase to archived packet metadata, evidence references, gate outcomes, commits, and deployments without depending on mutable checkpoint rows or local handoff files alone."
      acceptanceCriteria:
        - "AC1: A versioned run-ledger record schema is implemented and documented with tenant scope, plan_id, task_id, workstream_id, handoff_id, phase, phase_status/verdict, archived packet refs, evidence refs, validation outcomes, commit refs, deployment refs, timestamps, agent_run_id/actor_id when available, and source event ids."
        - "AC2: Run-ledger persistence is DynamoDB-backed but logically separate from mutable checkpoint/lease state, with distinct table configuration or clearly namespaced storage that does not read or mutate checkpoint lease attributes."
        - "AC3: State-api exposes an additive run-ledger write/read surface suitable for agents and later readiness checks, returning structured ledger records and actionable errors while preserving existing checkpoint, lease, and archive APIs."
        - "AC4: Ledger writes can ingest packet-archive records by reference, including `s3_uri`, `s3_key`, `content_sha256`, `artifact_kind`, `phase`, `status/outcome`, and archive event id when available, without copying packet bodies into DynamoDB."
        - "AC5: The ledger can represent validation outcomes for `qa-validate`, `flow-audit`, memory-health, CI, deployment smoke checks, merge readiness, commit SHA(s), PR URL, deployment environment, and deployment status in a shape that later `canon readiness check` can consume."
        - "AC6: A local CLI/helper path can create or dry-run run-ledger records from explicit JSON/archive metadata inputs using tenant and task identifiers, but this task does not implement `canon readiness check` or enforce readiness policy."
        - "AC7: Documentation explains the boundary between packet archive, run ledger, mutable checkpoint/lease state, and later readiness checks, including required environment variables and expected write/query flow."
        - "AC8: Tests cover schema validation, DynamoDB key isolation, idempotent or conflict-safe writes, query behavior by plan/task/handoff, archive-reference ingestion, no packet body persistence, state-api behavior with moto DynamoDB, and CLI/helper dry-run behavior without live AWS."
    repository:
      primaryLanguages: ["Python", "Terraform", "Markdown"]
      testFramework: "pytest; backend/state-api uses FastAPI TestClient plus moto for AWS-backed tests; repo smoke uses pytest and scripts/smoke-test.sh when environment permits"
      relevantFiles:
        - "backend/shared/canon_backend_shared/packet_archive.py"
        - "backend/shared/canon_backend_shared/events.py"
        - "backend/shared/canon_backend_shared/run_ledger.py"
        - "backend/state-api/state_api/config.py"
        - "backend/state-api/state_api/main.py"
        - "backend/state-api/state_api/models.py"
        - "backend/state-api/state_api/storage.py"
        - "backend/state-api/state_api/packet_archive.py"
        - "backend/state-api/state_api/run_ledger.py"
        - "backend/state-api/tests/conftest.py"
        - "backend/state-api/tests/test_run_ledger.py"
        - "backend/state-api/README.md"
        - "src/canon_systems/cli.py"
        - "src/canon_systems/run_ledger.py"
        - "src/canon_systems/run_ledger_cli.py"
        - "tests/test_run_ledger.py"
        - "tests/test_run_ledger_cli.py"
        - "infra/terraform/modules/dynamodb-canon-state/main.tf"
        - "docs/SYSTEM-WORKFLOW.md"
        - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
        - "README.md"
        - "CHANGELOG.md"
    constraints:
      dependencies:
        - "Build on the existing packet-archive implementation in the current working tree; do not redesign archive key or artifact-kind semantics unless strictly necessary for ledger references."
        - "Do not edit /Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md."
        - "Do not implement `canon readiness check` in this task; only shape the data/API/CLI surfaces it will later consume."
        - "Keep run-ledger data separate from mutable checkpoint/lease state; if state-api exposes it, use a separate router/store/model path from checkpoint lease handling."
        - "Use existing Python, FastAPI, boto3, pydantic, pytest, moto, and argparse patterns; avoid new dependencies unless clearly justified."
      mustNotBreak:
        - "Existing `canon checkpoint` and state-api checkpoint/lease wire protocol."
        - "Existing `POST /state/archive` behavior, packet archive schema, deterministic archive keys, and `packet_archived` canonical event shape."
        - "Existing packet-archive tests and CLI dry-run behavior."
        - "Existing flow-audit, qa-validate, release-status, and smoke-test behavior."
        - "Existing DynamoDB checkpoint rows and lease TTL semantics."
      requiredTests:
        - "pytest backend/state-api/tests/test_run_ledger.py -q"
        - "pytest backend/state-api/tests/test_packet_archive.py backend/state-api/tests/test_run_ledger.py -q"
        - "pytest tests/test_run_ledger.py tests/test_run_ledger_cli.py tests/test_packet_archive.py tests/test_packet_archive_cli.py -q"
        - "pytest -q"
        - "bash scripts/smoke-test.sh when environment permits"
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "AC1: A versioned run-ledger record schema is implemented and documented with tenant scope, plan_id, task_id, workstream_id, handoff_id, phase, phase_status/verdict, archived packet refs, evidence refs, validation outcomes, commit refs, deployment refs, timestamps, agent_run_id/actor_id when available, and source event ids."
        implementation_targets: ["backend/shared/canon_backend_shared/run_ledger.py", "backend/state-api/state_api/models.py", "src/canon_systems/run_ledger.py", "backend/state-api/README.md"]
        verification_tests: ["tests/test_run_ledger.py::test_run_ledger_record_schema_requires_scope_archive_refs_and_outcomes", "backend/state-api/tests/test_run_ledger.py::test_run_ledger_response_contains_required_metadata"]
      - criterion: "AC2: Run-ledger persistence is DynamoDB-backed but logically separate from mutable checkpoint/lease state, with distinct table configuration or clearly namespaced storage that does not read or mutate checkpoint lease attributes."
        implementation_targets: ["backend/state-api/state_api/config.py", "backend/state-api/state_api/storage.py", "backend/state-api/state_api/run_ledger.py", "infra/terraform/modules/dynamodb-canon-state/main.tf"]
        verification_tests: ["backend/state-api/tests/test_run_ledger.py::test_run_ledger_uses_separate_store_and_does_not_write_lease_attributes", "tests/test_run_ledger.py::test_run_ledger_keys_are_namespaced_away_from_checkpoint_keys"]
      - criterion: "AC3: State-api exposes an additive run-ledger write/read surface suitable for agents and later readiness checks, returning structured ledger records and actionable errors while preserving existing checkpoint, lease, and archive APIs."
        implementation_targets: ["backend/state-api/state_api/main.py", "backend/state-api/state_api/run_ledger.py", "backend/state-api/state_api/models.py", "backend/state-api/README.md"]
        verification_tests: ["backend/state-api/tests/test_run_ledger.py::test_post_run_ledger_writes_record", "backend/state-api/tests/test_run_ledger.py::test_get_run_ledger_queries_by_scope"]
      - criterion: "AC4: Ledger writes can ingest packet-archive records by reference, including `s3_uri`, `s3_key`, `content_sha256`, `artifact_kind`, `phase`, `status/outcome`, and archive event id when available, without copying packet bodies into DynamoDB."
        implementation_targets: ["backend/shared/canon_backend_shared/run_ledger.py", "backend/state-api/state_api/run_ledger.py", "src/canon_systems/run_ledger.py"]
        verification_tests: ["tests/test_run_ledger.py::test_archive_record_converts_to_bodyless_ledger_packet_ref", "backend/state-api/tests/test_run_ledger.py::test_run_ledger_rejects_packet_body_fields"]
      - criterion: "AC5: The ledger can represent validation outcomes for `qa-validate`, `flow-audit`, memory-health, CI, deployment smoke checks, merge readiness, commit SHA(s), PR URL, deployment environment, and deployment status in a shape that later `canon readiness check` can consume."
        implementation_targets: ["backend/shared/canon_backend_shared/run_ledger.py", "src/canon_systems/run_ledger.py", "docs/SYSTEM-WORKFLOW.md", "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"]
        verification_tests: ["tests/test_run_ledger.py::test_validation_commit_and_deployment_refs_round_trip", "backend/state-api/tests/test_run_ledger.py::test_run_ledger_accepts_gate_outcomes_and_deployment_refs"]
      - criterion: "AC6: A local CLI/helper path can create or dry-run run-ledger records from explicit JSON/archive metadata inputs using tenant and task identifiers, but this task does not implement `canon readiness check` or enforce readiness policy."
        implementation_targets: ["src/canon_systems/cli.py", "src/canon_systems/run_ledger.py", "src/canon_systems/run_ledger_cli.py", "tests/test_run_ledger_cli.py"]
        verification_tests: ["tests/test_run_ledger_cli.py::test_run_ledger_cli_dry_run_outputs_record_without_network", "tests/test_run_ledger_cli.py::test_run_ledger_cli_posts_explicit_record_payload"]
      - criterion: "AC7: Documentation explains the boundary between packet archive, run ledger, mutable checkpoint/lease state, and later readiness checks, including required environment variables and expected write/query flow."
        implementation_targets: ["backend/state-api/README.md", "docs/SYSTEM-WORKFLOW.md", "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md", "README.md", "CHANGELOG.md"]
        verification_tests: ["manual::review docs for archive-ledger-checkpoint-readiness boundaries", "manual::confirm no edits to canon_readiness_gates_c389cad8.plan.md"]
      - criterion: "AC8: Tests cover schema validation, DynamoDB key isolation, idempotent or conflict-safe writes, query behavior by plan/task/handoff, archive-reference ingestion, no packet body persistence, state-api behavior with moto DynamoDB, and CLI/helper dry-run behavior without live AWS."
        implementation_targets: ["backend/state-api/tests/test_run_ledger.py", "tests/test_run_ledger.py", "tests/test_run_ledger_cli.py", "backend/state-api/tests/conftest.py"]
        verification_tests: ["pytest backend/state-api/tests/test_run_ledger.py -q", "pytest tests/test_run_ledger.py tests/test_run_ledger_cli.py -q", "pytest -q"]
    risks_and_assumptions:
      assumptions:
        - "The prior `packet-archive` task is locally ready to merge and provides the archive record metadata the ledger should reference."
        - "State-api is an appropriate exposure point for run-ledger writes/queries because it already owns checkpoint, lease, archive, DynamoDB, and canonical event integration."
        - "A separate run-ledger table/configuration is preferable for the first implementation because the user explicitly wants the ledger separate from mutable checkpoint/lease state."
      openQuestions: []
      risks:
        - "DynamoDB table design may need future GSIs for cross-plan or deployment-centric queries; this task should cover plan/task/handoff queries needed by readiness checks without over-indexing prematurely."
        - "If ledger writes are made too mutable, they can blur into checkpoint state; prefer append-only or conflict-safe records with explicit supersession/status fields."
        - "If the ledger stores full packet or evidence bodies, DynamoDB item size and confidentiality risks increase; store only archive refs, hashes, summaries, and outcomes."
    later_task_integration:
      - "Packet archive produces immutable S3-backed packet/evidence records; run ledger indexes those records by plan/task/phase/handoff and adds validation, commit, PR, and deployment context."
      - "`canon readiness check` should later query run-ledger records to verify required packet refs, QA/pass gates, flow-audit, CI/deploy evidence, and commit/deployment lineage."
      - "The mutable checkpoint/lease plane remains the operational coordination layer; the run ledger is historical/audit evidence and should not be used for lock ownership or phase concurrency."
END_HANDOFF_TO_CURSOR_PILOT
