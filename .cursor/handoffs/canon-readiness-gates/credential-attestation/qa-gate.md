GATE_RESULTS
  handoff_id: "canon-readiness-gates"
  verdict: PASS
  acceptance_criteria:
    - criterion: "AC1: Shared AWS secret resolution exposes a structured, non-secret attestation object that includes effective AWS profile, region, resolved secret id, cache path/existence, cache hit/miss when known, and resolution status without leaking secret values or bearer tokens."
      status: PASS
      covering_tests:
        - "tests/test_aws_secrets.py::test_aws_secret_resolution_attestation_has_non_secret_fields"
        - "tests/test_aws_secrets.py::test_aws_secret_resolution_attestation_redacts_secret_values"
      run_result: "pass; focused suite 63 passed"
    - criterion: "AC2: The attestation design accounts for process-env versus repo-local env precedence, including the known case where process `AWS_PROFILE=canon-systems` can shadow repo-local `.canon/memory-layer.local.env` `AWS_PROFILE=canon-systems-v2`, and surfaces that mismatch as a warning/degraded credential-resolution signal."
      status: PASS
      covering_tests:
        - "tests/test_shared.py::test_get_credential_attestation_env_precedence_profile_mismatch"
      run_result: "pass; focused suite 63 passed"
    - criterion: "AC3: `canon doctor --json` includes the structured credential/Secrets Manager attestation and the human doctor output summarizes the effective profile, repo-local profile, resolved secret id, cache status, and actionable mismatch warning while preserving existing tenant, DNS, cache, and raw-IP diagnostics."
      status: PASS
      covering_tests:
        - "tests/test_doctor.py::test_doctor_json_includes_credential_attestation"
        - "tests/test_doctor.py::test_doctor_human_output_warns_on_aws_profile_mismatch"
        - "tests/test_doctor.py::test_doctor_existing_dns_and_tenant_diagnostics_remain"
      run_result: "pass; focused suite 63 passed"
    - criterion: "AC4: `canon preflight` records credential/Secrets Manager attestation in `.canon/memory/context-latest.json` and summarizes non-secret credential status in `.canon/memory/context-latest.md` so failed or stale memory hydration shows why resolution degraded."
      status: PASS
      covering_tests:
        - "tests/test_mempalace_fallback.py::test_preflight_persists_credential_attestation_summary_ac4"
      run_result: "pass; focused suite 63 passed"
    - criterion: "AC5: `canon memory-health --json` includes credential/Secrets Manager attestation alongside backend health rows, and the existing exit-code contract remains backend-health driven unless a required backend is unhealthy or usage is invalid."
      status: PASS
      covering_tests:
        - "tests/test_memory_health.py::test_ac5_json_includes_credential_attestation_non_secret_shape"
        - "tests/test_memory_health.py::test_ac6_exit_code_backend_driven_when_credential_reports_degraded"
        - "tests/test_memory_health.py::test_exit_code_matrix"
      run_result: "pass; focused suite 63 passed"
    - criterion: "AC6: Existing credential recovery, secret fetching, cache behavior, URL hydration, and readiness-gate behavior remain compatible; no deploy attestation, AWS writes, secret value logging, or plan-file edits are introduced."
      status: PASS
      covering_tests:
        - "tests/test_aws_secrets.py::test_aws_secret_resolution_attestation_redacts_secret_values"
        - "tests/test_doctor.py::test_doctor_existing_dns_and_tenant_diagnostics_remain"
        - "tests/test_memory_health.py::test_urls_from_home_canon_env_when_local_env_omits_urls"
        - "tests/test_agent_templates.py::test_hooks_include_credential_recovery_flow"
      run_result: "pass; adjacent regression suite 92 passed"
  iterations: 0
  regression_checked: true
  remaining_gaps: []
  notes: "Added two bounded AC1 tests in `tests/test_aws_secrets.py` to reconcile missing evidence IDs and explicitly prove cached secret payload redaction. Ran focused credential suites (`63 passed`) and adjacent regression suites (`92 passed`)."
END_GATE_RESULTS
