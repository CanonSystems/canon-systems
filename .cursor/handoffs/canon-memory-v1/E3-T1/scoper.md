# E3-T1 — Scoper packet: Fork and deploy `backend/axon-service`

## SCOPE SUMMARY

Deliver a new **FastAPI** service under `backend/axon-service/` that ingests per-tenant graph snapshots (S3 object + DynamoDB metadata), serves **query** and **impact** reads with **path-scoped** `company_id` and `repository_id`, enforces a **bearer-token** auth shim, emits **CanonicalEvent**-shaped telemetry for graph operations, and ships a **Terraform** `axon-snapshots` module with **local validate** and **documented apply/import** (operator executes cloud apply). **Living-spec** updates stay **additive**; **infra layout tests** extend the **dynamodb-canon-state** pattern. **`canon memory-health`** already includes a **graph** row wired to **`AXON_SERVICE_URL`**; E3-T1 completes the **healthz contract** on the service side and adds **focused tests** for optional **graph** probe behavior where gaps remain.

---

## SCOPE PACKET

### Identifiers
- handoff_id: `handoff_20260422_wave3_canon_memory_v1_E3_T1`
- company_id: `IMC`
- repository_id: `innermost`
- Branch: `wave/3/canon-memory-v1` (tip `ef4e9e2`)

### Story

**title:** Fork and deploy `backend/axon-service`
**userValue:** Multi-tenant graph index plane (ingest + query + impact) with durable snapshots and merge-gate health alignment, without blocking on live AWS apply in CI.

