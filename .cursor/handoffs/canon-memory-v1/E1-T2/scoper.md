# E1-T2 Scoper Packet

**Task:** Fix memory-adapter endpoint resolution + queue fallback
**Wave branch:** `wave/1/canon-memory-v1` (E1-T1 committed @ 0d71319)
**DoR verdict:** PASS

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E1-T2 eliminates silent mempalace 404s by (a) recording an explicit `mempalace_status` block (status/latency_ms/last_error/endpoint_ref) in `.canon/memory/context-latest.md` (+ `.json`) during preflight, (b) adding a stdlib JSONL retry queue at `.canon/memory/mempalace-retry-queue.jsonl` (new module `src/canon_systems/memory_queue.py`, modeled on `src/canon_systems/dor_log.py`'s queue pattern), and (c) wiring `context_preload.py` and `ask_hybrid._mempalace_hits` to classify each attempted `/memory/search` call, enqueue a retry record on non-ok outcomes, and surface the status in `canon ask --json` so failed searches never return as empty success. Queue drain is deferred. Integration test `tests/test_mempalace_fallback.py` mocks `request_json` at both call sites; no live HTTP; stdlib-only; no deps; no git ops; additive living-spec edits only (no overlap with E1-T3 on §5/§6 of SYSTEM-WORKFLOW or release-orchestrator templates)."

  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      plan_id: "canon_memory_platform_build_d21073e1"
      task_id: "E1-T2"
      workstream_id: "wave-1b"
      epic_id: "E1"
      repo_ref: "canon-systems @ wave/1/canon-memory-v1 (E1-T1 committed @ 0d71319)"

    story:
      title: "Fix memory-adapter endpoint resolution + queue fallback"
      userValue: "Agents stop treating mempalace 404s / DNS failures as 'no hits'. Preflight records an explicit mempalace_status in context-latest.md so downstream subagents (scoper, cursor-pilot, qa-gate) can see the backend is degraded, and failed /memory/search calls enqueue a retry record to a local JSONL queue instead of silently dropping — unblocks E1-T3 which wires memory-health into release gates."
      acceptanceCriteria:
        - "AC1: Preflight records `mempalace_status` block in `.canon/memory/context-latest.md` (sub-section with keys status/latency_ms/last_error/endpoint_ref). Status enum: ok | degraded | unreachable | not_configured."
        - "AC2: `.canon/memory/context-latest.json` sidecar gains top-level `mempalace_status` with same 4-field object. Existing keys remain backward-compatible."
        - "AC3: Non-ok preflight outcome appends JSONL record to `.canon/memory/mempalace-retry-queue.jsonl` with keys: queued_at, call_site, endpoint_ref, request_body, last_status, last_error, actor_id, company_id, repository_id. `ok` and `not_configured` do NOT enqueue."
        - "AC4: `ask_hybrid._mempalace_hits` same classify+enqueue; `canon ask --json` output gains top-level `mempalace_status`; default text output gains `mempalace: <status>` stderr line when != ok. `canonical_hits` flow normally."
        - "AC5: New module `src/canon_systems/memory_queue.py` exposes `queue_path()`, `classify_mempalace_response(...)`, `enqueue_mempalace_retry(record)`, `is_degraded(block)`. Stdlib-only; no HTTP; imports only stdlib + `.shared.now_stamp`/`.shared.repo_root`."
        - "AC6: `tests/test_mempalace_fallback.py` covers: (a) preflight unreachable (md + sidecar + queue), (b) preflight ok (no queue), (c) ask unreachable (json payload + queue + stderr), (d) classifier not_configured (no enqueue)."
        - "AC7: Only `context_preload.py` and `ask_hybrid.py` import `memory_queue`. `capture_session.py` untouched."
        - "AC8: Stdlib-only. No pyproject/requirements-dev changes."
        - "AC9: `src/canon_systems/memory_health.py` unchanged (E1-T1 frozen — import only)."
        - "AC10: No edits under backend/**, infra/**, canon-systems-v2/**, .cursor/rules/**, .cursor/plans/**, frozen Wave-0 docs, pyproject.toml, pytest.ini, requirements-dev.txt, .github/workflows/**, src/canon_systems/templates/**, memory_health.py."
        - "AC11: ADDITIVE living-spec: README new subsection `### Memory degraded-mode fallback` AFTER `## Commands` table (don't touch memory-health row). CHANGELOG [Unreleased] Added: new `- E1-T2: ...` bullet at TOP of list (above E1-T1). SYSTEM-WORKFLOW §1 append-only sub-bullet at END of bullet list. DO NOT touch §5 or §6 (E1-T3 owns)."
        - "AC12: `pytest -q` exits 0; import smoke one-liner `from canon_systems.memory_queue import queue_path, classify_mempalace_response, enqueue_mempalace_retry, is_degraded` prints ok; preflight & ask still exit 0 on degraded mempalace."
        - "AC13: No queue drain CLI (future). No git ops."
        - "AC14: Preflight + ask exit codes unchanged on degraded mempalace (returns 0; degraded is advisory)."

      done_signal:
        - "tests/test_mempalace_fallback.py PASS (all 4 sub-cases)."
        - "pytest -q exits 0 at repo root."
        - "memory_queue import smoke prints ok."
        - "canon preflight + ask --json against mocked 404 behave per AC1-AC4."
        - "README + CHANGELOG + SYSTEM-WORKFLOW updated per AC11 (ADDITIVE)."
        - "No diffs under forbidden surfaces."

    in_scope_paths_to_create:
      - "src/canon_systems/memory_queue.py"
      - "tests/test_mempalace_fallback.py"

    in_scope_paths_to_modify:
      - "src/canon_systems/context_preload.py"
      - "src/canon_systems/ask_hybrid.py"
      - "README.md (new subsection AFTER ## Commands table)"
      - "CHANGELOG.md ([Unreleased] Added — TOP of list, above E1-T1)"
      - "docs/SYSTEM-WORKFLOW.md (§1 Runtime model — append-only sub-bullet)"

    shared_surface_overlap_zones_with_parallel_tasks:
      E1-T3:
        - "CHANGELOG.md Added: E1-T3 also inserts bullet. Mitigation: ordered final state E1-T3 > E1-T2 > E1-T1; trivial ordering merge only."
        - "README.md: E1-T3 touches release-orchestrator/gate wording, NOT ## Commands or post-Commands subsection. No collision."
        - "SYSTEM-WORKFLOW.md: E1-T3 touches §5 + possibly §6. E1-T2 touches only §1. Explicit non-overlap."
      guidance_for_implementer:
        - "All living-spec edits MUST be ADDITIVE (new bullets/sections only; no reflows/renamings/reorderings)."
        - "Never modify E1-T1 memory-health row in README command table."
        - "Never modify §5 or §6 of SYSTEM-WORKFLOW.md (E1-T3 owns)."

    out_of_scope_paths:
      - "backend/**, infra/**, canon-systems-v2/**"
      - ".cursor/rules/**, .cursor/plans/**"
      - "Frozen Wave-0 docs"
      - "pyproject.toml, pytest.ini, requirements-dev.txt"
      - ".github/workflows/**"
      - "src/canon_systems/templates/** (E1-T3 owns)"
      - "src/canon_systems/memory_health.py (E1-T1 frozen)"
      - "src/canon_systems/capture_session.py (not a mempalace call site)"
      - "Queue drainer / canon memory-drain (future)"
      - "State/graph backend fallback (mempalace-only)"
      - "backend/memory-adapter contract (frozen this wave)"

    forbidden_surface:
      - "No live HTTP to any backend URL."
      - "No git ops."
      - "No new deps."
      - "No backend/infra/Wave-0-doc changes."
      - "No rule/plan/template edits."
      - "No edits to memory_health.py."
      - "No CI edits."

    queue_contract:
      path: ".canon/memory/mempalace-retry-queue.jsonl"
      record_keys: [queued_at, call_site, endpoint_ref, request_body, last_status, last_error, actor_id, company_id, repository_id]
      enqueue_when: [degraded, unreachable]
      no_enqueue_when: [ok, not_configured]

    mempalace_status_contract:
      block_keys: [status, latency_ms, last_error, endpoint_ref]
      status_enum: [ok, degraded, unreachable, not_configured]
      md_section_title: "## MemPalace Status"
      json_sidecar_key: "mempalace_status"
      ask_hybrid_json_key: "mempalace_status"

    acceptable_scope_expansion:
      pre_authorized:
        - "New module src/canon_systems/memory_queue.py (stdlib-only)."
        - "New tests/test_mempalace_fallback.py."
        - "Small edits to context_preload.py + ask_hybrid.py."
        - "ADDITIVE living-spec edits."
        - "Optional import of BACKENDS from memory_health (read-only)."
      not_pre_authorized:
        - "Edits to memory_health.py."
        - "canon memory-drain CLI (future)."
        - "capture_session.py edits."
        - "Renaming/removing README/CHANGELOG sections."
        - "Edits to §5/§6 of SYSTEM-WORKFLOW.md."
        - "New deps."
        - "Template edits."
        - ".github/workflows edits."
        - "Rule/plan edits."

    openQuestions:
      - "OQ-E1-T2-01 (non-blocking): field name mempalace_status vs backlog's memory_adapter_status → use mempalace_status (parity with memory_health.BACKENDS)."
      - "OQ-E1-T2-02 (non-blocking): queue drain deferred to future canon memory-drain."
      - "OQ-E1-T2-03 (non-blocking): enqueue on not_configured? NO (no attempt)."
      - "OQ-E1-T2-04 (non-blocking): ask exit code on degraded? stays 0."
      - "OQ-E1-T2-05 (non-blocking): queue dedup in v1? NO."
      - "OQ-E1-T2-06 (non-blocking): mock request_json (not urlopen) — module-level seam."
      - "OQ-E1-T2-07 (non-blocking): md subsection title `## MemPalace Status` (implementer may adjust; tests must match)."
      - "OQ-E1-T2-08 (non-blocking): no queue-inspection CLI in v1."

    prior_work_references:
      - ".cursor/handoffs/canon-memory-v1/E1-T1/* (packet-shape precedent; memory_health module; _probe test-seam)"
      - "src/canon_systems/dor_log.py (JSONL queue precedent: _queue_path, _enqueue_failed_event)"
      - "src/canon_systems/context_preload.py (preflight writer — the hook point for AC1-AC3)"
      - "src/canon_systems/ask_hybrid.py::_mempalace_hits (silent-empty-success failure mode AC4 fixes)"
      - "docs/MEMORY-PLATFORM-BACKLOG.md E1-T2 ACs (authoritative)"

    dor_checklist:
      overall: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
