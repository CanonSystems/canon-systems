# Backend monorepo (`backend/`)

Python (and one reserved non-Python slot) services that back Canon’s memory
platform. Each subdirectory is an installable package or a documented
placeholder.

| Directory | Role |
|-----------|------|
| `shared/` | **`canon_backend_shared`** — IDs, canonical events, auth stub. |
| `knowledge-api/` | HTTP API for canonical knowledge (FastAPI scaffold). |
| `knowledge-worker/` | Async / worker surface (FastAPI scaffold). |
| `memory-adapter/` | Memory adapter (FastAPI scaffold). |
| `state-api/` | Checkpoints + leases (FastAPI scaffold). |
| `axon-service/` | Code graph (FastAPI scaffold). |
| `synthesis/` | Vault / synthesis generator (FastAPI scaffold). |
| `synthesis-web/` | Reserved UI slot; stack chosen in **E5-T4**. |

**Workspace install** (from repo root):

- `uv sync --all-packages`, or
- `bash scripts/backend/install-workspace.sh`

See [§C in the backlog](../docs/MEMORY-PLATFORM-BACKLOG.md) for the canonical
event envelope and [§A](../docs/MEMORY-PLATFORM-BACKLOG.md) for deterministic
IDs.
