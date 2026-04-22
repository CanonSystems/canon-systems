# E3-T1 — Implementer handoff

## HANDOFF_TO_QA

- **Task:** E3-T1 — Fork and deploy `backend/axon-service` + `infra/terraform/modules/axon-snapshots` + living-spec + memory-health tests + layout tests
- **Branch / HEAD:** `wave/3/canon-memory-v1` (verify at `git rev-parse HEAD`)

### Files changed (summary)

- `backend/axon-service/` — Full FastAPI app (`axon_service/`), `pyproject.toml` (deps + `[test]`), `README.md` (OIDC deferred, env, endpoints, Terraform pointer)
- `backend/axon-service/axon_service_tests/` — moto + TestClient tests (12 tests; **directory name avoids `tests.conftest` collision with `state-api`**)
- `infra/terraform/modules/axon-snapshots/` — `main.tf`, `variables.tf`, `outputs.tf`, `README.md`
- `infra/terraform/main.tf`, `outputs.tf` — `module "axon_snapshots"`, four outputs
- `infra/terraform/README.md`, `infra/README.md` — E3-T1 / axon-snapshots documentation
- `tests/test_infra_layout.py` — six axon module assertions
- `tests/test_memory_health.py` — `test_graph_optional_not_configured_exit_ok`, `test_graph_required_unhealthy_when_unset`
- `requirements-dev.txt` — `moto[s3,dynamodb]`, `httpx` (for root `pytest` + axon tests)
- `pytest.ini` — unchanged from stock (`pythonpath = src` only) after conftest fix
- `CHANGELOG.md` [Unreleased] ### Added — E3-T1 bullet
- `README.md` — axon-service + `AXON_*` / `AXON_SERVICE_URL` / memory-health cell
- `docs/SYSTEM-WORKFLOW.md` — graph / axon + `AXON_SERVICE_URL` bullet
- *No edits:* `backend/state-api/**`, `backend/knowledge-api/**`, `backend/shared/**`, `.cursor/rules/**`, `.cursor/plans/**`, `src/canon_systems/cli.py`, `src/canon_systems/templates/**` (forbidden-surface `git diff` check clean)

### Verification (executed)

| Command | Result |
| --- | --- |
| `pytest -q` (repo root) | **261 passed** |
| `cd backend/axon-service && pip install -e '.[test]' && pytest -q axon_service_tests/` | **12 passed** |
| `SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh` | **exit 0** |
| `cd infra/terraform && terraform init -backend=false && terraform validate` | **Success** (Terraform 1.5+ / AWS provider 5.x) |

**CanonicalEvent:** `make_graph_event()` in `backend/axon-service/axon_service/events.py` uses the same fields as `backend/state-api/state_api/checkpoints.py` (`schema_version=1`, `event_id` UUID, `parent_event_id=""`, `plan_id`/`task_id`/`handoff_id` empty, `agent_name="axon-service"`, `state_version=0`, `timestamp` RFC3339Z).

**boto3:** only `backend/axon-service/axon_service/storage.py` in the service package; tests and `axon_service_tests/conftest.py` use boto3 for moto setup/assertions (AC#10: production gate on storage; tests are separate).

### AC → evidence (24 from scoper)

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | POST index accepts body + returns stable response | `routers/index.py::post_index`, `test_index.py::test_post_index_persists_s3_and_dynamo` |
| 2 | S3 gzip key `{c}/{r}/{sha}.json.gz` | `storage.py` `_snapshot_key`, `put_snapshot`, `test_post_index_persists_s3_and_dynamo` |
| 3 | DynamoDB meta `pk`/`sk` + attributes | `storage.py` `put_item`, `test_post_index_persists_s3_and_dynamo` |
| 4 | GET query shortlist shape | `routers/query.py`, `test_query.py::test_query_returns_shortlist_shape` |
| 5 | GET impact blast-radius shape | `routers/impact.py`, `test_impact.py::test_impact_returns_blast_radius_shape` |
| 6 | Path-only tenant for storage | `routers/*` use path `company_id`/`repository_id`; `test_path_tenant_authoritative` |
| 7 | Cross-tenant isolation | `test_query.py::test_cross_tenant_isolation` |
| 8 | GET `/healthz` ok\|degraded + snapshots | `routers/health.py`, `test_healthz.py` |
| 9 | Bearer 401/403; healthz open | `auth.py`, `test_auth.py` |
| 10 | Only `storage.py` imports boto3 (service) | Grep; review |
| 11 | `retrieval.graph.index` via emitter | `index.py` + `make_graph_event`, `test_events.py` |
| 12 | query + impact events + payload fields | `query.py`, `impact.py`, `test_events.py` |
| 13 | Terraform module S3+ddb | `modules/axon-snapshots/`, `test_axon_snapshots_module_files_exist` + `test_axon_snapshots_module_declares_s3_and_dynamodb` |
| 14 | Root `main.tf` + `outputs.tf` wire | `test_root_wires_axon_snapshots_module` + `test_root_outputs_expose_axon_snapshots` |
| 15 | `infra/terraform/README.md` + `infra/README.md` E3-T1 | `test_infra_readme_e3t1_section` + doc review |
| 16 | `tests/test_infra_layout.py` extensions | six new tests in `test_infra_layout.py` |
| 17 | moto + TestClient; no live AWS | `axon_service_tests/conftest.py` + all axon tests |
| 18 | Named tests (8) | `test_post_index_persists_s3_and_dynamo`, `test_query_returns_shortlist_shape`, `test_impact_returns_blast_radius_shape`, `test_auth_rejects_missing_token`, `test_healthz_ok_shape`, `test_cross_tenant_isolation`, `test_event_emissions_logged_or_called`, `test_path_tenant_authoritative` (plus `test_index_400_on_missing_commit_sha` for validation) |
| 19 | CHANGELOG bullet | `CHANGELOG.md` top Added |
| 20 | README axon + env | `README.md` backend + command table |
| 21 | SYSTEM-WORKFLOW graph/axon | `docs/SYSTEM-WORKFLOW.md` §6 bullet |
| 22 | memory-health optional vs required graph | `test_graph_optional_not_configured_exit_ok`, `test_graph_required_unhealthy_when_unset` |
| 23 | axon README OIDC deferred | `backend/axon-service/README.md` |
| 24 | Forbidden surfaces | `git diff` allowlist; no state-api/knowledge/shared edits |

**Note:** E3-T1 **AC#15** in the scoper table references infra README; **AC#16** is the layout file — numbering in the scoper “traceability” table has a gap; all 24 story ACs in `scoper.md` are mapped above.

END_HANDOFF_TO_QA

---

*Parent: persist this block for qa-gate; do not commit to `main` from this file.*
