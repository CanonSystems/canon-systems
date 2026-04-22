# memory-adapter

`memory-adapter` is the first thin service boundary around MemPalace for Canon Systems v2.

It is intentionally small. The MVP role is to provide a typed, permissions-aware interface that orchestration code can call without knowing MemPalace internals.

## What it does now

- defines typed search request and response models
- wraps MemPalace-style search semantics
- supports an injected backend for tests or alternate implementations
- can call `mempalace.searcher.search_memories` when MemPalace is available on `PYTHONPATH`
- returns structured unavailability responses instead of crashing when the backend is missing
- exposes a minimal FastAPI surface for health and search

## What it does not do yet

- no database
- no persistence
- no Slack integration
- no canonical write-back
- no permissions policy enforcement beyond the adapter boundary

## MVP role

The orchestration layer will eventually use this service to:

1. search historical memory before asking the user a question
2. attach relevant memory hits to work items and artifacts
3. keep short sessions viable by restoring prior context quickly

## Environment

The service can be configured with:

- `CANON_ENV`
- `MEMORY_ADAPTER_DEFAULT_LIMIT`
- `MEMPALACE_ENABLED`
- `MEMPALACE_PATH`

If `MEMPALACE_PATH` is unset, the adapter stays importable but reports that no backend is configured.

## Local development

The package is laid out as a normal Python project under `src/memory_adapter`.
It can be installed in editable mode and run locally:

```bash
uvicorn memory_adapter.main:app --reload
```
