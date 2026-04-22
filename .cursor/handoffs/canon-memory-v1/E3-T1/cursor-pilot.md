# E3-T1 Cursor-Pilot Packet

**Task:** Fork and deploy `backend/axon-service`
**Branch:** `wave/3/canon-memory-v1` (tip ef4e9e2)

---

```
CURSOR_PILOT_PROMPT

ROLE: Additive backend + infra + tests implementer. FastAPI + boto3 service scaffold with S3 + DynamoDB persistence (moto-tested). Terraform module + additive living-spec.

TASK (E3-T1): Stand up backend/axon-service/ as a multi-tenant graph-index service (POST /axon/{company_id}/{repository_id}/index, GET /.../query, GET /.../impact, GET /healthz) with bearer-token auth, CanonicalEvent emissions, S3 + DynamoDB persistence. Ship infra/terraform/modules/axon-snapshots Terraform module with local `terraform validate` + documented apply/import. Extend tests/test_infra_layout.py with assertions for the new module. Living-spec additive updates to CHANGELOG, README, SYSTEM-WORKFLOW.

REPOSITORY:
- Workdir: /Users/edwardwalker/localwork/canon-systems
- Branch: wave/3/canon-memory-v1 (verify with `git rev-parse HEAD` → ef4e9e2...)
- Scope packet: .cursor/handoffs/canon-memory-v1/E3-T1/scoper.md
- Peer patterns to mirror exactly:
  * backend/state-api/{pyproject.toml, state_api/{main.py, api.py, config.py, models.py, storage.py, events.py}, tests/conftest.py}
  * backend/shared/canon_backend_shared/events.py (CanonicalEvent dataclass — DO NOT edit; import it)
  * infra/terraform/modules/dynamodb-canon-state/{main.tf,variables.tf,outputs.tf,README.md}
  * tests/test_infra_layout.py (append-only new tests)

REASONING (directory layout to create):

backend/axon-service/
  pyproject.toml           # deps: boto3, canon-backend-shared, fastapi, uvicorn, pydantic, pydantic-settings; test: pytest, moto[s3,dynamodb], httpx
  README.md                # purpose, endpoints, env vars, wire examples, OIDC deferred note
  axon_service/
    __init__.py            # empty
    main.py                # FastAPI app factory; include routers; /healthz registered at root (unauth)
    api.py                 # APIRouter aggregator for /axon routes (guarded by Bearer auth)
    config.py              # pydantic-settings Settings: s3_bucket (AXON_S3_BUCKET), meta_table_name (AXON_META_TABLE_NAME), aws_region (AWS_REGION default us-east-1), service_token (AXON_SERVICE_TOKEN)
    models.py              # Pydantic: IndexRequest (commit_sha, nodes, edges, optional metadata dict), IndexResponse (commit_sha, company_id, repository_id, snapshot_key, uploaded_at, node_count, edge_count), QueryResponse (nodes, edges, scores, source_spans), ImpactResponse (upstream, downstream, symbol, depth), HealthResponse (status, snapshots)
    storage.py             # THE ONLY FILE THAT IMPORTS boto3. class AxonStore(s3_bucket, meta_table_name, region): put_snapshot(gzip bytes + meta row), get_snapshot_meta(company_id, repository_id, commit_sha) -> Optional[dict], list_snapshots_count() -> int, get_snapshot_body(key) -> Optional[bytes]
    auth.py                # FastAPI Depends-style Bearer shim: raises HTTPException 401 if missing, 403 if mismatch; read token from settings
    events.py              # EventEmitter type + default_emitter (logs JSON via logger 'axon_service.events'); helpers emit_index/emit_query/emit_impact that construct CanonicalEvent
    routers/
      __init__.py
      health.py            # GET /healthz (unauth) — returns {status: "ok"|"degraded", snapshots: int|None}. Degraded if AxonStore construction fails (wrap in try/except; return degraded + null count). No auth dependency.
      index.py             # POST /axon/{company_id}/{repository_id}/index  (Bearer required)
      query.py             # GET /axon/{company_id}/{repository_id}/query   (Bearer required)
      impact.py            # GET /axon/{company_id}/{repository_id}/impact  (Bearer required)
  tests/
    __init__.py
    conftest.py            # fixtures: moto mock_aws; s3_bucket + dynamodb_meta_table creation; client fixture with FastAPI dependency overrides; captured_events fixture
    test_healthz.py        # test_healthz_ok_shape + degraded fallback
    test_auth.py           # test_auth_rejects_missing_token, test_auth_rejects_wrong_token, test_auth_accepts_valid_token
    test_index.py          # test_post_index_persists_s3_and_dynamo, test_path_tenant_authoritative (body tenant ignored), test_index_400_on_missing_commit_sha
    test_query.py          # test_query_returns_shortlist_shape, test_cross_tenant_isolation
    test_impact.py         # test_impact_returns_blast_radius_shape
    test_events.py         # test_event_emissions_logged_or_called (captured_events verifies three event_types)

infra/terraform/modules/axon-snapshots/
  main.tf                  # aws_s3_bucket "snapshots" (name "${var.name_prefix}-axon-snapshots") + aws_s3_bucket_versioning (enabled) + aws_s3_bucket_server_side_encryption_configuration (AES256) + aws_s3_bucket_public_access_block (all true) + aws_dynamodb_table "meta" (PAY_PER_REQUEST, pk hash, sk range, PITR, deletion_protection=true, SSE aws-owned)
  variables.tf             # name_prefix (string, required)
  outputs.tf               # snapshots_bucket_name, snapshots_bucket_arn, meta_table_name, meta_table_arn
  README.md                # purpose, inputs, outputs, key schema, waiver note

infra/terraform/main.tf              — append `module "axon_snapshots" { source = "./modules/axon-snapshots" name_prefix = var.name_prefix }` (ADDITIVE; no reflow)
infra/terraform/outputs.tf           — append 4 root outputs: snapshots_bucket_name / _arn + meta_table_name / _arn wired from module.axon_snapshots
infra/terraform/README.md            — append "## E3-T1 — axon-snapshots module" section with `terraform apply` and `terraform import module.axon_snapshots.aws_s3_bucket.snapshots <bucket>` + `module.axon_snapshots.aws_dynamodb_table.meta <table>` examples
infra/README.md                      — append one bullet about the axon-snapshots module

tests/test_infra_layout.py           — append (≥6 new asserts):
    test_axon_snapshots_module_files_exist: verifies modules/axon-snapshots/{main,variables,outputs}.tf + README.md
    test_axon_snapshots_module_declares_s3_and_dynamodb: grep main.tf for `aws_s3_bucket`, `aws_dynamodb_table`, `PAY_PER_REQUEST`, `point_in_time_recovery`, `deletion_protection_enabled`
    test_axon_snapshots_module_exposes_expected_outputs: outputs.tf contains snapshots_bucket_name, snapshots_bucket_arn, meta_table_name, meta_table_arn
    test_root_wires_axon_snapshots_module: infra/terraform/main.tf has `module "axon_snapshots"` and `source = "./modules/axon-snapshots"`
    test_root_outputs_expose_axon_snapshots: infra/terraform/outputs.tf contains the four axon outputs
    test_infra_readme_e3t1_section: infra/terraform/README.md contains "E3-T1" and "axon-snapshots"

tests/test_memory_health.py          — append two tests:
    test_graph_optional_not_configured_exit_ok: unset AXON_SERVICE_URL; default required only canonical+mempalace; memory_health run should not fail on graph absence (exit 0 when canonical+mempalace healthy OR degraded as today; focus: graph entry present with configured=false without tripping failure).
    test_graph_required_unhealthy_when_unset: CANON_MEMORY_HEALTH_REQUIRED="canonical,mempalace,graph"; AXON_SERVICE_URL unset; run should fail (non-zero exit or failed summary) with an error referencing graph / AXON_SERVICE_URL.

CHANGELOG.md — prepend new bullet at TOP of [Unreleased] ### Added:
  "E3-T1: backend/axon-service (FastAPI) — multi-tenant graph-index service (POST /index, GET /query, GET /impact, GET /healthz) with S3 snapshot + DynamoDB metadata persistence, Bearer auth shim, canonical retrieval.graph.* events; infra/terraform/modules/axon-snapshots module; memory-health graph probe backed by AXON_SERVICE_URL."

README.md — additive:
  - Under backend services section, add `backend/axon-service` line with brief description + env vars (AXON_SERVICE_URL, AXON_S3_BUCKET, AXON_META_TABLE_NAME, AXON_SERVICE_TOKEN).
  - In memory-health row of the `canon …` commands table, add mention that graph probe uses AXON_SERVICE_URL (one in-place cell update).

docs/SYSTEM-WORKFLOW.md §6 or nearest retrieval section — additive bullet:
  "Graph retrieval plane: `backend/axon-service` exposes /axon/{company}/{repo}/{index,query,impact} and /healthz; `canon memory-health` probes the graph backend via AXON_SERVICE_URL; cloud apply of infra/terraform/modules/axon-snapshots is operator-run."

OUTPUT FORMAT:
- Emit HANDOFF_TO_QA with files_changed list, verification commands, and AC→test mapping for all 24 ACs.

STOP CONDITIONS:
- `pytest -q` exits 0 (expect ≥241 + new tests).
- `cd backend/axon-service && pip install -e '.[test]' && pytest -q` exits 0 (service-local suite green).
- `cd infra/terraform && terraform validate` exits 0 (if terraform binary available locally; otherwise mark as waived with `terraform fmt -check` proxy).
- `SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh` exits 0.
- No forbidden-surface edits:
    backend/state-api/**, backend/knowledge-api/**, backend/shared/** (read-only import only),
    .cursor/rules/**, .cursor/plans/**,
    src/canon_systems/cli.py (no new CLI subcommand yet — E3-T3),
    src/canon_systems/templates/** (E3-T4 concern),
    existing tests bodies (append-only).

DO NOT:
- Commit or push.
- Add live AWS calls in tests.
- Skip terraform artifacts or the S3 bucket module.
- Touch backend/state-api/** or knowledge-api/** or shared/events.py.
- Reflow README.md or CHANGELOG.md existing content.

END_CURSOR_PILOT_PROMPT
```
