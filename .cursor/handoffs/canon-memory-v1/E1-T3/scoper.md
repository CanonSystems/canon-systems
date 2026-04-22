# E1-T3 Scoper Packet

**Task:** Release gate — require memory-health PASS for critical backends
**Wave branch:** `wave/1/canon-memory-v1` (E1-T1 committed @ 0d71319; E1-T2 in-flight)
**DoR verdict:** PASS

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E1-T3 closes Wave-1b by wiring `canon memory-health` into release-orchestrator merge gates as a hard, flow-audit-enforced check. Three surfaces change: (1) `src/canon_systems/templates/agents/release-orchestrator.md` gains a new required Merge-gates bullet naming memory-health as a gate + documenting the evidence-artifact contract (`.cursor/handoffs/<handoff_id>/<task_id>/memory-health.json` produced via `canon memory-health --output <path>`); (2) `src/canon_systems/flow_audit.py` gets a new opt-in flag `--require-memory-health` that verifies evidence exists, parses as valid JSON with schema_version='1', and has overall_status='ok'; (3) tests extended: `tests/test_agent_templates.py` asserts new gate bullet; `tests/test_flow_audit.py` adds 3 cases (ok/missing/unhealthy) + back-compat lock. Living-spec: CHANGELOG bullet at TOP of Added (above E1-T2); SYSTEM-WORKFLOW §5 + §6 new bullets. NO edits to memory_health.py (E1-T1 frozen), context_preload/ask_hybrid/memory_queue (E1-T2 owns), qa_validate.py (singular ownership to flow-audit), rule §6 (declined — tooling is enforcement surface), README (E1-T2 owns), SYSTEM-WORKFLOW §1 (E1-T2 owns)."

  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      plan_id: "canon_memory_platform_build_d21073e1"
      task_id: "E1-T3"
      workstream_id: "wave-1b"
      epic_id: "E1"
      repo_ref: "canon-systems @ wave/1/canon-memory-v1 (E1-T1 committed @ 0d71319)"

    story:
      title: "Release gate: require memory-health PASS for critical backends"
      userValue: "Release-orchestrator gains a hard, machine-checked memory-health gate so no Wave-1+ task can auto-merge when required memory-platform backends are unhealthy. Evidence persisted per handoff; flow-audit (already per-task) becomes enforcement surface. Closes rule §6 loop without drifting the authoritative rule."
      acceptanceCriteria:
        - "AC1: Release-orchestrator template adds new Merge-gates bullet naming memory-health as required gate; evidence path `.cursor/handoffs/<handoff_id>/<task_id>/memory-health.json`; producer `canon memory-health --output <path>`; verifier `canon flow-audit --require-memory-health`."
        - "AC2: `flow_audit.py` gains `--require-memory-health` flag (default off). When set, verifies evidence exists, parses as JSON, has schema_version=='1' and overall_status=='ok'. Failures produce distinct diagnostics; exit 1 on any failure."
        - "AC3: Evidence path contract: `.cursor/handoffs/<handoff_id>/<task_id>/memory-health.json` (per-task; parallel to packet quartet)."
        - "AC4: Back-compat: flag default off; Wave-0 packets and pre-gate handoffs continue to pass without the flag. Parent orchestrator opts in from Wave 1 onward per updated template."
        - "AC5: Schema strictness: missing/non-string schema_version, mismatch, missing/non-string overall_status, non-ok overall_status → specific per-defect error strings. Malformed JSON → `invalid JSON in memory-health evidence: <path>`."
        - "AC6: Sampling: existing `--sample-rate` skip path unchanged; memory-health check also skipped when task sampled out."
        - "AC7: `qa_validate.py` NOT modified — singular ownership to flow-audit."
        - "AC8: Rule §6 NOT modified — declined explicitly; tooling is the enforcement surface."
        - "AC9: `tests/test_agent_templates.py` asserts template contains: 'memory-health' in Merge-gates context, `.cursor/handoffs/<handoff_id>/<task_id>/memory-health.json`, `--require-memory-health`, `canon memory-health --output`."
        - "AC10: `tests/test_flow_audit.py` adds `test_flow_audit_passes_with_memory_health_evidence_ok` (packet + memory-health.json with overall_status=ok; --require-memory-health; exit 0)."
        - "AC11: Adds `test_flow_audit_fails_when_memory_health_evidence_missing` (packet exists; memory-health.json absent; --require-memory-health; exit 1 + `missing memory-health evidence` diagnostic)."
        - "AC12: Adds `test_flow_audit_fails_when_memory_health_overall_status_not_ok` (evidence has overall_status=unhealthy; --require-memory-health; exit 1 + `overall_status='unhealthy' (expected 'ok')` diagnostic)."
        - "AC13: Adds explicit back-compat lock: without `--require-memory-health`, handoff with NO memory-health.json still passes."
        - "AC14: CHANGELOG [Unreleased] Added — new `- E1-T3: ...` bullet inserted ABOVE E1-T2 bullet (final order E1-T3 > E1-T2 > E1-T1)."
        - "AC15: SYSTEM-WORKFLOW §5 gets additive bullet describing `canon flow-audit --require-memory-health` enforcement; do NOT modify existing line 99-104 paragraph beyond additive expansion."
        - "AC16: SYSTEM-WORKFLOW §6 gets additive bullet documenting evidence-persistence form + enforcement form."
        - "AC17: Scope isolation from E1-T2 — README NOT modified; SYSTEM-WORKFLOW §1 NOT modified; only CHANGELOG ordering overlaps (parent resolves)."
        - "AC18: Forbidden surfaces unchanged (memory_health.py, E1-T2 files, qa_validate.py, backend/**, infra/**, canon-systems-v2/**, .cursor/rules/**, .cursor/plans/**, pyproject.toml, pytest.ini, requirements-dev.txt, .github/workflows/**, frozen Wave-0 docs). No new deps. No git ops."
        - "AC19: `pytest -q` exits 0; `bash scripts/smoke-test.sh` exits 0; `canon flow-audit --help` shows `--require-memory-health`."

      done_signal:
        - "tests/test_agent_templates.py PASS (extended or new test asserts new gate bullet)."
        - "tests/test_flow_audit.py PASS (3 new cases + back-compat lock)."
        - "pytest -q exits 0 at repo root."
        - "canon flow-audit --help shows --require-memory-health."
        - "CHANGELOG + SYSTEM-WORKFLOW §5 + §6 updated per AC14/15/16 (ADDITIVE)."
        - "Release-orchestrator template contains memory-health gate bullet per AC1/AC9."
        - "No diffs under forbidden surfaces."

    in_scope_paths_to_create: []

    in_scope_paths_to_modify:
      - "src/canon_systems/templates/agents/release-orchestrator.md (AC1 — new Merge-gates bullet + evidence contract doc)"
      - "src/canon_systems/flow_audit.py (AC2/AC3/AC5/AC6 — new --require-memory-health flag + evidence check)"
      - "tests/test_agent_templates.py (AC9 — assert new gate bullet text)"
      - "tests/test_flow_audit.py (AC10/AC11/AC12/AC13 — 3 new cases + back-compat lock)"
      - "CHANGELOG.md (AC14 — new bullet above E1-T2 under [Unreleased] Added)"
      - "docs/SYSTEM-WORKFLOW.md (AC15 §5 new bullet, AC16 §6 new bullet — additive only)"

    out_of_scope_paths:
      - "src/canon_systems/memory_health.py (E1-T1 frozen)"
      - "src/canon_systems/{context_preload,ask_hybrid,memory_queue}.py (E1-T2)"
      - "src/canon_systems/qa_validate.py (AC7)"
      - "src/canon_systems/cli.py (memory-health + flow-audit already registered)"
      - ".cursor/rules/memory-platform-build-discipline.mdc (AC8)"
      - "README.md (E1-T2 owns)"
      - "docs/SYSTEM-WORKFLOW.md §1 (E1-T2 owns)"
      - "backend/**, infra/**, canon-systems-v2/**"
      - ".cursor/plans/**"
      - "Frozen Wave-0 docs"
      - "pyproject.toml, pytest.ini, requirements-dev.txt, .github/workflows/**"
      - ".cursor/handoffs/canon-memory-v1/E0-*/** (no back-fill)"

    forbidden_surface:
      - "No edits to memory_health.py, E1-T2 files, qa_validate.py, rule file, plan file, templates other than release-orchestrator.md."
      - "No new deps."
      - "No live HTTP in tests (fixtures only)."
      - "No git ops."
      - "No Wave-0 memory-health.json back-fill."
      - "No new helper modules."
      - "No reflow/reorder of existing content."

    shared_surface_overlap_zones_with_parallel_tasks:
      E1-T2:
        - "CHANGELOG.md Added: E1-T3 inserts NEW bullet ABOVE E1-T2's; final order top→bottom E1-T3 > E1-T2 > E1-T1. Parent resolves at commit time (ordering-only)."
        - "README.md: NO overlap — E1-T3 does NOT touch README."
        - "SYSTEM-WORKFLOW.md: distinct sections — E1-T2 §1; E1-T3 §5+§6."

    evidence_artifact_contract:
      path: ".cursor/handoffs/<handoff_id>/<task_id>/memory-health.json"
      producer: "canon memory-health --output .cursor/handoffs/<handoff_id>/<task_id>/memory-health.json"
      consumer: "canon flow-audit --handoff-id <id> --task-id <id> --require-memory-health"
      required_fields_checked: [schema_version=='1', overall_status=='ok']
      failure_diagnostics:
        - "missing memory-health evidence: <path>"
        - "invalid JSON in memory-health evidence: <path>"
        - "memory-health evidence payload must be object: <path>"
        - "memory-health evidence schema_version mismatch (got <v>, expected '1'): <path>"
        - "memory-health evidence overall_status='<s>' (expected 'ok'): <path>"

    flow_audit_flag_contract:
      new_flag: "--require-memory-health"
      default: false
      behavior_unset: "identical to current flow-audit (Wave-0 semantics preserved)"
      behavior_set_sampled_out: "SKIPPED path returns 0 (no memory-health check)"
      behavior_set_selected: "Verify evidence per contract; fail → exit 1 with diagnostic"

    template_edit_contract:
      target_file: "src/canon_systems/templates/agents/release-orchestrator.md"
      target_section: "'## Required governance' > '3. Merge gates (all required)'"
      insertion: "append new bullet after existing `canon flow-audit --handoff-id ... --sample-rate 0.2`"
      required_tokens: ["memory-health", "`.cursor/handoffs/<handoff_id>/<task_id>/memory-health.json`", "`canon memory-health --output`", "`--require-memory-health`"]

    acceptable_scope_expansion:
      pre_authorized:
        - "`--require-memory-health` argparse flag in flow_audit.py"
        - "Small local helper `_collect_memory_health_errors(base: Path) -> list[str]` in flow_audit.py"
        - "Append new Merge-gates bullet to release-orchestrator template"
        - "Extend tests/test_agent_templates.py + tests/test_flow_audit.py"
        - "Additive-only CHANGELOG + SYSTEM-WORKFLOW §5 + §6 edits"
      not_pre_authorized:
        - "Edits to memory_health.py, qa_validate.py, rule file"
        - "New runtime deps"
        - "Wave-0 back-fill"
        - "New top-level CLI subcommand"
        - "Template edits to other agent templates"
        - "Reordering/reflow of existing content"

    openQuestions:
      - "OQ-E1-T3-01: rule §6 edit? NO — already lists memory-health conceptually; tooling is enforcement."
      - "OQ-E1-T3-02: evidence path? per-task under handoff dir."
      - "OQ-E1-T3-03: qa_validate.py also? NO — singular to flow-audit."
      - "OQ-E1-T3-04: Wave-0 back-fill? NO — opt-in flag covers back-compat."
      - "OQ-E1-T3-05: new helper module? NO — inline in flow_audit.py."
      - "OQ-E1-T3-06: sampling interaction? skip path unchanged."
      - "OQ-E1-T3-07: TTL on generated_at? NO in v1."
      - "OQ-E1-T3-08: deploy-gate memory-health? OUT OF SCOPE — merge-gate only."
      - "OQ-E1-T3-09: lint required_set/backends fields? NO — overall_status authoritative."
      - "OQ-E1-T3-10: CHANGELOG ordering with E1-T2 — parent resolves."

    prior_work_references:
      - ".cursor/handoffs/canon-memory-v1/E1-T1/* (memory-health JSON schema; OQ-02/03 deferrals resolved here)"
      - ".cursor/handoffs/canon-memory-v1/E1-T2/scoper.md (shared-surface discipline precedent)"
      - "docs/MEMORY-PLATFORM-BACKLOG.md E1-T3 ACs (authoritative)"
      - ".cursor/rules/memory-platform-build-discipline.mdc §6 line 99"
      - "docs/SYSTEM-WORKFLOW.md §5 lines 99-104 (anchor for additive bullet); §6 lines 116-122"
      - "src/canon_systems/flow_audit.py — argparse + _sample_selected + errors aggregation"
      - "src/canon_systems/templates/agents/release-orchestrator.md — Merge-gates list structure"
      - "tests/test_flow_audit.py — _write_task_artifacts helper + monkeypatch pattern"

    dor_checklist:
      overall: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
