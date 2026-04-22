# Scoper packet — E0-T3

- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E0-T3
- workstream_id: wave-0c
- parent_epic: E0 (Inventory and consolidation)
- branch: `wave/0/canon-memory-v1`
- agent_name: scoper
- phase: scoper
- phase_status: pass
- definition_of_ready: pass
- prior_task: E0-T2 (complete — quartet on disk, commit `da02e41` on wave branch)

## Scope summary

E0-T3 consolidates the three in-use backend services (`knowledge-api`, `knowledge-worker`, `memory-adapter`) from the read-only sibling repo `canon-systems-v2` into this repo's `backend/` monorepo, REPLACING the E0-T2 scaffolds with the real v2 source. Because v2 history for these services is a single squashed "Initial import" commit (`ebecb91` in `/Users/edwardwalker/localwork/canon-systems-v2`), git history preservation offers trivial ROI and carries merge-conflict risk against the E0-T2 scaffold — this packet explicitly WAIVES subtree/filter-repo import in favor of a copy + waiver record in `docs/E0-T3-MIGRATION-NOTES.md` (v2 SHA + per-file source paths). AC2 "remain serviceable end-to-end" is interpreted as: production `KNOWLEDGE_API_URL` / `KNOWLEDGE_WORKER_URL` / `MEMORY_ADAPTER_URL` stay serviceable because E0-T3 does NOT redeploy anything (v2 ECR images untouched; infra import is E0-T4; integration smoke is E0-T5), AND the new `backend/<svc>/` source boots locally on its documented port. AC3/done_signal "CI builds each service" is satisfied by a new `scripts/backend/build-services.sh` that runs `pip install -e backend/<svc>` + an `import <pkg>.main; app = <pkg>.main.app` smoke per service — dedicated CI workflow wiring is flagged as a carried OQ for E0-T4/E0-T5. The E0-T2 `tests/test_backend_layout.py` is extended to accept src-layout for `knowledge-worker` and `memory-adapter` (v2 uses `src/<pkg>/`), preserving every E0-T2 assertion.

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "Consolidate canon-systems-v2 services/knowledge-api, services/knowledge-worker, services/memory-adapter into canon-systems backend/<svc>/ by copying source files (no git subtree; single-commit v2 history makes the waiver the least-risk path; record in docs/E0-T3-MIGRATION-NOTES.md). Replace E0-T2 scaffold placeholders. Adopt v2 layouts: knowledge-api flat (backend/knowledge-api/app/), knowledge-worker src-layout (backend/knowledge-worker/src/knowledge_worker/), memory-adapter src-layout (backend/memory-adapter/src/memory_adapter/). Add canon-backend-shared as an explicit dependency in each moved pyproject to preserve the E0-T2 shared-lib wiring. Update tests/test_backend_layout.py to parameterize main.py paths. Add scripts/backend/build-services.sh (install + import-smoke per service) as the CI done_signal surrogate. Update living-spec (README, CHANGELOG, SYSTEM-WORKFLOW §10). Do NOT touch infra/, sibling repos, deploy configs, src/canon_systems/**, pytest.ini, or anything outside backend/ and the listed living-spec files. Branch stays wave/0/canon-memory-v1."

  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      plan_id: "canon_memory_platform_build_d21073e1"
      task_id: "E0-T3"
      workstream_id: "wave-0c"
      epic_id: "E0"
      agent_name: "scoper"
      company_id: "IMC"
      repository_id: "innermost"
      repo_ref: "canon-systems @ wave/0/canon-memory-v1 (verified via git branch --show-current, tip=da02e41, 2026-04-22)"
      upstream_source_repo: "canon-systems-v2 @ /Users/edwardwalker/localwork/canon-systems-v2 (sibling, read-only)"
      upstream_source_commit: "ebecb91 — Initial import of canon-systems-v2 workspace"
      prior_checkpoint: ".cursor/handoffs/canon-memory-v1/E0-T2/release-status.md (READY_TO_MERGE; commit da02e41)"

    story:
      title: "Consolidate in-use services into backend/"
      userValue: "Wave 1+ needs the real KNOWLEDGE_API_URL/KNOWLEDGE_WORKER_URL/MEMORY_ADAPTER_URL sources in canon-systems so E1-T2 can fix memory-adapter routing, E2-T2 can add state-api alongside them, and E0-T4 can import infra against a single repo."
      acceptanceCriteria:
        - "Each service builds and runs in place from backend/<service>/."
        - "Existing KNOWLEDGE_API_URL/KNOWLEDGE_WORKER_URL/MEMORY_ADAPTER_URL remain serviceable end-to-end."
        - "Git history for moved code is preserved or explicitly waived in the task notes."
        - "backend/knowledge-api/ contains the real v2 app/ package (app/main.py, app/auth/**, app/models/**, app/db/**, app/storage/**, app/policies/**, app/bootstrap.py, app/config.py, app/__init__.py), plus alembic/ + alembic.ini; pycache/egg-info excluded; imports app.main:app successfully after pip install -e backend/knowledge-api."
        - "backend/knowledge-worker/ adopts src-layout with backend/knowledge-worker/src/knowledge_worker/{main.py,service.py,config.py,models.py,__init__.py,api/router.py,api/__init__.py,projections/memory_capture_to_markdown.py,projections/memory_to_markdown.py,projections/__init__.py}; imports knowledge_worker.main:app successfully after pip install -e backend/knowledge-worker."
        - "backend/memory-adapter/ adopts src-layout with backend/memory-adapter/src/memory_adapter/{main.py,service.py,config.py,models.py,__init__.py,api/router.py,api/__init__.py,adapters/mempalace.py,adapters/__init__.py}; imports memory_adapter.main:app successfully after pip install -e backend/memory-adapter."
        - "Each of the three moved services' pyproject.toml declares canon-backend-shared alongside the v2 runtime deps so the E0-T2 shared-lib wiring is preserved; version/range values MUST match v2."
        - "E0-T2 scaffold placeholder files for these three services are REMOVED in favor of the real v2 content."
        - "scripts/backend/build-services.sh exists, is executable, runs pip install -e backend/<svc> for all six Python services and then executes an import-smoke for each; exits non-zero on the first failure."
        - "docs/E0-T3-MIGRATION-NOTES.md records the waiver with v2 SHA ebecb91, per-file source paths, target paths, exclusions."
        - "tests/test_backend_layout.py updated so PYTHON_SERVICES maps slug → main.py relative path; every existing E0-T2 assertion continues to pass."
        - "Root pytest collection stays green; v2 services/<svc>/tests/ directories are NOT copied (deferred to E1-T2/E0-T5)."
        - "README.md, CHANGELOG.md, docs/SYSTEM-WORKFLOW.md §10 updated per backlog §G living-spec invariant."
        - "No file under canon-systems-v2 modified; no infra/ created; no Dockerfile modified; no src/canon_systems/** touched."
      done_signal:
        - "CI builds each service package."
        # satisfied in-repo by scripts/backend/build-services.sh exit 0 until dedicated CI is wired (see OQ-E0-T3-03)

    repository:
      primaryLanguages: ["Python 3.10+", "Markdown", "TOML", "Bash", "INI"]
      testFramework: "pytest (root canon-systems tests/ only; per-service v2 tests/ NOT copied)"
      build_tool: "setuptools per service; workspace orchestrated by root [tool.uv.workspace].members=['backend/*'] (from E0-T2) + scripts/backend/install-workspace.sh + new scripts/backend/build-services.sh"
      reference_files_in_sibling_repo_readonly:
        - "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api/{README.md,pyproject.toml,alembic.ini,alembic/**,app/**}"
        - "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-worker/{README.md,pyproject.toml,src/knowledge_worker/**}"
        - "/Users/edwardwalker/localwork/canon-systems-v2/services/memory-adapter/{README.md,pyproject.toml,src/memory_adapter/**}"
      git_history_status:
        preservation_decision: "explicit_waiver"
        justification: "git log --follow on each moved file in canon-systems-v2 returns a single commit (ebecb91, 'Initial import of canon-systems-v2 workspace')."
        waiver_record_location: "docs/E0-T3-MIGRATION-NOTES.md"

    in_scope_paths_to_create:
      # knowledge-api (flat layout)
      - "backend/knowledge-api/app/bootstrap.py"
      - "backend/knowledge-api/app/config.py"
      - "backend/knowledge-api/app/auth/{__init__.py,dependencies.py,models.py}"
      - "backend/knowledge-api/app/models/{__init__.py,artifact_api.py,artifact_db.py,run_api.py,run_db.py,work_item_api.py,work_item_db.py}"
      - "backend/knowledge-api/app/policies/{__init__.py,artifacts.py}"
      - "backend/knowledge-api/app/storage/{__init__.py,s3.py}"
      - "backend/knowledge-api/app/db/{__init__.py,session.py}"
      - "backend/knowledge-api/alembic.ini"
      - "backend/knowledge-api/alembic/{env.py,script.py.mako,versions/*.py,versions/README.md}"
      # knowledge-worker (src-layout)
      - "backend/knowledge-worker/src/knowledge_worker/{__init__.py,main.py,service.py,config.py,models.py}"
      - "backend/knowledge-worker/src/knowledge_worker/api/{__init__.py,router.py}"
      - "backend/knowledge-worker/src/knowledge_worker/projections/{__init__.py,memory_capture_to_markdown.py,memory_to_markdown.py}"
      # memory-adapter (src-layout)
      - "backend/memory-adapter/src/memory_adapter/{__init__.py,main.py,service.py,config.py,models.py}"
      - "backend/memory-adapter/src/memory_adapter/api/{__init__.py,router.py}"
      - "backend/memory-adapter/src/memory_adapter/adapters/{__init__.py,mempalace.py}"
      # Migration notes + build-services helper
      - "docs/E0-T3-MIGRATION-NOTES.md"
      - "scripts/backend/build-services.sh"

    in_scope_paths_to_modify:
      - "backend/knowledge-api/README.md                 # replace with v2 README"
      - "backend/knowledge-api/pyproject.toml            # replace with v2 pyproject + canon-backend-shared dep"
      - "backend/knowledge-api/app/__init__.py           # replace with v2 content"
      - "backend/knowledge-api/app/main.py               # replace with v2 main.py"
      - "backend/knowledge-worker/README.md              # replace with v2 README"
      - "backend/knowledge-worker/pyproject.toml         # replace with v2 pyproject + canon-backend-shared; package-dir='src'"
      - "backend/memory-adapter/README.md                # replace with v2 README"
      - "backend/memory-adapter/pyproject.toml           # replace with v2 pyproject + canon-backend-shared; package-dir='src'"
      - "tests/test_backend_layout.py                    # parameterize main-path, preserve all E0-T2 assertions, add E0-T3 assertions"
      - "README.md                                       # Backend monorepo section: list three services as real (no longer scaffolds); link to migration notes"
      - "CHANGELOG.md                                    # Unreleased entry referencing docs/E0-T3-MIGRATION-NOTES.md"
      - "docs/SYSTEM-WORKFLOW.md                         # §10 augment"

    in_scope_paths_to_delete:
      - "backend/knowledge-worker/knowledge_worker/__init__.py"
      - "backend/knowledge-worker/knowledge_worker/main.py"
      - "backend/memory-adapter/memory_adapter/__init__.py"
      - "backend/memory-adapter/memory_adapter/main.py"

    out_of_scope_paths:
      - "src/canon_systems/**"
      - "pyproject.toml (root)"
      - "pytest.ini"
      - ".cursor/rules/memory-platform-build-discipline.mdc"
      - ".cursor/plans/canon_memory_platform_build_d21073e1.plan.md"
      - "docs/MEMORY-PLATFORM-BACKLOG.md / PLAN.md / WAVE-0-AUDIT.md / DEPRECATIONS.md / OBSIDIAN-MIND-CATALOGUE.md"
      - "infra/**, .github/workflows/**, any Dockerfile / deploy manifest / Terraform .tf / Kubernetes manifest"
      - "backend/knowledge-api/tests/**, backend/knowledge-worker/tests/**, backend/memory-adapter/tests/**  # v2 tests deferred"
      - "backend/shared/**, backend/state-api/**, backend/axon-service/**, backend/synthesis/**, backend/synthesis-web/**  # untouched E0-T2 slots"
      - "backend/README.md (prefer top-level README.md for messaging)"
      - "Any path inside sibling repos (canon-platform, canon-systems-v2, mempalace, obsidian-mind, temporal, total_recall)"

    scaffold_replacement_contract:
      knowledge-api:
        layout: "flat (backend/knowledge-api/app/*)"
        v2_source_root: "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api"
        exclusions: ["**/__pycache__/**", "**/*.pyc", "**/*.egg-info/**", "tests/**"]
      knowledge-worker:
        layout: "src-layout (backend/knowledge-worker/src/knowledge_worker/*)"
        v2_source_root: "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-worker"
        exclusions: ["**/__pycache__/**", "**/*.pyc", "**/*.egg-info/**", "app/**", "tests/**"]
        note: "v2 has empty services/knowledge-worker/app/ subdirs — DO NOT import"
      memory-adapter:
        layout: "src-layout (backend/memory-adapter/src/memory_adapter/*)"
        v2_source_root: "/Users/edwardwalker/localwork/canon-systems-v2/services/memory-adapter"
        exclusions: ["**/__pycache__/**", "**/*.pyc", "**/*.egg-info/**", "tests/**"]
      canon-backend-shared_dep_addition:
        "Add 'canon-backend-shared' string to [project].dependencies in each of the three moved pyprojects (no version pin; local editable via workspace)."

    test_backend_layout_update_contract:
      current_shape: "PYTHON_SERVICES is dict[slug, package_name]; test joins base/pkg/main.py."
      required_shape: "PYTHON_SERVICES is dict[slug, main_path_relative_to_service_dir]; test finds main.py at base / rel_path."
      new_mapping:
        knowledge-api: "app/main.py"
        knowledge-worker: "src/knowledge_worker/main.py"
        memory-adapter: "src/memory_adapter/main.py"
        state-api: "state_api/main.py"
        axon-service: "axon_service/main.py"
        synthesis: "synthesis/main.py"
      additional_assertions_required_for_E0_T3:
        - "test_canon_backend_shared_listed_in_moved_service_pyprojects"
        - "test_knowledge_api_has_alembic"
        - "test_migration_notes_exists (references ebecb91)"
        - "test_no_orphan_scaffold_flat_dirs"
        - "test_build_services_script_present_and_executable"
      preserved_assertions: "All E0-T2 tests continue to pass"

    ac_traceability:
      - criterion: "Each service builds and runs in place from backend/<service>/."
        verification: "test_python_services_have_entrypoints (updated) + test_canon_backend_shared_listed + manual: bash scripts/backend/build-services.sh exits 0"
      - criterion: "Existing URLs remain serviceable end-to-end."
        verification: "build-services.sh import-smoke + git status shows no infra/ or canon-systems-v2/ writes; interpretation: zero redeploy risk + local boot parity."
      - criterion: "Git history preserved or explicitly waived."
        verification: "test_migration_notes_exists + manual spot-check docs/E0-T3-MIGRATION-NOTES.md contains ebecb91 + per-file mapping"

    scope_compliance:
      permitted_paths_added:
        - "backend/knowledge-api/app/**, backend/knowledge-api/alembic/**, alembic.ini"
        - "backend/knowledge-worker/src/knowledge_worker/**"
        - "backend/memory-adapter/src/memory_adapter/**"
        - "docs/E0-T3-MIGRATION-NOTES.md"
        - "scripts/backend/build-services.sh"
      permitted_paths_modified:
        - "backend/knowledge-api/{README.md,pyproject.toml,app/__init__.py,app/main.py}"
        - "backend/knowledge-worker/{README.md,pyproject.toml}"
        - "backend/memory-adapter/{README.md,pyproject.toml}"
        - "tests/test_backend_layout.py"
        - "README.md, CHANGELOG.md, docs/SYSTEM-WORKFLOW.md"
      permitted_paths_deleted:
        - "backend/knowledge-worker/knowledge_worker/__init__.py"
        - "backend/knowledge-worker/knowledge_worker/main.py"
        - "backend/memory-adapter/memory_adapter/__init__.py"
        - "backend/memory-adapter/memory_adapter/main.py"
      prohibited_paths_touched:
        - "src/canon_systems/**, infra/**, .github/workflows/**, pyproject.toml (root), pytest.ini"
        - "Hard-lock rule, plan, backlog, plan doc, E0-T1 frozen docs, E0-T2 assets (backend/shared/, backend/state-api/, backend/axon-service/, backend/synthesis/, backend/synthesis-web/)"
        - "Any path inside sibling repos"
      git_history_preservation: "explicit waiver per OQ-E0-T3-01; record in docs/E0-T3-MIGRATION-NOTES.md"

    openQuestions:
      - id: "OQ-E0-T3-01"
        question: "Git history preservation — full subtree import vs explicit waiver?"
        proposed_resolution: "Explicit waiver (single-commit v2 history makes subtree ROI near-zero; migration notes preserve forensic trail)."
        blocking_for_this_task: false
      - id: "OQ-E0-T3-02"
        question: "memory-adapter deployment topology — when does MEMORY_ADAPTER_URL get a real runtime target?"
        proposed_resolution: "NOT in E0-T3. Carried to E0-T4 / E1-T2."
        blocking_for_this_task: false
      - id: "OQ-E0-T3-03"
        question: "Done signal 'CI builds each service package' — scope of CI wiring?"
        proposed_resolution: "scripts/backend/build-services.sh satisfies done_signal; dedicated CI deferred to E0-T4/E0-T5."
        blocking_for_this_task: false
      - id: "OQ-E0-T3-04"
        question: "Do v2 services/<svc>/tests/ come along in E0-T3?"
        proposed_resolution: "No. Root pytest auto-collection would fail; defer to E1-T2 / E0-T5."
        blocking_for_this_task: false
      - id: "OQ-E0-T3-05"
        question: "Should scripts/backend/install-workspace.sh be edited for src-layout?"
        proposed_resolution: "No edit expected (setuptools reads pyproject.package-dir automatically). Implementer verifies empirically."
        blocking_for_this_task: false
      - id: "OQ-E0-T3-06"
        question: "Carry alembic/versions/ for knowledge-api?"
        proposed_resolution: "Yes (minus __pycache__). app.bootstrap references migration state; omitting would block later waves."
        blocking_for_this_task: false

    dor_checklist:
      all: "pass"

END_HANDOFF_TO_CURSOR_PILOT
```

**DEFINITION_OF_READY verdict: PASS.**
