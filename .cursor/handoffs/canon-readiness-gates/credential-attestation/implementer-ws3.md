HANDOFF_TO_QA_SHARD
shard_id: ws3
task_id: credential-attestation
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
workstream_id: credential-attestation

acceptance_criteria:
  - id: AC4
    status: satisfied
    evidence:
      - "src/canon_systems/context_preload.py"
      - "tests/test_mempalace_fallback.py::test_preflight_persists_credential_attestation_summary_ac4"
  - id: AC6
    status: satisfied
    evidence:
      - "tests/test_mempalace_fallback.py"

tests:
  command: "python3 -m pytest tests/test_mempalace_fallback.py -q"
  result: "5 passed"
END_HANDOFF_TO_QA_SHARD
HANDOFF_TO_QA_SHARD
shard_id: ws3
task_id: credential-attestation
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
workstream_id: credential-attestation

acceptance_criteria:
  - id: AC4
    status: satisfied
    evidence:
      - "src/canon_systems/context_preload.py::run — calls get_credential_attestation() after load_repo_context; JSON includes credential_attestation; _write_markdown emits ## Credential / Secrets resolution"
      - "tests/test_mempalace_fallback.py::test_preflight_persists_credential_attestation_summary_ac4"
      - "tests/test_mempalace_fallback.py — existing preflight tests assert credential sidecar keys + markdown section"
  - id: AC6
    status: satisfied
    evidence:
      - "No changes to apply_canon_systems_secrets_from_aws, deploy attestation, or secret logging; mempalace classifier + queue behavior unchanged (tests extended, all pass)"
      - "tests/test_mempalace_fallback.py — AC4 test asserts md has no BEARER/TOKEN substrings"

tests:
  command: "python3 -m pytest tests/test_mempalace_fallback.py -q"
  result: "5 passed"

notes: |
  Retrieval: canon graph query exited 5 (SSL CERTIFICATE_VERIFY_FAILED); canon checkpoint read exited 5 (connection refused). Degraded to file + canonical context only.
  retrieval_breakdown (implementer phase, illustrative): constructed via build_retrieval_breakdown_event — graph 0/0, state 0/0, canonical ~1200/400, file ~8000/3200 (estimated tokens_in/out).

END_HANDOFF_TO_QA_SHARD
