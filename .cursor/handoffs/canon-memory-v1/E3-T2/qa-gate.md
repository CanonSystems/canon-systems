# E3-T2 QA gate — Indexer pipeline for repo changes

**Branch:** `wave/3/canon-memory-v1`  
**Handoff:** `handoff_20260422_e3t2_indexer_pipeline`

## Reconciliation

- **Changed/untracked (vs HEAD):** `CHANGELOG.md`, `README.md`, `backend/axon-service/README.md`, `backend/axon-service/axon_service/api.py`, `docs/SYSTEM-WORKFLOW.md`, `src/canon_systems/cli.py`, `.github/workflows/axon-reindex.yml`, `backend/axon-service/axon_service/routers/status.py`, `backend/axon-service/axon_service_tests/test_reindex_status.py`, `scripts/hooks/pre-push-graph-index.sh`, `src/canon_systems/graph_indexer.py`, `tests/test_graph_indexer.py`, plus handoff/scoper/implementer under `.cursor/handoffs/...` and incidental `.canon/memory/*` captures.
- **Forbidden surfaces:** No paths under `backend/state-api/`, `backend/knowledge-api/`, `backend/shared/`, `.cursor/rules/`, `.cursor/plans/`; stable modules `checkpoint_cli.py`, `flow_audit.py`, `qa_validate.py`, `memory_health.py`, `checkpoints.py` not in diff.
- **Tests:** Root `pytest -q` → **283 passed**; `backend/axon-service` `pytest -q axon_service_tests/` → **16 passed**; `SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh` → **exit 0** (`ALL STAGES PASSED`). `canon graph index --help` and `canon graph reindex-status --help` → **exit 0** (local argparse only).
- **Shape checks:** `graph_indexer.py` defines `EXIT_*` 0–5, `TransportError`, `_http_request` seam, `run(argv)->int`, `_cmd_index` / `_cmd_reindex_status`, placeholders `_cmd_query` / `_cmd_impact` without `_http_request`. `cli.py` adds `graph` subparser with `REMAINDER` → `run_graph_cli`. `status.py` Bearer-gated `GET /axon/{c}/{r}/reindex-status`. `pre-push-graph-index.sh` mode **755**. Workflow has `workflow_dispatch` and `if: vars.AXON_REINDEX_ENABLED == 'true'`.
- **Append-only tests:** New modules `tests/test_graph_indexer.py` and `test_reindex_status.py` only; no modified bodies in pre-existing test files in this change set.

## Memory capture

`canon capture` was invoked for distillation; the memory-layer HTTP response was non-OK in this environment—the gate verdict below is based on repo tests and commands above.

---

