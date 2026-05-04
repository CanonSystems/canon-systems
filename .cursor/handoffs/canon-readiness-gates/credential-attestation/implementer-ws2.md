HANDOFF_TO_QA_SHARD
shard_id: ws2
task_id: credential-attestation
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
branch: feature/canon-run-ledger-readiness

summary: |
  `canon doctor` now attaches structured `credential_attestation` to JSON and human output, including effective/repo-local profile, secret id, cache status, and mismatch warning without leaking secrets.

acceptance_criteria:
  - id: AC3
    status: satisfied
    evidence:
      - "src/canon_systems/doctor_cli.py"
      - "tests/test_doctor.py::test_doctor_json_includes_credential_attestation"
      - "tests/test_doctor.py::test_doctor_human_output_warns_on_aws_profile_mismatch"
  - id: AC6
    status: satisfied
    evidence:
      - "tests/test_doctor.py::test_doctor_existing_dns_and_tenant_diagnostics_remain"

verification:
  command: "python3 -m pytest tests/test_doctor.py -v"
  result: "9 passed"
END_HANDOFF_TO_QA_SHARD