**acceptanceCriteria** (24, testable):
1. POST `/axon/{company_id}/{repository_id}/index` accepts JSON body with `commit_sha` + graph payload; returns stable success response with identifiers for later reads.
2. Index persists snapshot bytes to S3 at key `{company_id}/{repository_id}/{commit_sha}.json.gz` (bucket via `AXON_S3_BUCKET`) using gzip.
3. Index writes DynamoDB metadata row: `pk=company_id#repository_id`, `sk=commit_sha`, attrs `uploaded_at`, `size_bytes`, `node_count`, `edge_count`.
4. GET `/axon/{company_id}/{repository_id}/query?q=&commit_sha=&limit=` returns JSON shortlist with `nodes`, `edges`, `scores`, `source_spans` (empty lists when no matches).
5. GET `/axon/{company_id}/{repository_id}/impact?symbol=&commit_sha=&depth=` returns upstream/downstream blast-radius JSON.
6. Handlers use only path-level `company_id`/`repository_id` for storage keys; body cannot override tenant scope.
7. Cross-tenant isolation: snapshot for (C1, R1) not returned when querying (C2, R1) or (C1, R2) for same commit_sha.
8. GET `/healthz` returns 200 JSON with `status` ∈ {ok, degraded} and `snapshots` (integer count or null) — suitable for `canon memory-health` classification.
9. Auth shim: index/query/impact require `Authorization: Bearer <token>` matching `AXON_SERVICE_TOKEN`; 401/403 on mismatch. `/healthz` unauthenticated.
10. Only `axon_service/storage.py` imports boto3.
11. Successful index emits `retrieval.graph.index` via CanonicalEvent on injectable EventEmitter.
12. Query emits `retrieval.graph.query`; impact emits `retrieval.graph.impact`; payload includes `company_id`, `repository_id`, `commit_sha`, operation-specific fields.
13. `infra/terraform/modules/axon-snapshots/` exists with `main.tf`, `variables.tf`, `outputs.tf`, `README.md`: S3 bucket + DynamoDB table (PAY_PER_REQUEST, PITR, deletion protection, pk/sk keys per brief).
14. Root terraform `main.tf` + `outputs.tf` wire the module additively (no reflow).
15. `infra/terraform/README.md` + `infra/README.md` append E3-T1 validate/plan/apply/import examples.
16. `tests/test_infra_layout.py` appends axon-snapshots module + root wiring assertions (mirror dynamodb-canon-state coverage).
17. `backend/axon-service/tests/` uses `moto[s3,dynamodb]` + TestClient; no live AWS.
18. Named tests: `test_post_index_persists_s3_and_dynamo`, `test_query_returns_shortlist_shape`, `test_impact_returns_blast_radius_shape`, `test_auth_rejects_missing_token`, `test_healthz_ok_shape`, `test_cross_tenant_isolation`, `test_event_emissions_logged_or_called`, `test_path_tenant_authoritative`.
19. CHANGELOG `[Unreleased] ### Added` gains top bullet for axon-service + module.
20. README additively documents axon-service + env vars (`AXON_SERVICE_URL`, `AXON_S3_BUCKET`, `AXON_SERVICE_TOKEN`).
21. `docs/SYSTEM-WORKFLOW.md` additively documents graph/axon probe path via `canon memory-health` + `AXON_SERVICE_URL`.
22. memory-health: AXON_SERVICE_URL documented; tests cover optional-not-configured vs required-unhealthy cases.
23. `backend/axon-service/README.md` states OIDC/Cognito explicitly deferred.
24. Forbidden: no edits under backend/state-api/**, backend/knowledge-api/**, .cursor/rules/**, .cursor/plans/**; no reflow-only edits; terraform artifacts not skipped.

### Repository
- primaryLanguages: Python, HCL
- testFramework: pytest
- relevantFiles: backend/state-api/** (peer), backend/shared/canon_backend_shared/events.py, src/canon_systems/memory_health.py, tests/test_memory_health.py, infra/terraform/modules/dynamodb-canon-state/**, infra/terraform/{main.tf,outputs.tf,README.md}, infra/README.md, tests/test_infra_layout.py, CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md

### Constraints
- dependencies: E1-T1 satisfied (memory-health graph row already wired)
- mustNotBreak: `canon memory-health` default required set (canonical, mempalace); graph stays optional unless `CANON_MEMORY_HEALTH_REQUIRED` includes graph
- discipline: cloud-apply waiver; additive living-spec; moto-only tests; single boto3 module; no reflow

### Prior work references
- peer:backend/state-api (E2-T2) — FastAPI layout + moto tests + storage boto3 gate + events.py CanonicalEvent emitter
- peer:infra/terraform/modules/dynamodb-canon-state (E2-T1) — module trio + PITR/deletion-protection pattern
- peer:src/canon_systems/memory_health.py (E1-T1) — graph backend → AXON_SERVICE_URL probe wiring

---

## AC traceability

| # | Criterion | Targets | Tests |
|---|---|---|---|
| 1 | POST index | axon_service/routers/index.py | tests/test_index.py::test_post_index_persists_s3_and_dynamo |
| 2 | S3 gzip key | storage.py, config.py | test_post_index_persists_s3_and_dynamo |
| 3 | DynamoDB meta row | storage.py, models.py | test_post_index_persists_s3_and_dynamo |
| 4 | Query shape | routers/query.py | tests/test_query.py::test_query_returns_shortlist_shape |
| 5 | Impact shape | routers/impact.py | tests/test_impact.py::test_impact_returns_blast_radius_shape |
| 6 | Path tenant scope | api.py | tests/test_index.py::test_path_tenant_authoritative |
| 7 | Cross-tenant isolation | storage.py, routers | tests/test_query.py::test_cross_tenant_isolation |
| 8 | /healthz shape | routers/health.py, main.py | tests/test_healthz.py::test_healthz_ok_shape |
| 9 | Bearer auth | auth.py, routers | tests/test_auth.py::test_auth_rejects_missing_token |
| 10 | boto3 isolated | package tree | code review + test conftest gate |
| 11-12 | Canonical events | events.py, routers | tests/test_events.py::test_event_emissions_logged_or_called |
| 13 | Terraform module | modules/axon-snapshots/** | tests/test_infra_layout.py::test_axon_snapshots_module_files_exist |
| 14 | Root wiring | infra/terraform/{main.tf,outputs.tf} | tests/test_infra_layout.py::test_root_wires_axon_snapshots_module |
| 15 | Infra README E3-T1 | infra/{terraform/,}README.md | tests/test_infra_layout.py::test_infra_readme_e3t1_section |
| 17 | moto tests | tests/conftest.py | pytest green |
| 19-21 | Living-spec additive | CHANGELOG/README/SYSTEM-WORKFLOW | qa-gate diff review |
| 22 | memory-health graph | tests/test_memory_health.py | tests/test_memory_health.py::test_graph_optional_not_configured_exit_ok + test_graph_required_unhealthy_when_unset |
| 23 | OIDC deferred note | backend/axon-service/README.md | qa-gate doc scan |
| 24 | Forbidden surfaces | (process) | git diff allowlist |

---

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: E3-T1 adds backend/axon-service (FastAPI) for per-(company_id, repository_id) graph snapshot ingest and query/impact reads with S3+DynamoDB persistence (moto-tested), bearer auth, CanonicalEvent emissions, a new infra/terraform/modules/axon-snapshots stack with documented apply/import under the cloud-apply waiver, infra layout test extensions, and additive living-spec updates; canon memory-health already maps graph to AXON_SERVICE_URL—complete /healthz and any missing optional-graph probe tests.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260422_wave3_canon_memory_v1_E3_T1"
      company_id: "IMC"
      repository_id: "innermost"
    story:
      title: "Fork and deploy backend/axon-service"
      acceptanceCriteria:
        - "POST /axon/{company_id}/{repository_id}/index accepts commit_sha and graph payload and returns a stable success response."
        - "Index writes S3 object {company_id}/{repository_id}/{commit_sha}.json.gz under AXON_S3_BUCKET with gzip compression."
        - "Index writes DynamoDB metadata pk=company_id#repository_id sk=commit_sha with uploaded_at, size_bytes, node_count, edge_count."
        - "GET /axon/{company_id}/{repository_id}/query?q=&commit_sha=&limit= returns JSON with nodes, edges, scores, source spans."
        - "GET /axon/{company_id}/{repository_id}/impact?symbol=&commit_sha=&depth= returns upstream/downstream blast-radius JSON."
        - "Handlers scope storage only to path company_id and repository_id; body cannot override tenant."
        - "Cross-tenant reads do not leak another tenant's snapshot for the same commit_sha."
        - "GET /healthz returns JSON with status ok|degraded and snapshots count or null."
        - "index/query/impact require Bearer token matching AXON_SERVICE_TOKEN; healthz unauthenticated."
        - "Only axon_service/storage.py imports boto3."
        - "Index emits retrieval.graph.index via injectable EventEmitter using CanonicalEvent."
        - "Query emits retrieval.graph.query; impact emits retrieval.graph.impact with payload containing company_id, repository_id, commit_sha."
        - "infra/terraform/modules/axon-snapshots exists with S3 + DynamoDB (PAY_PER_REQUEST, PITR, deletion protection, pk/sk per brief) and module README."
        - "infra/terraform main.tf and outputs.tf wire axon-snapshots module with additive outputs."
        - "infra/terraform/README.md and infra/README.md add E3-T1 validate/apply/import documentation."
        - "tests/test_infra_layout.py appends axon-snapshots module and root wiring assertions."
        - "backend/axon-service tests use moto[s3,dynamodb] and TestClient; no live AWS."
        - "Tests include test_post_index_persists_s3_and_dynamo, test_query_returns_shortlist_shape, test_impact_returns_blast_radius_shape, test_auth_rejects_missing_token, test_healthz_ok_shape, test_cross_tenant_isolation, test_event_emissions_logged_or_called."
        - "CHANGELOG.md [Unreleased] ### Added gains top bullet for axon-service and module."
        - "README.md additively documents axon-service and AXON_SERVICE_URL, AXON_S3_BUCKET, AXON_SERVICE_TOKEN."
        - "docs/SYSTEM-WORKFLOW.md additively documents graph/axon and memory-health AXON_SERVICE_URL."
        - "memory-health tests: test_graph_optional_not_configured_exit_ok and test_graph_required_unhealthy_when_unset cover optional vs required graph."
        - "backend/axon-service/README.md states OIDC deferred."
        - "Do not modify backend/state-api/**, backend/knowledge-api/**, .cursor/rules/**, .cursor/plans/**; no reflow-only edits; terraform artifacts not skipped."
    constraints:
      dependencies: ["E1-T1"]
      mustNotBreak: ["canon memory-health default required backends (canonical, mempalace)", "optional graph backend unless CANON_MEMORY_HEALTH_REQUIRED includes graph"]
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
