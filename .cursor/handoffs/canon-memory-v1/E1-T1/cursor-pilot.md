# E1-T1 Cursor-Pilot Prompt

Generated from `.cursor/handoffs/canon-memory-v1/E1-T1/scoper.md` (DoR PASS).

Parent orchestrator elected single-stream execution (per STOP_CONDITIONS): one implementer produces both code + tests + docs in one shot; within-task parallelization would add more coordination cost than it saves for ~300 LOC. Cross-task parallelization at the wave level is retained (E1-T2 + E1-T3 fan out after E1-T1 lands).

---

**ROLE:** `implementer` (default: `composer-2-fast`) — implement code/tests exactly as scoped. No re-scoping. No git ops (parent owns per rule §9). Stay within in-scope surface.

**TASK:** Add `canon memory-health` CLI — stdlib-only subcommand that sequentially single-flight probes `/healthz` across canonical/mempalace/state/graph backends, emits structured JSON, exits 0 iff all required backends respond OK within budget. Honors `CANON_MEMORY_HEALTH_REQUIRED` env.

**ACCEPTANCE CRITERIA:** All 17 ACs from scoper packet (AC1-AC17). See scoper.md for full text.

**CONTEXT:**
- `handoff_id: canon-memory-v1`, `plan_id: canon_memory_platform_build_d21073e1`, `task_id: E1-T1`, `workstream_id: wave-1a`, `epic_id: E1`
- `repository_id: canon-systems @ wave/1/canon-memory-v1` (cut from origin/main @ f34698e)
- Non-blocking OQ resolutions baked in (4 backends; no rule-§6 wiring here; no auto-persist; /healthz only; sequential probes; honor --repo-root; no auth headers)

**REPOSITORY:**
- primaryLanguages: Python (stdlib-only per AC10)
- testFramework: pytest
- relevantFiles: `src/canon_systems/{memory_health.py[new], cli.py, shared.py, flow_audit.py, qa_validate.py, dor_log.py}`, `tests/test_memory_health.py[new]`, `README.md`, `CHANGELOG.md`, `docs/SYSTEM-WORKFLOW.md`
- mustNotBreak: existing `pytest -q` (≥104 tests) + `bash scripts/smoke-test.sh` + all existing `canon` subcommand signatures

**REASONING — implementation approach:**

1. **New module `src/canon_systems/memory_health.py`** — covers AC1, AC2, AC4-AC10:
   - Public: `run(argv: list[str] | None = None) -> int`
   - Internal: `BACKENDS` dict (canonical, mempalace, state, graph), `_resolve_env`, `_resolve_required`, `_resolve_timeout_ms`, `_probe(url, timeout_ms)` (test seam — single-flight urllib GET; never raises), `_classify` (status mapping per AC7), `_build_report`
   - Stdlib-only; no AWS; reads repo root via `CANON_SYSTEMS_REPO_ROOT` env or `shared.repo_root()`
   - Reads `.canon/memory-layer.local.env` via `shared.load_env_file`; no `shared.load_repo_context` call (keeps probes credential-free)

2. **CLI registration in `src/canon_systems/cli.py`** — covers AC1, AC9: mirror `flow-audit` subparser pattern; add `from .memory_health import run as run_memory_health`; add dispatch branch.

3. **Tests `tests/test_memory_health.py`** — covers AC11, AC15, AC16, AC17: monkeypatch `memory_health._probe` (preferred) + env vars via `tmp_path` / `monkeypatch`. Full matrix: healthy, required-degraded, all-unreachable, not_configured, env-override-expands/shrinks, unknown_backend, timeout_budget, json_shape, output_flag, empty-required-exits-0, CLI help, unknown-flag-exit-2, stdlib-only-imports, doc-presence (README/CHANGELOG/SYSTEM-WORKFLOW).

4. **Living-spec edits** — AC12/13/14: surgical inserts; no reformat.

**ac_traceability:** every AC mapped to impl target + verification test. See cursor-pilot subagent output (full mapping preserved in release-status).

**OUTPUT FORMAT:** Only files listed in `in_scope_paths`. No refactors. No new deps. No docstrings narrating obvious behavior.

**STOP CONDITIONS:** Emit `HANDOFF_TO_QA` block with all 17 ACs + evidence file/line ranges + evidence test names + decisions + next_actions. Parent runs `pytest -q` and `bash scripts/smoke-test.sh` before qa-gate.

**FORBIDDEN:**
- No edits to `backend/**`, `infra/**`, `canon-systems-v2/**`, `.cursor/rules/**`, `.cursor/plans/**`, frozen Wave-0 docs.
- No edits to `pyproject.toml`, `pytest.ini`, `requirements-dev.txt`, `.github/workflows/**`, `src/canon_systems/templates/**`.
- No live HTTP in code or tests.
- No git ops.
- No new deps.
