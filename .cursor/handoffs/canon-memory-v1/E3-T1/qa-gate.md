# E3-T1 — QA gate (behavioral verification)

**handoff_id:** `handoff_20260422_wave3_canon_memory_v1_E3_T1`  
**repo:** `/Users/edwardwalker/localwork/canon-systems`  
**branch:** `wave/3/canon-memory-v1`

## Commands executed (this run)

| Step | Command | Result |
| --- | --- | --- |
| 1 | `pytest -q` (repo root) | **261 passed** |
| 2 | `SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh` | **exit 0** |
| 3 | `cd backend/axon-service && pip install -e '.[test]'; pytest -q axon_service_tests/` | **12 passed** |
| 4 | `terraform -chdir=infra/terraform init -backend=false; terraform -chdir=infra/terraform validate` | **Success** |
| 5 | `grep` boto3 in `backend/axon-service/axon_service/` | **only** `storage.py` has `import boto3` |
| 6 | `git diff --name-only` + `git status --porcelain` | No forbidden paths (see AC-24) |
| 7 | `canon capture` (optional) | Invoked; returned `http=500` (non-blocking for local verification) |

**CanonicalEvent:** `backend/axon-service/axon_service/events.py::make_graph_event` constructs `CanonicalEvent` with all fields required by `backend/shared/canon_backend_shared/events.py` (`schema_version` through `payload`).

**AC-10 note:** `axon_service/` package imports boto3 only in `storage.py`. `axon_service_tests/conftest.py` and `test_index.py` import boto3 for moto / assertions; matches implementer “production gate on storage.”

**AC-17 note:** Scoper text references `backend/axon-service/tests/`; actual package is `backend/axon-service/axon_service_tests/` to avoid `tests.conftest` collision with state-api. Same moto + TestClient, no live AWS.

**requirements-dev.txt:** Additive `moto[s3,dynamodb]` + `httpx` — covers root-collected axon tests; justified under AC-17 run_result.

---

## Per-AC matrix (24)

