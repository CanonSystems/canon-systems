# Cursor-pilot packet — E0-T3

- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E0-T3
- workstream_id: wave-0c
- branch: wave/0/canon-memory-v1
- phase: cursor-pilot
- phase_status: pass

## CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
</ROLE>

<TASK>
E0-T3 — Consolidate the three in-use backend services (`knowledge-api`,
`knowledge-worker`, `memory-adapter`) from the read-only sibling repo
`canon-systems-v2` into this repo's `backend/` monorepo, replacing the
E0-T2 scaffold placeholders with real v2 source. History preservation is
an explicit waiver (recorded in `docs/E0-T3-MIGRATION-NOTES.md`); the
per-service pyprojects keep `canon-backend-shared` wired; a new
`scripts/backend/build-services.sh` (pip install -e + import-smoke across
six leaf services) is the CI done-signal surrogate; layout tests
are extended; living-spec (README/CHANGELOG/SYSTEM-WORKFLOW §10) is
updated.
</TASK>

<ACCEPTANCE_CRITERIA>
- Each service builds and runs in place from `backend/<service>/`.
- Existing `KNOWLEDGE_API_URL` / `KNOWLEDGE_WORKER_URL` / `MEMORY_ADAPTER_URL` remain serviceable end-to-end (interpreted as: zero redeploy, no infra/v2 writes, local boot parity via import-smoke).
- Git history for moved code is preserved or explicitly waived in the task notes (waived here, recorded in `docs/E0-T3-MIGRATION-NOTES.md` with v2 SHA `ebecb91`).
- `backend/knowledge-api/` contains the real v2 `app/` package plus `alembic/` + `alembic.ini`; `__pycache__` / `*.egg-info` / `tests/` excluded; `import app.main; assert hasattr(app.main, 'app')` succeeds after `pip install -e backend/knowledge-api`.
- `backend/knowledge-worker/` adopts src-layout with `backend/knowledge-worker/src/knowledge_worker/{__init__.py,main.py,service.py,config.py,models.py,api/{__init__.py,router.py},projections/{__init__.py,memory_capture_to_markdown.py,memory_to_markdown.py}}`; import-smoke succeeds after `pip install -e backend/knowledge-worker`.
- `backend/memory-adapter/` adopts src-layout with `backend/memory-adapter/src/memory_adapter/{__init__.py,main.py,service.py,config.py,models.py,api/{__init__.py,router.py},adapters/{__init__.py,mempalace.py}}`; import-smoke succeeds after `pip install -e backend/memory-adapter`.
- Each of the three moved services' `pyproject.toml` declares `canon-backend-shared` in `[project].dependencies` alongside the v2 runtime deps (version/range values MUST match v2; no version pin for `canon-backend-shared`).
- E0-T2 scaffold placeholder files for `knowledge-worker` and `memory-adapter` are REMOVED in favor of the real v2 content (flat `backend/knowledge-worker/knowledge_worker/` and `backend/memory-adapter/memory_adapter/` dirs gone).
- `scripts/backend/build-services.sh` exists, is executable, runs `pip install -e backend/<svc>` for `shared` + the six leaf services (`knowledge-api`, `knowledge-worker`, `memory-adapter`, `state-api`, `axon-service`, `synthesis`) and executes an import-smoke for each of the six leaf services; exits non-zero on first failure. `backend/shared` gets only the install step (no `main.app` smoke).
- `docs/E0-T3-MIGRATION-NOTES.md` records the waiver with v2 SHA `ebecb91`, per-file source-path → target-path mapping, and the exclusions list.
- `tests/test_backend_layout.py` updated so `PYTHON_SERVICES` is a `dict[slug, main_path_relative_to_service_dir]`; every existing E0-T2 assertion continues to pass; new assertions added: `test_canon_backend_shared_listed_in_moved_service_pyprojects`, `test_knowledge_api_has_alembic`, `test_migration_notes_exists` (must reference `ebecb91`), `test_no_orphan_scaffold_flat_dirs`, `test_build_services_script_present_and_executable`.
- Root `pytest` collection stays green; v2 `services/<svc>/tests/` directories are NOT copied.
- `README.md`, `CHANGELOG.md`, `docs/SYSTEM-WORKFLOW.md` §10 updated per backlog §G.
- No file under `canon-systems-v2` modified; no `infra/` created; no Dockerfile modified; no `src/canon_systems/**` touched.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- company_id: IMC
- repository_id: innermost
- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E0-T3
- workstream_id: wave-0c
- branch: `wave/0/canon-memory-v1` (tip `da02e41`) — DO NOT create/switch branches.
- prior_work_references:
  - `.cursor/handoffs/canon-memory-v1/E0-T3/scoper.md` (DoR PASS)
  - `.cursor/handoffs/canon-memory-v1/E0-T2/release-status.md` (READY_TO_MERGE; tip `da02e41`)
  - `.cursor/rules/memory-platform-build-discipline.mdc` §9 (parent owns per-task commit; implementer MUST NOT commit/push)
  - `docs/MEMORY-PLATFORM-BACKLOG.md` §G (living-spec invariant)
  - Upstream source (READ-ONLY): `/Users/edwardwalker/localwork/canon-systems-v2` @ commit `ebecb91`
