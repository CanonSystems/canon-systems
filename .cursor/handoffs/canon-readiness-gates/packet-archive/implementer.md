HANDOFF_TO_QA
  handoff_id: "canon-readiness-gates"
  acceptance_criteria_covered:
    - criterion: "AC1: A versioned packet/evidence archive record schema is implemented and documented with required fields for tenant scope, plan/task/workstream/handoff ids, phase, artifact kind, local path or source label, S3 URI/key, content SHA-256, byte length, content type, created_at, agent_run_id/actor_id when available, outcome/status when available, and optional S3 version id."
      evidence_files:
        - "backend/shared/canon_backend_shared/packet_archive.py:1-260"
        - "backend/state-api/state_api/models.py:249-314"
        - "backend/state-api/state_api/packet_archive.py:115-155"
        - "backend/state-api/README.md:7-52"
      evidence_tests:
        - "tests/test_packet_archive.py::test_packet_archived_event_payload_omits_unknown_keys"
    - criterion: "AC2: Archive key generation is deterministic, tenant-scoped, path-traversal-safe, and content-addressed or otherwise immutable so the same body resolves to the same durable object identity without overwriting a different body."
      evidence_files:
        - "backend/shared/canon_backend_shared/packet_archive.py:68-161"
      evidence_tests:
        - "tests/test_packet_archive.py::test_deterministic_key_includes_sha_and_is_stable"
        - "tests/test_packet_archive.py::test_different_content_yields_different_keys"
        - "tests/test_packet_archive.py::test_sanitize_segment_rejects_traversal"
        - "backend/state-api/tests/test_packet_archive.py::test_archive_idempotent_same_body_same_key"
        - "backend/state-api/tests/test_packet_archive.py::test_archive_different_body_different_keys"
        - "backend/state-api/tests/test_packet_archive.py::test_archive_path_traversal_rejected"
    - criterion: "AC3: Packet kinds cover the five phase packets (`scoper.md`, `cursor-pilot.md`, `implementer.md` or shard handoff, `qa-gate.md`, `release-status.md`) plus HANDOFF_NOT_READY packets and DoR telemetry artifacts; evidence kinds cover JSON evidence blobs such as memory-health, deployment smoke, runtime/browser/shell evidence, and future typed QA evidence labels without hard-coding the run ledger."
      evidence_files:
        - "backend/shared/canon_backend_shared/packet_archive.py:13-75"
        - "backend/shared/canon_backend_shared/packet_archive.py:97-112"
      evidence_tests:
        - "tests/test_packet_archive.py::test_validate_extension_evidence_kind"
        - "backend/state-api/tests/test_packet_archive.py::test_implementer_shard_requires_subtype"
    - criterion: "AC4: A state-api/backend archive write surface stores packet/evidence bodies in the configured S3 artifact bucket and returns a structured archive record; failures are actionable and do not create partial success claims."
      evidence_files:
        - "backend/state-api/state_api/packet_archive.py:62-155"
        - "backend/state-api/state_api/config.py:11-28"
      evidence_tests:
        - "backend/state-api/tests/test_packet_archive.py::test_archive_success_writes_s3_and_emits_event"
        - "backend/state-api/tests/test_packet_archive.py::test_archive_sha256_mismatch"
        - "backend/state-api/tests/test_packet_archive.py::test_archive_bucket_unset_returns_503"
    - criterion: "AC5: Successful archive writes emit one canonical `packet_archived` or equivalent event containing archive metadata but not full packet/evidence body text; this task does not create DynamoDB run-ledger records."
      evidence_files:
        - "backend/state-api/state_api/packet_archive.py:157-183"
        - "backend/shared/canon_backend_shared/packet_archive.py:218-252"
      evidence_tests:
        - "backend/state-api/tests/test_packet_archive.py::test_archive_success_writes_s3_and_emits_event"
    - criterion: "AC6: A local/CLI-facing helper can archive an explicit packet/evidence file using tenant and task identifiers, supports dry-run or no-network test injection, and preserves existing local packet requirements."
      evidence_files:
        - "src/canon_systems/packet_archive_cli.py:1-160"
        - "src/canon_systems/packet_archive.py:1-120"
        - "src/canon_systems/cli.py:392-428,706-738"
      evidence_tests:
        - "tests/test_packet_archive_cli.py::test_packet_archive_cli_dry_run_resolves_record"
    - criterion: "AC7: Documentation explains the archive semantics, required environment/configuration, retention/immutability expectations, and the boundary with later run-ledger/readiness tasks."
      evidence_files:
        - "docs/SYSTEM-WORKFLOW.md:51-62,208-212"
        - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md:103-128"
        - "README.md:284-286"
        - "backend/state-api/README.md:1-52"
        - "CHANGELOG.md:10-34"
    - criterion: "AC8: Tests prove hashing/key safety, idempotent same-body writes, non-overwrite behavior for different bodies, canonical event shape, backend API behavior with moto S3, and CLI/helper behavior without live AWS."
      evidence_files:
        - "tests/test_packet_archive.py"
        - "tests/test_packet_archive_cli.py"
        - "backend/state-api/tests/test_packet_archive.py"
      evidence_tests:
        - "tests/test_packet_archive.py::test_normalize_sha256_*"
        - "backend/state-api/tests/test_packet_archive.py::test_archive_*"
  summary: "Added shared archive v1 schema and S3 keying, state-api POST /state/archive with moto tests and packet_archived events, canon packet-archive + dry-run, docs/changelog, and fixed a CLI regression that omitted the graph sub-parser."
  decisions:
    - "Centralized deterministic keys and artifact-kind validation in canon_backend_shared.packet_archive so CLI and state-api stay aligned."
    - "Declared SHA-256 on the wire must match the decoded body; mismatches return 400 before any S3 write so there are no partial success claims."
    - "Enabled pydantic-settings populate_by_name=True so programmatic Settings(...) passes field names alongside validation_alias env names."
  next_actions:
    - "Optional automatic archival after each phase (orchestrator wiring) remains out of scope for this task."
    - "DynamoDB run-ledger rows indexing s3_uri / readiness remain deferred."
  open_questions:
    - "QA should confirm production artifact buckets use versioning (terraform module enables it) so s3_version_id is routinely populated."
  notes:
    - "Graph retrieval (canon graph query) was not used initially due to the transient graph_parser NameError; fixed in src/canon_systems/cli.py."
    - "canon checkpoint read not exercised (state-api optional locally)."
    - "retrieval_breakdown emitted via build_retrieval_breakdown_event with canonical/file token estimates for this implementer phase."
  blocked_tests: []
END_HANDOFF_TO_QA
