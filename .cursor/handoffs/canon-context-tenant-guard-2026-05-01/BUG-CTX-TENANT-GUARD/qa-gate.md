GATE_RESULTS
  handoff_id: "canon-context-tenant-guard-2026-05-01"
  verdict: PASS
  acceptance_criteria:
    - criterion: "When existing `.canon/memory/context-latest.md` or `.canon/memory/context-latest.json` contains a company_id or repository_id different from authoritative repo wiring, `canon preflight` clearly invalidates or overwrites the stale context before agents can trust it."
      status: PASS
      covering_tests:
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_md_and_json_before_network"
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_json_only_before_network"
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_md_only_before_network"
      run_result: "pass"
    - criterion: "`canon doctor` exits non-zero on a context tenant mismatch and emits a loud actionable warning in human output plus machine-readable JSON fields that identify expected and observed tenant values and the recommended remediation."
      status: PASS
      covering_tests:
        - "tests/test_doctor.py::test_doctor_tenant_mismatch_context_markdown_sidecar"
        - "tests/test_doctor.py::test_doctor_tenant_mismatch_json_sidecar_only"
        - "tests/test_doctor.py::test_doctor_tenant_mismatch_human_stderr_banner"
      run_result: "pass"
    - criterion: "Preflight success still writes fresh `context-latest.md` and `context-latest.json` with authoritative `company_id` and `repository_id`, preserving existing MemPalace degraded-status behavior."
      status: PASS
      covering_tests:
        - "tests/test_mempalace_fallback.py::test_preflight_stale_tenant_then_unreachable_still_queues_mempalace"
        - "tests/test_mempalace_fallback.py::test_preflight_unreachable_records_md_sidecar_and_queue"
        - "tests/test_mempalace_fallback.py::test_preflight_ok_no_queue"
      run_result: "pass"
    - criterion: "Agent-facing docs/templates instruct agents to treat mismatched or invalidated `context-latest.*` as untrusted and to prefer `.canon/memory-layer.local.env` / `canon doctor` for repo identity."
      status: PASS
      covering_tests:
        - "tests/test_agent_templates.py::test_agent_templates_and_defaults_tenant_context_trust_guidance"
        - "tests/test_infra_layout.py::test_packaged_memory_layer_defaults_tenant_context_guard"
      run_result: "pass"
    - criterion: "Regression tests cover both markdown and JSON sidecar mismatch cases without live AWS, graph, state, canonical, or MemPalace services."
      status: PASS
      covering_tests:
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_md_and_json_before_network"
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_json_only_before_network"
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_md_only_before_network"
        - "tests/test_doctor.py::test_doctor_tenant_mismatch_context_markdown_sidecar"
        - "tests/test_doctor.py::test_doctor_tenant_mismatch_json_sidecar_only"
      run_result: "pass"
  iterations: 0
  regression_checked: true
  remaining_gaps: []
  commands_run:
    - "python3 -m pytest <11 AC-specific tests> -q -> 11 passed"
    - "python3 -m pytest tests/test_mempalace_fallback.py tests/test_doctor.py tests/test_agent_templates.py tests/test_infra_layout.py tests/test_shared.py -q -> 88 passed"
  notes: "No QA fixes were needed. Lints reported no errors for the relevant source and test files. `CANON_STATE_API_URL` was unset, so checkpoint HTTP read/write was skipped per dev/sandbox policy."
END_GATE_RESULTS
