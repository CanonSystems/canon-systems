# E1-T1 Scoper Packet

**Task:** Add `canon memory-health` CLI
**Wave branch:** `wave/1/canon-memory-v1` (cut from origin/main @ f34698e post-Wave-0-merge)
**DoR verdict:** PASS

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E1-T1 opens Wave 1 by adding the `canon memory-health` subcommand: a single stdlib-only CLI that probes each backend's /healthz (knowledge-api = canonical, memory-adapter = mempalace, and stubs state-api + axon-service) in single-flight, returns a structured JSON report with schema_version + overall_status + per-backend {name, status, latency_ms, version, last_error, required, endpoint_ref}, exits 0 only when all required backends reply OK within a per-backend budget, honors CANON_MEMORY_HEALTH_REQUIRED (comma list) as the fail-closed set, and reports 'not_configured' when a backend's URL env var is unset and 'not_deployed' when the URL is set but the stub returns a non-OK scaffold. Deliverables: new module src/canon_systems/memory_health.py, CLI registration in src/canon_systems/cli.py, tests/test_memory_health.py (healthy / degraded / unreachable / not_configured / env-override / exit-code matrix / JSON shape), and living-spec mirroring in README command table, CHANGELOG [Unreleased], docs/SYSTEM-WORKFLOW.md §6. No live HTTP against real backends (unittest.mock.patch on urllib.request.urlopen only). No edits to backend/**, infra/**, canon-systems-v2/**, .cursor/rules/**, .cursor/plans/**, or any frozen Wave-0 doc. No git commit/push — parent handles per-task commit on READY_TO_MERGE per rule §9."

  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      plan_id: "canon_memory_platform_build_d21073e1"
      task_id: "E1-T1"
      workstream_id: "wave-1a"
      epic_id: "E1"
      repo_ref: "canon-systems @ wave/1/canon-memory-v1 (cut from origin/main tip f34698e post-Wave-0-merge)"

    story:
      title: "Add canon memory-health CLI"
      userValue: "Agents and release-orchestrator get an honest, fail-closed signal about backend memory health before acting or merging; this is the gate referenced by discipline rule §6 and workflow §5.1 from Wave 1 onward, and it unblocks E1-T2 (memory-adapter endpoint resolution) and E1-T3 (release gate wiring)."
      acceptanceCriteria:
        - "AC1: `canon memory-health` is a registered subcommand on `canon` (shows in `canon --help` and `canon memory-health --help`). Backed by new module `src/canon_systems/memory_health.py` exposing `run(argv: list[str] | None = None) -> int` imported and wired in `src/canon_systems/cli.py`."
        - "AC2: Emits a single JSON object to stdout matching the schema in `json_output_contract` below (schema_version, generated_at, overall_status, required_set, backends[]). Nothing else is written to stdout. Human-readable logs (if any) go to stderr and only when `--verbose` is passed."
        - "AC3: Exits 0 iff every backend in the resolved required-set has status == 'ok'. Exits 1 if any required backend has status in ('degraded','unreachable','not_deployed','not_configured','error'). `overall_status` is 'ok' when exit 0, 'degraded' when all required are ok but any optional is degraded/unreachable, 'unhealthy' when any required is not ok."
        - "AC4: Per-backend probe is single-flight (one GET to `<base>/healthz`), bounded by a timeout (default 2000 ms) configurable via `CANON_MEMORY_HEALTH_TIMEOUT_MS` (integer, 100-60000 ms; invalid value falls back to default and logs to stderr). Latency is measured as wall-clock ms around the single request and recorded as integer `latency_ms`."
        - "AC5: Required-set resolution — defaults to `canonical,mempalace`. `CANON_MEMORY_HEALTH_REQUIRED` (comma list, case-insensitive, whitespace-trimmed) overrides entirely when set. Empty string means 'no required backends'. Unknown names in the override surface as an error entry in backends[] with status='unknown_backend' and cause exit 1."
        - "AC6: Standard backend set = {`canonical`→KNOWLEDGE_API_URL, `mempalace`→MEMORY_ADAPTER_URL, `state`→STATE_API_URL, `graph`→AXON_SERVICE_URL}. URL env vars resolved from: process env > `<repo>/.canon/memory-layer.local.env` > `<repo>/.canon/scoper-chat.env` > hard default (reusing `load_env_file` + `repo_root()` from `shared.py`)."
        - "AC7: Status mapping: 'ok' (HTTP 200 + body.status in ok/healthy/absent); 'degraded' (HTTP 200 + body.status=='scaffold' OR non-JSON); 'unreachable' (connection error/DNS/timeout/non-2xx); 'not_configured' (URL env unset); 'not_deployed' (optional backend + probe failed). Required backends never downgrade to 'not_deployed'."
        - "AC8: `version` field from body.get('version'); null when absent. `last_error` null on ok; otherwise ≤200-char single-line failure summary. `endpoint_ref` is fully-resolved probed URL."
        - "AC9: Flags: `[--required <csv>]`, `[--timeout-ms <int>]`, `[--json]` (idempotent default), `[--output <path>]`, `[--verbose]`. Unknown flags exit 2."
        - "AC10: Stdlib-only (urllib, json, os, sys, time, pathlib, argparse, dataclasses). No new runtime/dev deps."
        - "AC11: tests/test_memory_health.py PASS covering: healthy; required-degraded; all-required-unreachable; not_configured (URL unset); env_override_expands/shrinks; unknown_backend; timeout_budget; json_shape; output_flag."
        - "AC12: README.md command table gains row after `canon flow-audit`: `canon memory-health [--required <csv>] [--timeout-ms <int>] [--output <path>] [--verbose]`."
        - "AC13: CHANGELOG.md [Unreleased] § Added gains bullet `E1-T1: canon memory-health CLI — ...`."
        - "AC14: docs/SYSTEM-WORKFLOW.md §6 'Validation commands' gains bullet `Memory health probe: canon memory-health [--required <csv>] [--timeout-ms <int>]`."
        - "AC15: `pytest -q` at repo root exits 0; `bash scripts/smoke-test.sh` exits 0."
        - "AC16: `python -c 'from canon_systems.memory_health import run; import sys; sys.exit(run([\"--required\",\"\"]))'` exits 0."
        - "AC17: No edits to forbidden surface. No git ops. No live HTTP in tests or build."

      done_signal:
        - "tests/test_memory_health.py PASS."
        - "README.md, CHANGELOG.md, docs/SYSTEM-WORKFLOW.md updated."
        - "`pytest -q` exits 0 at repo root."
        - "`canon memory-health --help` usage prints."
        - "No diffs under forbidden surfaces."

    in_scope_paths_to_create:
      - "src/canon_systems/memory_health.py"
      - "tests/test_memory_health.py"

    in_scope_paths_to_modify:
      - "src/canon_systems/cli.py (register `memory-health` subparser + dispatch)"
      - "README.md (command table row per AC12)"
      - "CHANGELOG.md ([Unreleased] § Added per AC13)"
      - "docs/SYSTEM-WORKFLOW.md (§6 per AC14)"

    out_of_scope_paths:
      - "backend/**, infra/**, canon-systems-v2/**"
      - ".cursor/rules/**, .cursor/plans/**"
      - "Frozen Wave-0 docs (MIGRATION-NOTES, INFRA-IMPORT, WAVE-0-CLOSEOUT, WAVE-0-AUDIT, DEPRECATIONS, OBSIDIAN-MIND-CATALOGUE, MEMORY-PLATFORM-PLAN, MEMORY-PLATFORM-BACKLOG)"
      - "pyproject.toml, pytest.ini, requirements-dev.txt"
      - ".github/workflows/**"
      - "src/canon_systems/templates/** (E1-T3 owns)"

    forbidden_surface:
      - "No live HTTP to KNOWLEDGE_API_URL / MEMORY_ADAPTER_URL / STATE_API_URL / AXON_SERVICE_URL."
      - "No git commit/push/branch ops — parent owns per rule §9."
      - "No new deps."
      - "No backend /healthz changes."
      - "No rule or plan edits."

    json_output_contract:
      top_level_keys: [schema_version, generated_at, overall_status, required_set, timeout_ms, backends]
      backend_object_keys: [name, required, endpoint_ref, status, latency_ms, version, last_error]
      exit_code_matrix:
        - "all required ok → exit 0, overall=ok"
        - "all required ok + some optional impaired → exit 0, overall=degraded"
        - "any required not ok → exit 1, overall=unhealthy"

    acceptable_scope_expansion:
      pre_authorized:
        - "New module src/canon_systems/memory_health.py."
        - "New tests/test_memory_health.py."
        - "CLI subparser registration in cli.py."
        - "Living-spec edits (README, CHANGELOG, SYSTEM-WORKFLOW §6)."
        - "Internal `_probe(url, timeout_ms)` seam for test injection."
      not_pre_authorized:
        - "New deps; backend /healthz changes; release-orchestrator template edits (E1-T3); flow-audit/qa-validate evidence wiring (E1-T3); rule §6 gate wiring (E1-T3); auto-persist memory-health-latest.json (E1-T3)."

    openQuestions:
      - "OQ-E1-T1-01: backlog=4 backends, parent brief mentioned 3. Resolution: follow backlog (4 backends; state+graph optional default not_configured). Non-blocking."
      - "OQ-E1-T1-02: add memory-health to rule §6 now? NO — E1-T3 owns. Non-blocking."
      - "OQ-E1-T1-03: auto-persist evidence to .canon/memory/memory-health-latest.json? NO in v1 (use --output flag). E1-T3 decides sticky path. Non-blocking."
      - "OQ-E1-T1-04: /healthz vs /ready? /healthz only — no /ready route exists. Non-blocking."
      - "OQ-E1-T1-05: parallel probes? NO — sequential single-flight sufficient. Non-blocking."
      - "OQ-E1-T1-06: honor --repo-root? YES via existing parent dispatcher. Non-blocking."
      - "OQ-E1-T1-07: auth on /healthz? NO — all /healthz are unauthenticated. Non-blocking."
      - "OQ-E1-T1-08: run qa-validate / dor-log at task end? parent orchestrator handles. Non-blocking."

    prior_work_references:
      - ".cursor/handoffs/canon-memory-v1/E0-T5/scoper.md (packet-shape precedent)"
      - "docs/WAVE-0-CLOSEOUT.md (resume state)"
      - "docs/MEMORY-PLATFORM-BACKLOG.md epic E1 (authoritative ACs)"
      - ".cursor/rules/memory-platform-build-discipline.mdc §§3-6, §§9-10"
      - "src/canon_systems/flow_audit.py + qa_validate.py (CLI wiring precedent)"
      - "src/canon_systems/dor_log.py (stdlib urllib probe precedent)"
      - "backend/{knowledge-api,memory-adapter,state-api,axon-service} /healthz shapes"

    dor_checklist:
      overall: "pass"

END_HANDOFF_TO_CURSOR_PILOT
```
