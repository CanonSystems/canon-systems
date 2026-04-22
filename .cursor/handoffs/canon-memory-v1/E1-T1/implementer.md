# E1-T1 Implementer Handoff

**Task:** Add `canon memory-health` CLI
**Status:** COMPLETE

## Files changed (6)

**New (untracked until parent stages):**
- `src/canon_systems/memory_health.py` — stdlib-only health-check module
- `tests/test_memory_health.py` — 23 pytest cases covering full AC11 matrix

**Modified:**
- `src/canon_systems/cli.py` — `memory-health` subparser + dispatch
- `README.md` — command-table row
- `CHANGELOG.md` — `[Unreleased]` → `Added` bullet
- `docs/SYSTEM-WORKFLOW.md` — §6 validation-commands bullet

## Verification

| Check | Outcome |
|---|---|
| `pytest -q tests/test_memory_health.py` | 23 passed |
| `pytest -q` (full suite) | 130 passed |
| `python -c '... run(["--required",""])...'` | exit 0 (AC16) |
| `canon memory-health --help` | usage printed, exit 0 (AC1) |
| `bash scripts/smoke-test.sh` | NOT RUN here (qa-gate runs) |
| Forbidden-surface touches | none |

## AC evidence

| AC | Status | Evidence |
|---|---|---|
| AC1 | PASS | `cli.py:18,267-289,468-480`; `memory_health.run` |
| AC2 | PASS | `memory_health.py:43-44,331-400` (stdout JSON; verbose→stderr) |
| AC3 | PASS | `memory_health.py:291-303,350-409` (`_overall_status` + exit code) |
| AC4 | PASS | `memory_health.py:65-104,130-160,350-355` (timeout + perf_counter latency) |
| AC5 | PASS | `memory_health.py:162-201,384-409` (CLI>env>default; empty; unknown_backend) |
| AC6 | PASS | `memory_health.py:19-33,112-128` (`BACKENDS` + layered env resolution) |
| AC7 | PASS | `memory_health.py:204-275` (`_classify`; required never not_deployed) |
| AC8 | PASS | `memory_health.py:258-275` (version/last_error/endpoint_ref) |
| AC9 | PASS | `memory_health.py:306-337`, `cli.py:267-289,468-480` (flag surface; unknown→exit 2) |
| AC10 | PASS | `memory_health.py:5-15` imports + `test_stdlib_only_imports` |
| AC11 | PASS | 23 test cases in `tests/test_memory_health.py` |
| AC12 | PASS | `README.md` row present; `test_readme_row_present` |
| AC13 | PASS | `CHANGELOG.md` Added bullet; `test_changelog_unreleased_added_bullet` |
| AC14 | PASS | `docs/SYSTEM-WORKFLOW.md` §6 bullet; `test_system_workflow_section_6_bullet` |
| AC15 | pytest PASS; smoke-test deferred to qa-gate | |
| AC16 | PASS | verified via `python -c` one-liner |
| AC17 | PASS | no forbidden-surface touches; tests mock `_probe`; no new deps |

## Decisions

- **Optional vs required non-2xx:** optional → `not_deployed`; required → `unreachable`. Transport errors / http==0 → `unreachable` for both.
- **`required_set` JSON:** sorted(must) + sorted(unknown tokens). Unknowns force exit 1, `overall_status=unhealthy`.
- **Test seam:** monkeypatch `canon_systems.memory_health._probe` rather than `urllib.request.urlopen` — cleaner, no urllib globals perturbed.

## Forbidden surface

No touches. Verified.

## Next actions

- Parent stages untracked files (`memory_health.py`, `test_memory_health.py`) after qa-gate PASS.
- qa-gate runs `bash scripts/smoke-test.sh` for AC15.
