# E3-T3 Implementer handoff — graph query + impact CLI

## Summary

Replaced E3-T2 `query`/`impact` placeholders with `GET` clients for `/axon/{company_id}/{repository_id}/query` and `/impact`, using `_get_bearer_and_print` shared with `reindex-status`. `build_parser()` exposes real flags; living docs and CHANGELOG/README updated. Placeholder tests removed; eight named behavioral tests plus `test_graph_query_help_returns_0`, `test_graph_impact_help_returns_0`, `test_graph_query_missing_base_url_returns_2`, and `test_graph_query_unexpected_http_returns_1` added.

## Verification (local)

- `pytest tests/test_graph_indexer.py -q` → 28 passed
- `pytest -q` → 293 passed
- `python3 -m canon_systems.cli graph query --help` / `graph impact --help` → exit 0

## HANDOFF_TO_QA

```
HANDOFF_TO_QA
  handoff_id: handoff_20260422_e3t3_graph_read_cli
  branch: wave/3/canon-memory-v1
  scope_summary: "E3-T3 implements canon graph query and impact as stdlib GET clients to axon-service /query and /impact with Bearer auth, env-layered base URL and token, shared _get_bearer_and_print response mapping, and tests for success, optional limit/depth, 4xx unwrap, 5xx, transport, usage (no HTTP), and help."
  files_modified:
    - src/canon_systems/graph_indexer.py
    - tests/test_graph_indexer.py
    - README.md
    - CHANGELOG.md
    - docs/SYSTEM-WORKFLOW.md
  suite_result:
    focused: "28 passed in 0.05s"
    full: "293 passed in 3.84s"
  acceptance_criteria:
    - id: 1
      status: MET
      evidence: "_cmd_query builds GET URL /axon/{c}/{r}/query with q= and commit_sha= URL-encoded, Bearer in headers; 200 prints via _get_bearer_and_print"
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_success -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_success
    - id: 2
      status: MET
      evidence: "limit query param only when args.limit is not None"
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_with_limit -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_with_limit
        - tests/test_graph_indexer.py::test_graph_query_success
    - id: 3
      status: MET
      evidence: "_cmd_impact builds GET /axon/{c}/{r}/impact with symbol= and commit_sha="
      run_result: "pytest tests/test_graph_indexer.py::test_graph_impact_success -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_impact_success
    - id: 4
      status: MET
      evidence: "depth only appended when args.depth is not None"
      run_result: "pytest tests/test_graph_indexer.py::test_graph_impact_with_depth -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_impact_with_depth
    - id: 5
      status: MET
      evidence: "_resolve_base_url and _resolve_token; missing base or token before HTTP returns EXIT_USAGE=2 with stderr messages from pilot"
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2 tests/test_graph_indexer.py::test_graph_query_missing_base_url_returns_2 -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2
        - tests/test_graph_indexer.py::test_graph_query_missing_base_url_returns_2
    - id: 6
      status: MET
      evidence: "EXIT_OK/HTTP_4XX/5XX/TRANSPORT and unexpected status via _get_bearer_and_print; argparse usage returns 2 (existing run() handler)"
      run_result: "pytest tests/test_graph_indexer.py (query/impact cases) -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_success
        - tests/test_graph_indexer.py::test_graph_query_http_4xx_returns_3_and_unwraps_detail
        - tests/test_graph_indexer.py::test_graph_query_transport_error_returns_5
        - tests/test_graph_indexer.py::test_graph_query_unexpected_http_returns_1
        - tests/test_graph_indexer.py::test_graph_impact_http_5xx_returns_4
        - tests/test_graph_indexer.py::test_index_usage_error_missing_commit_sha
    - id: 7
      status: MET
      evidence: "200 path calls _print_stdout_raw (same as index/reindex)"
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_success -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_success
    - id: 8
      status: MET
      evidence: "No _http_request when token or base_url missing; counter stays empty"
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2 tests/test_graph_indexer.py::test_graph_query_missing_base_url_returns_2 -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2
        - tests/test_graph_indexer.py::test_graph_query_missing_base_url_returns_2
    - id: 9
      status: MET
      evidence: "build_parser registers query and impact with required flags per cursor-pilot"
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_help_returns_0 tests/test_graph_indexer.py::test_graph_impact_help_returns_0 -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_help_returns_0
        - tests/test_graph_indexer.py::test_graph_impact_help_returns_0
    - id: 10
      status: MET
      evidence: "_get_bearer_and_print centralizes transport + status mapping; _cmd_query/_cmd_impact build URLs only"
      run_result: "code review: graph_indexer.py; reindex-status uses same helper"
      covering_tests:
        - tests/test_graph_indexer.py::test_reindex_status_success
        - tests/test_graph_indexer.py::test_graph_query_success
        - tests/test_graph_indexer.py::test_graph_impact_success
    - id: 11
      status: MET
      evidence: "Placeholder tests removed; eight named tests plus help and missing base added"
      run_result: "pytest tests/test_graph_indexer.py -q: 28 passed"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_success
        - tests/test_graph_indexer.py::test_graph_query_with_limit
        - tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2
        - tests/test_graph_indexer.py::test_graph_query_http_4xx_returns_3_and_unwraps_detail
        - tests/test_graph_indexer.py::test_graph_query_transport_error_returns_5
        - tests/test_graph_indexer.py::test_graph_query_unexpected_http_returns_1
        - tests/test_graph_indexer.py::test_graph_impact_success
        - tests/test_graph_indexer.py::test_graph_impact_with_depth
        - tests/test_graph_indexer.py::test_graph_impact_http_5xx_returns_4
        - tests/test_graph_indexer.py::test_graph_query_help_returns_0
        - tests/test_graph_indexer.py::test_graph_impact_help_returns_0
        - tests/test_graph_indexer.py::test_graph_query_missing_base_url_returns_2
    - id: 12
      status: MET
      evidence: "run(['query','--help']) and run(['impact','--help']) return 0"
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_help_returns_0 tests/test_graph_indexer.py::test_graph_impact_help_returns_0 -q PASSED; python3 -m canon_systems.cli graph query|impact --help exit 0"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_help_returns_0
        - tests/test_graph_indexer.py::test_graph_impact_help_returns_0
    - id: 13
      status: MET
      evidence: "test_query_placeholder and test_impact_placeholder deleted; behavior covered by new GET tests"
      run_result: "pytest tests/test_graph_indexer.py -q passes; grep -q test_query_placeholder returns false"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2
    - id: 14
      status: MET
      evidence: "README.md canon commands table: two rows after reindex-status per pilot"
      run_result: "manual file review; no reflow of prior rows"
      covering_tests: []
    - id: 15
      status: MET
      evidence: "CHANGELOG [Unreleased] ### Added: E3-T3 bullet prepended at top"
      run_result: "manual file review"
      covering_tests: []
    - id: 16
      status: MET
      evidence: "docs/SYSTEM-WORKFLOW.md §6 new Graph reads bullet"
      run_result: "manual file review"
      covering_tests: []
    - id: 17
      status: MET
      evidence: "Edits only under five allowlisted paths; no backend/, cli.py, or forbidden files"
      run_result: "diff scope: five files only"
      covering_tests: []
END_HANDOFF_TO_QA
```
