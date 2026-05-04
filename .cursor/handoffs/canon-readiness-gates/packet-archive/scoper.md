HANDOFF_TO_CURSOR_PILOT
  scope_summary: Define and implement the first reusable packet/evidence archive contract for Canon readiness gates: immutable S3/object-storage bodies, stable archive record metadata, content hashing, and canonical event emission for every phase packet and supporting evidence blob. Keep local `.cursor/handoffs/...` files as required working-copy artifacts, and stop before building the DynamoDB run ledger or `canon readiness check`; later tasks should consume the archive records produced here.
  scope_packet:
    identifiers:
      handoff_id: "canon-readiness-gates"
      company_id: "CSC"
      repository_id: "canon-systems"
      plan_id: "canon_readiness_gates_c389cad8"
      task_id: "packet-archive"
      workstream_id: "packet-archive"
      repo_ref: "feature/canon-run-ledger-readiness@d3528041e391dc930c7634ff906a70eaa7561a14"
    story:
      title: "Define durable S3 packet and evidence archive semantics"
      userValue: "Canon operators and downstream readiness/run-ledger tasks get a durable, server-side source of truth for phase packet bodies and evidence blobs, so merge/release gates do not depend only on local files that can be missing or stale."
      acceptanceCriteria:
        - "AC1: A versioned packet/evidence archive record schema is implemented and documented with required fields for tenant scope, plan/task/workstream/handoff ids, phase, artifact kind, local path or source label, S3 URI/key, content SHA-256, byte length, content type, created_at, agent_run_id/actor_id when available, outcome/status when available, and optional S3 version id."
        - "AC2: Archive key generation is deterministic, tenant-scoped, path-traversal-safe, and content-addressed or otherwise immutable so the same body resolves to the same durable object identity without overwriting a different body."
        - "AC3: Packet kinds cover the five phase packets (`scoper.md`, `cursor-pilot.md`, `implementer.md` or shard handoff, `qa-gate.md`, `release-status.md`) plus HANDOFF_NOT_READY packets and DoR telemetry artifacts; evidence kinds cover JSON evidence blobs such as memory-health, deployment smoke, runtime/browser/shell evidence, and future typed QA evidence labels without hard-coding the run ledger."
        - "AC4: A state-api/backend archive write surface stores packet/evidence bodies in the configured S3 artifact bucket and returns a structured archive record; failures are actionable and do not create partial success claims."
        - "AC5: Successful archive writes emit one canonical `packet_archived` or equivalent event containing archive metadata but not full packet/evidence body text; this task does not create DynamoDB run-ledger records."
        - "AC6: A local/CLI-facing helper can archive an explicit packet/evidence file using tenant and task identifiers, supports dry-run or no-network test injection, and preserves existing local packet requirements."
        - "AC7: Documentation explains the archive semantics, required environment/configuration, retention/immutability expectations, and the boundary with later run-ledger/readiness tasks."
        - "AC8: Tests prove hashing/key safety, idempotent same-body writes, non-overwrite behavior for different bodies, canonical event shape, backend API behavior with moto S3, and CLI/helper behavior without live AWS."
    repository:
      primaryLanguages: ["Python", "Terraform", "Markdown"]
      testFramework: "pytest; backend/state-api uses FastAPI TestClient plus moto for AWS-backed tests; repo smoke uses scripts/smoke-test.sh with pytest and terraform validate"
      relevantFiles:
        - "src/canon_systems/cli.py"
        - "src/canon_systems/checkpoint_cli.py"
        - "src/canon_systems/flow_audit.py"
        - "src/canon_systems/qa_validate.py"
        - "src/canon_systems/checkpoints.py"
        - "backend/state-api/state_api/main.py"
        - "backend/state-api/state_api/config.py"
        - "backend/state-api/state_api/models.py"
        - "backend/state-api/state_api/storage.py"
        - "backend/state-api/state_api/checkpoints.py"
        - "backend/state-api/README.md"
        - "backend/state-api/pyproject.toml"
        - "backend/shared/canon_backend_shared/events.py"
        - "backend/synthesis/synthesis/publisher.py"
        - "infra/terraform/modules/s3-artifacts/main.tf"
        - "infra/terraform/modules/s3-artifacts/variables.tf"
        - "infra/terraform/modules/s3-artifacts/outputs.tf"
        - "docs/SYSTEM-WORKFLOW.md"
        - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md"
        - "README.md"
        - "CHANGELOG.md"
        - "tests/test_flow_audit.py"
        - "tests/test_qa_validate.py"
        - "backend/state-api/tests/test_checkpoint_put.py"
        - "backend/state-api/tests/conftest.py"
    constraints:
      dependencies:
        - "Implementation must happen on branch feature/canon-run-ledger-readiness."
        - "Do not edit /Users/edwardwalker/.cursor/plans/canon_readiness_gates_c389cad8.plan.md."
        - "Preserve local .cursor/handoffs packet persistence as the required working-copy/git-review artifact."
        - "Use existing boto3/FastAPI/TestClient/moto patterns; avoid adding a new HTTP client dependency."
        - "Archive semantics must be compatible with later DynamoDB run-ledger and readiness-check tasks, but must not implement those tasks here."
      mustNotBreak:
        - "Existing canon checkpoint and lease wire protocol."
        - "Existing qa-validate and flow-audit behavior unless changes are strictly additive."
        - "Existing synthesis S3 vault publisher behavior."
        - "Existing canonical event envelope schema in canon_backend_shared.events."
        - "Repo-root pytest and backend/state-api pytest."
      requiredTests:
        - "pytest backend/state-api/tests -q"
        - "pytest tests/test_packet_archive*.py tests/test_flow_audit.py tests/test_qa_validate.py -q"
        - "pytest -q"
        - "bash scripts/smoke-test.sh when environment permits"
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "AC1"
        implementation_targets: ["backend/state-api/state_api/models.py", "src/canon_systems/packet_archive.py", "backend/state-api/README.md", "docs/SYSTEM-WORKFLOW.md"]
        verification_tests: ["tests/test_packet_archive.py::test_archive_record_schema_requires_scope_hash_and_object_fields", "backend/state-api/tests/test_packet_archive.py::test_archive_response_contains_required_metadata"]
      - criterion: "AC2"
        implementation_targets: ["src/canon_systems/packet_archive.py", "backend/state-api/state_api/storage.py"]
        verification_tests: ["tests/test_packet_archive.py::test_key_builder_is_deterministic_and_rejects_path_traversal", "tests/test_packet_archive.py::test_distinct_body_hashes_produce_distinct_keys"]
      - criterion: "AC3"
        implementation_targets: ["src/canon_systems/packet_archive.py", "src/canon_systems/checkpoints.py", "docs/SYSTEM-WORKFLOW.md"]
        verification_tests: ["tests/test_packet_archive.py::test_supported_artifact_kinds_cover_phase_packets_and_evidence_blobs"]
      - criterion: "AC4"
        implementation_targets: ["backend/state-api/state_api/main.py", "backend/state-api/state_api/config.py", "backend/state-api/state_api/storage.py", "backend/state-api/state_api/models.py"]
        verification_tests: ["backend/state-api/tests/test_packet_archive.py::test_archive_endpoint_writes_body_to_s3_with_metadata", "backend/state-api/tests/test_packet_archive.py::test_archive_endpoint_reports_missing_bucket_configuration"]
      - criterion: "AC5"
        implementation_targets: ["backend/state-api/state_api/models.py", "backend/state-api/state_api/storage.py", "backend/state-api/state_api/main.py", "backend/shared/canon_backend_shared/events.py"]
        verification_tests: ["backend/state-api/tests/test_packet_archive.py::test_archive_success_emits_bodyless_packet_archived_event", "backend/state-api/tests/test_packet_archive.py::test_archive_does_not_write_run_ledger_table"]
      - criterion: "AC6"
        implementation_targets: ["src/canon_systems/cli.py", "src/canon_systems/packet_archive.py", "tests/test_packet_archive_cli.py"]
        verification_tests: ["tests/test_packet_archive_cli.py::test_cli_archives_explicit_file_with_scope_fields", "tests/test_packet_archive_cli.py::test_cli_dry_run_hashes_without_network"]
      - criterion: "AC7"
        implementation_targets: ["backend/state-api/README.md", "docs/SYSTEM-WORKFLOW.md", "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md", "README.md", "CHANGELOG.md"]
        verification_tests: ["manual::review docs for no plan-file edits"]
      - criterion: "AC8"
        implementation_targets: ["tests/test_packet_archive.py", "tests/test_packet_archive_cli.py", "backend/state-api/tests/test_packet_archive.py", "backend/state-api/pyproject.toml"]
        verification_tests: ["pytest backend/state-api/tests -q", "pytest tests/test_packet_archive*.py -q", "pytest -q"]
    risks_and_assumptions:
      assumptions:
        - "The artifact bucket can reuse or extend the existing Terraform S3 artifacts module, which already enables versioning, SSE, and public access blocking."
        - "State-api is the right server-side boundary for S3 archival because it already owns checkpoint state and canonical event emission."
        - "The first task should add a reusable archive record/write contract, not automatically modify every agent template to call it at phase completion."
        - "Content-addressed S3 keys are sufficient for immutable semantics in this task; stricter S3 Object Lock/legal-hold policy can be added later if required by ops."
      openQuestions: []
      risks:
        - "Credential or live AWS availability may be absent locally; tests must use moto/injected clients and surface live configuration as actionable runtime errors."
        - "If archive metadata is too ledger-shaped, this task could pre-empt the run-ledger task; keep the returned record self-contained and let later DynamoDB work index relationships."
        - "S3 versioning exists in Terraform, but object lock is not currently present; document the exact immutability guarantee delivered by content addressing and versioning."
        - "CLI parser currently has drift around some documented validation flags; avoid bundling that unrelated fix unless needed to expose the archive command cleanly."
    later_task_integration:
      - "Run-ledger task should persist archive records by reference (`packet_uri`, `packet_sha256`, `evidence_refs`, event id), not re-read local packet bodies as source of truth."
      - "Readiness-check task should validate packet archive retention by querying ledger/archive metadata, not by requiring local files only."
      - "QA evidence normalization should map typed evidence labels to archive records produced here."
      - "Credential/deploy attestation tasks should publish their evidence blobs through the same artifact-kind/schema without extending this task’s API shape."
    retrieval_notes:
      - "Graph retrieval attempted with `canon graph query` for packet/evidence archive semantics but degraded because AXON_SERVICE_URL/base-url was unavailable after an AWS credentials warning."
      - "State checkpoint read attempted for plan `canon_readiness_gates_c389cad8`, task `packet-archive`, workstream `packet-archive`, but local state-api was unreachable."
      - "Canonical memory query returned only an unrelated MemPalace activation proof; file-level inspection supplied the usable scope evidence."
      - "Working tree already had unrelated modified docs and .canon memory files; scoper performed read-only inspection and made no edits."
    prior_work_references:
      - artifact_id: "canon_readiness_gates_c389cad8.plan.md:70-124"
        source: "canonical"
        relevance: "Defines the packet archive/run ledger split, representative ledger fields, and fix areas; this task should implement only the archive semantics portion."
      - artifact_id: "docs/SYSTEM-WORKFLOW.md:51-63"
        source: "canonical"
        relevance: "Existing living spec already states local packets remain required while phase packets should also be archived to S3/object storage with canonical IDs, hashes, timestamps, phase, status/verdict, and evidence refs."
      - artifact_id: "docs/SYSTEM-WORKFLOW.md:38-46"
        source: "canonical"
        relevance: "Confirms the current local packet quartet remains mandatory and must not be replaced by server-side archival."
END_HANDOFF_TO_CURSOR_PILOT
