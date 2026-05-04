# state-api

Operational-state plane for the Canon Memory Platform: DynamoDB-backed **checkpoints** and **leases**, a separate DynamoDB-backed **run ledger** for durable readiness/run records, plus **S3 packet/evidence archive** uploads (`POST /state/archive`), exposed as REST endpoints. Checkpoint items are stored **flat** in the canon-state table (TTL on numeric `lease_expires_at`); JSON responses follow backlog §B with a **nested `lease`** object (`acquired_at` / `expires_at` as **epoch seconds**). `GET /state/checkpoint` never inspects the lease and **never** returns `lease_token`.

**Boundaries:** checkpoint/lease rows are **mutable** and participate in optimistic concurrency + lease tokens. The **run ledger** uses a **different** DynamoDB table and partition/sort key shape (`#run_ledger` suffix on `pk`); it never reads or writes `lease_*` fields. **Packet archive** persists object bytes in S3; ledger rows may reference archive metadata (URI, key, digest, kind) only—never `body_base64` or inline packet text.

## Configuration

| Variable | Meaning |
|----------|---------|
| `STATE_TABLE_NAME` | DynamoDB table name (e.g. `${project}-${environment}-canon-state`). If unset, `GET /healthz` returns **503 degraded**. |
| `STATE_RUN_LEDGER_TABLE_NAME` | DynamoDB table for run-ledger rows (e.g. `${project}-${environment}-canon-run-ledger`). If unset or empty, run-ledger routes return **503** `run_ledger_table_unset`. Does not affect checkpoint health (`GET /healthz` still keys off `STATE_TABLE_NAME` only). |
| `AWS_REGION` | AWS region for boto3 (default `us-east-1`). |
| `STATE_ARTIFACT_BUCKET` | S3 bucket for packet/evidence archive writes (`POST /state/archive`). If unset, archive uploads return **503** `artifact_bucket_unset`. |
| `STATE_ARCHIVE_KEY_PREFIX` | Logical prefix for archive keys (default `canon/packets`). Each object key is still content-addressed by SHA-256. |

## Lease token protocol (v1)

- Tokens are **server-generated UUIDv4** strings.
- They are **opaque** to clients and **not reconstructable** from scope or identity alone.
- Losing a token means waiting until **TTL expiry** on `lease_expires_at` (or obtaining a new lease after expiry) before another writer can claim the row.

## Canonical events

Successful `PUT /state/checkpoint` emits exactly one `checkpoint_write` **`CanonicalEvent`** (from `canon_backend_shared.events`, `schema_version=1`) with `X-Canon-Event-Id` mirroring `event_id`.

Successful `POST /state/archive` emits exactly one **`packet_archived`** event with the same envelope rules; payload carries archive metadata only (S3 URI/key, hashes, kinds, scope ids)—never raw packet bodies.

- **`EventEmitter`**: `Callable[[CanonicalEvent], None]`, exposed as FastAPI dependency `get_event_emitter`.
- **Default sink**: one JSON line per event via `logging.getLogger("state_api.events").info(...)`.
- **Pluggability**: override `get_event_emitter` in tests or future wiring; a later **Wave-6** upgrade can replace the logger with a bus/SQS/Kinesis sink without changing routers.

## Endpoints

### `GET /healthz`

- **200** — `{ "status": "ok", "service": "state-api", "table": "<name>" }` when `STATE_TABLE_NAME` is set.
- **503** — `{ "status": "degraded", "reason": "state_table_name_unset" }` when unset.

```bash
curl -sS "$BASE/healthz"
```

### `POST /state/archive`

JSON body includes tenant scope (`company_id`, `repository_id`, `plan_id`, `task_id`, `workstream_id`, `handoff_id`), `phase`, `artifact_kind`, `source_label`, `content_type`, `body_base64`, `content_sha256` (must match server-side digest of decoded bytes), optional `agent_run_id` / `actor_id` / `outcome` / `status` / `evidence_subtype`.

- **200** — Archive record (`schema_version=1`) including `s3_bucket`, `s3_key`, `s3_uri`, optional `s3_version_id` when bucket versioning is enabled.
- **400** — `archive_validation_error`, `archive_sha256_mismatch`, or `archive_body_decode_failed`.
- **503** — `artifact_bucket_unset` when `STATE_ARTIFACT_BUCKET` is empty.
- **502** — `s3_put_failed` on boto3 errors.

Sets **`X-Canon-Event-Id`** for the emitted `packet_archived` event.

Prefer **`canon packet-archive`** (repo-root CLI) for uploads from workstations; integration examples live in `backend/state-api/tests/test_packet_archive.py`.

### `PUT /state/run-ledger`

JSON body: versioned run-ledger record (`schema_version=1`)—tenant scope (`company_id`, `repository_id`), `plan_id`, `task_id`, `workstream_id`, `handoff_id`, `ledger_run_id`, `phase`, `phase_status`, timestamps, optional `archive_refs` (metadata only), `evidence_refs`, `validation_outcomes`, `commits`, `pull_request`, `deployment`, `agent_run_id` / `actor_id`, `source_event_ids`, etc. Validation uses `canon_backend_shared.run_ledger.validate_run_ledger_record`; archive snapshots must not include body fields.

