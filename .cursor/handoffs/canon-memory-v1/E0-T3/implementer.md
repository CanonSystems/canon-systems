HANDOFF_TO_QA
  handoff_id: "canon-memory-v1"
  task_id: "E0-T3"
  branch: "wave/0/canon-memory-v1"
  changed_files:
    created:
      - "docs/E0-T3-MIGRATION-NOTES.md"
      - "scripts/backend/build-services.sh"
      - "backend/knowledge-api/alembic.ini"
      - "backend/knowledge-api/alembic/**"
      - "backend/knowledge-api/app/api/**"
      - "backend/knowledge-api/app/auth/**"
      - "backend/knowledge-api/app/bootstrap.py"
      - "backend/knowledge-api/app/config.py"
      - "backend/knowledge-api/app/db/**"
      - "backend/knowledge-api/app/models/**"
      - "backend/knowledge-api/app/policies/**"
      - "backend/knowledge-api/app/services/**"
      - "backend/knowledge-api/app/storage/**"
      - "backend/knowledge-worker/src/knowledge_worker/**"
      - "backend/memory-adapter/src/memory_adapter/**"
      - "backend/knowledge-schema/**"
      - "backend/knowledge-policy/**"
      - "backend/knowledge-client/**"
    modified:
      - ".gitignore"
      - "README.md"
      - "CHANGELOG.md"
      - "docs/SYSTEM-WORKFLOW.md"
      - "tests/test_backend_layout.py"
      - "backend/knowledge-api/README.md"
      - "backend/knowledge-api/pyproject.toml"
      - "backend/knowledge-api/app/__init__.py"
      - "backend/knowledge-api/app/main.py"
      - "backend/knowledge-api/app/bootstrap.py"
      - "backend/knowledge-worker/README.md"
      - "backend/knowledge-worker/pyproject.toml"
      - "backend/memory-adapter/README.md"
      - "backend/memory-adapter/pyproject.toml"
    deleted:
      - "backend/knowledge-worker/knowledge_worker/__init__.py"
      - "backend/knowledge-worker/knowledge_worker/main.py"
      - "backend/memory-adapter/memory_adapter/__init__.py"
      - "backend/memory-adapter/memory_adapter/main.py"
  how_to_run_workspace_build:
    command: "bash scripts/backend/build-services.sh"
    exit_code: 0
    summary: "Installs backend/shared, knowledge-schema, knowledge-policy, knowledge-client, memory-adapter (prereqs), then the six leaf services with pip install -e; import-smokes `<pkg>.main.app` via python3-or-python; completed successfully in this environment (~20s)."
  how_to_run_tests:
    command: "pytest tests/test_backend_layout.py -v"
    summary: "24 passed, 0 failed, 0 skipped"
  acceptance_criteria_covered:
    - "Real v2 knowledge-api tree (app + alembic + alembic.ini), exclusions honored; canon-backend-shared + schema/policy deps; bootstrap paths for backend/libs"
    - "knowledge-worker + memory-adapter src-layout; flat scaffolds removed; canon-backend-shared; worker deps memory-adapter + knowledge-client"
    - "scripts/backend/build-services.sh: set -euo pipefail, chmod +x, shared then prereqs then six leaf services, import smoke each leaf"
    - "docs/E0-T3-MIGRATION-NOTES.md with ebecb91, waiver, exclusions, per-file tables, scaffold deletes, lib copies"
    - "tests/test_backend_layout.py: PYTHON_SERVICES dict by main path; E0-T2 assertions preserved; five new E0-T3 tests"
    - "README, CHANGELOG Unreleased, SYSTEM-WORKFLOW §10 updated; no v2/infra/root pyproject/pytest/src/canon_systems edits"
  summary: "Consolidated the three services from read-only canon-systems-v2 into backend/ with migration notes (history waived at ebecb91). Added v2 libraries under backend/ and explicit pyproject dependencies plus build-script install order so knowledge-api and knowledge-worker import-smokes pass without a sibling libs/ tree. Ignored *.egg-info/ repo-wide after local pip produced backend egg-info dirs."
  decisions:
    - "build-services.sh resolves PYTHON_CMD as python3 if present, else python (macOS often lacks python on PATH)."
    - "Copied libs/knowledge-schema, knowledge-policy, knowledge-client from v2 into backend/; knowledge-api depends on schema+policy; knowledge-worker depends on knowledge-client+memory-adapter; script installs prereqs before the six-leaf loop."
    - "knowledge-api app/bootstrap.py: prefer backend/knowledge-{schema,policy}/src, retain libs/ fallback."
    - ".gitignore: added *.egg-info/ so local editable installs do not surface spurious untracked metadata."
  next_actions:
    - "Parent agent: stage/commit on wave/0/canon-memory-v1 per discipline rule §9 (implementer did not commit)."
    - "E0-T4/E0-T5: optional CI workflow wiring + integration smoke; consider uv/pip consistency in CI images."
  open_questions: []
END_HANDOFF_TO_QA
