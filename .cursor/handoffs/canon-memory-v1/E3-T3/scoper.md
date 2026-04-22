# E3-T3 Scoper Packet — canon graph query + canon graph impact CLI

## SCOPE SUMMARY

E3-T3 replaces the E3-T2 `query`/`impact` placeholders in `src/canon_systems/graph_indexer.py` with real stdlib-only GET implementations that hit the existing axon-service `GET /axon/{c}/{r}/query` and `GET /axon/{c}/{r}/impact` endpoints (provided by E3-T1). JSON output echoes the axon wire shape (`nodes`, `edges`, `scores`, `source_spans` for query; `symbol`, `depth`, `upstream`, `downstream` for impact). Inherits `AXON_SERVICE_URL`/`AXON_SERVICE_TOKEN` env layering + Bearer auth + 0/1/2/3/4/5 exit-code catalog from E3-T2. No new backend work.

## SCOPE PACKET

### Identifiers
- handoff_id: `handoff_20260422_e3t3_graph_read_cli`
- branch: `wave/3/canon-memory-v1` (tip 35af637)

### Story — acceptanceCriteria (17)
1. `canon graph query --commit-sha <sha> --company-id <c> --repository-id <r> --q <query-string>` GETs `/axon/{c}/{r}/query?q=<urlencoded>&commit_sha=<sha>[&limit=<n>]` with Bearer and prints the response body on 200.
2. `--limit` optional; only appended to URL when set.
3. `canon graph impact --commit-sha <sha> --company-id <c> --repository-id <r> --symbol <sym>` GETs `/axon/{c}/{r}/impact?symbol=<urlencoded>&commit_sha=<sha>[&depth=<n>]` with Bearer.
4. `--depth` optional; only appended when set.
5. Env fallbacks: `--base-url` → `AXON_SERVICE_URL`; `--service-token` → `AXON_SERVICE_TOKEN`. Missing → exit 2 with usage message.
6. Exit codes: 0 success, 1 unexpected status, 2 usage/argparse, 3 HTTP 4xx (detail unwrapped to stderr), 4 HTTP 5xx, 5 transport.
7. Output on 200: raw JSON body printed to stdout (no re-formatting).
8. No HTTP on usage errors (assert via monkeypatch counter).
9. `build_parser()` replaces the two empty placeholder subparsers with real argparse groups exposing the flags above.
10. `_cmd_query(args)` and `_cmd_impact(args)` are refactored from placeholders → real implementations sharing a helper for URL building + response mapping.
11. `tests/test_graph_indexer.py` updates:
    - Remove or replace `test_query_placeholder_does_not_call_http` + `test_impact_placeholder_does_not_call_http` with equivalent named tests that verify GET semantics.
    - New tests: `test_graph_query_success`, `test_graph_query_with_limit`, `test_graph_query_missing_token_returns_2`, `test_graph_query_http_4xx_returns_3_and_unwraps_detail`, `test_graph_query_transport_error_returns_5`, `test_graph_impact_success`, `test_graph_impact_with_depth`, `test_graph_impact_http_5xx_returns_4`. (≥8 new tests.)
