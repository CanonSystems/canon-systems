HANDOFF_TO_QA_SHARD
shard_id: ws2
task_id: deploy-attestation
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8

summary: |
  Public `canon flow-audit` now accepts and forwards `--require-deploy-attestation`
  to `flow_audit.run`, matching direct module invocation. Added CLI-level tests for
  the happy path and for sampling skip, where deploy attestation must not run when
  the audit sample is skipped.

acceptance_criteria:
  - id: AC4
    status: satisfied
    evidence:
      - path: src/canon_systems/cli.py
        note: "`flow-audit` subparser adds `--require-deploy-attestation`; dispatch appends the flag when building `fa_args`."
      - path: tests/test_flow_audit.py
        note: "`test_public_cli_flow_audit_forwards_require_deploy_attestation` and `test_public_cli_flow_audit_deploy_sampling_skip_does_not_validate_file`."
      - command: "python3 -m pytest tests/test_flow_audit.py -q"
        note: "37 passed."

notes: |
  Graph retrieval degraded with `canon graph query` exit 5 / SSL certificate verification failure.
  `flow_audit.py` was unchanged in this shard; ws1 already implemented validation and sampling behavior.
  The plan file was not modified.

files_touched:
  - src/canon_systems/cli.py
  - tests/test_flow_audit.py

END_HANDOFF_TO_QA_SHARD
