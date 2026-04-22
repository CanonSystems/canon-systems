# `backend/shared`

Python package **`canon_backend_shared`**: common types and helpers for every
service under `backend/`. It is stdlib-only so services can depend on it
without inflating the shared dependency graph.

Install with the root workspace tools (`uv sync --all-packages` or
`bash scripts/backend/install-workspace.sh`).

Modules:

- `canon_backend_shared.auth` — caller verification stub (real auth in E2-T2 / E1-T2).
- `canon_backend_shared.ids` — `deterministic_id` (SHA-256 over joined parts; backlog §A).
- `canon_backend_shared.events` — `CanonicalEvent` envelope (backlog §C).