GATE_RESULTS
```yaml
handoff_id: "handoff_20260422_e3t2_indexer_pipeline"
verdict: PASS
regression_checked: true
acceptance_criteria_all_pass: true
iterations: 0
remaining_gaps: []
acceptance_criteria:
  - id: AC-01
    criterion: "Stub incremental/full indexer in graph_indexer POSTs bearer-auth'd index requests with AXON_SERVICE_URL/AXON_SERVICE_TOKEN env fallbacks and deterministic minimal nodes/edges (one node per changed file; same-dir edges)."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py::test_index_success_with_changed_files"
      - "tests/test_graph_indexer.py::test_index_success_full_mode"
      - "tests/test_graph_indexer.py::test_index_env_fallback_resolves_base_url_and_token"
    run_result: "pytest passed; POST body includes nodes/edges and Authorization bearer."
  - id: AC-02
    criterion: "Index run measures elapsed time; if >60s, stderr warning; success still exit 0; stub tests complete in <1s and still cover warning path (injected clock / mocked long response)."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py::test_index_soft_budget_warning"
    run_result: "pytest passed; warning path exercised with mocked slow HTTP response; suite wall time <1s for this test module."
  - id: AC-03
    criterion: "Exit codes: 0 success, 1 server/app error, 2 usage, 3 HTTP 4xx, 4 HTTP 5xx, 5 transport."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py::test_index_success_with_changed_files"
      - "tests/test_graph_indexer.py::test_index_unexpected_http_returns_1"
      - "tests/test_graph_indexer.py::test_index_usage_error_missing_commit_sha"
      - "tests/test_graph_indexer.py::test_index_http_4xx_returns_3_and_unwraps_detail"
      - "tests/test_graph_indexer.py::test_index_http_5xx_returns_4"
      - "tests/test_graph_indexer.py::test_index_transport_error_returns_5"
    run_result: "pytest passed; each exit code path asserted."
  - id: AC-04
    criterion: "canon graph registered in cli.py with nargs=argparse.REMAINDER delegating to graph_indexer.run; subcommands index and reindex-status."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py::test_index_help_returns_0"
      - "src/canon_systems/cli.py"
    run_result: "REMAINDER graph args and run_graph_cli wiring present; help/delegation test passed."
  - id: AC-05
    criterion: "GET /axon/{company_id}/{repository_id}/reindex-status?commit_sha=<sha> returns {company_id, repository_id, commit_sha, status: ready|missing|error, uploaded_at, node_count, edge_count, size_bytes}; missing meta → status=missing; Bearer-gated."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_reindex_status.py::test_reindex_status_ready_after_index"
      - "backend/axon-service/axon_service_tests/test_reindex_status.py::test_reindex_status_missing_when_no_meta"
      - "backend/axon-service/axon_service_tests/test_reindex_status.py::test_reindex_status_rejects_missing_token"
    run_result: "pytest passed; JSON shape and missing/auth behavior covered; ready state in integration test."
  - id: AC-06
    criterion: "canon graph reindex-status CLI exercises the new endpoint; router wired in backend/axon-service/axon_service/api.py."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py::test_reindex_status_success"
      - "backend/axon-service/axon_service_tests/test_reindex_status.py::test_reindex_status_ready_after_index"
      - "backend/axon-service/axon_service/api.py"
    run_result: "CLI test passes with mocked HTTP; service test hits mounted router after include_router(status)."
  - id: AC-07
    criterion: "scripts/hooks/pre-push-graph-index.sh exists, executable, documented in README; not auto-installed."
    verdict: PASS
    covering_tests:
      - "scripts/hooks/pre-push-graph-index.sh"
      - "README.md"
    run_result: "File mode 755; README optional hook section present."
  - id: AC-08
    criterion: ".github/workflows/axon-reindex.yml scaffold with workflow_dispatch using AXON_SERVICE_URL + AXON_SERVICE_TOKEN secrets; not a required check."
    verdict: PASS
    covering_tests:
      - ".github/workflows/axon-reindex.yml"
    run_result: "workflow_dispatch and secrets present; job gated by AXON_REINDEX_ENABLED var (opt-in)."
  - id: AC-09
    criterion: "docs/SYSTEM-WORKFLOW.md + backend/axon-service/README.md state query/impact are pure RPC; indexing only via canon graph index (pre-push/CI)."
    verdict: PASS
    covering_tests:
      - "docs/SYSTEM-WORKFLOW.md"
      - "backend/axon-service/README.md"
    run_result: "Indexer pipeline bullet and Indexing invariant section found."
  - id: AC-10
    criterion: "README + CHANGELOG document new commands under [Unreleased] ### Added (top bullet)."
    verdict: PASS
    covering_tests:
      - "README.md"
      - "CHANGELOG.md"
    run_result: "Commands table lists canon graph; CHANGELOG Added opens with E3-T2."
  - id: AC-11
    criterion: "tests/test_graph_indexer.py ≥10 tests with HTTP seam mocked; no live network."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py"
    run_result: "18 tests collected; full root pytest passed (HTTP mocked)."
  - id: AC-12
    criterion: "backend/axon-service/axon_service_tests/test_reindex_status.py ≥3 tests: ready, missing, auth."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_reindex_status.py"
    run_result: "4 tests collected including ready_after_index, missing_when_no_meta, rejects_missing_token."
  - id: AC-13
    criterion: "graph_indexer separates write (index) from read argv paths; no POST on placeholder query/impact argv (test asserts)."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py::test_query_placeholder_does_not_call_http"
      - "tests/test_graph_indexer.py::test_impact_placeholder_does_not_call_http"
    run_result: "pytest passed; _http_request not invoked for query/impact argv."
  - id: AC-14
    criterion: "Integration test satisfies backlog done_signal: POST index then GET reindex-status returns status=ready."
    verdict: PASS
    covering_tests:
      - "backend/axon-service/axon_service_tests/test_reindex_status.py::test_reindex_status_ready_after_index"
    run_result: "pytest passed; POST /index then GET /reindex-status asserts status ready and counts."
  - id: AC-15
    criterion: "No edits under backend/state-api/**, backend/knowledge-api/**, backend/shared/**, .cursor/rules/**, .cursor/plans/**."
    verdict: PASS
    covering_tests:
      - "src/canon_systems/graph_indexer.py"
      - "backend/axon-service/axon_service/api.py"
    run_result: "git diff --name-only vs HEAD shows no paths under forbidden prefixes."
  - id: AC-16
    criterion: "No modifications to existing test function bodies; append-only."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py"
      - "backend/axon-service/axon_service_tests/test_reindex_status.py"
    run_result: "New test files only; no modified pre-existing test modules in this change set."
  - id: AC-17
    criterion: "No modifications to checkpoint_cli.py, flow_audit.py, qa_validate.py, memory_health.py, checkpoints.py."
    verdict: PASS
    covering_tests:
      - "src/canon_systems/cli.py"
    run_result: "Stable module paths absent from git diff --name-only."
  - id: AC-18
    criterion: "FastAPI detail unwrap pattern from checkpoint_cli mirrored."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py::test_index_http_4xx_returns_3_and_unwraps_detail"
    run_result: "pytest passed; _unwrap_detail extracts FastAPI detail from JSON body."
  - id: AC-19
    criterion: "Env fallbacks: --base-url/--service-token resolve to AXON_SERVICE_URL/AXON_SERVICE_TOKEN when CLI flags omitted."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py::test_index_env_fallback_resolves_base_url_and_token"
    run_result: "pytest passed; resolves from env when flags unset."
  - id: AC-20
    criterion: "--full flag builds full-repo payload (stub: git ls-files output); --changed-files accepts a space-separated list."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py::test_index_success_full_mode"
      - "tests/test_graph_indexer.py::test_index_success_with_changed_files"
      - "tests/test_graph_indexer.py::test_index_usage_error_both_full_and_changed"
    run_result: "pytest passed; full vs changed-files modes and mutual exclusion covered."
  - id: AC-21
    criterion: "--help prints usage for canon graph index and canon graph reindex-status (two distinct help blocks)."
    verdict: PASS
    covering_tests:
      - "tests/test_graph_indexer.py::test_index_help_returns_0"
      - "tests/test_graph_indexer.py::test_reindex_status_help_returns_0"
    run_result: "pytest passed; canon graph index --help and reindex-status --help exit 0 with distinct usage."
```
END_GATE_RESULTS
