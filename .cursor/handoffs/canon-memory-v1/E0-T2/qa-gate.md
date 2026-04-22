# QA-gate packet — E0-T2

- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E0-T2
- workstream_id: wave-0b
- branch: wave/0/canon-memory-v1
- agent_name: qa-gate
- phase: qa-gate
- phase_status: pass

## QA_VERDICT

**PASS** — All eight acceptance criteria satisfied by 19/19 green tests
(`tests/test_backend_layout.py`), full-suite regression 89/89 green, scope
compliance clean, living-spec invariant honored, hard-lock rule §2 evidenced
by packet-vs-code timestamps, and both workspace-build proposals shipped.
No iterations required (no fixes applied; implementer's tree was correct
on first inspection).

## ac_coverage

| # | Criterion (verbatim from scoper.story.acceptanceCriteria) | Covering tests | Pass/Fail | Iteration |
|---|---|---|---|---|
| AC1 | `backend/{knowledge-api,knowledge-worker,memory-adapter,state-api,axon-service,synthesis,synthesis-web}` directories exist with README placeholders and matching entry-point scaffolding. | `tests/test_backend_layout.py::test_seven_service_dirs_exist` (7 params), `::test_python_services_have_entrypoints` (6 params), `::test_synthesis_web_is_readme_only` | PASS (14/14) | 0 |
| AC2 | `backend/shared/` exposes auth, ids, events modules consumable by every service package. | `::test_shared_modules_importable`, `::test_deterministic_id_is_stable_and_supports_prefix`, `::test_canonical_event_roundtrip`, `::test_verify_caller_docstring_and_notimplemented` | PASS (4/4) | 0 |
| AC3 | Root pyproject/poetry/turbo (language-appropriate) builds the workspace cleanly. | `::test_workspace_declaration_or_script_present` + manual done_signal (root pyproject has `[tool.uv.workspace] members = ["backend/*"]` AND `scripts/backend/install-workspace.sh` ships `0755`, `bash -n` syntax-clean; implementer recorded `bash scripts/backend/install-workspace.sh` exited 0 because `uv` was unavailable locally). | PASS | 0 |
| AC4 | No canon-systems-v2 service code is moved into `backend/` under this task; all service directories are stubs only (git history preservation is E0-T3). | Static inspection: `backend/**/main.py` all contain only `FastAPI(title=..., version='0.0.0-scaffold')` + `/healthz` stub (~10 lines each); no imports of canon-systems-v2 packages; `git status --porcelain` shows no moves/renames; `backend/synthesis-web/` has no `.py` files (enforced by `::test_synthesis_web_is_readme_only`). | PASS | 0 |
| AC5 | `backend/shared/ids.py` exposes a callable `deterministic_id(*parts: str, prefix: str | None = None) -> str` implemented via `hashlib.sha256` (per backlog §A). | `::test_deterministic_id_is_stable_and_supports_prefix` (stability + 64-char hex + `evt_` prefix join) — reviewed `backend/shared/canon_backend_shared/ids.py` L13: `hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()`. | PASS | 0 |
| AC6 | `backend/shared/events.py` exposes a `CanonicalEvent` type + `to_dict`/`from_dict` round-trip matching backlog §C field names. | `::test_canonical_event_roundtrip` (round-trip covers all 16 §C fields: schema_version, event_id, parent_event_id, event_type, company_id, repository_id, plan_id, task_id, handoff_id, agent_name, agent_run_id, actor_id, model, timestamp, state_version, payload). | PASS | 0 |
| AC7 | `backend/shared/auth.py` exposes a stub `verify_caller(headers: Mapping[str, str]) -> AuthContext` signature raising `NotImplementedError` with a docstring pointing to E2-T2/E1-T2; no real auth logic in this task. | `::test_verify_caller_docstring_and_notimplemented` (asserts docstring contains both `E2-T2` and `E1-T2`, and `verify_caller({})` raises `NotImplementedError('real auth…')`). | PASS | 0 |
| AC8 | Root `README.md`, `CHANGELOG.md`, and `docs/SYSTEM-WORKFLOW.md` are updated to reference the new `backend/` layout (per backlog §G living-spec invariant). | Manual diff inspection (`git diff README.md CHANGELOG.md docs/SYSTEM-WORKFLOW.md`): new "Backend monorepo" section in README; new `Added: E0-T2: backend/ skeleton + shared lib` bullet in CHANGELOG Unreleased; new §10 "Backend monorepo layout" in SYSTEM-WORKFLOW. All three edits reference `backend/README.md` and both install paths. | PASS | 0 |

