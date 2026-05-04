# state-api

Operational-state plane for the Canon Memory Platform: DynamoDB-backed **checkpoints** and **leases** with REST endpoints. Items are stored **flat** in DynamoDB (TTL on numeric `lease_expires_at`); JSON responses follow backlog §B with a **nested `lease`** object (`acquired_at` / `expires_at` as **epoch seconds**). `GET /state/checkpoint` never inspects the lease and **never** returns `lease_token`.

## Configuration

| Variable | Meaning |
|----------|---------|
| `STATE_TABLE_NAME` | DynamoDB table name (e.g. `${project}-${environment}-canon-state`). If unset, `GET /healthz` returns **503 degraded**. |
| `AWS_REGION` | AWS region for boto3 (default `us-east-1`). |

## Lease token protocol (v1)

- Tokens are **server-generated UUIDv4** strings.
- They are **opaque** to clients and **not reconstructable** from scope or identity alone.
- Losing a token means waiting until **TTL expiry** on `lease_expires_at` (or obtaining a new lease after expiry) before another writer can claim the row.

## Canonical events

Successful `PUT /state/checkpoint` emits exactly one `checkpoint_write` **`CanonicalEvent`** (from `canon_backend_shared.events`, `schema_version=1`) with `X-Canon-Event-Id` mirroring `event_id`.

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

### `GET /state/checkpoint`

Query (all required): `company_id`, `repository_id`, `plan_id`, `task_id`, `workstream_id`.

- **200** — §B checkpoint JSON; `lease` nested from flat attrs; **no** `lease_token`.
- **404** — `{ "error": "not_found", "pk", "sk" }`.

```bash
curl -sS "$BASE/state/checkpoint?company_id=MJC&repository_id=marrow&plan_id=p1&task_id=E2-T2&workstream_id=ws1"
```

### `PUT /state/checkpoint`

Body: §B fields including `handoff_id`, `phase`, `phase_status`, optimistic `state_version` (expected), and `lease_token`. Requires a **live** lease (`lease_expires_at` &gt; now) and matching token. On success: `state_version` increments, `updated_at` set (RFC3339 Z), `last_event_id` set to the new event id, **`X-Canon-Event-Id`** returned.

**409** codes: `state_version_conflict`, `lease_required`, `lease_expired`, `lease_token_mismatch` (with `expected`/`actual` for version conflicts).

```bash
curl -sS -X PUT "$BASE/state/checkpoint" \
  -H 'Content-Type: application/json' \
  -d '{"company_id":"MJC","repository_id":"marrow","plan_id":"p1","task_id":"E2-T2","workstream_id":"ws1","handoff_id":"h1","phase":"implementer","phase_status":"pass","state_version":0,"lease_token":"<token>"}'
```

### `POST /state/lease/acquire`

Body: scope ids, `owner_agent_run_id`, `owner_actor_id`, `ttl_seconds` (1–3600).

- **200** — `{ lease_token, expires_at, acquired_at, owner_agent_run_id, owner_actor_id }`.
- **409** — `lease_held` (foreign live lease; **no** token leak).
- Same owner while lease is live: **idempotent** — same token, bumped `expires_at`.

```bash
curl -sS -X POST "$BASE/state/lease/acquire" \
  -H 'Content-Type: application/json' \
  -d '{"company_id":"MJC","repository_id":"marrow","plan_id":"p1","task_id":"E2-T2","workstream_id":"ws1","owner_agent_run_id":"run-1","owner_actor_id":"actor-1","ttl_seconds":300}'
```

### `POST /state/lease/renew`

Body: `scope_ids` (object with the five ids), `lease_token`, `ttl_seconds` (1–3600).

- **200** — `{ lease_token, expires_at }`.
- **409** — `lease_token_mismatch` or `lease_expired` (post-fail `GetItem` disambiguation).

```bash
curl -sS -X POST "$BASE/state/lease/renew" \
  -H 'Content-Type: application/json' \
  -d '{"scope_ids":{"company_id":"MJC","repository_id":"marrow","plan_id":"p1","task_id":"E2-T2","workstream_id":"ws1"},"lease_token":"<token>","ttl_seconds":600}'
```

### `POST /state/lease/release`

Body: `scope_ids`, `lease_token`. Clears all five `lease_*` attributes when the token matches. **No** canonical event in v1.

- **200** — `{ "released": true }`.
- **409** — `lease_token_mismatch`.

```bash
curl -sS -X POST "$BASE/state/lease/release" \
  -H 'Content-Type: application/json' \
  -d '{"scope_ids":{"company_id":"MJC","repository_id":"marrow","plan_id":"p1","task_id":"E2-T2","workstream_id":"ws1"},"lease_token":"<token>"}'
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
