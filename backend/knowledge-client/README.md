# knowledge-client

Thin Python client SDK for Canon Systems v2 internal services.

It intentionally stays small:
- `KnowledgeApiClient` for artifact create/list/get against `knowledge-api`
- `KnowledgeApiClient` body retrieval for canonical markdown/content reads
- `MemoryAdapterClient` for search against `memory-adapter`
- `KnowledgeWorkerClient` for projection jobs against `knowledge-worker`
- `VaultSyncClient` for Obsidian vault projection jobs against `vault-sync`
- `TemporalRuntimeClient` for Temporal-ready workflow-start intent queries against `temporal-runtime`
- `KnowledgeApiClient` dispatch transition calls for optimistic starter-safe run acquisition
- `CanonSystemsClient` as a convenience bundle when you need the full local platform

## Install

```bash
pip install -e libs/knowledge-client
```

## Example

```python
from knowledge_client import (
    ArtifactType,
    BatchVaultProjectionRequest,
    BodyRef,
    CanonSystemsClient,
    CreateArtifactRequest,
    MemoryCaptureRequest,
    MemoryProjectionRequest,
    MemorySearchRequest,
    WorkflowIntentQuery,
    VaultProjectionRequest,
    Visibility,
)

client = CanonSystemsClient(
    knowledge_api_url="http://localhost:8000",
    memory_adapter_url="http://localhost:8010",
    knowledge_worker_url="http://localhost:8091",
    vault_sync_url="http://localhost:8092",
    temporal_runtime_url="http://localhost:8093",
    actor_id="edward",
    actor_groups=["team-a"],
)

artifact = client.knowledge_api.create_artifact(
    CreateArtifactRequest(
        artifact_id="art_123",
        version_id="ver_123",
        artifact_type=ArtifactType.CURRENT_STATE_NOTE,
        title="Current State",
        visibility=Visibility.TEAM,
        source_system="manual",
        created_by="edward",
        body_ref=BodyRef(storage="s3", bucket="canon", key="artifacts/art_123/ver_123.md"),
        body_text="# current state",
    )
)

body = client.knowledge_api.get_artifact_body("art_123")

hits = client.memory_adapter.search(MemorySearchRequest(query="auth flow"))

projection = client.knowledge_worker.project_memory(
    MemoryProjectionRequest(
        query="why postgres",
        artifact_id="art_proj_1",
        version_id="ver_proj_1",
        title="Projected Memory",
        created_by="edward",
    )
)

capture = client.knowledge_worker.capture_memory(
    MemoryCaptureRequest(
        artifact_id="art_capture_1",
        version_id="ver_capture_1",
        title="Short Session Memory",
        transcript_text="We narrowed orchestration runtime to Temporal.",
        created_by="edward",
    )
)

vault_projection = client.vault_sync.project_artifact(
    VaultProjectionRequest(
        artifact_id="art_123",
        vault_name="team-shared",
    )
)

batch_projection = client.vault_sync.project_current_truth(
    BatchVaultProjectionRequest(
        scope_id="familyone",
        vault_name="team-shared",
    )
)

start_intents = client.temporal_runtime.list_start_intents(
    WorkflowIntentQuery(
        task_queue="tq_context_hydration",
        claim_dispatch=True,
        claimer_id="svc_temporal_runtime",
    )
)
```

The client uses `httpx` and Pydantic models for typed request/response handling.
