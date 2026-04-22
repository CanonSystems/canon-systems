# E0-T3 migration notes (canon-systems-v2 → backend/)

## Git history

**Waived.** Per-task decision: `canon-systems-v2` records a single squashed commit
for these paths (`ebecb91` — *Initial import of canon-systems-v2 workspace*), so
preserving history via subtree/filter-repo was deferred in favor of a verbatim
file copy plus this forensic mapping. No `git subtree` / `git filter-repo` was
used on this repo.

**Upstream read-only root:** `/Users/edwardwalker/localwork/canon-systems-v2` @ `ebecb91`.

## Exclusions (not copied)

The following glob patterns were excluded from rsync:

- `**/__pycache__/**`
- `**/*.pyc`
- `**/*.egg-info/**`
- `tests/**` (all v2 per-service tests; deferred per E0-T3 scope)
- `app/**` under `knowledge-worker` only (empty placeholder dirs in v2; must not be imported)

## Scaffold removals

These E0-T2 placeholder paths were **deleted** after adopting v2 layout:

- `backend/knowledge-worker/knowledge_worker/__init__.py`
- `backend/knowledge-worker/knowledge_worker/main.py`
- (entire `backend/knowledge-worker/knowledge_worker/` directory removed)
- `backend/memory-adapter/memory_adapter/__init__.py`
- `backend/memory-adapter/memory_adapter/main.py`
- (entire `backend/memory-adapter/memory_adapter/` directory removed)

## Pyproject edits

For `knowledge-api`, `knowledge-worker`, and `memory-adapter`, `[project].dependencies`
in `pyproject.toml` matches v2 version/range pins **except**:

- `canon-backend-shared` (no version pin; workspace editable install).
- `knowledge-schema` and `knowledge-policy` on `knowledge-api` only: v2 relied on
  `app/bootstrap.py` adding `libs/*/src` to `sys.path`; this monorepo copies those
  packages under `backend/` and lists them as dependencies so `pip install -e`
  resolves imports without a sibling `libs/` tree.
- `knowledge-client` and `memory-adapter` on `knowledge-worker`: v2 resolved these
  via workspace layout; explicit deps + `build-services.sh` install order satisfy
  `knowledge_worker/__init__.py` → `service` import chain.

`app/bootstrap.py` was updated to prefer `backend/knowledge-{schema,policy}/src`
and still fall back to `libs/...` for older checkouts.

## Per-file source → target

### `knowledge-api`

