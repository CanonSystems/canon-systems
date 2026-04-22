# knowledge-worker

Background job service for canonical backend support.

Phase 1 responsibilities:

- projection job scaffolding
- reconciliation job scaffolding
- ingest job scaffolding
- async maintenance tasks

Current implemented slice:

- a first memory-backed projection workflow
- render memory hits into compact markdown
- create canonical artifacts from memory results via injected or HTTP clients
- capture short-session transcripts and distilled outputs into canonical memory artifacts

This is the first job path that ties:

- `memory-adapter`
- `knowledge-api`
- canonical artifact creation

Current service surface:

- `GET /healthz`
- `POST /jobs/project-memory`
- `POST /jobs/capture-memory`
