# Cursor-pilot packet — E0-T2

- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E0-T2
- workstream_id: wave-0b
- branch: wave/0/canon-memory-v1
- agent_name: cursor-pilot
- phase: cursor-pilot
- phase_status: pass

## CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor on the
canon-systems repo. This prompt MUST be executed by that subagent (default
model: `composer-2-fast`), not by the parent planner agent. You are operating
under the hard-lock rule `.cursor/rules/memory-platform-build-discipline.mdc`
(§§1–10); §2 (packet-gated writes) is satisfied because both
`.cursor/handoffs/canon-memory-v1/E0-T2/scoper.md` and this
`cursor-pilot.md` are on disk before you begin. §9 (per-task commit) is owned
by the PARENT orchestrator — you MUST NOT run `git commit` or `git push`.
</ROLE>

<TASK>
Stand up the `backend/` monorepo skeleton on branch `wave/0/canon-memory-v1`:
seven service directories (`knowledge-api`, `knowledge-worker`,
`memory-adapter`, `state-api`, `axon-service`, `synthesis`, `synthesis-web`)
each with a `README.md` placeholder and matching entry-point scaffolding, plus
`backend/shared/` exposing `auth`, `ids`, `events` modules under import path
`canon_backend_shared`, importable by every service package. Wire the root
workspace build (uv workspace + shell-script fallback). Add
`tests/test_backend_layout.py` asserting the tree + shared-lib behavior. Touch
the living-spec files (README / CHANGELOG / SYSTEM-WORKFLOW). This is
**skeleton-only**: no real service code is moved from canon-systems-v2 (that
is E0-T3) and no infra work is done (E0-T4).
</TASK>

<ACCEPTANCE_CRITERIA>
- backend/{knowledge-api,knowledge-worker,memory-adapter,state-api,axon-service,synthesis,synthesis-web} directories exist with README placeholders and matching entry-point scaffolding.
- backend/shared/ exposes auth, ids, events modules consumable by every service package.
- Root pyproject/poetry/turbo (language-appropriate) builds the workspace cleanly.
- No canon-systems-v2 service code is moved into backend/ under this task; all service directories are stubs only (git history preservation is E0-T3).
- backend/shared/ids.py exposes a callable `deterministic_id(*parts: str, prefix: str | None = None) -> str` implemented via hashlib.sha256 (per backlog §A).
- backend/shared/events.py exposes a `CanonicalEvent` type + `to_dict`/`from_dict` round-trip matching backlog §C field names.
- backend/shared/auth.py exposes a stub `verify_caller(headers: Mapping[str, str]) -> AuthContext` signature raising NotImplementedError with a docstring pointing to E2-T2/E1-T2; no real auth logic in this task.
- Root README.md, CHANGELOG.md, and docs/SYSTEM-WORKFLOW.md are updated to reference the new backend/ layout (per backlog §G living-spec invariant).
- done_signal: Workspace build passes (either `uv sync --all-packages` exits 0 OR `bash scripts/backend/install-workspace.sh` exits 0).
- done_signal: `tests/test_backend_layout.py` asserts the expected directory tree and runs cleanly under the existing `pytest.ini` (pythonpath=src) with no new plugins.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E0-T2
- workstream_id: wave-0b
- epic_id: E0
- company_id: IMC
- repository_id: innermost
- branch: wave/0/canon-memory-v1 (already checked out; do NOT create a new branch)
- prior_checkpoint: .cursor/handoffs/canon-memory-v1/E0-T1/release-status.md (READY_TO_MERGE)

- prior_work_references:
  - E0_T1_scoper — .cursor/handoffs/canon-memory-v1/E0-T1/scoper.md — Wave 0 packet shape + DoR conventions
  - E0_T1_cursor_pilot — .cursor/handoffs/canon-memory-v1/E0-T1/cursor-pilot.md — Pilot prompt shape precedent
  - wave0_audit — docs/WAVE-0-AUDIT.md — confirms Python 3.10+/FastAPI/uvicorn precedent for services
  - backlog_section_A_ids — docs/MEMORY-PLATFORM-BACKLOG.md §A — deterministic_id spec
  - backlog_section_C_evt — docs/MEMORY-PLATFORM-BACKLOG.md §C — canonical event envelope spec
  - backlog_section_G — docs/MEMORY-PLATFORM-BACKLOG.md §G — living-spec invariant
  - hard_lock_rule_s2 — .cursor/rules/memory-platform-build-discipline.mdc §2 — packet-gated writes
  - v2_ka_pyproject — /Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api/pyproject.toml — setuptools-per-service precedent (READ-ONLY)
  - ctx_latest — .canon/memory/context-latest.md — company_id=IMC, repository_id=innermost