| Source (v2) | Target (this repo) |
|---|---|
| `canon-systems-v2/services/knowledge-api/app/__init__.py` | `backend/knowledge-api/app/__init__.py` |
| `canon-systems-v2/services/knowledge-api/app/api/__init__.py` | `backend/knowledge-api/app/api/__init__.py` |
| `canon-systems-v2/services/knowledge-api/app/api/router.py` | `backend/knowledge-api/app/api/router.py` |
| `canon-systems-v2/services/knowledge-api/app/api/routers/__init__.py` | `backend/knowledge-api/app/api/routers/__init__.py` |
| `canon-systems-v2/services/knowledge-api/app/api/routers/artifacts.py` | `backend/knowledge-api/app/api/routers/artifacts.py` |
| `canon-systems-v2/services/knowledge-api/app/api/routers/health.py` | `backend/knowledge-api/app/api/routers/health.py` |
| `canon-systems-v2/services/knowledge-api/app/api/routers/runs.py` | `backend/knowledge-api/app/api/routers/runs.py` |
| `canon-systems-v2/services/knowledge-api/app/api/routers/work_items.py` | `backend/knowledge-api/app/api/routers/work_items.py` |
| `canon-systems-v2/services/knowledge-api/app/auth/__init__.py` | `backend/knowledge-api/app/auth/__init__.py` |
| `canon-systems-v2/services/knowledge-api/app/auth/dependencies.py` | `backend/knowledge-api/app/auth/dependencies.py` |
| `canon-systems-v2/services/knowledge-api/app/auth/models.py` | `backend/knowledge-api/app/auth/models.py` |
| `canon-systems-v2/services/knowledge-api/app/bootstrap.py` | `backend/knowledge-api/app/bootstrap.py` |
| `canon-systems-v2/services/knowledge-api/app/config.py` | `backend/knowledge-api/app/config.py` |
| `canon-systems-v2/services/knowledge-api/app/db/__init__.py` | `backend/knowledge-api/app/db/__init__.py` |
| `canon-systems-v2/services/knowledge-api/app/db/base.py` | `backend/knowledge-api/app/db/base.py` |
| `canon-systems-v2/services/knowledge-api/app/db/init_db.py` | `backend/knowledge-api/app/db/init_db.py` |
| `canon-systems-v2/services/knowledge-api/app/db/session.py` | `backend/knowledge-api/app/db/session.py` |
| `canon-systems-v2/services/knowledge-api/app/main.py` | `backend/knowledge-api/app/main.py` |
| `canon-systems-v2/services/knowledge-api/app/models/__init__.py` | `backend/knowledge-api/app/models/__init__.py` |
| `canon-systems-v2/services/knowledge-api/app/models/artifact_api.py` | `backend/knowledge-api/app/models/artifact_api.py` |
| `canon-systems-v2/services/knowledge-api/app/models/artifact_db.py` | `backend/knowledge-api/app/models/artifact_db.py` |
| `canon-systems-v2/services/knowledge-api/app/models/run_api.py` | `backend/knowledge-api/app/models/run_api.py` |
| `canon-systems-v2/services/knowledge-api/app/models/run_db.py` | `backend/knowledge-api/app/models/run_db.py` |
| `canon-systems-v2/services/knowledge-api/app/models/work_item_api.py` | `backend/knowledge-api/app/models/work_item_api.py` |
| `canon-systems-v2/services/knowledge-api/app/models/work_item_db.py` | `backend/knowledge-api/app/models/work_item_db.py` |
| `canon-systems-v2/services/knowledge-api/app/policies/__init__.py` | `backend/knowledge-api/app/policies/__init__.py` |
| `canon-systems-v2/services/knowledge-api/app/policies/artifacts.py` | `backend/knowledge-api/app/policies/artifacts.py` |
| `canon-systems-v2/services/knowledge-api/app/services/__init__.py` | `backend/knowledge-api/app/services/__init__.py` |
| `canon-systems-v2/services/knowledge-api/app/services/artifacts.py` | `backend/knowledge-api/app/services/artifacts.py` |
| `canon-systems-v2/services/knowledge-api/app/services/runs.py` | `backend/knowledge-api/app/services/runs.py` |
| `canon-systems-v2/services/knowledge-api/app/services/work_items.py` | `backend/knowledge-api/app/services/work_items.py` |
| `canon-systems-v2/services/knowledge-api/app/storage/__init__.py` | `backend/knowledge-api/app/storage/__init__.py` |
| `canon-systems-v2/services/knowledge-api/app/storage/s3.py` | `backend/knowledge-api/app/storage/s3.py` |
| `canon-systems-v2/services/knowledge-api/alembic/env.py` | `backend/knowledge-api/alembic/env.py` |
| `canon-systems-v2/services/knowledge-api/alembic/script.py.mako` | `backend/knowledge-api/alembic/script.py.mako` |
| `canon-systems-v2/services/knowledge-api/alembic/versions/20260410_0001_initial_artifacts.py` | `backend/knowledge-api/alembic/versions/20260410_0001_initial_artifacts.py` |
| `canon-systems-v2/services/knowledge-api/alembic/versions/20260411_0002_run_dispatch_metadata.py` | `backend/knowledge-api/alembic/versions/20260411_0002_run_dispatch_metadata.py` |
| `canon-systems-v2/services/knowledge-api/alembic/versions/20260411_0003_run_claim_metadata.py` | `backend/knowledge-api/alembic/versions/20260411_0003_run_claim_metadata.py` |
| `canon-systems-v2/services/knowledge-api/alembic/versions/20260411_0004_run_launch_scope_metadata.py` | `backend/knowledge-api/alembic/versions/20260411_0004_run_launch_scope_metadata.py` |
| `canon-systems-v2/services/knowledge-api/alembic/versions/20260414_0005_run_jira_task_linkage.py` | `backend/knowledge-api/alembic/versions/20260414_0005_run_jira_task_linkage.py` |
| `canon-systems-v2/services/knowledge-api/alembic/versions/README.md` | `backend/knowledge-api/alembic/versions/README.md` |
| `canon-systems-v2/services/knowledge-api/alembic.ini` | `backend/knowledge-api/alembic.ini` |
| `canon-systems-v2/services/knowledge-api/README.md` | `backend/knowledge-api/README.md` |
| `canon-systems-v2/services/knowledge-api/pyproject.toml` | `backend/knowledge-api/pyproject.toml` *(+ `canon-backend-shared`, `knowledge-schema`, `knowledge-policy`)* |

### `knowledge-worker`

