HANDOFF_TO_QA_SHARD
shard_id: ws4
task_id: credential-attestation
handoff_id: canon-readiness-gates

summary: |
  Wired `canon memory-health` JSON output to include `credential_attestation` from `shared.get_credential_attestation()` after layered env apply. Preserved schema_version "1", backend-driven exit codes, and non-secret attestation shape from ws1.

artifacts:
  - src/canon_systems/memory_health.py
  - tests/test_memory_health.py

verification:
  command: "python3 -m pytest tests/test_memory_health.py -q"
  result: "30 passed"

acceptance_criteria:
  - id: AC5
    status: satisfied
    evidence:
      - "tests/test_memory_health.py::test_ac5_json_includes_credential_attestation_non_secret_shape"
  - id: AC6
    status: satisfied
    evidence:
      - "tests/test_memory_health.py::test_ac6_exit_code_backend_driven_when_credential_reports_degraded"
END_HANDOFF_TO_QA_SHARD