- OQs resolved: OQ-E0-T3-01 (history waiver), -02 (adapter topology deferred), -03 (CI via script), -04 (v2 tests deferred), -05 (install-workspace.sh untouched), -06 (carry alembic/versions minus __pycache__).
</CONTEXT>

<REPOSITORY>
- primaryLanguages: Python 3.10+, Markdown, TOML, Bash, INI
- testFramework: pytest (root `tests/`; v2 service tests NOT copied)
- build_tool: setuptools per service; workspace via root `[tool.uv.workspace]` (E0-T2) + `scripts/backend/install-workspace.sh` + new `scripts/backend/build-services.sh`

- Upstream READ-ONLY references:
  - `/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api/{README.md,pyproject.toml,alembic.ini,alembic/**,app/**}`
  - `/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-worker/{README.md,pyproject.toml,src/knowledge_worker/**}`
  - `/Users/edwardwalker/localwork/canon-systems-v2/services/memory-adapter/{README.md,pyproject.toml,src/memory_adapter/**}`

- Target (write here):
  - `backend/knowledge-api/{README.md,pyproject.toml,alembic.ini,alembic/**,app/**}`
  - `backend/knowledge-worker/{README.md,pyproject.toml,src/knowledge_worker/**}`
  - `backend/memory-adapter/{README.md,pyproject.toml,src/memory_adapter/**}`
  - `docs/E0-T3-MIGRATION-NOTES.md`
  - `scripts/backend/build-services.sh`
  - `tests/test_backend_layout.py`
  - `README.md`, `CHANGELOG.md`, `docs/SYSTEM-WORKFLOW.md`

- Orphan scaffold dirs to DELETE:
  - `backend/knowledge-worker/knowledge_worker/{__init__.py,main.py}`
  - `backend/memory-adapter/memory_adapter/{__init__.py,main.py}`

- mustNotBreak:
  - Root `pytest` green
  - All E0-T2 assertions in `tests/test_backend_layout.py` continue to pass
  - E0-T2 quartet slots untouched: `backend/shared/`, `backend/state-api/`, `backend/axon-service/`, `backend/synthesis/`, `backend/synthesis-web/`
  - Root `[tool.uv.workspace].members=['backend/*']` unchanged
  - `scripts/backend/install-workspace.sh` unchanged (setuptools reads pyproject.package-dir)
  - No writes to `canon-systems-v2/**` or any sibling repo
  - No edits to `infra/**`, `.github/workflows/**`, Dockerfiles, Terraform, K8s manifests
  - No edits to root `pyproject.toml`, `pytest.ini`, `src/canon_systems/**`
  - No edits to hard-lock rule, plan, backlog, E0-T1/E0-T2 frozen docs
  - No new pytest plugins; no pip-install at test collection time
</REPOSITORY>

<REASONING>
1. Migration bookkeeping + build harness (AC: builds in place, waived in notes):
   - Author `docs/E0-T3-MIGRATION-NOTES.md` with v2 SHA `ebecb91`, waiver justification, per-file source→target table, exclusions list.
   - Author `scripts/backend/build-services.sh` (bash `set -euo pipefail`): install `backend/shared` first, then loop through the six leaf services running `pip install -e backend/<svc>` and `python -c "import <pkg>.main; assert hasattr(<pkg>.main, 'app')"`; exit non-zero on first failure; chmod +x.

2. knowledge-api (flat layout):
   - Overwrite scaffold files in `backend/knowledge-api/{README.md,pyproject.toml,app/__init__.py,app/main.py}` with v2 content verbatim.
   - Copy v2 `app/**` tree + `alembic.ini` + `alembic/**` (minus excluded patterns).
   - Add `"canon-backend-shared"` to `[project].dependencies`.

3. knowledge-worker (adopt src-layout):
   - Copy v2 `src/knowledge_worker/**` into `backend/knowledge-worker/src/knowledge_worker/`.
   - Replace README.md and pyproject.toml with v2 content (keep `package-dir = {"" = "src"}`, add `canon-backend-shared`).
   - DELETE flat scaffold `backend/knowledge-worker/knowledge_worker/__init__.py` and `main.py`.

4. memory-adapter (adopt src-layout):
   - Copy v2 `src/memory_adapter/**` into `backend/memory-adapter/src/memory_adapter/`.
   - Replace README.md and pyproject.toml (package-dir=src, add `canon-backend-shared`).
   - DELETE flat scaffold `backend/memory-adapter/memory_adapter/__init__.py` and `main.py`.

