# E3-T2 Implementer handoff — Indexer pipeline

## Summary

Implemented stdlib-only `canon graph` CLI (`graph_indexer.py`), Bearer-gated `GET /axon/{company_id}/{repository_id}/reindex-status`, wiring in `cli.py` / `api.py`, pre-push hook scaffold, opt-in `axon-reindex.yml`, docs and CHANGELOG/README updates, and pytest coverage (root + axon_service_tests).

## Verification run (local)

- `pytest -q` → **283 passed**
- `cd backend/axon-service && pytest -q axon_service_tests/` → **16 passed**
- `SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh` → **exit 0**
- `canon graph index --help` / `canon graph reindex-status --help` → **exit 0**

## HANDOFF_TO_QA

```
HANDOFF_TO_QA
  task_id: E3-T2
  branch: wave/3/canon-memory-v1
  ac_coverage:
    - id: AC1
      criterion: "Stub incremental/full indexer POSTs bearer-auth'd index requests with AXON_SERVICE_URL/AXON_SERVICE_TOKEN fallbacks and deterministic nodes/edges"
      evidence:
        - file: src/canon_systems/graph_indexer.py
        - test: tests/test_graph_indexer.py::test_index_success_with_changed_files
        - test: tests/test_graph_indexer.py::test_index_success_full_mode
        - test: tests/test_graph_indexer.py::test_index_env_fallback_resolves_base_url_and_token
    - id: AC2
      criterion: "Elapsed >60s stderr warning; success exit 0; warning path covered"
      evidence:
        - file: src/canon_systems/graph_indexer.py (_cmd_index soft budget)
        - test: tests/test_graph_indexer.py::test_index_soft_budget_warning
    - id: AC3
      criterion: "Exit codes 0/1/2/3/4/5"
      evidence:
        - file: src/canon_systems/graph_indexer.py (EXIT_* constants, _cmd_index/_cmd_reindex_status)
        - test: tests/test_graph_indexer.py::test_index_success_with_changed_files (0)
        - test: tests/test_graph_indexer.py::test_index_unexpected_http_returns_1 (1)
        - test: tests/test_graph_indexer.py::test_index_usage_error_missing_commit_sha (2)
        - test: tests/test_graph_indexer.py::test_index_http_4xx_returns_3_and_unwraps_detail (3)
        - test: tests/test_graph_indexer.py::test_index_http_5xx_returns_4 (4)
        - test: tests/test_graph_indexer.py::test_index_transport_error_returns_5 (5)
    - id: AC4
      criterion: "canon graph in cli.py with REMAINDER → graph_indexer.run"
      evidence:
        - file: src/canon_systems/cli.py
        - test: tests/test_graph_indexer.py::test_index_help_returns_0 (delegation path)
    - id: AC5
      criterion: "GET reindex-status JSON shape; missing→missing; Bearer-gated"
      evidence:
        - file: backend/axon-service/axon_service/routers/status.py
        - test: backend/axon-service/axon_service_tests/test_reindex_status.py::test_reindex_status_missing_when_no_meta
        - test: backend/axon-service/axon_service_tests/test_reindex_status.py::test_reindex_status_rejects_missing_token
    - id: AC6
      criterion: "reindex-status CLI + router in api.py"
      evidence:
        - file: src/canon_systems/graph_indexer.py (_cmd_reindex_status)
        - file: backend/axon-service/axon_service/api.py
        - test: tests/test_graph_indexer.py::test_reindex_status_success
    - id: AC7
      criterion: "pre-push script executable; documented"
      evidence:
        - file: scripts/hooks/pre-push-graph-index.sh (mode +x)
        - file: README.md (setup step 4 optional hook)
    - id: AC8
      criterion: "axon-reindex.yml opt-in (vars + secrets)"
      evidence:
        - file: .github/workflows/axon-reindex.yml
    - id: AC9
      criterion: "Docs: pure-RPC reads; indexing via canon graph index"
      evidence:
        - file: docs/SYSTEM-WORKFLOW.md (§6 bullet)
        - file: backend/axon-service/README.md (### Indexing invariant)
    - id: AC10
      criterion: "README + CHANGELOG"
      evidence:
        - file: README.md (Commands table)
        - file: CHANGELOG.md ([Unreleased] ### Added)
    - id: AC11
      criterion: "tests/test_graph_indexer ≥10 mocked HTTP tests"
      evidence:
        - file: tests/test_graph_indexer.py (18 tests)
    - id: AC12
      criterion: "axon_service_tests ≥3 reindex-status tests"
      evidence:
        - file: backend/axon-service/axon_service_tests/test_reindex_status.py (4 tests)
    - id: AC13
      criterion: "query/impact placeholders do not call _http_request"
      evidence:
        - file: src/canon_systems/graph_indexer.py (_cmd_query/_cmd_impact)
        - test: tests/test_graph_indexer.py::test_query_placeholder_does_not_call_http
        - test: tests/test_graph_indexer.py::test_impact_placeholder_does_not_call_http
    - id: AC14
      criterion: "Integration POST index then GET reindex-status ready"
      evidence:
        - test: backend/axon-service/axon_service_tests/test_reindex_status.py::test_reindex_status_ready_after_index
    - id: AC15
      criterion: "No forbidden surfaces touched"
      evidence:
        - process: git status / diff — no backend/state-api, knowledge-api, shared, .cursor/rules, .cursor/plans
    - id: AC16
      criterion: "Append-only existing tests (new files only for new tests)"
      evidence:
        - process: no edits to existing axon_service_tests bodies
    - id: AC17
      criterion: "checkpoint_cli, flow_audit, qa_validate, memory_health, checkpoints untouched"
      evidence:
        - process: not in changed file list
    - id: AC18
      criterion: "FastAPI detail unwrap pattern"
      evidence:
        - file: src/canon_systems/graph_indexer.py (_unwrap_detail)
        - test: tests/test_graph_indexer.py::test_index_http_4xx_returns_3_and_unwraps_detail
    - id: AC19
      criterion: "Env fallbacks AXON_SERVICE_URL / AXON_SERVICE_TOKEN"
      evidence:
        - file: src/canon_systems/graph_indexer.py (_resolve_base_url/_resolve_token)
        - test: tests/test_graph_indexer.py::test_index_env_fallback_resolves_base_url_and_token
    - id: AC20
      criterion: "--full vs --changed-files modes; mutual exclusion"
      evidence:
        - file: src/canon_systems/graph_indexer.py (_build_payload, _cmd_index)
        - test: tests/test_graph_indexer.py::test_index_success_full_mode
        - test: tests/test_graph_indexer.py::test_index_success_with_changed_files
        - test: tests/test_graph_indexer.py::test_index_usage_error_both_full_and_changed
    - id: AC21
      criterion: "--help for index and reindex-status"
      evidence:
        - test: tests/test_graph_indexer.py::test_index_help_returns_0
        - test: tests/test_graph_indexer.py::test_reindex_status_help_returns_0
  extra_tests:
    - test: backend/axon-service/axon_service_tests/test_reindex_status.py::test_reindex_status_cross_tenant_returns_missing
    - test: tests/test_graph_indexer.py::test_reindex_status_missing
    - test: tests/test_graph_indexer.py::test_reindex_status_http_4xx
  notes:
    - "Placeholder stderr message for query/impact matches pilot spec (same string for both subcommands)."
END_HANDOFF_TO_QA
```
