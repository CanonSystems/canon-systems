# axon-service

FastAPI service for the **graph retrieval plane** (canon “Axon”): ingest per-tenant code-graph snapshots, store them in S3 (gzip JSON) with metadata in DynamoDB, and serve **query** and **impact** reads scoped by path parameters `company_id` and `repository_id`.

**Authentication:** `Authorization: Bearer <token>` on `/axon/...` routes; the token must match `AXON_SERVICE_TOKEN`. **`/healthz`** is unauthenticated (for `canon memory-health` and load balancers).

**OIDC / Cognito:** explicit integration is **deferred** to a later task; the Bearer shim is the supported contract for this wave.

## Endpoints

| Method | Path | Auth |
| --- | --- | --- |
| GET | `/healthz` | no |
| POST | `/axon/{company_id}/{repository_id}/index` | Bearer |
| GET | `/axon/{company_id}/{repository_id}/reindex-status` | Bearer |
| GET | `/axon/{company_id}/{repository_id}/query` | Bearer |
| GET | `/axon/{company_id}/{repository_id}/impact` | Bearer |

### Indexing invariant

Writes flow only through POST `/index` (invoked by `canon graph index` pre-push or CI). Query/impact endpoints are pure RPC reads and MUST NOT trigger indexing side-effects.

## Environment (pydantic-settings)

| Env var | Default (dev) | Purpose |
| --- | --- | --- |
| `AXON_S3_BUCKET` | `axon-snapshots-dev` | S3 bucket for snapshot objects |
| `AXON_META_TABLE_NAME` | `axon-snapshots-meta-dev` | DynamoDB metadata table |
| `AXON_SERVICE_TOKEN` | `dev-token` | Bearer token value |
| `AXON_AWS_REGION` | `us-east-1` | AWS region for boto3 clients |

`canon memory-health` uses **`AXON_SERVICE_URL`** (repository root / `.canon` env) as the **base URL** for the **graph** backend; the probe calls `{base}/healthz`.

## Local run

```bash
cd backend/axon-service
pip install -e '.[test]'
uvicorn axon_service.main:app --host 0.0.0.0 --port 8100
```

## Tests

```bash
cd backend/axon-service
pytest -q axon_service_tests/
```

Tests use **moto** (S3 + DynamoDB); no live AWS calls.

## Terraform

Snapshot storage is provisioned by [`infra/terraform/modules/axon-snapshots/`](../../infra/terraform/modules/axon-snapshots/) (operator `terraform apply`; see module README and root `infra/terraform/README.md`).