```yaml
acceptance_criteria:
  - id: AC-01
    criterion: "POST `/axon/{company_id}/{repository_id}/index` accepts JSON body with `commit_sha` + graph payload; returns stable success response with identifiers for later reads."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_index.py::test_post_index_persists_s3_and_dynamo"
    run_result: "12 axon tests pass; index returns stable JSON with commit identifiers."

  - id: AC-02
    criterion: "Index persists snapshot bytes to S3 at key `{company_id}/{repository_id}/{commit_sha}.json.gz` (bucket via `AXON_S3_BUCKET`) using gzip."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_index.py::test_post_index_persists_s3_and_dynamo"
    run_result: "test asserts S3 key suffix .json.gz and gzip; moto-backed."

  - id: AC-03
    criterion: "Index writes DynamoDB metadata row: `pk=company_id#repository_id`, `sk=commit_sha`, attrs `uploaded_at`, `size_bytes`, `node_count`, `edge_count`."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_index.py::test_post_index_persists_s3_and_dynamo"
    run_result: "Dynamo item shape asserted in same test."

  - id: AC-04
    criterion: "GET `/axon/{company_id}/{repository_id}/query?q=&commit_sha=&limit=` returns JSON shortlist with `nodes`, `edges`, `scores`, `source_spans` (empty lists when no matches)."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_query.py::test_query_returns_shortlist_shape"
    run_result: "pytest pass; shortlist keys present."

  - id: AC-05
    criterion: "GET `/axon/{company_id}/{repository_id}/impact?symbol=&commit_sha=&depth=` returns upstream/downstream blast-radius JSON."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_impact.py::test_impact_returns_blast_radius_shape"
    run_result: "pytest pass; shape includes upstream/downstream style fields."

  - id: AC-06
    criterion: "Handlers use only path-level `company_id`/`repository_id` for storage keys; body cannot override tenant scope."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_index.py::test_path_tenant_authoritative"
    run_result: "Path tenant used over conflicting body; test pass."

  - id: AC-07
    criterion: "Cross-tenant isolation: snapshot for (C1, R1) not returned when querying (C2, R1) or (C1, R2) for same commit_sha."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_query.py::test_cross_tenant_isolation"
    run_result: "pytest pass."

  - id: AC-08
    criterion: "GET `/healthz` returns 200 JSON with `status` ∈ {ok, degraded} and `snapshots` (integer count or null) — suitable for `canon memory-health` classification."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_healthz.py::test_healthz_ok_shape"
      - "backend/axon-service/axon_service_tests/test_healthz.py::test_healthz_degraded_on_store_failure"
    run_result: "ok and degraded paths covered; pytest pass."

  - id: AC-09
    criterion: "Auth shim: index/query/impact require `Authorization: Bearer <token>` matching `AXON_SERVICE_TOKEN`; 401/403 on mismatch. `/healthz` unauthenticated."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_auth.py::test_auth_rejects_missing_token"
      - "backend/axon-service/axon_service_tests/test_auth.py::test_auth_rejects_wrong_token"
    run_result: "Missing/wrong token rejected; healthz not auth-gated in tests."

  - id: AC-10
    criterion: "Only `axon_service/storage.py` imports boto3."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service/storage.py"
    run_result: "Grep of `import boto3` / `from boto3` in `backend/axon-service/axon_service/` finds only `storage.py`; conftest and tests import boto3 for moto outside the `axon_service` package (expected)."

  - id: AC-11
    criterion: "Successful index emits `retrieval.graph.index` via CanonicalEvent on injectable EventEmitter."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_events.py::test_event_emissions_logged_or_called"
    run_result: "Emitter/CanonicalEvent path exercised; 261+12 pytest pass."

  - id: AC-12
    criterion: "Query emits `retrieval.graph.query`; impact emits `retrieval.graph.impact`; payload includes `company_id`, `repository_id`, `commit_sha`, operation-specific fields."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_events.py::test_event_emissions_logged_or_called"
    run_result: "Event test asserts event types and payload fields."

  - id: AC-13
    criterion: "`infra/terraform/modules/axon-snapshots/` exists with `main.tf`, `variables.tf`, `outputs.tf`, `README.md`: S3 bucket + DynamoDB table (PAY_PER_REQUEST, PITR, deletion protection, pk/sk keys per brief)."
    verdict: PASS
    covering_tests:
      - "tests/test_infra_layout.py::test_axon_snapshots_module_files_exist"
      - "tests/test_infra_layout.py::test_axon_snapshots_module_declares_s3_and_dynamodb"
    run_result: "Layout tests pass; terraform validate success."

  - id: AC-14
    criterion: "Root terraform `main.tf` + `outputs.tf` wire the module additively (no reflow)."
    verdict: PASS
    covering_tests:
      - "tests/test_infra_layout.py::test_root_wires_axon_snapshots_module"
      - "tests/test_infra_layout.py::test_root_outputs_expose_axon_snapshots"
    run_result: "Layout + validate pass."

  - id: AC-15
    criterion: "`infra/terraform/README.md` + `infra/README.md` append E3-T1 validate/plan/apply/import examples."
    verdict: PASS
    covering_tests:
      - "tests/test_infra_layout.py::test_infra_readme_e3t1_section"
    run_result: "String checks for E3-T1/axon-snapshots in both READMEs; test pass."

  - id: AC-16
    criterion: "`tests/test_infra_layout.py` appends axon-snapshots module + root wiring assertions (mirror dynamodb-canon-state coverage)."
    verdict: PASS
    covering_tests:
      - "tests/test_infra_layout.py::test_axon_snapshots_module_files_exist"
      - "tests/test_infra_layout.py::test_axon_snapshots_module_declares_s3_and_dynamodb"
      - "tests/test_infra_layout.py::test_axon_snapshots_module_exposes_expected_outputs"
      - "tests/test_infra_layout.py::test_root_wires_axon_snapshots_module"
      - "tests/test_infra_layout.py::test_root_outputs_expose_axon_snapshots"
    run_result: "Six axon-related layout tests; full suite 261 pass."

  - id: AC-17
    criterion: "`backend/axon-service/tests/` uses `moto[s3,dynamodb]` + TestClient; no live AWS."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/conftest.py"
      - "backend/axon-service/axon_service_tests/ (moto + TestClient suite)"
    run_result: "Package dir `axon_service_tests/` (per collision workaround); 12 moto tests pass; `requirements-dev.txt` adds moto/httpx for root pytest."

  - id: AC-18
    criterion: "Named tests: `test_post_index_persists_s3_and_dynamo`, `test_query_returns_shortlist_shape`, `test_impact_returns_blast_radius_shape`, `test_auth_rejects_missing_token`, `test_healthz_ok_shape`, `test_cross_tenant_isolation`, `test_event_emissions_logged_or_called`, `test_path_tenant_authoritative`."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_index.py::test_post_index_persists_s3_and_dynamo"
      - "backend/axon-service/axon_service_tests/test_query.py::test_query_returns_shortlist_shape"
      - "backend/axon-service/axon_service_tests/test_impact.py::test_impact_returns_blast_radius_shape"
      - "backend/axon-service/axon_service_tests/test_auth.py::test_auth_rejects_missing_token"
      - "backend/axon-service/axon_service_tests/test_healthz.py::test_healthz_ok_shape"
      - "backend/axon-service/axon_service_tests/test_query.py::test_cross_tenant_isolation"
      - "backend/axon-service/axon_service_tests/test_events.py::test_event_emissions_logged_or_called"
      - "backend/axon-service/axon_service_tests/test_index.py::test_path_tenant_authoritative"
    run_result: "All eight names present under axon_service_tests/; all pass."

  - id: AC-19
    criterion: "CHANGELOG `[Unreleased] ### Added` gains top bullet for axon-service + module."
    verdict: PASS
    covering_tests:
      - "CHANGELOG.md"
    run_result: "Line 12: E3-T1 first ### Added bullet documents axon-service + module."

  - id: AC-20
    criterion: "README additively documents axon-service + env vars (`AXON_SERVICE_URL`, `AXON_S3_BUCKET`, `AXON_SERVICE_TOKEN`)."
    verdict: PASS
    covering_tests:
      - "README.md"
    run_result: "Backend section and memory-health table mention axon and AXON_* vars."

  - id: AC-21
    criterion: "`docs/SYSTEM-WORKFLOW.md` additively documents graph/axon probe path via `canon memory-health` + `AXON_SERVICE_URL`."
    verdict: PASS
    covering_tests:
      - "docs/SYSTEM-WORKFLOW.md"
    run_result: "Graph retrieval / AXON_SERVICE_URL bullet present (e.g. ~line 122)."

  - id: AC-22
    criterion: "memory-health: AXON_SERVICE_URL documented; tests cover optional-not-configured vs required-unhealthy cases."
    verdict: PASS
    covering_tests:
      - "tests/test_memory_health.py::test_graph_optional_not_configured_exit_ok"
      - "tests/test_memory_health.py::test_graph_required_unhealthy_when_unset"
    run_result: "Both pass in 261 root run; README documents AXON_SERVICE_URL."

  - id: AC-23
    criterion: "`backend/axon-service/README.md` states OIDC/Cognito explicitly deferred."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/README.md"
    run_result: "OIDC / Cognito deferred sentence present (line 7)."

  - id: AC-24
    criterion: "Forbidden: no edits under backend/state-api/**, backend/knowledge-api/**, .cursor/rules/**, .cursor/plans/**; no reflow-only edits; terraform artifacts not skipped."
    verdict: PASS
    covering_tests:
      - "scripts/smoke-test.sh"
    run_result: "2026-04-22 QA gate: `git status --porcelain` and `git diff --name-only` show no paths under `backend/state-api/`, `backend/knowledge-api/`, `backend/shared/`, `.cursor/rules/`, `.cursor/plans/`, or `src/canon_systems/cli.py` / `src/canon_systems/templates/**`; new terraform module and root wiring present (not skipped). Smoke test exit 0 in this run."

