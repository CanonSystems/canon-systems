# E3-T3 QA Gate Packet — canon graph query + canon graph impact CLI

## Verification summary

- Focused suite: `pytest tests/test_graph_indexer.py -q` → `28 passed in 0.04s`
- Full suite:    `pytest -q` → `293 passed in 3.95s`
- Modified files (exactly the 5 allowlisted, plus tolerated auto-churn):
  - `CHANGELOG.md`
  - `README.md`
  - `docs/SYSTEM-WORKFLOW.md`
  - `src/canon_systems/graph_indexer.py`
  - `tests/test_graph_indexer.py`
  - (out-of-scope churn ignored: `.canon/memory/capture-failures.log`, `.canon/memory/capture-latest.json`)

```
GATE_RESULTS
  handoff_id: "handoff_20260422_e3t3_graph_read_cli"
  task_id: "E3-T3"
  overall_verdict: PASS
  verdict: PASS
  regression_checked: true
  iterations: 0
  suite_result: "focused: 28 passed in 0.04s; full: 293 passed in 3.95s"
  acceptance_criteria:
    - id: AC-1
      summary: "canon graph query GETs /axon/{c}/{r}/query?q=&commit_sha=[&limit=] with Bearer and prints raw JSON body on 200."
      status: MET
      evidence: "test_graph_query_success monkeypatches _http_request, asserts GET URL contains /axon/acme/repo1/query?q=hello&commit_sha=abc, Authorization: Bearer header, exit 0, and raw JSON body on stdout."
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_success -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_success
    - id: AC-2
      summary: "--limit only appended to URL when provided."
      status: MET
      evidence: "test_graph_query_with_limit asserts 'limit=25' in captured URL; test_graph_query_success asserts no 'limit=' token when --limit absent."
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_with_limit -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_with_limit
        - tests/test_graph_indexer.py::test_graph_query_success
    - id: AC-3
      summary: "canon graph impact GETs /axon/{c}/{r}/impact?symbol=&commit_sha=[&depth=] with Bearer."
      status: MET
      evidence: "test_graph_impact_success monkeypatches _http_request and asserts URL path /axon/acme/repo1/impact with symbol+commit_sha query and Bearer Authorization header; exit 0."
      run_result: "pytest tests/test_graph_indexer.py::test_graph_impact_success -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_impact_success
    - id: AC-4
      summary: "--depth only appended to URL when provided."
      status: MET
      evidence: "test_graph_impact_with_depth asserts 'depth=3' appears in captured URL; test_graph_impact_success asserts no 'depth=' token when --depth absent."
      run_result: "pytest tests/test_graph_indexer.py::test_graph_impact_with_depth -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_impact_with_depth
        - tests/test_graph_indexer.py::test_graph_impact_success
    - id: AC-5
      summary: "--base-url falls back to AXON_SERVICE_URL env; --service-token falls back to AXON_SERVICE_TOKEN; missing → exit 2 with usage message."
      status: MET
      evidence: "test_graph_query_missing_token_returns_2 unsets AXON_SERVICE_TOKEN and omits flag; asserts exit 2 and stderr mentions missing token. test_graph_query_missing_base_url_returns_2 covers the base-url case symmetrically."
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2 tests/test_graph_indexer.py::test_graph_query_missing_base_url_returns_2 -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2
        - tests/test_graph_indexer.py::test_graph_query_missing_base_url_returns_2
    - id: AC-6
      summary: "Exit codes: 0 success, 1 unexpected, 2 usage, 3 HTTP 4xx (detail unwrapped), 4 HTTP 5xx, 5 transport."
      status: MET
      evidence: "Each code mapped by a dedicated test: 0 (success), 1 (unexpected_http), 2 (missing_token/base_url), 3 (4xx_unwraps_detail — stderr contains 'no snapshot'), 4 (impact 5xx), 5 (transport_error)."
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_success tests/test_graph_indexer.py::test_graph_query_unexpected_http_returns_1 tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2 tests/test_graph_indexer.py::test_graph_query_http_4xx_returns_3_and_unwraps_detail tests/test_graph_indexer.py::test_graph_impact_http_5xx_returns_4 tests/test_graph_indexer.py::test_graph_query_transport_error_returns_5 -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_success
        - tests/test_graph_indexer.py::test_graph_query_unexpected_http_returns_1
        - tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2
        - tests/test_graph_indexer.py::test_graph_query_http_4xx_returns_3_and_unwraps_detail
        - tests/test_graph_indexer.py::test_graph_impact_http_5xx_returns_4
        - tests/test_graph_indexer.py::test_graph_query_transport_error_returns_5
    - id: AC-7
      summary: "On 200, raw JSON body is printed verbatim to stdout (no re-formatting)."
      status: MET
      evidence: "test_graph_query_success asserts capsys stdout equals the raw bytes returned by the seam (reuses _print_stdout_raw shared with index/reindex)."
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_success -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_success
        - tests/test_graph_indexer.py::test_graph_impact_success
    - id: AC-8
      summary: "No HTTP request is issued on usage errors (asserted via monkeypatch counter)."
      status: MET
      evidence: "test_graph_query_missing_token_returns_2 and test_graph_query_missing_base_url_returns_2 monkeypatch _http_request with a counter; assert counter == 0 after a usage-error invocation."
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2 tests/test_graph_indexer.py::test_graph_query_missing_base_url_returns_2 -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2
        - tests/test_graph_indexer.py::test_graph_query_missing_base_url_returns_2
    - id: AC-9
      summary: "build_parser() replaces the two empty placeholder subparsers with real argparse groups exposing the documented flags."
      status: MET
      evidence: "test_graph_query_help_returns_0 and test_graph_impact_help_returns_0 invoke the real parser with --help; both exit 0 with distinct usage strings (proves the subparsers are registered with real flag specs)."
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_help_returns_0 tests/test_graph_indexer.py::test_graph_impact_help_returns_0 -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_help_returns_0
        - tests/test_graph_indexer.py::test_graph_impact_help_returns_0
    - id: AC-10
      summary: "_cmd_query and _cmd_impact are refactored from placeholders to real implementations sharing a helper for URL building + response mapping."
      status: MET
      evidence: "Both commands route through the shared _get_bearer_and_print response mapper (also used by reindex-status); behavioural parity asserted via test_reindex_status_success + the query/impact success paths exercising the same helper."
      run_result: "pytest tests/test_graph_indexer.py::test_reindex_status_success tests/test_graph_indexer.py::test_graph_query_success tests/test_graph_indexer.py::test_graph_impact_success -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_reindex_status_success
        - tests/test_graph_indexer.py::test_graph_query_success
        - tests/test_graph_indexer.py::test_graph_impact_success
    - id: AC-11
      summary: "tests/test_graph_indexer.py updates: remove the two placeholder tests and add ≥8 named tests covering success, optional flags, 4xx, 5xx, transport, usage, help."
      status: MET
      evidence: "12 new named tests collected in tests/test_graph_indexer.py (query/impact: success, with_limit/with_depth, missing_token, missing_base_url, 4xx_unwrap, 5xx, transport, unexpected_http, help_returns_0 x2) — exceeds ≥8 minimum."
      run_result: "pytest tests/test_graph_indexer.py -q → 28 passed"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_success
        - tests/test_graph_indexer.py::test_graph_query_with_limit
        - tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2
        - tests/test_graph_indexer.py::test_graph_query_missing_base_url_returns_2
        - tests/test_graph_indexer.py::test_graph_query_http_4xx_returns_3_and_unwraps_detail
        - tests/test_graph_indexer.py::test_graph_query_transport_error_returns_5
        - tests/test_graph_indexer.py::test_graph_query_unexpected_http_returns_1
        - tests/test_graph_indexer.py::test_graph_impact_success
        - tests/test_graph_indexer.py::test_graph_impact_with_depth
        - tests/test_graph_indexer.py::test_graph_impact_http_5xx_returns_4
        - tests/test_graph_indexer.py::test_graph_query_help_returns_0
        - tests/test_graph_indexer.py::test_graph_impact_help_returns_0
    - id: AC-12
      summary: "canon graph query --help and canon graph impact --help exit 0 with distinct usage strings."
      status: MET
      evidence: "test_graph_query_help_returns_0 and test_graph_impact_help_returns_0 invoke run(['query','--help']) / run(['impact','--help']) and assert SystemExit code 0."
      run_result: "pytest tests/test_graph_indexer.py::test_graph_query_help_returns_0 tests/test_graph_indexer.py::test_graph_impact_help_returns_0 -q PASSED"
      covering_tests:
        - tests/test_graph_indexer.py::test_graph_query_help_returns_0
        - tests/test_graph_indexer.py::test_graph_impact_help_returns_0
    - id: AC-13
      summary: "Existing E3-T2 tests untouched except the two placeholder tests (test_query_placeholder_does_not_call_http, test_impact_placeholder_does_not_call_http) are replaced by equivalent behavioural tests."
      status: MET
      evidence: "grep confirms neither placeholder test name remains in tests/test_graph_indexer.py; reindex-status + index suite (16 prior tests) all still pass — 28 total collected, 8 E3-T2 index tests + 3 reindex + 12 new graph query/impact tests + 5 helper/setup tests still present."
      run_result: "grep -n 'test_query_placeholder\\|test_impact_placeholder' tests/test_graph_indexer.py → no matches; pytest tests/test_graph_indexer.py -q → 28 passed"
      covering_tests:
        - tests/test_graph_indexer.py::test_reindex_status_success
        - tests/test_graph_indexer.py::test_index_success_full_mode
        - tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2
    - id: AC-14
      summary: "README additive: canon graph query and canon graph impact rows appended to the canon commands table."
      status: MET
      evidence: "README.md lines 221-222 contain new rows '| `canon graph query ...` |' and '| `canon graph impact ...` |' immediately after the reindex-status row; no prior rows reflowed."
      run_result: "grep -n 'canon graph query\\|canon graph impact' README.md → lines 221, 222"
      covering_tests:
        - README.md
    - id: AC-15
      summary: "CHANGELOG additive: E3-T3 bullet prepended at TOP of [Unreleased] ### Added."
      status: MET
      evidence: "CHANGELOG.md line 12 is the E3-T3 bullet (first entry under [Unreleased] ### Added): '- **E3-T3** `canon graph query` and `canon graph impact` CLI subcommands ...'."
      run_result: "grep -n 'E3-T3' CHANGELOG.md → line 12"
      covering_tests:
        - CHANGELOG.md
    - id: AC-16
      summary: "docs/SYSTEM-WORKFLOW.md §6: additive 'Graph reads' bullet describing pure-RPC query/impact clients, env layering, and source_spans citation."
      status: MET
      evidence: "docs/SYSTEM-WORKFLOW.md line 124 contains new bullet '- **Graph reads**: canon graph query and canon graph impact are pure-RPC clients ... source_spans so agents can cite graph-backed evidence; impact returns upstream/downstream ...'."
      run_result: "grep -n 'Graph reads' docs/SYSTEM-WORKFLOW.md → line 124"
      covering_tests:
        - docs/SYSTEM-WORKFLOW.md
    - id: AC-17
      summary: "Forbidden surfaces untouched: backend/**, .cursor/rules/**, .cursor/plans/**, cli.py, checkpoint_cli.py, flow_audit/qa_validate/memory_health/checkpoints modules, templates/**."
      status: MET
      evidence: "git diff --name-only returns only 5 allowlisted files (CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md, src/canon_systems/graph_indexer.py, tests/test_graph_indexer.py) plus tolerated auto-churn (.canon/memory/capture-failures.log, .canon/memory/capture-latest.json). No backend/, cli.py, rules, plans, or forbidden module paths."
      run_result: "git diff --name-only → CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md, src/canon_systems/graph_indexer.py, tests/test_graph_indexer.py (+ ignored .canon/memory/*)"
      covering_tests:
        - src/canon_systems/graph_indexer.py
        - tests/test_graph_indexer.py
  remaining_gaps: []
  notes: |
    All 17 acceptance criteria verified. Focused suite 28/28 passing, full suite 293/293 passing, zero iterations required. Modified-files set matches the 5 allowlisted paths exactly; .canon/memory/capture-failures.log and .canon/memory/capture-latest.json are tolerated auto-generated churn per qa-gate instructions and do not constitute forbidden-surface violations. Doc-only ACs (14-17) use raw file-path evidence as instructed; behavioural ACs (1-13) map to pytest node ids in tests/test_graph_indexer.py.
END_GATE_RESULTS
```
