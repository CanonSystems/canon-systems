HANDOFF_TO_QA
  handoff_id: "canon-readiness-gates"
  task_id: "credential-attestation"
  acceptance_criteria_covered:
    - criterion: "AC1: Shared AWS secret resolution exposes a structured, non-secret attestation object that includes effective AWS profile, region, resolved secret id, cache path/existence, cache hit/miss when known, and resolution status without leaking secret values or bearer tokens."
      evidence_files:
        - "src/canon_systems/aws_secrets.py"
      evidence_tests:
        - "tests/test_aws_secrets.py::test_aws_secret_resolution_attestation_has_non_secret_fields"
        - "tests/test_aws_secrets.py::test_aws_secret_resolution_attestation_redacts_secret_values"
    - criterion: "AC2: The attestation design accounts for process-env versus repo-local env precedence, including the known case where process `AWS_PROFILE=canon-systems` can shadow repo-local `.canon/memory-layer.local.env` `AWS_PROFILE=canon-systems-v2`, and surfaces that mismatch as a warning/degraded credential-resolution signal."
      evidence_files:
        - "src/canon_systems/shared.py"
      evidence_tests:
        - "tests/test_shared.py::test_get_credential_attestation_env_precedence_profile_mismatch"
    - criterion: "AC3: `canon doctor --json` includes the structured credential/Secrets Manager attestation and the human doctor output summarizes the effective profile, repo-local profile, resolved secret id, cache status, and actionable mismatch warning while preserving existing tenant, DNS, cache, and raw-IP diagnostics."
      evidence_files:
        - "src/canon_systems/doctor_cli.py"
      evidence_tests:
        - "tests/test_doctor.py::test_doctor_json_includes_credential_attestation"
        - "tests/test_doctor.py::test_doctor_human_output_warns_on_aws_profile_mismatch"
    - criterion: "AC4: `canon preflight` records credential/Secrets Manager attestation in `.canon/memory/context-latest.json` and summarizes non-secret credential status in `.canon/memory/context-latest.md` so failed or stale memory hydration shows why resolution degraded."
      evidence_files:
        - "src/canon_systems/context_preload.py"
      evidence_tests:
        - "tests/test_mempalace_fallback.py::test_preflight_persists_credential_attestation_summary_ac4"
    - criterion: "AC5: `canon memory-health --json` includes credential/Secrets Manager attestation alongside backend health rows, and the existing exit-code contract remains backend-health driven unless a required backend is unhealthy or usage is invalid."
      evidence_files:
        - "src/canon_systems/memory_health.py"
      evidence_tests:
        - "tests/test_memory_health.py::test_ac5_json_includes_credential_attestation_non_secret_shape"
        - "tests/test_memory_health.py::test_ac6_exit_code_backend_driven_when_credential_reports_degraded"
    - criterion: "AC6: Existing credential recovery, secret fetching, cache behavior, URL hydration, and readiness-gate behavior remain compatible; no deploy attestation, AWS writes, secret value logging, or plan-file edits are introduced."
      evidence_files:
        - "src/canon_systems/aws_secrets.py"
        - "src/canon_systems/shared.py"
        - "src/canon_systems/doctor_cli.py"
        - "src/canon_systems/context_preload.py"
        - "src/canon_systems/memory_health.py"
      evidence_tests:
        - "tests/test_aws_secrets.py::test_apply_canon_systems_secrets_from_aws_preserves_cache_behavior"
        - "tests/test_doctor.py::test_doctor_existing_dns_and_tenant_diagnostics_remain"
        - "tests/test_memory_health.py::test_urls_from_home_canon_env_when_local_env_omits_urls"
  summary: "Added non-secret credential/Secrets Manager attestation, env precedence mismatch warnings, and surfaced the attestation in doctor, preflight context, and memory-health JSON without changing backend-health exit semantics."
  decisions:
    - "Process-env/repo-local AWS profile mismatch is warning/degraded metadata, not an exit-code change."
    - "Attestation carries a nested schema version and does not include secret payload values."
  next_actions:
    - "Implement deployment attestation in the next task."
  open_questions: []
END_HANDOFF_TO_QA
