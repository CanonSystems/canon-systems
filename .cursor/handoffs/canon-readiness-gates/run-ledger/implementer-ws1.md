HANDOFF_TO_QA_SHARD
shard_id: ws1
task_id: run-ledger
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
branch: feature/canon-run-ledger-readiness

implementation_summary: |
  WS1 adds versioned run-ledger schema (v1), validation, DynamoDB key helpers
  disjoint from checkpoint pk/sk, archive-by-reference ingest that strips body
  fields, validation_outcomes slots for readiness gates, CLI re-exports and
  merge_archive_snapshots_into_record for later dry-run wiring. No state-api,
  DynamoDB persistence, run-ledger CLI, or readiness command in this shard.
  Packet-archive module behavior is unchanged.

artifacts:
  - backend/shared/canon_backend_shared/run_ledger.py
  - src/canon_systems/run_ledger.py
  - tests/test_run_ledger.py

acceptance_criteria:
  - id: AC1
    status: SATISFIED
    evidence:
      - "Module docstring + RUN_LEDGER_RECORD_SCHEMA_VERSION=1; validate_run_ledger_record enforces tenant scope, plan_id, task_id, workstream_id, handoff_id, phase, phase_status, optional verdict, archive_refs, evidence_refs, validation_outcomes, commits, pull_request, deployment, timestamps, agent_run_id, actor_id, source_event_ids."
      - "tests/test_run_ledger.py::test_ac1_validate_minimal_round_trip"
      - "tests/test_run_ledger.py::test_ac1_optional_verdict_validation_outcomes_commits_pr_deployment"
  - id: AC4
    status: SATISFIED
    evidence:
      - "archive_record_to_ledger_reference copies only ARCHIVE_REFERENCE_ALLOWED_KEYS; FORBIDDEN_VALUE_KEYS rejected; no body fields in output."
      - "tests/test_run_ledger.py::test_ac4_archive_reference_requires_digest_and_kind"
      - "tests/test_run_ledger.py::test_ac4_rejects_body_like_fields_on_archive"
  - id: AC5
    status: SATISFIED
    evidence:
      - "VALIDATION_OUTCOME_SLOTS drives validation_outcomes normalization (qa_validate, flow_audit, memory_health, ci, deployment_smoke, merge_readiness); commits, pull_request.url, deployment.environment/status supported."
      - "tests/test_run_ledger.py::test_ac5_unknown_validation_slot_rejected"
  - id: AC2
    status: PARTIAL_KEYING_ONLY
    evidence:
      - "build_run_ledger_pk / build_run_ledger_sk use suffix #run_ledger on pk and four-part sk including ledger_run_id; never matches state_api checkpoint pk=company#repo, sk=plan#task#workstream."
      - "tests/test_run_ledger.py::test_checkpoint_vs_ledger_keys_never_collide"
  - id: AC8
    status: PARTIAL_WS1
    evidence:
      - "Key isolation + schema + archive ref + no body persistence covered in tests; DynamoDB/state-api/CLI/idempotent writes deferred to ws2/ws3."
      - "tests/test_run_ledger.py"

pytest: "18 passed (tests/test_run_ledger.py + tests/test_packet_archive.py regression smoke)"
END_HANDOFF_TO_QA_SHARD
