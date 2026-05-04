HANDOFF_TO_CURSOR_PILOT
  scope_summary: Expose structured credential and Secrets Manager resolution attestation so operators can see which AWS profile, region, secret id, cache state, and resolution source are being used by Canon memory wiring. Scope this to shared AWS secret resolution plus `canon doctor`, `canon preflight`, and `canon memory-health`; do not implement deploy attestation or change backend health classification semantics.
  scope_packet:
    identifiers:
      handoff_id: "canon-readiness-gates"
      company_id: "CSC"
      repository_id: "canon-systems"
      plan_id: "canon_readiness_gates_c389cad8"
      task_id: "credential-attestation"
      workstream_id: "credential-attestation"
      branch: "feature/canon-run-ledger-readiness"
      repo_ref: "d3528041e391dc930c7634ff906a70eaa7561a14"
    story:
      title: "Expose credential and Secrets Manager resolution attestation"
      userValue: "Canon operators benefit because credential failures become diagnosable from doctor, preflight, and memory-health output without guessing whether process env, repo-local env, AWS profile, cache, or Secrets Manager resolution was used."
      acceptanceCriteria:
        - "AC1: Shared AWS secret resolution exposes a structured, non-secret attestation object that includes effective AWS profile, region, resolved secret id, cache path/existence, cache hit/miss when known, and resolution status without leaking secret values or bearer tokens."
        - "AC2: The attestation design accounts for process-env versus repo-local env precedence, including the known case where process `AWS_PROFILE=canon-systems` can shadow repo-local `.canon/memory-layer.local.env` `AWS_PROFILE=canon-systems-v2`, and surfaces that mismatch as a warning/degraded credential-resolution signal."
        - "AC3: `canon doctor --json` includes the structured credential/Secrets Manager attestation and the human doctor output summarizes the effective profile, repo-local profile, resolved secret id, cache status, and actionable mismatch warning while preserving existing tenant, DNS, cache, and raw-IP diagnostics."
        - "AC4: `canon preflight` records credential/Secrets Manager attestation in `.canon/memory/context-latest.json` and summarizes non-secret credential status in `.canon/memory/context-latest.md` so failed or stale memory hydration shows why resolution degraded."
        - "AC5: `canon memory-health --json` includes credential/Secrets Manager attestation alongside backend health rows, and the existing exit-code contract remains backend-health driven unless a required backend is unhealthy or usage is invalid."
        - "AC6: Existing credential recovery, secret fetching, cache behavior, URL hydration, and readiness-gate behavior remain compatible; no deploy attestation, AWS writes, secret value logging, or plan-file edits are introduced."
    repository:
      primaryLanguages: ["Python", "Markdown", "HCL/Terraform"]
      testFramework: "pytest"
      relevantFiles:
        - "src/canon_systems/aws_secrets.py"
        - "src/canon_systems/shared.py"
        - "src/canon_systems/doctor_cli.py"
        - "src/canon_systems/context_preload.py"
        - "src/canon_systems/memory_health.py"
        - "tests/test_aws_secrets.py"
        - "tests/test_shared.py"
        - "tests/test_doctor.py"
        - "tests/test_mempalace_fallback.py"
        - "tests/test_memory_health.py"
    constraints:
      dependencies:
        - "`apply_layered_canon_env_for_repo()` currently merges home/repo env via `os.environ.setdefault()` before calling AWS secret hydration."
        - "`apply_canon_systems_secrets_from_aws()` currently returns `None`, reads `~/.canon/memory-layer-aws-cache.json`, resolves the secret id, and prints failures to stderr."
      mustNotBreak:
        - "Do not edit `.cursor/plans/canon_readiness_gates_c389cad8.plan.md`."
        - "Do not implement deploy attestation or broaden this task beyond AWS/Secrets Manager credential-resolution attestation for memory wiring surfaces."
        - "Do not log, return, or persist secret values, bearer tokens, API keys, or full secret payload contents."
        - "Do not change the resolved secret-id naming contract."
        - "Do not change existing `canon memory-health` backend rows, required-set behavior, or exit-code semantics except to add non-secret attestation metadata."
        - "Do not remove existing `canon doctor` tenant-context mismatch, DNS/WARP, cache, raw IPv4 URL, or `--fix-cache` behavior."
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "AC1: Shared AWS secret resolution exposes a structured, non-secret attestation object that includes effective AWS profile, region, resolved secret id, cache path/existence, cache hit/miss when known, and resolution status without leaking secret values or bearer tokens."
        implementation_targets: ["src/canon_systems/aws_secrets.py", "tests/test_aws_secrets.py"]
        verification_tests: ["tests/test_aws_secrets.py::test_aws_secret_resolution_attestation_has_non_secret_fields", "tests/test_aws_secrets.py::test_aws_secret_resolution_attestation_redacts_secret_values"]
      - criterion: "AC2: The attestation design accounts for process-env versus repo-local env precedence, including the known case where process `AWS_PROFILE=canon-systems` can shadow repo-local `.canon/memory-layer.local.env` `AWS_PROFILE=canon-systems-v2`, and surfaces that mismatch as a warning/degraded credential-resolution signal."
        implementation_targets: ["src/canon_systems/aws_secrets.py", "src/canon_systems/shared.py", "tests/test_shared.py", "tests/test_aws_secrets.py"]
        verification_tests: ["tests/test_aws_secrets.py::test_attestation_warns_when_process_profile_shadows_repo_local_profile", "tests/test_shared.py::test_layered_env_attestation_reports_process_env_profile_precedence"]
      - criterion: "AC3: `canon doctor --json` includes the structured credential/Secrets Manager attestation and the human doctor output summarizes the effective profile, repo-local profile, resolved secret id, cache status, and actionable mismatch warning while preserving existing tenant, DNS, cache, and raw-IP diagnostics."
        implementation_targets: ["src/canon_systems/doctor_cli.py", "tests/test_doctor.py"]
        verification_tests: ["tests/test_doctor.py::test_doctor_json_includes_credential_attestation", "tests/test_doctor.py::test_doctor_human_output_warns_on_aws_profile_mismatch", "tests/test_doctor.py::test_doctor_existing_dns_and_tenant_diagnostics_remain"]
      - criterion: "AC4: `canon preflight` records credential/Secrets Manager attestation in `.canon/memory/context-latest.json` and summarizes non-secret credential status in `.canon/memory/context-latest.md` so failed or stale memory hydration shows why resolution degraded."
        implementation_targets: ["src/canon_systems/context_preload.py", "tests/test_mempalace_fallback.py"]
        verification_tests: ["tests/test_mempalace_fallback.py::test_preflight_writes_credential_attestation_json", "tests/test_mempalace_fallback.py::test_preflight_markdown_summarizes_credential_resolution_status"]
      - criterion: "AC5: `canon memory-health --json` includes credential/Secrets Manager attestation alongside backend health rows, and the existing exit-code contract remains backend-health driven unless a required backend is unhealthy or usage is invalid."
        implementation_targets: ["src/canon_systems/memory_health.py", "tests/test_memory_health.py"]
        verification_tests: ["tests/test_memory_health.py::test_memory_health_json_includes_credential_attestation", "tests/test_memory_health.py::test_memory_health_exit_code_unchanged_by_credential_attestation_warning", "tests/test_memory_health.py::test_memory_health_required_backend_failure_still_exits_one"]
      - criterion: "AC6: Existing credential recovery, secret fetching, cache behavior, URL hydration, and readiness-gate behavior remain compatible; no deploy attestation, AWS writes, secret value logging, or plan-file edits are introduced."
        implementation_targets: ["src/canon_systems/aws_secrets.py", "src/canon_systems/shared.py", "src/canon_systems/doctor_cli.py", "src/canon_systems/context_preload.py", "src/canon_systems/memory_health.py"]
        verification_tests: ["tests/test_agent_templates.py::test_hooks_include_credential_recovery_flow", "tests/test_memory_health.py::test_urls_from_home_canon_env_when_local_env_omits_urls", "tests/test_doctor.py::test_doctor_json_ok_when_wired_no_hits", "tests/test_aws_secrets.py::test_apply_canon_systems_secrets_from_aws_preserves_cache_behavior"]
    risks_and_assumptions:
      assumptions:
        - "Credential attestation should classify states such as `ok`, `cache_hit`, `not_configured`, `missing_boto3`, `fetch_failed`, `secret_empty`, and `profile_mismatch` or equivalent stable strings."
        - "A process-env/repo-local AWS profile mismatch remains a warning/degraded credential-resolution signal; it does not by itself change doctor or memory-health exit codes."
        - "The attestation object has its own nested `schema_version` field under `credential_resolution` / `credential_attestation` payloads."
      openQuestions: []
END_HANDOFF_TO_CURSOR_PILOT