regression_checked: true
acceptance_criteria_all_pass: true
iterations: 0
remaining_gaps: []
```

---

```yaml
GATE_RESULTS
handoff_id: "handoff_20260422_wave3_canon_memory_v1_E3_T1"
verdict: PASS
acceptance_criteria_all_pass: true
regression_checked: true
iterations: 0
remaining_gaps: []
acceptance_criteria:
  - id: AC-01
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_index.py::test_post_index_persists_s3_and_dynamo"
    run_result: "POST index: 12 axon tests pass; returns stable JSON with commit identifiers."
  - id: AC-02
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_index.py::test_post_index_persists_s3_and_dynamo"
    run_result: "S3 key suffix .json.gz + gzip asserted; moto-backed."
  - id: AC-03
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_index.py::test_post_index_persists_s3_and_dynamo"
    run_result: "DynamoDB item shape asserted in same test."
  - id: AC-04
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_query.py::test_query_returns_shortlist_shape"
    run_result: "Shortlist keys nodes/edges/scores/source_spans present."
  - id: AC-05
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_impact.py::test_impact_returns_blast_radius_shape"
    run_result: "Upstream/downstream blast-radius shape asserted."
  - id: AC-06
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_index.py::test_path_tenant_authoritative"
    run_result: "Path tenant authoritative over conflicting body."
  - id: AC-07
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_query.py::test_cross_tenant_isolation"
    run_result: "Cross-tenant isolation verified."
  - id: AC-08
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_healthz.py::test_healthz_ok_shape"
      - "backend/axon-service/axon_service_tests/test_healthz.py::test_healthz_degraded_on_store_failure"
    run_result: "ok and degraded paths covered."
  - id: AC-09
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_auth.py::test_auth_rejects_missing_token"
      - "backend/axon-service/axon_service_tests/test_auth.py::test_auth_rejects_wrong_token"
    run_result: "Missing/wrong token rejected; healthz not auth-gated."
  - id: AC-10
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service/storage.py"
    run_result: "Grep of import boto3 in axon_service/ finds only storage.py."
  - id: AC-11
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_events.py::test_event_emissions_logged_or_called"
    run_result: "retrieval.graph.index via injectable EventEmitter."
  - id: AC-12
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_events.py::test_event_emissions_logged_or_called"
    run_result: "query/impact event types + payload fields asserted."
  - id: AC-13
    verdict: PASS
    covering_tests:
      - "tests/test_infra_layout.py::test_axon_snapshots_module_files_exist"
      - "tests/test_infra_layout.py::test_axon_snapshots_module_declares_s3_and_dynamodb"
    run_result: "Module trio + README + key attributes verified; terraform validate Success."
  - id: AC-14
    verdict: PASS
    covering_tests:
      - "tests/test_infra_layout.py::test_root_wires_axon_snapshots_module"
      - "tests/test_infra_layout.py::test_root_outputs_expose_axon_snapshots"
    run_result: "Additive root wiring + outputs verified."
  - id: AC-15
    verdict: PASS
    covering_tests:
      - "tests/test_infra_layout.py::test_infra_readme_e3t1_section"
    run_result: "E3-T1/axon-snapshots strings present in both READMEs."
  - id: AC-16
    verdict: PASS
    covering_tests:
      - "tests/test_infra_layout.py::test_axon_snapshots_module_files_exist"
      - "tests/test_infra_layout.py::test_axon_snapshots_module_declares_s3_and_dynamodb"
      - "tests/test_infra_layout.py::test_axon_snapshots_module_exposes_expected_outputs"
      - "tests/test_infra_layout.py::test_root_wires_axon_snapshots_module"
      - "tests/test_infra_layout.py::test_root_outputs_expose_axon_snapshots"
      - "tests/test_infra_layout.py::test_infra_readme_e3t1_section"
    run_result: "Six axon-related layout tests all pass."
  - id: AC-17
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/conftest.py"
    run_result: "Package dir axon_service_tests/ (collision workaround); moto[s3,dynamodb] + TestClient; 12 tests green; no live AWS."
  - id: AC-18
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_index.py::test_post_index_persists_s3_and_dynamo"
      - "backend/axon-service/axon_service_tests/test_query.py::test_query_returns_shortlist_shape"
      - "backend/axon-service/axon_service_tests/test_impact.py::test_impact_returns_blast_radius_shape"
      - "backend/axon-service/axon_service_tests/test_auth.py::test_auth_rejects_missing_token"
      - "backend/axon-service/axon_service_tests/test_healthz.py::test_healthz_ok_shape"
      - "backend/axon-service/axon_service_tests/test_query.py::test_cross_tenant_isolation"
      - "backend/axon-service/axon_service_tests/test_events.py::test_event_emissions_logged_or_called"
      - "backend/axon-service/axon_service_tests/test_index.py::test_path_tenant_authoritative"
    run_result: "All eight named tests present and passing."
  - id: AC-19
    verdict: PASS
    covering_tests:
      - "CHANGELOG.md"
    run_result: "E3-T1 first [Unreleased] ### Added bullet documents axon-service + module."
  - id: AC-20
    verdict: PASS
    covering_tests:
      - "README.md"
    run_result: "Backend section and memory-health table mention axon + AXON_* env vars."
  - id: AC-21
    verdict: PASS
    covering_tests:
      - "docs/SYSTEM-WORKFLOW.md"
    run_result: "Graph retrieval / AXON_SERVICE_URL bullet present in §6."
  - id: AC-22
    verdict: PASS
    covering_tests:
      - "tests/test_memory_health.py::test_graph_optional_not_configured_exit_ok"
      - "tests/test_memory_health.py::test_graph_required_unhealthy_when_unset"
    run_result: "Both optional-unset and required-unset tests pass; README documents AXON_SERVICE_URL."
  - id: AC-23
    verdict: PASS
    covering_tests:
      - "backend/axon-service/README.md"
    run_result: "OIDC/Cognito deferred sentence present in README."
  - id: AC-24
    verdict: PASS
    covering_tests:
      - "scripts/smoke-test.sh"
    run_result: "git diff --name-only shows no paths under backend/state-api/, backend/knowledge-api/, backend/shared/, .cursor/rules/, .cursor/plans/, cli.py, or templates/**; terraform module + root wiring added (not skipped); smoke exit 0."
notes: "No fix/retest cycles. CanonicalEvent matches canon_backend_shared.events.CanonicalEvent. boto3 imported only in axon_service/storage.py. `canon capture` HTTP 500 is environment-side and non-blocking; local test evidence is authoritative."
END_GATE_RESULTS
```