Cumulative: 19 pytest cases covering 8 ACs, 19 PASS / 0 FAIL / 0 SKIP.

## scope_compliance

- **permitted_paths_added verified** (from `git status --porcelain`, all untracked):
  - `backend/**` — 19 files across 8 directories (shared + 6 FastAPI services + synthesis-web + top-level README). Matches `in_scope_paths_to_create` item-for-item (see scoper.md L94–L128).
  - `scripts/backend/install-workspace.sh` — 10 lines, `0755`, bash syntax clean.
  - `tests/test_backend_layout.py` — 145 lines, stdlib-only imports.
- **permitted_paths_modified verified** (from `git status --porcelain`, all `M `):
  - `pyproject.toml` — one additive block `[tool.uv.workspace] members = ["backend/*"]` appended; canon-systems `[project]`/`[tool.setuptools]` sections byte-identical.
  - `README.md` — one "Backend monorepo" section inserted between existing sections.
  - `CHANGELOG.md` — one bullet added under Unreleased/Added.
  - `docs/SYSTEM-WORKFLOW.md` — new §10 appended.
- **prohibited_paths_touched: NONE**. Confirmed via `git diff --stat` showing only the 4 modified files above. `src/canon_systems/**`, `infra/**`, `.cursor/rules/memory-platform-build-discipline.mdc`, `.cursor/plans/canon_memory_platform_build_d21073e1.plan.md`, `docs/MEMORY-PLATFORM-BACKLOG.md`, `docs/MEMORY-PLATFORM-PLAN.md`, `docs/WAVE-0-AUDIT.md`, `docs/DEPRECATIONS.md`, `docs/OBSIDIAN-MIND-CATALOGUE.md`, and `pytest.ini` all untouched.
- **Additive-only**: no file deletions; no renames; no git moves from sibling repos.

## living_spec_invariant (backlog §G)

- **README.md** — new top-level "Backend monorepo" section added (8 lines) pointing to `backend/README.md` and both install paths (`uv sync --all-packages` / `bash scripts/backend/install-workspace.sh`). Cross-links to SYSTEM-WORKFLOW §10. Coherent.
- **CHANGELOG.md** — `Added: E0-T2: backend/ skeleton + shared lib` under Unreleased. Matches E0-T1's entry shape. Coherent.
- **docs/SYSTEM-WORKFLOW.md** — new §10 "Backend monorepo layout" (7 lines) describing Python setuptools per-service packages + stdlib-only `canon_backend_shared`, `synthesis-web` reserved for E5-T4, and the install paths. Consistent with §5.1 commit/PR discipline added in E0-T1.
- Verdict: **all three living-spec files updated, mutually consistent, and AC8-compliant.**

## hermeticity

- `pytest tests/test_backend_layout.py -v` ran cleanly under existing `pytest.ini` (`pythonpath=src`) with **no new plugins loaded** (plugins observed: `asyncio-1.2.0, anyio-4.11.0, cov-7.0.0` — identical to pre-E0-T2 baseline).
- Test file imports only stdlib (`ast`, `sys`, `tomllib`, `pathlib`) + `pytest`. No `pip install` at import/collection time.
- No `conftest.py` introduced anywhere under `tests/` or `backend/` (confirmed via `find tests backend -name conftest.py` → empty).
- Shared-lib importability is achieved by prepending `backend/shared` to `sys.path` inside the test (stdlib-only path manipulation); no external installer required to run tests.
- Test runtime: 0.02s for the 19 AC tests; 0.55s for the full suite. Deterministic (no sleeps, no network, no filesystem writes).
- Verdict: **hermetic. Honors scoper packet constraint "MUST run under current pytest config without extra plugins" (scoper L169).**

## contract checks

### entry_point_scaffolding_contract

For each of the six FastAPI services (`knowledge-api`, `knowledge-worker`, `memory-adapter`, `state-api`, `axon-service`, `synthesis`), `backend/<slug>/<python_pkg>/main.py` was inspected:

