# knowledge-api

Canonical API service.

**Co-install:** `app.main` mounts `memory_adapter.api.router.search_router` so `POST /memory/search` is available on the same base URL as the canonical API (for stacks without a separate memory-adapter ECS service). Install `backend/memory-adapter` before this package (`scripts/backend/build-services.sh` order).

Phase 1 responsibilities:

- artifact CRUD
- versioning
- permissions enforcement
- scope and repository lookup
- run and event recording
- filtered artifact listing for current-truth projections
- durable orchestration dispatch metadata for future Temporal workflows

Suggested implementation:

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic

Minimal local run target:

```bash
uvicorn app.main:app --reload --app-dir services/knowledge-api
```

Local schema bootstrap:

```bash
PYTHONPATH=libs/knowledge-schema/src:libs/knowledge-policy/src:services/knowledge-api \
python3 services/knowledge-api/app/db/init_db.py
```

Migration path:

```bash
cd services/knowledge-api
PYTHONPATH=../../libs/knowledge-schema/src:../../libs/knowledge-policy/src:. alembic upgrade head
```

Optional body upload path:

- `CreateArtifactRequest` and `CreateArtifactVersionRequest` accept `body_text`
- when provided, the API writes the body to the configured S3-compatible object store before recording the version metadata

Current body retrieval path:

- `GET /api/v1/artifacts/{artifact_id}/body`
- `GET /api/v1/artifacts/{artifact_id}/versions/{version_id}/body`

Current artifact filtering path:

- `GET /api/v1/artifacts?artifact_type=...&status=...&visibility=...&scope_id=...&repo_id=...&work_item_id=...`

Current run dispatch path:

- `POST /api/v1/runs/{run_id}/dispatch`
- `POST /api/v1/runs/{run_id}/dispatch/transition`
- `GET /api/v1/runs/summaries`
- `GET /api/v1/runs/summaries/recent-scope-launches`

Current claim-safe dispatch fields:

- `dispatch_status`
- `claimed_by`
- `claimed_at`
