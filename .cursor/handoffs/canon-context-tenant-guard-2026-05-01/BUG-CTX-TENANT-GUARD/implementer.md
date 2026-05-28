HANDOFF_TO_QA
  handoff_id: "canon-context-tenant-guard-2026-05-01"
  acceptance_criteria_covered:
    - criterion: "When existing `.canon/memory/context-latest.md` or `.canon/memory/context-latest.json` contains a company_id or repository_id different from authoritative repo wiring, `canon preflight` clearly invalidates or overwrites the stale context before agents can trust it."
      evidence_files:
        - "src/canon_systems/shared.py:418-441"
        - "src/canon_systems/context_preload.py:100-103"
      evidence_tests:
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_md_and_json_before_network"
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_json_only_before_network"
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_md_only_before_network"
    - criterion: "`canon doctor` exits non-zero on a context tenant mismatch and emits a loud actionable warning in human output plus machine-readable JSON fields that identify expected and observed tenant values and the recommended remediation."
      evidence_files:
        - "src/canon_systems/doctor_cli.py:62-103"
        - "src/canon_systems/doctor_cli.py:347-375"
        - "src/canon_systems/doctor_cli.py:362-423"
      evidence_tests:
        - "tests/test_doctor.py::test_doctor_tenant_mismatch_context_markdown_sidecar"
        - "tests/test_doctor.py::test_doctor_tenant_mismatch_json_sidecar_only"
        - "tests/test_doctor.py::test_doctor_tenant_mismatch_human_stderr_banner"
    - criterion: "Preflight success still writes fresh `context-latest.md` and `context-latest.json` with authoritative `company_id` and `repository_id`, preserving existing MemPalace degraded-status behavior."
      evidence_files:
        - "src/canon_systems/context_preload.py:98-118"
      evidence_tests:
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_md_and_json_before_network"
        - "tests/test_mempalace_fallback.py::test_preflight_stale_tenant_then_unreachable_still_queues_mempalace"
    - criterion: "Agent-facing docs/templates instruct agents to treat mismatched or invalidated `context-latest.*` as untrusted and to prefer `.canon/memory-layer.local.env` / `canon doctor` for repo identity."
      evidence_files:
        - "src/canon_systems/templates/rules/memory-layer-defaults.mdc"
        - "src/canon_systems/templates/agents/scoper.md"
        - "src/canon_systems/templates/agents/implementer.md"
      evidence_tests:
        - "tests/test_agent_templates.py::test_agent_templates_and_defaults_tenant_context_trust_guidance"
        - "tests/test_infra_layout.py::test_packaged_memory_layer_defaults_tenant_context_guard"
    - criterion: "Regression tests cover both markdown and JSON sidecar mismatch cases without live AWS, graph, state, canonical, or MemPalace services."
      evidence_files:
        - "tests/test_mempalace_fallback.py:63-171"
        - "tests/test_doctor.py:133-193"
      evidence_tests:
        - "tests/test_mempalace_fallback.py::test_preflight_invalidates_stale_md_and_json_before_network"
        - "tests/test_doctor.py::test_doctor_tenant_mismatch_context_markdown_sidecar"
        - "tests/test_doctor.py::test_doctor_tenant_mismatch_json_sidecar_only"
  summary: "Preflight now invalidates stale cross-repo context sidecars before network work, doctor exposes loud human and structured JSON mismatch diagnostics, and agent templates no longer trust mismatched context-latest as repo identity."
  decisions:
    - "Treat `.canon/memory-layer.local.env` via `load_repo_context` as authoritative and generated `context-latest.*` as invalidatable sidecars."
    - "Preserve hook compatibility by keeping preflight non-fatal while replacing stale sidecars with an explicit invalidated stub."
  next_actions:
    - "Parent qa-gate may widen pytest or CI beyond the focused four-file regression set if required."
  open_questions:
    - "Checkpoint/state-api hydration was skipped locally when unavailable; confirm in gated environments if needed."
END_HANDOFF_TO_QA