12. `canon graph query --help` / `canon graph impact --help` exit 0 with distinct usage.
13. Existing E3-T2 tests untouched except the two placeholder tests being replaced (convert not delete — rename + rewrite body is acceptable per append-only-where-possible; document exact mapping in implementer packet).
14. README additive: add `canon graph query` and `canon graph impact` rows to the canon commands table (two rows below existing `canon graph index` / `canon graph reindex-status`).
15. CHANGELOG additive: prepend E3-T3 bullet at TOP of `[Unreleased] ### Added`.
16. docs/SYSTEM-WORKFLOW.md §6 additive bullet: "Graph reads: `canon graph query` / `canon graph impact` hit axon-service GET /query and /impact — pure RPC; inherit `AXON_SERVICE_URL`/`AXON_SERVICE_TOKEN` env layering; `source_spans` in query response enables agents to cite graph-backed evidence."
17. Forbidden surfaces untouched: backend/state-api/**, backend/knowledge-api/**, backend/shared/**, .cursor/rules/**, .cursor/plans/**, src/canon_systems/{cli,checkpoint_cli,flow_audit,qa_validate,memory_health,checkpoints,checkpoint_cli}.py (cli.py is NOT modified — E3-T2 already registered the `graph` subparser).

### Repository
- primaryLanguages: Python
- testFramework: pytest
- relevantFiles: src/canon_systems/graph_indexer.py, tests/test_graph_indexer.py, README.md, CHANGELOG.md, docs/SYSTEM-WORKFLOW.md, backend/axon-service/axon_service/routers/{query,impact}.py (READ-ONLY wire reference)

### Constraints
- dependencies: E3-T1 (axon /query /impact routes), E3-T2 (graph_indexer HTTP seam)
- mustNotBreak: canon graph index / reindex-status (existing 18 CLI tests + 16 service tests)

### Prior work references
- peer:src/canon_systems/graph_indexer.py (E3-T2 self-peer) — HTTP seam, exit codes, `_resolve_base_url`, `_resolve_token`, `_unwrap_detail`, `_print_stdout_raw`
- peer:backend/axon-service/axon_service/routers/{query.py,impact.py} (E3-T1) — GET wire shape

### ac_traceability

| # | Target | Test |
|---|---|---|
| 1-2 | graph_indexer.py::_cmd_query, build_parser query | tests/test_graph_indexer.py::test_graph_query_success, ::test_graph_query_with_limit |
| 3-4 | graph_indexer.py::_cmd_impact, build_parser impact | tests/test_graph_indexer.py::test_graph_impact_success, ::test_graph_impact_with_depth |
| 5 | _resolve_base_url/_resolve_token (reused) | tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2 |
| 6 | exit code mapping | tests/test_graph_indexer.py (all query/impact cases) |
| 7 | stdout raw body | tests/test_graph_indexer.py::test_graph_query_success (capsys) |
| 8 | no HTTP on usage error | tests/test_graph_indexer.py::test_graph_query_missing_token_returns_2 (counter assertion) |
| 9-10 | build_parser + _cmd_* | tests/test_graph_indexer.py (help + dispatch) |
| 11 | test file updates | tests/test_graph_indexer.py new tests |
| 12 | --help | tests/test_graph_indexer.py::test_graph_query_help + impact help |
| 13 | placeholder test replacement | tests/test_graph_indexer.py (renamed from E3-T2) |
| 14 | README | grep |
| 15 | CHANGELOG | grep |
| 16 | SYSTEM-WORKFLOW | grep |
| 17 | Forbidden surfaces | git diff allowlist |

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: E3-T3 replaces E3-T2 query/impact placeholders in graph_indexer.py with real GET implementations hitting axon-service /query and /impact routes. Inherits HTTP seam + exit codes + env layering. Additive living-spec. No backend changes.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260422_e3t3_graph_read_cli"
    story:
      title: "canon graph query + canon graph impact CLI"
      acceptanceCriteria:
        - "canon graph query --commit-sha --company-id --repository-id --q [--limit N] [--base-url] [--service-token] GETs axon query endpoint with Bearer; prints raw JSON body on 200."
        - "canon graph impact --commit-sha --company-id --repository-id --symbol [--depth N] [--base-url] [--service-token] GETs axon impact endpoint with Bearer."
        - "Exit codes 0/1/2/3/4/5 inherited from graph_indexer."
        - "Env fallbacks AXON_SERVICE_URL/AXON_SERVICE_TOKEN."
        - "Usage error (missing base-url or token) exits 2 and makes no HTTP call."
        - "FastAPI detail unwrapped to stderr on 4xx."
        - "tests/test_graph_indexer.py has ≥8 new tests covering both commands (success with/without optional flags, 4xx, 5xx, transport, usage error, help)."
        - "Placeholder tests test_query_placeholder_does_not_call_http + test_impact_placeholder_does_not_call_http replaced by real behavioral tests."
        - "README table updated additively with canon graph query + canon graph impact rows."
        - "CHANGELOG prepends E3-T3 bullet at top of [Unreleased] ### Added."
        - "docs/SYSTEM-WORKFLOW.md §6 additive bullet on graph reads."
        - "No edits under forbidden surfaces."
        - "cli.py already wires `graph` subparser (from E3-T2); no change needed."
    constraints:
      dependencies: ["E3-T1", "E3-T2"]
      mustNotBreak: ["canon graph index", "canon graph reindex-status", "18 existing CLI tests minus the 2 placeholder tests being replaced"]
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