- Module-level `app = FastAPI(title="<slug>", version="0.0.0-scaffold")` ✓ (asserted by `::test_python_services_have_entrypoints`).
- `@app.get("/healthz")` returning `{"status": "scaffold", "service": "<slug>"}` ✓ (verified by source read; each service's `main.py` is ~10 lines and follows the identical shape).
- Python package naming per scoper L178–L184: `knowledge-api→app`, `knowledge-worker→knowledge_worker`, `memory-adapter→memory_adapter`, `state-api→state_api`, `axon-service→axon_service`, `synthesis→synthesis` ✓.
- `backend/synthesis-web/` contains only `README.md` + `.gitkeep` (no `pyproject.toml`, no `*.py`) ✓ (asserted by `::test_synthesis_web_is_readme_only`; README states "Entry-point and language are chosen in E5-T4").

### shared_lib_contract

- `package_import_path: canon_backend_shared` ✓ (`backend/shared/canon_backend_shared/{__init__,auth,ids,events}.py`; `pyproject.toml` name `canon-backend-shared`; include pattern `canon_backend_shared*`).
- `auth.verify_caller(headers)` raises `NotImplementedError('real auth lands in E2-T2 / E1-T2')`, docstring references both `E2-T2` and `E1-T2`; `AuthContext` is empty `@dataclass(slots=True)` ✓.
- `ids.deterministic_id(*parts, prefix=None)` uses `hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()` with optional `<prefix>_` join ✓.
- `events.CanonicalEvent` is a `@dataclass` with all 16 backlog §C fields, `to_dict()` via `dataclasses.asdict` + payload copy, `from_dict()` classmethod with type coercion, `__post_init__` enforces `schema_version == 1` ✓.
- `backend/shared/pyproject.toml` declares `dependencies = []` ✓ (zero runtime deps beyond stdlib as required by scoper L166).

### workspace_build_contract

- Primary: root `pyproject.toml` contains `[tool.uv.workspace]` with `members = ["backend/*"]` ✓ (additive-only; canon-systems CLI project section untouched; verified by diff).
- Fallback: `scripts/backend/install-workspace.sh` exists, `0755`, starts with `#!/usr/bin/env bash` + `set -euo pipefail`, installs `backend/shared` first, then iterates `knowledge-api knowledge-worker memory-adapter state-api axon-service synthesis` ✓. `bash -n` syntax-check passes.
- Both shipped as required by scoper L159 ("SHIP BOTH"). Done-signal is satisfiable by either path.

## iterations log

- **Iteration 0** (no fixes applied): Initial inspection of the tree showed all 19 tests green on first run. No test gaps found relative to scoper `ac_traceability`. No implementation defects found. Gate passes in a single pass.

## commands run

```bash
# Scope + branch verification
$ git status --porcelain
 M CHANGELOG.md
 M README.md
 M docs/SYSTEM-WORKFLOW.md
 M pyproject.toml
?? .cursor/handoffs/canon-memory-v1/E0-T2/
?? backend/
?? scripts/backend/
?? tests/test_backend_layout.py

$ git branch --show-current
wave/0/canon-memory-v1

# AC-coverage test run (scoper-mandated suite)
$ pytest tests/test_backend_layout.py -v
============================= test session starts ==============================
platform darwin -- Python 3.13.7, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/edwardwalker/localwork/canon-systems
configfile: pytest.ini
plugins: asyncio-1.2.0, anyio-4.11.0, cov-7.0.0
collected 19 items

tests/test_backend_layout.py .................................. (19 items)
============================== 19 passed in 0.02s ==============================

# Regression sweep (full canon-systems suite)
$ pytest -q
89 passed in 0.55s

# Hermeticity/conftest check
$ find tests backend -name conftest.py
(no output — none present)

# Install-script syntax + perms
$ bash -n scripts/backend/install-workspace.sh && ls -la scripts/backend/install-workspace.sh
-rwxr-xr-x  1 edwardwalker  staff  283 Apr 22 12:32 scripts/backend/install-workspace.sh

# Hard-lock §2 timestamp evidence (packets precede non-markdown writes)
$ stat -f '%m %Sm %N' .cursor/handoffs/canon-memory-v1/E0-T2/*.md backend/shared/pyproject.toml tests/test_backend_layout.py
1776875144 Apr 22 12:25:44 2026 scoper.md
1776875500 Apr 22 12:31:40 2026 cursor-pilot.md
1776875528 Apr 22 12:32:08 2026 backend/shared/pyproject.toml       # 28s after pilot
1776875570 Apr 22 12:32:50 2026 tests/test_backend_layout.py        # 70s after pilot

# Canon validators (optional, requested by parent)
$ command -v canon
(not installed in PATH — validators skipped; not blocking per parent's instruction that these are "if available")
```

## hard_lock_rule_compliance (§2 packet-gated writes)

- **§2 evidenced**: `scoper.md` (mtime 12:25:44) and `cursor-pilot.md` (mtime 12:31:40) both present on disk before the earliest non-markdown write (`backend/shared/pyproject.toml` at 12:32:08, which is 28 seconds later). First non-markdown write post-dates both packets. Compliance verified.
- **§9 (per-task commit)**: not invoked here — commit ownership belongs to the parent orchestrator / release-orchestrator per the cursor-pilot STOP_CONDITIONS. QA-gate does not commit.
- Hard-lock rule file itself unchanged (not in modified set).

## open_questions_carried_forward

- **OQ-E0T3-01 (non-blocking, follow-up for E0-T3+)**: `.gitignore` currently covers `src/*.egg-info/` but NOT `backend/**/*.egg-info/`. No such egg-info is currently in the committed tree, but running `bash scripts/backend/install-workspace.sh` (or `pip install -e backend/<svc>`) in CI will create them and leave them untracked. Recommend adding `backend/**/*.egg-info/` (and optionally `backend/**/__pycache__/` — already covered by generic `__pycache__/` rule) to `.gitignore` as part of E0-T3 or a dedicated `chore/gitignore-backend` touch. This does NOT block E0-T2 merge because (a) no egg-info exists in the tree now, (b) it is not mentioned in AC1–AC8, and (c) adding it would exceed scoper `permitted_paths_modified` for E0-T2.
- **OQ-E0T3-02 (non-blocking, informational)**: `canon qa-validate` and `canon flow-audit` were requested by parent but the `canon` CLI is not on PATH in this session. The packet-validation checks they would perform are substituted here by manual structural inspection (verdict, ac_coverage table, commands block, `handoff_id`/`task_id` headers — all present). If the parent requires a CLI-gated validation record, re-run `canon qa-validate --file .cursor/handoffs/canon-memory-v1/E0-T2/qa-gate.md --require-pass` from an environment where `canon` is installed; structural shape of this packet matches E0-T1's qa-gate.md which passed that validator.
- **OQ-E0T3-03 (non-blocking, informational)**: The implementer's local environment did not have `uv` available, so the primary workspace-build proposal (`uv sync --all-packages`) was not executed end-to-end; only the fallback (`bash scripts/backend/install-workspace.sh`, exit 0) was. AC3 is still satisfied because the scoper's `test_interpretation` (scoper L214) explicitly says "either (a) or (b)" suffices. CI should run `uv sync --all-packages` when a uv-enabled runner is available to validate the primary path.

## recommendation for release-orchestrator

**READY_TO_MERGE.**

E0-T2 satisfies every acceptance criterion (AC1–AC8) with a green 19/19
AC-targeted test run and a green 89/89 full-suite regression sweep. Scope
compliance is clean (zero prohibited paths touched; additive-only changes
within the scoper's `permitted_paths_added` + `permitted_paths_modified`
allowlist). Living-spec invariant is honored. Hard-lock rule §2 is
evidenced by file-mtime ordering. Both the `uv` primary and `bash`
fallback workspace-build proposals ship. Shared library is
stdlib-only and contract-compliant. Entry-point scaffolding matches the
six-service / one-reserved-slot shape exactly.

The release-orchestrator may proceed to `git add` the E0-T2 permitted-path
set and `git commit` per hard-lock §9, then fast-forward `wave/0/canon-memory-v1`.
The three open questions above are documented follow-ups for E0-T3 or later;
none gate this merge.

END_QA_GATE_PACKET
