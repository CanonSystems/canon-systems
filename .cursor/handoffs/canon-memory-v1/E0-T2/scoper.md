# Scoper packet — E0-T2

- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E0-T2
- workstream_id: wave-0b
- parent_epic: E0 (Inventory and consolidation)
- branch: wave/0/canon-memory-v1
- agent_name: scoper
- phase: scoper
- phase_status: pass
- definition_of_ready: pass
- prior_task: E0-T1 (complete — packet quartet on disk)

## Scope summary

E0-T2 stands up the `backend/` monorepo skeleton in canon-systems: seven
service directories (`knowledge-api`, `knowledge-worker`, `memory-adapter`,
`state-api`, `axon-service`, `synthesis`, `synthesis-web`) each with a
`README.md` placeholder and matching entry-point scaffolding, plus
`backend/shared/` exposing `auth`, `ids`, `events` modules importable by
every service package. This task is **skeleton-only** — it does not move
any existing canon-systems-v2 code (that is E0-T3) and does not touch
infra (E0-T4). The root workspace is made to "build cleanly" via per-service
`pyproject.toml` files plus a root-level `[tool.uv.workspace]` members
declaration (fallback: `scripts/backend/install-workspace.sh`). A new
`tests/test_backend_layout.py` asserts the expected directory tree and the
importability of `backend.shared.{auth,ids,events}`.

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "Create backend/ monorepo skeleton: 7 service dirs with README + entry-point scaffolding, backend/shared/ with auth/ids/events modules, root workspace build passes, tests/test_backend_layout.py asserts layout. No service moves (E0-T3). No infra (E0-T4). Wave 0 branch: wave/0/canon-memory-v1."

  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      plan_id: "canon_memory_platform_build_d21073e1"
      task_id: "E0-T2"
      workstream_id: "wave-0b"
      epic_id: "E0"
      agent_name: "scoper"
      company_id: "IMC"                 # from .canon/memory/context-latest.md
      repository_id: "innermost"        # from .canon/memory/context-latest.md
      repo_ref: "canon-systems @ wave/0/canon-memory-v1 (local branch verified 2026-04-22)"
      prior_checkpoint: ".cursor/handoffs/canon-memory-v1/E0-T1/release-status.md (READY_TO_MERGE)"

    story:
      title: "Create backend/ monorepo skeleton with shared lib"   # verbatim backlog
      userValue: "Wave 0 downstream tasks (E0-T3 consolidation, E1/E2/E3 new services) need a stable monorepo layout with a shared lib so per-service packages can be added without re-litigating shape every time."
      acceptanceCriteria:
        # verbatim from docs/MEMORY-PLATFORM-BACKLOG.md E0-T2
        - "backend/{knowledge-api,knowledge-worker,memory-adapter,state-api,axon-service,synthesis,synthesis-web} directories exist with README placeholders and matching entry-point scaffolding."
        - "backend/shared/ exposes auth, ids, events modules consumable by every service package."
        - "Root pyproject/poetry/turbo (language-appropriate) builds the workspace cleanly."
        # scoper-added testable refinements (do not widen backlog intent):
        - "No canon-systems-v2 service code is moved into backend/ under this task; all service directories are stubs only (git history preservation is E0-T3)."
        - "backend/shared/ids.py exposes a callable `deterministic_id(*parts: str, prefix: str | None = None) -> str` implemented via hashlib.sha256 (per backlog §A)."
        - "backend/shared/events.py exposes a `CanonicalEvent` type + `to_dict`/`from_dict` round-trip matching backlog §C field names."
        - "backend/shared/auth.py exposes a stub `verify_caller(headers: Mapping[str, str]) -> AuthContext` signature raising NotImplementedError with a docstring pointing to E2-T2/E1-T2; no real auth logic in this task."
        - "Root README.md, CHANGELOG.md, and docs/SYSTEM-WORKFLOW.md are updated to reference the new backend/ layout (per backlog §G living-spec invariant)."
      done_signal:
        # verbatim from backlog
        - "Workspace build passes."
        - "tests/test_backend_layout.py asserts the expected directory tree."

    repository:
      primaryLanguages: ["Python 3.10+", "Markdown", "TOML"]
      testFramework: "pytest (canon-systems root tests/; pytest.ini has pythonpath=src)"
      build_tool: "setuptools (root) + per-service pyproject.toml; uv workspace declaration at root for orchestrated install"
      relevantFiles_read_only_for_context:
        - "docs/MEMORY-PLATFORM-BACKLOG.md"                 # §A (IDs), §C (events), §G (invariants), E0-T2 entry
        - "docs/MEMORY-PLATFORM-PLAN.md"
        - "docs/SYSTEM-WORKFLOW.md"
        - "docs/WAVE-0-AUDIT.md"                             # identifies Python/FastAPI/uvicorn precedent
        - "docs/DEPRECATIONS.md"
        - ".cursor/plans/canon_memory_platform_build_d21073e1.plan.md"
        - ".cursor/rules/memory-platform-build-discipline.mdc"
        - ".cursor/handoffs/canon-memory-v1/E0-T1/scoper.md"
        - ".cursor/handoffs/canon-memory-v1/E0-T1/cursor-pilot.md"
        - ".cursor/handoffs/canon-memory-v1/E0-T1/qa-gate.md"
        - "pyproject.toml"                                   # current root build config
        - "pytest.ini"
        - "README.md"
        - "CHANGELOG.md"
      reference_files_in_sibling_repo_readonly:
        - "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api/pyproject.toml"      # setuptools shape precedent
        - "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api/app/main.py"        # FastAPI entry precedent
        - "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-worker/README.md"
        - "/Users/edwardwalker/localwork/canon-systems-v2/services/memory-adapter/README.md"

    in_scope_paths_to_create:
      - "backend/README.md"                                     # top-level backend monorepo README
      - "backend/knowledge-api/README.md"
      - "backend/knowledge-api/pyproject.toml"
      - "backend/knowledge-api/app/__init__.py"
      - "backend/knowledge-api/app/main.py"
      - "backend/knowledge-worker/README.md"
      - "backend/knowledge-worker/pyproject.toml"
      - "backend/knowledge-worker/knowledge_worker/__init__.py"
      - "backend/knowledge-worker/knowledge_worker/main.py"
      - "backend/memory-adapter/README.md"
      - "backend/memory-adapter/pyproject.toml"
      - "backend/memory-adapter/memory_adapter/__init__.py"
      - "backend/memory-adapter/memory_adapter/main.py"
      - "backend/state-api/README.md"
      - "backend/state-api/pyproject.toml"
      - "backend/state-api/state_api/__init__.py"
      - "backend/state-api/state_api/main.py"
      - "backend/axon-service/README.md"
      - "backend/axon-service/pyproject.toml"
      - "backend/axon-service/axon_service/__init__.py"
      - "backend/axon-service/axon_service/main.py"
      - "backend/synthesis/README.md"
      - "backend/synthesis/pyproject.toml"
      - "backend/synthesis/synthesis/__init__.py"
      - "backend/synthesis/synthesis/main.py"
      - "backend/synthesis-web/README.md"                       # README-only; language TBD (E5-T4)
      - "backend/synthesis-web/.gitkeep"
      - "backend/shared/README.md"
      - "backend/shared/pyproject.toml"
      - "backend/shared/canon_backend_shared/__init__.py"
      - "backend/shared/canon_backend_shared/auth.py"
      - "backend/shared/canon_backend_shared/ids.py"
      - "backend/shared/canon_backend_shared/events.py"
      - "tests/test_backend_layout.py"
      - "scripts/backend/install-workspace.sh"                  # fallback installer if uv unavailable

    in_scope_paths_to_modify:
      - "pyproject.toml"                                        # add [tool.uv.workspace] members = ["backend/*"] (idempotent; does NOT change canon_systems package config)
      - "README.md"                                             # add short "backend/ monorepo" section referencing backend/README.md
      - "CHANGELOG.md"                                          # add entry under unreleased: "E0-T2: backend/ skeleton + shared lib"
      - "docs/SYSTEM-WORKFLOW.md"                               # add one-paragraph note in §1 or new §10 pointing to backend/ layout

    out_of_scope_paths:
      - "src/canon_systems/**"                                  # no CLI changes in this task
      - "infra/**"                                              # E0-T4
      - ".cursor/rules/memory-platform-build-discipline.mdc"    # hard-locked rule (read-only)
      - ".cursor/plans/canon_memory_platform_build_d21073e1.plan.md"  # plan file; markdown edits allowed only for orchestration, not for weakening
      - "docs/MEMORY-PLATFORM-BACKLOG.md"                       # do NOT rewrite backlog in this task
      - "docs/MEMORY-PLATFORM-PLAN.md"
      - "docs/WAVE-0-AUDIT.md"                                  # E0-T1 artifact; frozen
      - "docs/DEPRECATIONS.md"                                  # E0-T1 artifact; frozen
      - "docs/OBSIDIAN-MIND-CATALOGUE.md"                       # E0-T1 artifact; frozen
      - "Any file inside sibling repos (/Users/edwardwalker/localwork/canon-platform, canon-systems-v2, mempalace, obsidian-mind, temporal, total_recall)"
      - "Any git move/subtree/filter-repo operation importing real code from canon-systems-v2 (that is E0-T3 and MUST not be done here so git history preservation work is not pre-empted)"

    dependencies_and_prior_work:
      depends_on_task_ids: ["E0-T1"]
      prior_work_references:
        - {id: "E0_T1_scoper",          source: ".cursor/handoffs/canon-memory-v1/E0-T1/scoper.md",                relevance: "Establishes Wave 0 packet shape, IDs, DoR conventions reused here."}
        - {id: "E0_T1_cursor_pilot",    source: ".cursor/handoffs/canon-memory-v1/E0-T1/cursor-pilot.md",          relevance: "Pilot prompt shape this scoper expects cursor-pilot to mirror."}
        - {id: "wave0_audit",           source: "docs/WAVE-0-AUDIT.md",                                             relevance: "Confirms knowledge-api/worker/memory-adapter are Python 3.10+ FastAPI/uvicorn services; informs per-service scaffolding shape."}
        - {id: "backlog_section_A_ids", source: "docs/MEMORY-PLATFORM-BACKLOG.md §A",                               relevance: "Mandates deterministic_id via sha256(company_id|plan_id|task_id|...). Implemented in backend/shared/ids.py."}
        - {id: "backlog_section_C_evt", source: "docs/MEMORY-PLATFORM-BACKLOG.md §C",                               relevance: "Canonical event envelope spec. Reflected as CanonicalEvent in backend/shared/events.py."}
        - {id: "backlog_section_G",     source: "docs/MEMORY-PLATFORM-BACKLOG.md §G",                               relevance: "Living-spec invariant: README/CHANGELOG/SYSTEM-WORKFLOW must be updated alongside code."}
        - {id: "hard_lock_rule_s2",     source: ".cursor/rules/memory-platform-build-discipline.mdc §2",            relevance: "Non-markdown writes require scoper.md AND cursor-pilot.md on disk before implementer acts. This packet is half of that contract."}
        - {id: "v2_ka_pyproject",       source: "/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api/pyproject.toml", relevance: "Setuptools-per-service precedent used by real services that E0-T3 will move in."}
        - {id: "ctx_latest",            source: ".canon/memory/context-latest.md",                                  relevance: "Confirms company_id=IMC, repository_id=innermost for identifier consistency."}

    constraints:
      dependencies:
        - "No runtime dependency additions to the root pyproject (root stays as canon-systems CLI)."
        - "Per-service pyprojects MAY list FastAPI + uvicorn + pydantic as dependencies to match v2 precedent, but MUST NOT pin to versions that conflict with canon-systems-v2's services/<svc>/pyproject.toml (use the same >=/< ranges)."
        - "backend/shared MUST have zero runtime dependencies beyond the Python stdlib so every service can consume it without dependency-graph conflict."
      mustNotBreak:
        - "Existing src/canon_systems/** package layout, tests, and CLI (canon command) — no changes in this task."
        - "Existing pytest discovery (pytest.ini pythonpath=src). test_backend_layout.py MUST run under the current pytest config without extra plugins."
        - "Hard-lock rule §2 markdown-only-until-packets contract — this packet itself gates non-markdown writes."
        - "Existing KNOWLEDGE_API_URL / KNOWLEDGE_WORKER_URL / MEMORY_ADAPTER_URL resolution in src/canon_systems/shared.py (do not move or rename)."
      mode: "additive monorepo skeleton; per-service stubs only; no real service code or infra."

    entry_point_scaffolding_contract:
      fastapi_services:
        applies_to: ["knowledge-api", "knowledge-worker", "memory-adapter", "state-api", "axon-service", "synthesis"]
        module_layout: "backend/<slug>/<python_pkg>/main.py with `app = FastAPI(title=..., version='0.0.0-scaffold')` and a GET /healthz returning {'status': 'scaffold', 'service': '<slug>'}"
        python_pkg_naming:
          knowledge-api:    "app"                   # matches canon-systems-v2 precedent (services/knowledge-api/app)
          knowledge-worker: "knowledge_worker"
          memory-adapter:   "memory_adapter"
          state-api:        "state_api"
          axon-service:     "axon_service"
          synthesis:        "synthesis"
        pyproject_shape: "setuptools build backend; name = <slug>; version = '0.0.0'; dependencies = [fastapi, uvicorn, pydantic]; [tool.setuptools.packages.find] where = ['.'] include = ['<pkg>*']"
      readme_only_service:
        applies_to: ["synthesis-web"]
        reason: "E5-T4 decides Python vs JS/TS renderer; scaffolding that choice here would pre-empt a downstream task. README MUST state 'entry-point and language chosen in E5-T4; this directory is a reserved slot'."
        marker_file: "backend/synthesis-web/.gitkeep"

    shared_lib_contract:
      package_import_path: "canon_backend_shared"
      rationale: "Avoid collision with src/canon_systems shared.py and be unambiguous when used by backend/ services."
      modules:
        auth:
          signature: "def verify_caller(headers: Mapping[str, str]) -> AuthContext"
          behavior: "raise NotImplementedError('real auth lands in E2-T2 / E1-T2'); AuthContext is an empty @dataclass(slots=True) stub."
        ids:
          signature: "def deterministic_id(*parts: str, prefix: str | None = None) -> str"
          behavior: "hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest() prefixed by `<prefix>_` if provided, else raw hex. Covered by at least one unit test in tests/test_backend_layout.py."
        events:
          signature: "@dataclass CanonicalEvent with fields matching backlog §C; to_dict() + from_dict() class method; schema_version=1"
          behavior: "Pure data class; no network, no disk, no side effects. Covered by round-trip test in tests/test_backend_layout.py."

    workspace_build_contract:
      primary_proposal:
        tool: "uv workspace"
        root_edit: "Add [tool.uv.workspace] members = ['backend/*'] to root pyproject.toml (additive; canon-systems project section untouched)."
        build_command: "uv sync --all-packages   # or: uv pip install -e backend/shared && for d in backend/knowledge-api backend/knowledge-worker backend/memory-adapter backend/state-api backend/axon-service backend/synthesis; do uv pip install -e \"$d\"; done"
      fallback_proposal_if_uv_not_available:
        tool: "setuptools per service + shell script"
        script: "scripts/backend/install-workspace.sh — runs `pip install -e backend/shared` then `pip install -e backend/<svc>` for each Python service."
        build_command: "bash scripts/backend/install-workspace.sh"
      test_interpretation: "The done_signal 'Workspace build passes' is satisfied if either (a) `uv sync --all-packages` exits 0, or (b) `bash scripts/backend/install-workspace.sh` exits 0 — whichever the implementer ships. tests/test_backend_layout.py MUST import backend.shared modules (after install) to prove shared is installable."

    tests_to_write:
      - path: "tests/test_backend_layout.py"
        framework: "pytest"
        purpose: "Assert the directory tree, presence of READMEs, shape of shared lib, and importability of canon_backend_shared.{auth,ids,events}."
        assertions:
          - "Each of the seven service directories exists at `backend/<slug>/` and contains a non-empty README.md."
          - "Each Python service (six of seven) contains `pyproject.toml` and a `<python_pkg>/main.py` with a module-level `app` symbol attribute string 'FastAPI' or importable via ast (import-free check acceptable if install not run in CI-lite mode)."
          - "backend/synthesis-web/ contains README.md AND .gitkeep (language-TBD marker present)."
          - "backend/shared/canon_backend_shared/{auth,ids,events}.py all exist."
          - "`canon_backend_shared.ids.deterministic_id('a', 'b') == canon_backend_shared.ids.deterministic_id('a', 'b')` and `deterministic_id('a', 'b', prefix='evt').startswith('evt_')`."
          - "CanonicalEvent round-trip: `CanonicalEvent.from_dict(CanonicalEvent(**minimal).to_dict()) == CanonicalEvent(**minimal)` where minimal includes every backlog §C required field."
          - "Root pyproject.toml contains either `[tool.uv.workspace]` or references scripts/backend/install-workspace.sh."
        skip_conditions:
          - "If canon_backend_shared cannot be imported (workspace not installed), the import-dependent assertions MAY use importlib.util.find_spec or ast-based static inspection; they MUST NOT xfail silently."

    ac_traceability:
      - criterion: "backend/{knowledge-api,knowledge-worker,memory-adapter,state-api,axon-service,synthesis,synthesis-web} directories exist with README placeholders and matching entry-point scaffolding."
        implementation_targets:
          - "backend/knowledge-api/{README.md,pyproject.toml,app/main.py}"
          - "backend/knowledge-worker/{README.md,pyproject.toml,knowledge_worker/main.py}"
          - "backend/memory-adapter/{README.md,pyproject.toml,memory_adapter/main.py}"
          - "backend/state-api/{README.md,pyproject.toml,state_api/main.py}"
          - "backend/axon-service/{README.md,pyproject.toml,axon_service/main.py}"
          - "backend/synthesis/{README.md,pyproject.toml,synthesis/main.py}"
          - "backend/synthesis-web/{README.md,.gitkeep}"
        verification_tests:
          - "tests/test_backend_layout.py::test_seven_service_dirs_exist"
          - "tests/test_backend_layout.py::test_python_services_have_entrypoints"
          - "tests/test_backend_layout.py::test_synthesis_web_is_readme_only"
      - criterion: "backend/shared/ exposes auth, ids, events modules consumable by every service package."
        implementation_targets:
          - "backend/shared/canon_backend_shared/auth.py"
          - "backend/shared/canon_backend_shared/ids.py"
          - "backend/shared/canon_backend_shared/events.py"
          - "backend/shared/pyproject.toml"
        verification_tests:
          - "tests/test_backend_layout.py::test_shared_modules_importable"
          - "tests/test_backend_layout.py::test_deterministic_id_is_stable_and_supports_prefix"
          - "tests/test_backend_layout.py::test_canonical_event_roundtrip"
      - criterion: "Root pyproject/poetry/turbo (language-appropriate) builds the workspace cleanly."
        implementation_targets:
          - "pyproject.toml (root — [tool.uv.workspace] or equivalent)"
          - "scripts/backend/install-workspace.sh (fallback)"
        verification_tests:
          - "tests/test_backend_layout.py::test_workspace_declaration_or_script_present"
          - "done_signal manual: `uv sync --all-packages` OR `bash scripts/backend/install-workspace.sh` exits 0 in QA harness."

    risks_and_assumptions:
      assumptions:
        - "uv is available in the implementer/QA environment OR the fallback install script satisfies the workspace-build done_signal."
        - "Per-service setuptools pyproject with FastAPI/uvicorn/pydantic dependencies will not conflict with canon-systems CLI tooling because services live under backend/ and are installed separately."
        - "Creating backend/shared with import path `canon_backend_shared` avoids any risk of shadowing src/canon_systems/shared.py."
        - "E0-T3 will be responsible for git history preservation (subtree/filter-repo) when moving canon-systems-v2 services into the backend/ slots; this task creating the slots first is strictly additive and does not damage that future history work."
        - "synthesis-web being README-only in this task satisfies the AC 'with README placeholders and matching entry-point scaffolding' because the README explicitly records 'no entry-point yet, chosen in E5-T4' — this is the minimum-viable scaffolding for a directory whose language is not yet decided."
      openQuestions:
        - id: "OQ-1"
          question: "Workspace tool: uv workspace vs shell-script install vs leaving each service install-on-deploy (Dockerfile) only?"
          proposed_resolution: "Add `[tool.uv.workspace] members = ['backend/*']` to root pyproject AND ship `scripts/backend/install-workspace.sh` as a pip-only fallback. Implementer picks whichever passes CI; both are acceptable under AC3."
          blocking_for_this_task: false
        - id: "OQ-2"
          question: "synthesis-web: Python stub vs README-only vs JS/TS placeholder?"
          proposed_resolution: "README-only with `.gitkeep`, README explicitly states 'language + framework chosen in E5-T4'. Keeps E5-T4 unconstrained."
          blocking_for_this_task: false
        - id: "OQ-3"
          question: "Depth of backend/shared/auth stub — leave as NotImplementedError, or provide a no-op success stub?"
          proposed_resolution: "NotImplementedError with docstring pointing to E2-T2/E1-T2. A no-op success would silently authenticate calls in early integration tests, which is dangerous."
          blocking_for_this_task: false
        - id: "OQ-4"
          question: "Living-spec touch list: must docs/SYSTEM-WORKFLOW.md really be edited now?"
          proposed_resolution: "Yes — per backlog §G, introducing backend/ is a runtime-layout change. One paragraph in §1 (or a new §10) is sufficient."
          blocking_for_this_task: false
      not_open_questions:
        - "Whether to move real code from canon-systems-v2/services/* now — NO, that is E0-T3 verbatim."
        - "Whether to touch infra/ — NO, that is E0-T4."
        - "Whether to touch src/canon_systems/** — NO, this task is additive under backend/ only."

    scope_compliance:
      hard_lock_rule_sections_consulted: ["§1 chain order", "§2 packet-gated writes", "§3 pre-flight", "§4 packet persistence", "§9 per-task commit", "§10 wave-branch commit"]
      packet_persistence_expected:
        - ".cursor/handoffs/canon-memory-v1/E0-T2/scoper.md           (this file)"
        - ".cursor/handoffs/canon-memory-v1/E0-T2/cursor-pilot.md     (next phase)"
        - ".cursor/handoffs/canon-memory-v1/E0-T2/qa-gate.md          (after implementer)"
        - ".cursor/handoffs/canon-memory-v1/E0-T2/release-status.md   (after qa-gate PASS)"
      permitted_paths_added:
        - "backend/**"
        - "tests/test_backend_layout.py"
        - "scripts/backend/install-workspace.sh"
      permitted_paths_modified:
        - "pyproject.toml"
        - "README.md"
        - "CHANGELOG.md"
        - "docs/SYSTEM-WORKFLOW.md"
      prohibited_paths_touched:
        - "src/canon_systems/**"
        - "infra/**"
        - ".cursor/rules/memory-platform-build-discipline.mdc"
        - ".cursor/plans/canon_memory_platform_build_d21073e1.plan.md"
        - "docs/MEMORY-PLATFORM-BACKLOG.md"
        - "docs/MEMORY-PLATFORM-PLAN.md"
        - "docs/WAVE-0-AUDIT.md"
        - "docs/DEPRECATIONS.md"
        - "docs/OBSIDIAN-MIND-CATALOGUE.md"
        - "Any path inside sibling repos on this machine"
      git_history_preservation: "Not applicable to this task. E0-T3 handles git history for real service moves; E0-T2 creates empty slots only."

    dor_checklist:
      story_title:                  "pass"
      story_user_value:             "pass"
      acceptance_criteria_present:  "pass (3 backlog + 5 scoper refinements, all testable)"
      repo_primary_languages:       "pass"
      test_framework:               "pass (pytest)"
      constraints_dependencies:     "pass"
      open_questions_resolved:      "pass (4 OQs, all non-blocking with proposed resolutions)"
      prior_work_references:        "pass (9 refs: E0-T1 packets, backlog §A/§C/§G, hard-lock rule §2, v2 precedent, context-latest)"
      repo_ref_verification:        "pass (branch wave/0/canon-memory-v1 confirmed via `git branch --show-current`)"
      ac_traceability:              "pass (every AC has at least one implementation target and one verification test)"
      scope_compliance_block:       "pass (permitted/prohibited paths explicit)"
      living_spec_invariant:        "pass (README + CHANGELOG + SYSTEM-WORKFLOW covered)"
      scope_vs_next_task_boundary:  "pass (E0-T3 service moves explicitly out of scope)"

END_HANDOFF_TO_CURSOR_PILOT
```

**DEFINITION_OF_READY verdict: PASS.**
