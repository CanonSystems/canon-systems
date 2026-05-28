HANDOFF_TO_CURSOR_PILOT
  scope_summary: Add a tenant guard so stale hydrated context from another repo cannot remain silently trusted when `.canon/memory-layer.local.env` says this repo is `CSC/canon-systems`. The conservative fix should reuse existing preflight/doctor patterns: validate `context-latest.md` and `context-latest.json` against authoritative repo wiring, loudly mark mismatches invalid, and keep `canon doctor` actionable.
  scope_packet:
    identifiers:
      handoff_id: "canon-context-tenant-guard-2026-05-01"
      company_id: "CSC"
      repository_id: "canon-systems"
      task_id: "BUG-CTX-TENANT-GUARD"
      plan_id: "canon_memory_platform_build_d21073e1"
      workstream_id: "tenant-context-guard"
    story:
      title: "Guard stale cross-repo context-latest tenant metadata"
      userValue: "Canon Systems agents and Edward benefit because repo identity is validated from authoritative wiring before any hydrated memory context is treated as trustworthy, preventing CSC/canon-systems from being mislabeled as Marrow/MJC."
      acceptanceCriteria:
        - "When existing `.canon/memory/context-latest.md` or `.canon/memory/context-latest.json` contains a company_id or repository_id different from authoritative repo wiring, `canon preflight` clearly invalidates or overwrites the stale context before agents can trust it."
        - "`canon doctor` exits non-zero on a context tenant mismatch and emits a loud actionable warning in human output plus machine-readable JSON fields that identify expected and observed tenant values and the recommended remediation."
        - "Preflight success still writes fresh `context-latest.md` and `context-latest.json` with authoritative `company_id` and `repository_id`, preserving existing MemPalace degraded-status behavior."
        - "Agent-facing docs/templates instruct agents to treat mismatched or invalidated `context-latest.*` as untrusted and to prefer `.canon/memory-layer.local.env` / `canon doctor` for repo identity."
        - "Regression tests cover both markdown and JSON sidecar mismatch cases without live AWS, graph, state, canonical, or MemPalace services."
    repository:
      primaryLanguages: ["Python", "Shell"]
      testFramework: "pytest"
      repo_ref: "branch cursor/cursor-sdk-poc at 6dedc2ee893f6dd528b894c2b79d4d69c39d7499; origin git@github.com:CanonSystems/canon-systems.git"
      relevantFiles:
        - "src/canon_systems/context_preload.py"
        - "src/canon_systems/doctor_cli.py"
        - "src/canon_systems/shared.py"
        - "src/canon_systems/cli.py"
        - "src/canon_systems/templates/hooks/memory-preflight.sh"
        - "src/canon_systems/templates/rules/memory-layer-defaults.mdc"
        - "src/canon_systems/templates/agents/scoper.md"
        - "src/canon_systems/templates/agents/implementer.md"
        - "tests/test_mempalace_fallback.py"
        - "tests/test_doctor.py"
        - "tests/test_shared.py"
        - "pyproject.toml"
    constraints:
      dependencies:
        - "Use `.canon/memory-layer.local.env` and `load_repo_context` / repo wiring as authoritative identity; do not derive repo truth from hydrated memory context."
        - "Keep preflight behavior conservative and compatible with existing hook invocation in `src/canon_systems/templates/hooks/memory-preflight.sh`."
        - "Do not introduce live-network test dependencies; existing tests mock request_json/probes."
        - "Preserve current doctor diagnostics for raw IPv4 URLs, AWS cache, and DNS/WARP checks."
      mustNotBreak:
        - "`canon preflight --quiet` still exits 0 in normal degraded MemPalace cases and writes context sidecars."
        - "`canon doctor --json` remains valid JSON and continues returning 1 for tenant mismatch or literal IP hits."
        - "Existing `tests/test_doctor.py` and `tests/test_mempalace_fallback.py` behavior remains intact."
        - "Hook output remains Cursor-compatible JSON with `{ \"permission\": \"allow\" }` unless there is an existing systemMessage condition."
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
    ac_traceability:
      - criterion: "When existing `.canon/memory/context-latest.md` or `.canon/memory/context-latest.json` contains a company_id or repository_id different from authoritative repo wiring, `canon preflight` clearly invalidates or overwrites the stale context before agents can trust it."
        implementation_targets:
          - "src/canon_systems/context_preload.py"
          - "src/canon_systems/shared.py"
        verification_tests:
          - "tests/test_mempalace_fallback.py::test_preflight_invalidates_existing_md_tenant_mismatch_before_remote_calls"
          - "tests/test_mempalace_fallback.py::test_preflight_invalidates_existing_json_tenant_mismatch_before_remote_calls"
      - criterion: "`canon doctor` exits non-zero on a context tenant mismatch and emits a loud actionable warning in human output plus machine-readable JSON fields that identify expected and observed tenant values and the recommended remediation."
        implementation_targets:
          - "src/canon_systems/doctor_cli.py"
        verification_tests:
          - "tests/test_doctor.py::test_doctor_tenant_mismatch_context"
          - "tests/test_doctor.py::test_doctor_json_reports_tenant_mismatch_remediation"
      - criterion: "Preflight success still writes fresh `context-latest.md` and `context-latest.json` with authoritative `company_id` and `repository_id`, preserving existing MemPalace degraded-status behavior."
        implementation_targets:
          - "src/canon_systems/context_preload.py"
        verification_tests:
          - "tests/test_mempalace_fallback.py::test_preflight_ok_no_queue"
          - "tests/test_mempalace_fallback.py::test_preflight_unreachable_records_md_sidecar_and_queue"
      - criterion: "Agent-facing docs/templates instruct agents to treat mismatched or invalidated `context-latest.*` as untrusted and to prefer `.canon/memory-layer.local.env` / `canon doctor` for repo identity."
        implementation_targets:
          - "src/canon_systems/templates/rules/memory-layer-defaults.mdc"
          - "src/canon_systems/templates/agents/scoper.md"
          - "src/canon_systems/templates/agents/implementer.md"
        verification_tests:
          - "tests/test_agent_templates.py::test_agent_templates_warn_context_latest_tenant_mismatch"
          - "tests/test_infra_layout.py::test_memory_layer_defaults_mentions_context_tenant_guard"
      - criterion: "Regression tests cover both markdown and JSON sidecar mismatch cases without live AWS, graph, state, canonical, or MemPalace services."
        implementation_targets:
          - "tests/test_mempalace_fallback.py"
          - "tests/test_doctor.py"
        verification_tests:
          - "pytest tests/test_mempalace_fallback.py tests/test_doctor.py tests/test_agent_templates.py"
    implementation_notes:
      - "Observed `.canon/memory-layer.local.env` currently declares `COMPANY_ID=CSC` and `REPOSITORY_ID=canon-systems`."
      - "Current `.canon/memory/context-latest.md` now matches `CSC/canon-systems`, but `doctor_cli._context_tenant` only parses markdown and `context_preload.run` does not visibly invalidate pre-existing mismatched context before external preflight work."
      - "A conservative design is to add a small reusable parser/validator for `context-latest.md` and `context-latest.json`, call it early in `context_preload.run` after authoritative `repo_ctx` is loaded, and write an explicit invalidated stub/status if mismatched before any network-dependent memory/truth calls can fail."
      - "Doctor already detects markdown mismatch and exits 1; extend that path to cover the JSON sidecar and include explicit expected/observed/remediation/trust-status fields in JSON."
    risks_and_assumptions:
      assumptions:
        - "Authoritative tenant identity for this repo is `.canon/memory-layer.local.env` as surfaced by `load_repo_context` and `canon doctor`."
        - "Invalidating stale context by replacing or marking the local `.canon/memory/context-latest.*` files is acceptable because they are generated artifacts."
        - "The fix should not attempt to solve partner-hub/FMO missing AWS_PROFILE setup, which is a distinct repo wiring issue."
      openQuestions: []
    prior_work_references:
      - artifact_id: "provided_prior_canonical_query:stale_context_latest_mismatch"
        source: "canonical"
        relevance: "Parent supplied prior Canon memory findings that this repo was misidentified as MJC/marrow due to stale cross-repo `context-latest` metadata."
      - artifact_id: "provided_prior_canonical_query:csc_canon_systems_identity"
        source: "canonical"
        relevance: "Parent supplied prior captures confirming this repo is `CSC/canon-systems`, not Innermost/Marrow."
      - artifact_id: "provided_prior_canonical_query:partner_hub_fmo_distinct_issue"
        source: "canonical"
        relevance: "Parent supplied prior memory separating partner-hub/FMO missing AWS_PROFILE setup from this tenant-context guard bug."
    retrieval:
      graph: "degraded: `canon graph query` exited 5 with transport 403 from the sandbox."
      state: "degraded: `canon checkpoint read` exited 5 with localhost connection refused."
      canonical: "degraded: `canon ask` attempted MemPalace retry queue write and failed under read-only sandbox; parent-provided prior canonical query facts were used."
      file: "used: inspected `.canon/memory-layer.local.env`, `.canon/memory/context-latest.md`, `context_preload.py`, `doctor_cli.py`, `memory_health.py`, hook/template files, and related tests."
END_HANDOFF_TO_CURSOR_PILOT
