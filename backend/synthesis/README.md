# synthesis

Scaffold for server-side vault generation and related HTTP entrypoints. This
package is FastAPI + `/healthz` only; full synthesis behavior is scheduled in
later epics (see backlog Wave 5).

See [docs/VAULT-LAYOUT.md](../../docs/VAULT-LAYOUT.md) for the vault projection contract (schema_version: 1).

## Infra requirements (operator-applied)

Depends on the **unwired** `infra/terraform/modules/synthesis-vault/` module (Precedent §1 — `cloud_execution_deferred`).

| Variable | Description |
| --- | --- |
| `SYNTHESIS_S3_BUCKET` | Target bucket (module output `bucket_name`). |
| `AWS_REGION` | AWS region (default `us-east-1`). |
| `STATE_API_BASE_URL` | Reserved for Wave-5-waived `StateApiEventSource`; no-op in CI. |

CI uses `InMemoryEventSource` plus a `moto` S3 idempotence test. No live AWS credentials required.
Tests are in `synthesis_tests/` (not `tests/`) to avoid a Pytest `tests.conftest` import collision with `backend/state-api/tests` when running the repository-wide suite.
