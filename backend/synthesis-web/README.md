# synthesis-web

Read-only FastAPI service that **server-renders HTML** over the E5-T2 S3 Obsidian vault layout (Wave 5 / E5-T4). Tenant scope uses **8-character hex** `company_shorthash` and `repo_shorthash` in URLs only (never raw `company_id` / `repository_id`).

## Routes

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/healthz` | Liveness JSON |
| `GET` | `/` | Vault-of-vaults HTML index |
| `GET` | `/v/{c}/{r}/` | Vault home (plans, `_index`, links to graph + search) |
| `GET` | `/v/{c}/{r}/{page_path}` | Markdown page → HTML with backlinks |
| `GET` | `/v/{c}/{r}/_graph` | Deterministic JSON graph |
| `GET` | `/v/{c}/{r}/_search?q=...&limit=N` | JSON substring search (cap 100) |

## Configuration

- `SYNTHESIS_WEB_BUCKET` — S3 bucket (default `synthesis-web-bucket`)
- `SYNTHESIS_WEB_PREFIX` — Key prefix for vault roots (default `vault`)

Objects are read with **GET** / **HEAD** only; metadata `content-hash` drives **ETag** and an in-process LRU (`ContentHashCache`).

## Markdown

Rendering uses **markdown-it-py** in CommonMark mode with `html=False` (no raw HTML pass-through). Wikilinks `[[plan:id]]`, `[[task:id]]`, `[[event:id]]` resolve to internal `/v/...` URLs when the target key exists.

## Tests

Tests live in **`synthesis_web_tests/`** (not `tests/`) so the repo-wide pytest run does not collide with `backend/state-api/tests/` or the root `tests/` package (same precedent as `backend/synthesis/synthesis_tests/`).

```bash
pip install -e 'backend/synthesis-web[test]'
pytest backend/synthesis-web/synthesis_web_tests -q
```

## Infra (deferred)

An unwired Terraform stub lives under [`infra/terraform/modules/synthesis-web/`](../infra/terraform/modules/synthesis-web/) (Precedent §1 `cloud_execution_deferred` — not referenced from root `infra/terraform/main.tf`).

## Design spike: SSR over rebuild-on-publish

**Chosen: request-time SSR** (Option A) with per-key caching keyed on S3 `content-hash` metadata. The vault is already content-addressed; SSR reflects publisher state immediately, avoids a second static build step on every E5-T7 publish, and lets backlink/graph/search logic evolve without re-publishing every object.

**Rejected: rebuild-on-publish** (Option B) would couple renderer changes to full vault rewrites, duplicate storage, and duplicate work already covered by idempotent publish.

AWS Lambda entry uses **Mangum** (`synthesis_web.main.handler`).