| Source (v2) | Target (this repo) |
|---|---|
| `canon-systems-v2/services/knowledge-worker/src/knowledge_worker/__init__.py` | `backend/knowledge-worker/src/knowledge_worker/__init__.py` |
| `canon-systems-v2/services/knowledge-worker/src/knowledge_worker/api/__init__.py` | `backend/knowledge-worker/src/knowledge_worker/api/__init__.py` |
| `canon-systems-v2/services/knowledge-worker/src/knowledge_worker/api/router.py` | `backend/knowledge-worker/src/knowledge_worker/api/router.py` |
| `canon-systems-v2/services/knowledge-worker/src/knowledge_worker/config.py` | `backend/knowledge-worker/src/knowledge_worker/config.py` |
| `canon-systems-v2/services/knowledge-worker/src/knowledge_worker/main.py` | `backend/knowledge-worker/src/knowledge_worker/main.py` |
| `canon-systems-v2/services/knowledge-worker/src/knowledge_worker/models.py` | `backend/knowledge-worker/src/knowledge_worker/models.py` |
| `canon-systems-v2/services/knowledge-worker/src/knowledge_worker/projections/__init__.py` | `backend/knowledge-worker/src/knowledge_worker/projections/__init__.py` |
| `canon-systems-v2/services/knowledge-worker/src/knowledge_worker/projections/memory_capture_to_markdown.py` | `backend/knowledge-worker/src/knowledge_worker/projections/memory_capture_to_markdown.py` |
| `canon-systems-v2/services/knowledge-worker/src/knowledge_worker/projections/memory_to_markdown.py` | `backend/knowledge-worker/src/knowledge_worker/projections/memory_to_markdown.py` |
| `canon-systems-v2/services/knowledge-worker/src/knowledge_worker/service.py` | `backend/knowledge-worker/src/knowledge_worker/service.py` |
| `canon-systems-v2/services/knowledge-worker/README.md` | `backend/knowledge-worker/README.md` |
| `canon-systems-v2/services/knowledge-worker/pyproject.toml` | `backend/knowledge-worker/pyproject.toml` *(+ `canon-backend-shared`, `knowledge-client`, `memory-adapter`)* |

### `memory-adapter`

| Source (v2) | Target (this repo) |
|---|---|
| `canon-systems-v2/services/memory-adapter/src/memory_adapter/__init__.py` | `backend/memory-adapter/src/memory_adapter/__init__.py` |
| `canon-systems-v2/services/memory-adapter/src/memory_adapter/adapters/__init__.py` | `backend/memory-adapter/src/memory_adapter/adapters/__init__.py` |
| `canon-systems-v2/services/memory-adapter/src/memory_adapter/adapters/mempalace.py` | `backend/memory-adapter/src/memory_adapter/adapters/mempalace.py` |
| `canon-systems-v2/services/memory-adapter/src/memory_adapter/api/__init__.py` | `backend/memory-adapter/src/memory_adapter/api/__init__.py` |
| `canon-systems-v2/services/memory-adapter/src/memory_adapter/api/router.py` | `backend/memory-adapter/src/memory_adapter/api/router.py` |
| `canon-systems-v2/services/memory-adapter/src/memory_adapter/config.py` | `backend/memory-adapter/src/memory_adapter/config.py` |
| `canon-systems-v2/services/memory-adapter/src/memory_adapter/main.py` | `backend/memory-adapter/src/memory_adapter/main.py` |
| `canon-systems-v2/services/memory-adapter/src/memory_adapter/models.py` | `backend/memory-adapter/src/memory_adapter/models.py` |
| `canon-systems-v2/services/memory-adapter/src/memory_adapter/service.py` | `backend/memory-adapter/src/memory_adapter/service.py` |
| `canon-systems-v2/services/memory-adapter/README.md` | `backend/memory-adapter/README.md` |
| `canon-systems-v2/services/memory-adapter/pyproject.toml` | `backend/memory-adapter/pyproject.toml` *(+ `canon-backend-shared`)* |

### `knowledge-schema` (library)

Copied from `canon-systems-v2/libs/knowledge-schema/` → `backend/knowledge-schema/`
(same exclusions as above). Declared dependency of `knowledge-api`.

| Source (v2) | Target (this repo) |
|---|---|
| `canon-systems-v2/libs/knowledge-schema/src/knowledge_schema/**` | `backend/knowledge-schema/src/knowledge_schema/**` |
| `canon-systems-v2/libs/knowledge-schema/README.md` | `backend/knowledge-schema/README.md` |
| `canon-systems-v2/libs/knowledge-schema/pyproject.toml` | `backend/knowledge-schema/pyproject.toml` |

### `knowledge-policy` (library)

Copied from `canon-systems-v2/libs/knowledge-policy/` → `backend/knowledge-policy/`.
Declared dependency of `knowledge-api`.

| Source (v2) | Target (this repo) |
|---|---|
| `canon-systems-v2/libs/knowledge-policy/src/knowledge_policy/**` | `backend/knowledge-policy/src/knowledge_policy/**` |
| `canon-systems-v2/libs/knowledge-policy/README.md` | `backend/knowledge-policy/README.md` |
| `canon-systems-v2/libs/knowledge-policy/pyproject.toml` | `backend/knowledge-policy/pyproject.toml` |

### `knowledge-client` (library)

Copied from `canon-systems-v2/libs/knowledge-client/` → `backend/knowledge-client/`.
Declared dependency of `knowledge-worker`.

| Source (v2) | Target (this repo) |
|---|---|
| `canon-systems-v2/libs/knowledge-client/src/knowledge_client/**` | `backend/knowledge-client/src/knowledge_client/**` |
| `canon-systems-v2/libs/knowledge-client/README.md` | `backend/knowledge-client/README.md` |
| `canon-systems-v2/libs/knowledge-client/pyproject.toml` | `backend/knowledge-client/pyproject.toml` |