- **200** — Stored or idempotent replay (same `ledger_run_id` and equivalent payload returns the existing row).
- **400** — `run_ledger_validation_error` or invalid query parameters on GET.
- **409** — `run_ledger_id_conflict` when the same `ledger_run_id` exists with a different payload.
- **503** — `run_ledger_table_unset` when `STATE_RUN_LEDGER_TABLE_NAME` is not configured.

Workstation helper: **`canon run-ledger`** (`--record-file` / `--record-json`, optional `--merge-archive-json`, `--dry-run` or `--state-api-url`).

### `GET /state/run-ledger`

Query (required): `company_id`, `repository_id`, `plan_id`, `task_id`, `workstream_id`. Optional: `ledger_run_id` (single row), `handoff_id` (filter), `limit` (1–200, default 50).

- **200** — Either `{ "ledger_run_id", "record" }` when `ledger_run_id` is set, or `{ "items", "count" }` for prefix query.
- **404** — `not_found` when `ledger_run_id` does not match.
- **503** — table unset (same as PUT).

**Read-only contract:** **`GET`** never writes ledger rows and does **not** touch checkpoint items or S3 artifact objects. Clients such as **`canon readiness check`** (workstation **`canon-systems`**) only consume this endpoint for diagnostics; readiness **does not** require a dedicated mutating **`/state/readiness`** route.

### `GET /state/checkpoint`

Query (all required): `company_id`, `repository_id`, `plan_id`, `task_id`, `workstream_id`.

- **200** — §B checkpoint JSON; `lease` nested from flat attrs; **no** `lease_token`.
- **404** — `{ "error": "not_found", "pk", "sk" }`.

```bash
curl -sS "$BASE/state/checkpoint?company_id=IMC&repository_id=innermost&plan_id=p1&task_id=E2-T2&workstream_id=ws1"
```

### `PUT /state/checkpoint`

Body: §B fields including `handoff_id`, `phase`, `phase_status`, optimistic `state_version` (expected), and `lease_token`. Requires a **live** lease (`lease_expires_at` &gt; now) and matching token. On success: `state_version` increments, `updated_at` set (RFC3339 Z), `last_event_id` set to the new event id, **`X-Canon-Event-Id`** returned.

**409** codes: `state_version_conflict`, `lease_required`, `lease_expired`, `lease_token_mismatch` (with `expected`/`actual` for version conflicts).

```bash
curl -sS -X PUT "$BASE/state/checkpoint" \
  -H 'Content-Type: application/json' \
  -d '{"company_id":"IMC","repository_id":"innermost","plan_id":"p1","task_id":"E2-T2","workstream_id":"ws1","handoff_id":"h1","phase":"implementer","phase_status":"pass","state_version":0,"lease_token":"<token>"}'
```

### `POST /state/lease/acquire`

Body: scope ids, `owner_agent_run_id`, `owner_actor_id`, `ttl_seconds` (1–3600).

- **200** — `{ lease_token, expires_at, acquired_at, owner_agent_run_id, owner_actor_id }`.
- **409** — `lease_held` (foreign live lease; **no** token leak).
- Same owner while lease is live: **idempotent** — same token, bumped `expires_at`.

```bash
curl -sS -X POST "$BASE/state/lease/acquire" \
  -H 'Content-Type: application/json' \
  -d '{"company_id":"IMC","repository_id":"innermost","plan_id":"p1","task_id":"E2-T2","workstream_id":"ws1","owner_agent_run_id":"run-1","owner_actor_id":"actor-1","ttl_seconds":300}'
```

### `POST /state/lease/renew`

Body: `scope_ids` (object with the five ids), `lease_token`, `ttl_seconds` (1–3600).

- **200** — `{ lease_token, expires_at }`.
- **409** — `lease_token_mismatch` or `lease_expired` (post-fail `GetItem` disambiguation).

```bash
curl -sS -X POST "$BASE/state/lease/renew" \
  -H 'Content-Type: application/json' \
  -d '{"scope_ids":{"company_id":"IMC","repository_id":"innermost","plan_id":"p1","task_id":"E2-T2","workstream_id":"ws1"},"lease_token":"<token>","ttl_seconds":600}'
```

### `POST /state/lease/release`

Body: `scope_ids`, `lease_token`. Clears all five `lease_*` attributes when the token matches. **No** canonical event in v1.

- **200** — `{ "released": true }`.
- **409** — `lease_token_mismatch`.

```bash
curl -sS -X POST "$BASE/state/lease/release" \
  -H 'Content-Type: application/json' \
  -d '{"scope_ids":{"company_id":"IMC","repository_id":"innermost","plan_id":"p1","task_id":"E2-T2","workstream_id":"ws1"},"lease_token":"<token>"}'
```

## Run / dev

```bash
pip install -e ../shared -e '.[test]'
uvicorn state_api.main:app --reload --port 8088
```

## Tests (offline)

Uses **moto** `mock_aws` and `httpx` **TestClient** (no AWS calls).

```bash
cd backend/state-api && pip install -e ../shared -e '.[test]' && pytest -q
```

Repo-root `pytest` does not install optional test extras; tests that need moto **skip** unless `moto` is installed (CI smoke uses the minimal env; run the command above for full coverage).

Additional coverage: `tests/test_run_ledger.py` and `tests/test_run_ledger_cli.py` at repo root (shared schema + CLI with mocked HTTP). This package's **`tests/test_run_ledger.py`** exercises `PUT`/`GET` with moto against both canon-state and run-ledger tables.
