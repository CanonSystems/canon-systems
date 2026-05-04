HANDOFF_TO_QA_SHARD
shard_id: ws1
task_id: credential-attestation
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
workstream_id: credential-attestation

acceptance_criteria:
  - id: AC1
    status: satisfied
    evidence:
      - "src/canon_systems/aws_secrets.py::build_aws_secrets_resolution_attestation"
      - "tests/test_aws_secrets.py"
  - id: AC2
    status: satisfied
    evidence:
      - "src/canon_systems/shared.py::get_credential_attestation"
      - "tests/test_shared.py::test_get_credential_attestation_env_precedence_profile_mismatch"
  - id: AC6
    status: satisfied
    evidence:
      - "apply_canon_systems_secrets_from_aws unchanged; attestation is read-only classification + env comparison."

tests:
  command: "python3 -m pytest tests/test_aws_secrets.py tests/test_shared.py -q"
  result: "17 passed"
END_HANDOFF_TO_QA_SHARD
