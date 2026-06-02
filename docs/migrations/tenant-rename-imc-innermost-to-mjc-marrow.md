# Tenant rename: IMC / innermost → MJC / marrow (memory continuity)

**Secrets Manager** only tells the CLI *which URLs and tokens to use*. Historical
**Canon memory** is still keyed by `company_id` + `repository_id` inside each
backend. After you point Marrow at `MJC` / `marrow`, you must **migrate** those
stores (or you will see an “empty” tenant).

## 1. Canonical artifacts + orchestration (knowledge-api Postgres)

Captures and `canon ask` filter on `artifacts.scope_ids` (company) and
`artifacts.repo_ids` (repository). Related tables (`runs`, `work_items`) use
`scope_id` / `project_scope_id` + `repository_id`.

From a machine with DB connectivity and sqlalchemy + psycopg:

```bash
cd /path/to/canon-systems
export DATABASE_URL='postgresql+psycopg://USER:PASS@HOST:5432/DB'  # production knowledge DB

python3 scripts/migrate_knowledge_api_tenant.py          # dry-run: counts + sample
python3 scripts/migrate_knowledge_api_tenant.py --apply # writes + commit
```

Or use the same `POSTGRES_*` env vars as `backend/knowledge-api` instead of
`DATABASE_URL`.

## 2. Checkpoints / leases (state-api DynamoDB)

Items use `pk = "company_id#repository_id"`. Migrate after or during a quiet
window (active leases can be disrupted if writers are using old ids).

```bash
export AWS_PROFILE=…   # admin or sufficient DynamoDB access
export AWS_REGION=us-east-1
export STATE_TABLE_NAME=…   # e.g. dev/prod state table from your stack

python3 scripts/migrate_state_api_tenant.py
python3 scripts/migrate_state_api_tenant.py --apply
```

## 3. Axon graph (optional, if you use `canon graph` for this repo)

Axon metadata is DynamoDB `pk = company_id#repository_id`; snapshot objects use
`{company_id}/{repository_id}/…` in S3. There is no bundled script yet — extend
the state-api pattern (scan old `pk`, copy with new `pk`, fix S3 keys), or
**re-index** from git for `MJC` / `marrow` after cutover.

## 4. MemPalace on-disk layout (optional)

If the deployed `MEMPALACE_PATH` (or equivalent) embeds the old tenant in
directories, rename or symlink paths on the memory hosts so search still finds
prior wings/rooms. If MemPalace is global and not per-repo, you may skip this.

## 5. Cutover order (recommended dry-run)

1. Dry-run both migration scripts; review counts.
2. **Apply** knowledge-api migration (largest user-visible effect for `canon ask`).
3. **Apply** state-api migration (if you care about checkpoint history).
4. **Apply** Axon / MemPalace if applicable.
5. Marrow repo: `COMPANY_ID=MJC`, `REPOSITORY_ID=marrow`, secret
   `canon-memory-dev/memory-layer__mjc__marrow`, IAM `GetSecretValue`, then
   `canon doctor --fix-cache` and `canon e2e-check --agent`.

Rollback = restore Postgres from backup and restore DynamoDB from PITR / backup
taken before `--apply`, plus revert Secrets Manager JSON if you changed it.