- read-only context files (read as needed; do NOT modify):
  - docs/MEMORY-PLATFORM-BACKLOG.md (§A, §C, §G, E0-T2 entry)
  - docs/MEMORY-PLATFORM-PLAN.md
  - docs/SYSTEM-WORKFLOW.md (will be modified; read first)
  - docs/WAVE-0-AUDIT.md
  - docs/DEPRECATIONS.md
  - .cursor/plans/canon_memory_platform_build_d21073e1.plan.md
  - .cursor/rules/memory-platform-build-discipline.mdc
  - .cursor/handoffs/canon-memory-v1/E0-T1/{scoper,cursor-pilot,qa-gate}.md
  - pyproject.toml (will be additively modified)
  - pytest.ini
  - README.md, CHANGELOG.md

- living-spec touch list (per backlog §G):
  - README.md — add short "Backend monorepo" section pointing to `backend/README.md`
  - CHANGELOG.md — add an Unreleased entry: "E0-T2: backend/ skeleton + shared lib"
  - docs/SYSTEM-WORKFLOW.md — one-paragraph note (either inside §1 or a new §10 titled "Backend monorepo layout") pointing to the new `backend/` layout

- sibling-repo references are READ-ONLY (shape inspiration only; do NOT import, copy, or git-move anything):
  - /Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api/pyproject.toml
  - /Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api/app/main.py
  - /Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-worker/README.md
  - /Users/edwardwalker/localwork/canon-systems-v2/services/memory-adapter/README.md
</CONTEXT>

<REPOSITORY>
- primaryLanguages: ["Python 3.10+", "Markdown", "TOML"]
- testFramework: pytest — canon-systems root `tests/` directory; existing `pytest.ini` declares `pythonpath=src`. Do NOT modify pytest.ini, do NOT add new plugins, and the new test file MUST work under the existing config.
- build_tool: setuptools (root canon-systems CLI stays untouched) + per-service pyproject.toml under `backend/*`. Workspace orchestration via `[tool.uv.workspace]` at root (additive) AND a fallback `scripts/backend/install-workspace.sh`.

- existing structural facts (from scoper packet — do NOT re-discover):
  - Root `pyproject.toml` hosts the canon-systems CLI package; `[tool.uv.workspace]` is NOT yet present.
  - `src/canon_systems/**` contains the CLI and `src/canon_systems/shared.py` (resolves KNOWLEDGE_API_URL / KNOWLEDGE_WORKER_URL / MEMORY_ADAPTER_URL env vars). This layout MUST NOT be touched in this task.
  - `backend/` does NOT yet exist; this task creates it.
  - canon-systems-v2 `services/knowledge-api/app/` is the Python-package-name precedent for `knowledge-api` (package name stays `app`, not `knowledge_api`).

- in_scope_paths_to_create (create exactly these files, nothing more):
  - backend/README.md
  - backend/knowledge-api/{README.md,pyproject.toml,app/__init__.py,app/main.py}
  - backend/knowledge-worker/{README.md,pyproject.toml,knowledge_worker/__init__.py,knowledge_worker/main.py}
  - backend/memory-adapter/{README.md,pyproject.toml,memory_adapter/__init__.py,memory_adapter/main.py}
  - backend/state-api/{README.md,pyproject.toml,state_api/__init__.py,state_api/main.py}
  - backend/axon-service/{README.md,pyproject.toml,axon_service/__init__.py,axon_service/main.py}
  - backend/synthesis/{README.md,pyproject.toml,synthesis/__init__.py,synthesis/main.py}
  - backend/synthesis-web/{README.md,.gitkeep}
  - backend/shared/{README.md,pyproject.toml,canon_backend_shared/__init__.py,canon_backend_shared/auth.py,canon_backend_shared/ids.py,canon_backend_shared/events.py}
  - tests/test_backend_layout.py
  - scripts/backend/install-workspace.sh

- in_scope_paths_to_modify:
  - pyproject.toml — add `[tool.uv.workspace] members = ["backend/*"]` (additive; existing canon-systems project section byte-identical apart from this addition).
  - README.md — add short "Backend monorepo" section referencing `backend/README.md`.
  - CHANGELOG.md — add Unreleased entry: "E0-T2: backend/ skeleton + shared lib".
  - docs/SYSTEM-WORKFLOW.md — one-paragraph note (in §1 or a new §10 "Backend monorepo layout").

