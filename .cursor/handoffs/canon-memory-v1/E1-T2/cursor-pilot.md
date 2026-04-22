# E1-T2 Cursor-Pilot Prompt

Generated from scoper packet. Single-stream execution (E1-T1 precedent).

**ROLE:** `implementer` (composer-2-fast). No re-scoping, no git ops.

**TASK:** Fix memory-adapter endpoint resolution + queue fallback. Add `mempalace_status` block to preflight outputs, stdlib JSONL retry queue at `.canon/memory/mempalace-retry-queue.jsonl`, wire preflight + ask call sites to classify and enqueue on non-ok.

**ACCEPTANCE CRITERIA:** All 14 ACs from scoper packet. See scoper.md.

**CONTEXT:**
- `handoff_id: canon-memory-v1`, `task_id: E1-T2`, `workstream_id: wave-1b`, `epic_id: E1`
- Branch `wave/1/canon-memory-v1`; E1-T1 committed @ 0d71319
- E1-T3 runs in parallel — E1-T2's living-spec edits MUST be additive (TOP of CHANGELOG [Unreleased]→Added list; NEW README subsection after Commands table; NEW bullet at END of SYSTEM-WORKFLOW §1)
- DO NOT touch §5 or §6 of SYSTEM-WORKFLOW.md (E1-T3 owns)

**REPOSITORY:**
- Python stdlib-only; pytest
- relevantFiles: `src/canon_systems/{memory_queue.py[new], context_preload.py, ask_hybrid.py, dor_log.py (read-only precedent), shared.py (request_json, now_stamp, repo_root), memory_health.py (FROZEN — import only)}`, `tests/test_mempalace_fallback.py[new]`, README.md, CHANGELOG.md, docs/SYSTEM-WORKFLOW.md
- mustNotBreak: memory_health.py (E1-T1 frozen), capture_session.py (not a mempalace call site), existing context-latest.json keys (backward-compat), ask/preflight exit code 0 on degraded, §5/§6 of SYSTEM-WORKFLOW.md (E1-T3 owns)

**REASONING:**

1. **`memory_queue.py`** (AC5, AC8): stdlib-only. Expose:
   - `queue_path() -> Path` (`<repo_root>/.canon/memory/mempalace-retry-queue.jsonl`; mkdir parents OK=True) — mirror `dor_log._queue_path`
   - `classify_mempalace_response(*, status: int, payload, endpoint_ref: str, latency_ms: int, configured: bool) -> dict` — returns `{status, latency_ms, last_error, endpoint_ref}`. Rules: `configured=False`→`not_configured`; `status==0`→`unreachable`; `2xx`+dict payload→`ok`; everything else (404, 5xx, non-JSON, wrong shape)→`degraded`. `last_error` concise ("http 404", "url error: ...", "" on ok).
   - `enqueue_mempalace_retry(record: dict) -> None` — append-only JSONL, mirror `dor_log._enqueue_failed_event`
   - `is_degraded(block) -> bool` — True iff `block["status"] in {degraded, unreachable}`
   Imports: `json`, `pathlib.Path`, `typing`, `.shared.now_stamp`, `.shared.repo_root`.

2. **`context_preload.py`** (AC1, AC2, AC3, AC14): wrap existing `request_json(memory_adapter_url + "/memory/search", ...)` with `time.perf_counter` for `latency_ms`. Compute `configured = bool(repo_ctx.memory_adapter_url)`. Call classifier → `mempalace_status` block. Render as `## MemPalace Status` section in markdown (key: value lines). Add `mempalace_status` top-level key to JSON sidecar. If `is_degraded(block)`: build AC3 record with `call_site="context_preload"` (or `"preflight"`), `request_body=memory_body`, `actor_id/company_id/repository_id` from identity context, `queued_at=now_stamp()`; call `enqueue_mempalace_retry`. Return 0 unconditionally.

3. **`ask_hybrid.py::_mempalace_hits`** (AC4, AC14): same wrap around `request_json`. Widen return type to `(hits, status_block)`. In `run()`:
   - Include `mempalace_status: status_block` in JSON payload (top-level)
   - When not `--json` and `is_degraded`, print `f"mempalace: {status_block['status']}"` to stderr before summary
   - Enqueue with `call_site="ask_hybrid"` on degraded/unreachable
   - Exit 0

4. **Tests `tests/test_mempalace_fallback.py`** (AC6, AC12):
   - Monkeypatch `canon_systems.context_preload.request_json` and `canon_systems.ask_hybrid.request_json` (module-level seam per OQ-06)
   - Monkeypatch `shared.repo_root` and/or `memory_queue.repo_root` → `tmp_path`
   - Stub `load_identity_context` / `load_repo_context` (deterministic actor/company/repo + URLs + context_dir=tmp_path/.canon/memory)
   - Case (a) preflight unreachable: `request_json` returns `(0, ...)` → assert md has `## MemPalace Status` + `status: unreachable`; sidecar JSON has `mempalace_status.status=="unreachable"`; queue file has 1 line with 9 AC3 keys
   - Case (b) preflight ok: `request_json` returns `(200, {"results":[]})` → sidecar `status=="ok"`; NO queue
   - Case (c) ask unreachable: invoke `ask_hybrid.run([...,"--json"])`; assert JSON `mempalace_status.status=="unreachable"` + queue entry with `call_site="ask_hybrid"`; re-run without --json and check stderr has `mempalace: unreachable`
   - Case (d) classifier not_configured: call `classify_mempalace_response(configured=False, ...)`; assert status=="not_configured" AND queue file absent

5. **Living-spec** (AC11, strictly additive):
   - README: NEW `### Memory degraded-mode fallback` subsection AFTER `## Commands` table (don't touch memory-health row)
   - CHANGELOG: NEW bullet at TOP of `[Unreleased]`→`Added` (above E1-T1): `- E1-T2: mempalace status classifier + retry queue for preflight and ask`
   - SYSTEM-WORKFLOW §1: APPEND-ONLY new sub-bullet at END of §1's bullet list. DO NOT touch §5 or §6.

**OUTPUT FORMAT:** Only scope changes. No refactors. No new deps. No forbidden-surface edits.

**STOP CONDITIONS:** Emit `HANDOFF_TO_QA` block with per-AC evidence (files + line ranges + test names). Parent runs `pytest -q` + `bash scripts/smoke-test.sh` before qa-gate.

**FORBIDDEN:**
- No edits to `memory_health.py`, `capture_session.py`, `templates/**`
- No edits to §5 or §6 of SYSTEM-WORKFLOW.md
- No edits to `backend/**`, `infra/**`, `canon-systems-v2/**`, `.cursor/rules/**`, `.cursor/plans/**`, frozen Wave-0 docs, pyproject.toml, pytest.ini, requirements-dev.txt, `.github/workflows/**`
- No live HTTP; no git ops; no new deps; no drain CLI
