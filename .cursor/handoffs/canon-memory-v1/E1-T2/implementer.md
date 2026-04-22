# E1-T2 Implementer Handoff

**Task:** Fix memory-adapter endpoint resolution + queue fallback
**Status:** IMPLEMENTATION_COMPLETE

## Files changed (7)

**New (untracked):**
- `src/canon_systems/memory_queue.py` — stdlib-only classifier + JSONL queue (lines 12-68: `queue_path`, `classify_mempalace_response`, `enqueue_mempalace_retry`, `is_degraded`)
- `tests/test_mempalace_fallback.py` — 4 test cases

**Modified:**
- `src/canon_systems/context_preload.py` — `## MemPalace Status` md section (lines 47-60, 154-161); JSON sidecar `mempalace_status` key (lines 165-184); enqueue on degraded (lines 131-144); return 0 unchanged (line 194)
- `src/canon_systems/ask_hybrid.py` — `_mempalace_hits` returns `(hits, status_block)` (lines 135-202); `run()` enqueue (lines 218-230), JSON `mempalace_status` (lines 237-245), stderr on degraded (lines 251-252), exit 0 (lines 249, 265)
- `README.md` — new `### Memory degraded-mode fallback` subsection after `## Commands` table (lines 218-220)
- `CHANGELOG.md` — `- E1-T2:` bullet inserted at top of `[Unreleased]` Added (line 12)
- `docs/SYSTEM-WORKFLOW.md` — §1 append-only sub-bullet (line 15)

## Verification

| Check | Outcome |
|---|---|
| `pytest -q tests/test_mempalace_fallback.py` | 4 passed |
| `pytest -q` (full suite) | 134 passed (130 from E1-T1 + 4 new) |
| `from canon_systems.memory_queue import ...` smoke | ok |
| Forbidden surface | clean |

## AC evidence

| AC | Status | Evidence |
|---|---|---|
| AC1 | PASS | `context_preload._write_markdown:47-60`, `run:154-161` |
| AC2 | PASS | `context_preload.run:165-184` sidecar key |
| AC3 | PASS | `context_preload.run:131-144` + `memory_queue.enqueue_mempalace_retry:57-63`; call_site="context_preload" |
| AC4 | PASS | `ask_hybrid._mempalace_hits:135-202` + `run:218-230,237-245,251-252` |
| AC5 | PASS | `memory_queue.py:12-68` (4 symbols, stdlib + `shared.now_stamp/repo_root`) |
| AC6 | PASS | `tests/test_mempalace_fallback.py` — 4 cases |
| AC7 | PASS | Only context_preload + ask_hybrid import memory_queue |
| AC8 | PASS | No pyproject/requirements-dev changes |
| AC9 | PASS | memory_health.py unchanged |
| AC10 | PASS | No forbidden-path touches |
| AC11 | PASS | README:218-220, CHANGELOG:12, SYSTEM-WORKFLOW:15 — ADDITIVE only |
| AC12 | PASS | 134 full-suite; import smoke ok |
| AC13 | PASS | No drain CLI; no git ops |
| AC14 | PASS | preflight returns 0 (`run:194`); ask returns 0 (`run:249, 265`) |

## Decisions

- Classifier status enum fixed at `{ok, degraded, unreachable, not_configured}`; `not_configured` never enqueues (OQ-03)
- Mocked `request_json` at caller module level (OQ-06), not urlopen, for deterministic tests
- Queue format is append-only JSONL with no dedup in v1 (OQ-05); drain deferred
- `_mempalace_hits` widened to `(hits, status_block)` tuple to plumb status into `ask_hybrid.run` without module-level global

## Forbidden surface: clean