- out_of_scope_paths (DO NOT touch):
  - src/canon_systems/**
  - infra/**
  - .cursor/rules/memory-platform-build-discipline.mdc
  - .cursor/plans/canon_memory_platform_build_d21073e1.plan.md
  - docs/MEMORY-PLATFORM-BACKLOG.md
  - docs/MEMORY-PLATFORM-PLAN.md
  - docs/WAVE-0-AUDIT.md
  - docs/DEPRECATIONS.md
  - docs/OBSIDIAN-MIND-CATALOGUE.md
  - pytest.ini
  - Any file inside sibling repos
  - Any git move/subtree/filter-repo operation importing real code from canon-systems-v2 (that is E0-T3)

- entry_point_scaffolding_contract:
  - fastapi_services applies_to: ["knowledge-api", "knowledge-worker", "memory-adapter", "state-api", "axon-service", "synthesis"]
    - module_layout: `backend/<slug>/<python_pkg>/main.py` with `app = FastAPI(title=..., version='0.0.0-scaffold')` and a GET `/healthz` returning `{'status': 'scaffold', 'service': '<slug>'}`.
    - python_pkg_naming: knowledge-api→`app`, knowledge-worker→`knowledge_worker`, memory-adapter→`memory_adapter`, state-api→`state_api`, axon-service→`axon_service`, synthesis→`synthesis`.
    - pyproject_shape: setuptools; `name = <slug>`; `version = "0.0.0"`; deps `[fastapi, uvicorn, pydantic]` with canon-systems-v2 compatible `>=`/`<` ranges (do NOT pin); `[tool.setuptools.packages.find] where = ["."] include = ["<pkg>*"]`.
  - readme_only_service applies_to: ["synthesis-web"]
    - README MUST state "entry-point and language chosen in E5-T4; this directory is a reserved slot".
    - marker_file: `backend/synthesis-web/.gitkeep`

- shared_lib_contract:
  - package_import_path: `canon_backend_shared` (avoid collision with `src/canon_systems/shared.py`).
  - auth — `def verify_caller(headers: Mapping[str, str]) -> AuthContext`; `raise NotImplementedError('real auth lands in E2-T2 / E1-T2')`; `AuthContext` is empty `@dataclass(slots=True)`.
  - ids — `def deterministic_id(*parts: str, prefix: str | None = None) -> str`; `hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()` prefixed by `<prefix>_` if provided.
  - events — `@dataclass CanonicalEvent` with backlog §C fields; `to_dict()` + `from_dict()` classmethod; `schema_version=1`; pure data.
  - zero runtime deps beyond stdlib in `backend/shared/pyproject.toml`.

- workspace_build_contract (SHIP BOTH):
  - primary: `[tool.uv.workspace] members = ["backend/*"]` in root pyproject. Build: `uv sync --all-packages`.
  - fallback: `scripts/backend/install-workspace.sh` — `#!/usr/bin/env bash` + `set -euo pipefail`; `pip install -e backend/shared` then `pip install -e backend/<svc>` for each of the six Python services.

- tests_to_write (path: tests/test_backend_layout.py; pytest; hermetic under existing pytest.ini):
  - test_seven_service_dirs_exist — each slug dir + non-empty README.md.
  - test_python_services_have_entrypoints — pyproject.toml + `<pkg>/main.py` declaring module-level `app` (ast-based inspection).
  - test_synthesis_web_is_readme_only — README.md + .gitkeep; no pyproject, no *.py.
  - test_shared_modules_importable — file-existence + (guarded) import checks for auth/ids/events.
  - test_deterministic_id_is_stable_and_supports_prefix — guarded import OR spec_from_file_location; verify stability + prefix.
  - test_canonical_event_roundtrip — minimal instance covers every §C required field; `from_dict(to_dict(x)) == x`.
  - test_workspace_declaration_or_script_present — parse root pyproject with tomllib; pass if `[tool.uv.workspace].members` includes `"backend/*"` OR `scripts/backend/install-workspace.sh` exists and is non-empty.

- mustNotBreak:
  - Existing `src/canon_systems/**` package layout, tests, and CLI.
  - Existing pytest discovery (`pytest.ini pythonpath=src`).
  - Hard-lock rule §2 markdown-only-until-packets contract.
  - Existing KNOWLEDGE_API_URL / KNOWLEDGE_WORKER_URL / MEMORY_ADAPTER_URL resolution in `src/canon_systems/shared.py`.

- dependencies:
  - No runtime dependency additions to the root pyproject.
  - Per-service pyprojects MAY list FastAPI + uvicorn + pydantic; use canon-systems-v2 compatible `>=`/`<` ranges.
  - `backend/shared` zero runtime deps beyond stdlib.
</REPOSITORY>

<REASONING>
1. Read-only prep. Read backlog §A/§C/§G, E0-T1 packet quartet, hard-lock rule, pyproject.toml, pytest.ini, README.md, CHANGELOG.md, docs/SYSTEM-WORKFLOW.md. Inspect v2 knowledge-api pyproject/main.py as shape reference only. No writes yet.

2. Create `backend/shared/` (foundational library): pyproject, `canon_backend_shared/{__init__.py, auth.py, ids.py, events.py}`, README.md. `events.CanonicalEvent` includes every backlog §C field; `ids.deterministic_id` uses hashlib.sha256; `auth.verify_caller` raises NotImplementedError.

3. Create the six FastAPI service scaffolds in parallel per `entry_point_scaffolding_contract`.

4. Create README-only `synthesis-web` slot + top-level `backend/README.md` index.

5. Wire workspace: additive `[tool.uv.workspace]` in root + `scripts/backend/install-workspace.sh` fallback.

6. Write `tests/test_backend_layout.py` — static inspection (`pathlib`, `tomllib`, `ast`, `importlib.util.find_spec`) to stay hermetic under existing pytest.ini. No conftest.py that installs packages at collection time.

7. Living-spec touches: README.md backend section, CHANGELOG.md Unreleased entry, docs/SYSTEM-WORKFLOW.md one-paragraph note.

8. Verify locally: `pytest tests/test_backend_layout.py -v` (must pass) + workspace build (either `uv sync --all-packages` or `bash scripts/backend/install-workspace.sh` must exit 0). `git status` to confirm scope.

ac_traceability:
- AC1 (seven dirs + entry-point scaffolding) → test_seven_service_dirs_exist, test_python_services_have_entrypoints, test_synthesis_web_is_readme_only.
- AC2 (shared lib) → test_shared_modules_importable, test_deterministic_id_is_stable_and_supports_prefix, test_canonical_event_roundtrip.
- AC3 (workspace build) → test_workspace_declaration_or_script_present + manual done_signal.
- AC4–AC8 (no v2 moves, ids/events/auth specs, living-spec) → covered by static tests + file-existence/content checks.
</REASONING>

<OUTPUT_FORMAT>
Produce only the code + doc changes needed to satisfy all acceptance criteria, plus `tests/test_backend_layout.py`. Do not refactor unrelated code. Do not add dependencies to the root `pyproject.toml`.

After implementation, verify locally (do NOT commit, do NOT push):
1. `pytest tests/test_backend_layout.py -v` — must exit 0 under existing `pytest.ini`.
2. Workspace build: try `uv sync --all-packages` first; if `uv` is unavailable, run `bash scripts/backend/install-workspace.sh`. At least one must exit 0.
3. `git status` — confirm changed files are exactly in the permitted set.

Record in your final response:
- Full list of created + modified files (git-status-style).
- Exact pytest command run and its stdout/stderr summary (pass/fail counts).
- Exact workspace-build command run and its exit code.
- AC→test mapping.
- HANDOFF_TO_QA block.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
If at any point you discover a blocker that prevents satisfying an AC without touching an out-of-scope path, STOP and emit `HANDOFF_NOT_READY` with quality_failures + remediation_steps.

Scope-compliance fences (violating any is an automatic HANDOFF_NOT_READY):
- Do NOT run `git add`, `git commit`, `git push`, `git subtree`, `git filter-repo`, or any history-rewriting command. Parent owns commits per hard-lock rule §9.
- Do NOT create or switch branches. Work stays on `wave/0/canon-memory-v1`.
- Do NOT touch any file inside sibling repos.
- Do NOT modify hard-lock rule, plan file, backlog, E0-T1 frozen docs, pytest.ini, `src/canon_systems/**`, or `infra/**`.
- Do NOT add new pytest plugins or modify pytest configuration.
- Do NOT ship a conftest.py that runs `pip install` at collection time.
- Do NOT skip living-spec touches — README.md, CHANGELOG.md, docs/SYSTEM-WORKFLOW.md updates mandatory per backlog §G.
- Do NOT widen scope by moving canon-systems-v2 service code (that is E0-T3).

When finished, emit this HANDOFF_TO_QA block verbatim (filled in) as the FINAL content of your response:

HANDOFF_TO_QA
  handoff_id: "canon-memory-v1"
  task_id: "E0-T2"
  branch: "wave/0/canon-memory-v1"
  changed_files:
    created: [...]
    modified: [...]
  how_to_run_workspace_build:
    primary: "uv sync --all-packages"
    fallback: "bash scripts/backend/install-workspace.sh"
    done_signal_satisfied_by: "<primary|fallback>"
    exit_code: <0 on success>
  how_to_run_tests:
    command: "pytest tests/test_backend_layout.py -v"
    summary: "<N passed, 0 failed, 0 skipped>"
  acceptance_criteria_covered: [...]
  summary: "..."
  decisions: [...]
  next_actions: [...]
  open_questions: []
END_HANDOFF_TO_QA

Do not declare the task complete without the HANDOFF_TO_QA block. Do not run `git commit` or `git push`.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