5. Test harness update (`tests/test_backend_layout.py`):
   - Refactor `PYTHON_SERVICES` to `dict[slug, main_path_relative_to_service_dir]`:
     - knowledge-api → `app/main.py`
     - knowledge-worker → `src/knowledge_worker/main.py`
     - memory-adapter → `src/memory_adapter/main.py`
     - state-api → `state_api/main.py`
     - axon-service → `axon_service/main.py`
     - synthesis → `synthesis/main.py`
   - Preserve every E0-T2 assertion; update entrypoint check to use `REPO_ROOT / "backend" / slug / rel_path`.
   - Add 5 new hermetic assertions: `test_canon_backend_shared_listed_in_moved_service_pyprojects` (tomllib), `test_knowledge_api_has_alembic`, `test_migration_notes_exists` (must contain `ebecb91`), `test_no_orphan_scaffold_flat_dirs`, `test_build_services_script_present_and_executable`.

6. Living-spec: README.md Backend monorepo section updated + link to migration notes; CHANGELOG Unreleased entry; docs/SYSTEM-WORKFLOW.md §10 augment.
</REASONING>

<OUTPUT_FORMAT>
Produce only the code, doc, and script changes needed to satisfy all ACs, plus tests that cover each. Do not refactor unrelated code.

All scoper contracts mirror into implementer constraints:

scaffold_replacement_contract (copy v2 byte-for-byte minus exclusions):
- knowledge-api: flat (backend/knowledge-api/app/*); exclusions `["**/__pycache__/**","**/*.pyc","**/*.egg-info/**","tests/**"]`
- knowledge-worker: src-layout (backend/knowledge-worker/src/knowledge_worker/*); exclusions `["**/__pycache__/**","**/*.pyc","**/*.egg-info/**","app/**","tests/**"]` (v2 empty `app/` dirs MUST NOT be imported)
- memory-adapter: src-layout (backend/memory-adapter/src/memory_adapter/*); exclusions `["**/__pycache__/**","**/*.pyc","**/*.egg-info/**","tests/**"]`
- Add `"canon-backend-shared"` string to each of the three moved pyproject.toml `[project].dependencies` (no version pin).

test_backend_layout_update_contract: see REASONING §5.

in_scope_paths_to_create / modify / delete / out_of_scope: see scoper.md.

Hard-lock reminders (non-negotiable):
- Do NOT run `git commit` / `git push` / `git subtree add` / `git subtree pull` / `git filter-repo` / `git rebase` / any history-rewriting command. Parent owns the per-task commit per rule §9.
- Do NOT create, switch, delete, or rename branches.
- Do NOT modify anything under `/Users/edwardwalker/localwork/canon-systems-v2` (read-only upstream).
- Do NOT add new pytest plugins; do NOT edit `pytest.ini` or root `pyproject.toml`.
- Use `pathlib` + `tomllib` for filesystem/TOML assertions; keep tests hermetic (no `pip install` at collection time).

Before declaring done, run locally and include stdout summaries in HANDOFF_TO_QA:
1. `pytest tests/test_backend_layout.py -v` → all pass.
2. `bash scripts/backend/build-services.sh` → exit 0.
3. `git status --short` → confirm scope.

Final response must include a HANDOFF_TO_QA block covering changed_files (created/modified/deleted), how_to_run_tests (command + summary), how_to_run_workspace_build (exit code), ac_coverage map, summary, decisions, next_actions, open_questions.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
If you hit a blocker, emit HANDOFF_NOT_READY instead.

Scope fences (violation = HANDOFF_NOT_READY):
- No git commit/push/branch operations.
- No writes under `canon-systems-v2/**` or sibling repos.
- No edits to `src/canon_systems/**`, `infra/**`, `.github/workflows/**`, `pytest.ini`, root `pyproject.toml`, hard-lock rule, plan, backlog, plan doc, E0-T1 frozen docs, or untouched E0-T2 slots.
- No new pytest plugins, no pip-install at collection time.
- Do NOT skip living-spec touches (README, CHANGELOG, SYSTEM-WORKFLOW).

Emit this block verbatim (filled in) as the FINAL content of your response:

HANDOFF_TO_QA
  handoff_id: "canon-memory-v1"
  task_id: "E0-T3"
  branch: "wave/0/canon-memory-v1"
  changed_files:
    created: [...]
    modified: [...]
    deleted: [...]
  how_to_run_workspace_build:
    command: "bash scripts/backend/build-services.sh"
    exit_code: <0 on success>
    summary: "<brief>"
  how_to_run_tests:
    command: "pytest tests/test_backend_layout.py -v"
    summary: "<N passed, 0 failed, 0 skipped>"
  acceptance_criteria_covered: [...]
  summary: "..."
  decisions: [...]
  next_actions: [...]
  open_questions: []
END_HANDOFF_TO_QA
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
