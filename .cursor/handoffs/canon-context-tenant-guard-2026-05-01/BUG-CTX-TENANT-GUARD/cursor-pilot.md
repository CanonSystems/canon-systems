CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor. This prompt must be executed by that subagent (default model: `composer-2-fast`), not by the parent planner agent.
</ROLE>

<TASK>
Implement "Guard stale cross-repo context-latest tenant metadata" so Canon Systems agents validate repo identity from authoritative wiring before trusting hydrated memory context. This prevents this repo, `CSC/canon-systems`, from being silently mislabeled by stale context from another tenant/repository such as Marrow/MJC.
</TASK>

<ACCEPTANCE_CRITERIA>
- When existing `.canon/memory/context-latest.md` or `.canon/memory/context-latest.json` contains a company_id or repository_id different from authoritative repo wiring, `canon preflight` clearly invalidates or overwrites the stale context before agents can trust it.
- `canon doctor` exits non-zero on a context tenant mismatch and emits a loud actionable warning in human output plus machine-readable JSON fields that identify expected and observed tenant values and the recommended remediation.
- Preflight success still writes fresh `context-latest.md` and `context-latest.json` with authoritative `company_id` and `repository_id`, preserving existing MemPalace degraded-status behavior.
- Agent-facing docs/templates instruct agents to treat mismatched or invalidated `context-latest.*` as untrusted and to prefer `.canon/memory-layer.local.env` / `canon doctor` for repo identity.
- Regression tests cover both markdown and JSON sidecar mismatch cases without live AWS, graph, state, canonical, or MemPalace services.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-context-tenant-guard-2026-05-01
- task_id: BUG-CTX-TENANT-GUARD
- plan_id: canon_memory_platform_build_d21073e1
- workstream_id: tenant-context-guard
- company_id: CSC
- repository_id: canon-systems
- scope_summary: Add a tenant guard so stale hydrated context from another repo cannot remain silently trusted when `.canon/memory-layer.local.env` says this repo is `CSC/canon-systems`. Reuse existing preflight/doctor patterns: validate `context-latest.md` and `context-latest.json` against authoritative repo wiring, loudly mark mismatches invalid, and keep `canon doctor` actionable.
- retrieval_notes:
  - graph: degraded; `canon graph query` exited 5 with transport 403 from the sandbox.
  - state: degraded; `canon checkpoint read` exited 5 with localhost connection refused.
  - canonical: parent `canon ask` in `CSC/canon-systems` returned prior captures showing stale `MJC/marrow` misidentification and partner-hub/FMO as a distinct credentials issue.
  - file: scoper inspected the relevant files and tests.
</CONTEXT>

<REPOSITORY>
- primaryLanguages: ["Python", "Shell"]
- testFramework: pytest
- repo_ref: branch cursor/cursor-sdk-poc
- relevantFiles:
  - src/canon_systems/context_preload.py
  - src/canon_systems/doctor_cli.py
  - src/canon_systems/shared.py
  - src/canon_systems/cli.py
  - src/canon_systems/templates/hooks/memory-preflight.sh
  - src/canon_systems/templates/rules/memory-layer-defaults.mdc
  - src/canon_systems/templates/agents/scoper.md
  - src/canon_systems/templates/agents/implementer.md
  - tests/test_mempalace_fallback.py
  - tests/test_doctor.py
  - tests/test_shared.py
  - tests/test_agent_templates.py
  - tests/test_infra_layout.py
  - pyproject.toml
- dependencies:
  - Use `.canon/memory-layer.local.env` and `load_repo_context` / repo wiring as authoritative identity; do not derive repo truth from hydrated memory context.
  - Keep preflight behavior conservative and compatible with existing hook invocation in `src/canon_systems/templates/hooks/memory-preflight.sh`.
  - Do not introduce live-network test dependencies; existing tests mock `request_json` / probes.
  - Preserve current doctor diagnostics for raw IPv4 URLs, AWS cache, and DNS/WARP checks.
- mustNotBreak:
  - `canon preflight --quiet` still exits 0 in normal degraded MemPalace cases and writes context sidecars.
  - `canon doctor --json` remains valid JSON and continues returning 1 for tenant mismatch or literal IP hits.
  - Existing `tests/test_doctor.py` and `tests/test_mempalace_fallback.py` behavior remains intact.
  - Hook output remains Cursor-compatible JSON with `{ "permission": "allow" }` unless there is an existing systemMessage condition.
</REPOSITORY>

<REASONING>
Implement a small, reusable tenant-context validator rather than duplicating ad hoc markdown parsing. The authoritative expected identity must come from `load_repo_context` / local repo wiring, not from `context-latest.*`.

Acceptance coverage:
- AC1 and AC3: add shared tenant-context parsing and early preflight invalidation in `src/canon_systems/shared.py` and `src/canon_systems/context_preload.py`; cover with mismatch and existing degraded preflight tests.
- AC2: extend `src/canon_systems/doctor_cli.py` to check both markdown and JSON sidecars and expose expected/observed/remediation fields in human and JSON output.
- AC4: update agent-facing templates to treat mismatched or invalidated context as untrusted.
- AC5: keep tests local/mocked and avoid live AWS, graph, state, canonical, or MemPalace dependencies.
</REASONING>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- wave 1: run `ws1` and `ws3` in parallel.
- wave 2: run `ws2` after `ws1`.
- wave 3: run `ws4` after `ws1`, `ws2`, and `ws3`.

Workstream `ws1`:
- goal: Add shared tenant-context parsing and preflight invalidation.
- targets: `src/canon_systems/shared.py`, `src/canon_systems/context_preload.py`, `tests/test_shared.py`, `tests/test_mempalace_fallback.py`.
- tests: mismatch markdown/json sidecar tests plus existing preflight degraded tests.
- can_run_parallel: true

Workstream `ws2`:
- goal: Extend doctor tenant diagnostics for markdown and JSON sidecars.
- targets: `src/canon_systems/doctor_cli.py`, `tests/test_doctor.py`.
- depends_on: `ws1`

Workstream `ws3`:
- goal: Update agent-facing tenant trust guidance.
- targets: `src/canon_systems/templates/rules/memory-layer-defaults.mdc`, `src/canon_systems/templates/agents/scoper.md`, `src/canon_systems/templates/agents/implementer.md`, `tests/test_agent_templates.py`, `tests/test_infra_layout.py`.
- can_run_parallel: true

Workstream `ws4`:
- goal: Run focused regression tests and fix integration fallout.
- depends_on: `ws1`, `ws2`, `ws3`
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Produce only the code changes needed to satisfy all acceptance criteria, plus tests that cover each. Do not refactor unrelated code. Preserve existing CLI and hook behavior unless directly required by the tenant-context guard.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
When running multiple parallel streams, each implementer must emit:

HANDOFF_TO_QA_SHARD
  handoff_id: "canon-context-tenant-guard-2026-05-01"
  shard_id: "<workstream id>"
  acceptance_criteria_covered:
    - criterion: "<exact AC text>"
      evidence_files:
        - "path/to/impl.ext:<line range>"
      evidence_tests:
        - "path/to/test.ext::<test name>"
  summary: "<1 sentence on this shard's changes>"
END_HANDOFF_TO_QA_SHARD

Parent must aggregate all shard outputs into one final `HANDOFF_TO_QA` before invoking `qa-gate`.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
