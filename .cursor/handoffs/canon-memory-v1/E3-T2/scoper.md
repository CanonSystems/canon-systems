# E3-T2 Scoper Packet — Indexer pipeline for repo changes

## SCOPE SUMMARY

E3-T2 adds a **stdlib-only `canon graph` CLI** that POSTs stub-but-valid graph snapshots to the existing axon `/index` API (mirroring the `canon checkpoint` REMAINDER delegation pattern), exposes a new Bearer-gated `GET /axon/{c}/{r}/reindex-status?commit_sha=` endpoint backed by existing AxonStore metadata, documents pure-RPC reads for query/impact, and ships a pre-push hook script plus a non-gating GitHub Actions `workflow_dispatch` scaffold. All verifiable with mocked HTTP + service tests. No forbidden-surface touches.

## SCOPE PACKET

### Identifiers
- handoff_id: `handoff_20260422_e3t2_indexer_pipeline`
- branch: `wave/3/canon-memory-v1` (tip e4fd6ed)

### Story
**acceptanceCriteria (21):**
1. Stub incremental/full indexer in `graph_indexer` POSTs bearer-auth'd index requests with `AXON_SERVICE_URL`/`AXON_SERVICE_TOKEN` env fallbacks and deterministic minimal nodes/edges (one node per changed file; same-dir edges).
2. Index run measures elapsed time; if >60s, stderr warning; success still exit 0; stub tests complete in <1s and still cover warning path (injected clock / mocked long response).
3. Exit codes: 0 success, 1 server/app error, 2 usage, 3 HTTP 4xx, 4 HTTP 5xx, 5 transport.
4. `canon graph` registered in `cli.py` with `nargs=argparse.REMAINDER` delegating to `graph_indexer.run`; subcommands `index` and `reindex-status`.
5. GET `/axon/{company_id}/{repository_id}/reindex-status?commit_sha=<sha>` returns `{company_id, repository_id, commit_sha, status: "ready"|"missing"|"error", uploaded_at, node_count, edge_count, size_bytes}`; missing meta → `status=missing`; Bearer-gated.
6. `canon graph reindex-status` CLI exercises the new endpoint; router wired in `backend/axon-service/axon_service/api.py`.
7. `scripts/hooks/pre-push-graph-index.sh` exists, executable, documented in README; not auto-installed.
8. `.github/workflows/axon-reindex.yml` scaffold with `workflow_dispatch` using `AXON_SERVICE_URL` + `AXON_SERVICE_TOKEN` secrets; not a required check.
9. `docs/SYSTEM-WORKFLOW.md` + `backend/axon-service/README.md` state query/impact are pure RPC; indexing only via `canon graph index` (pre-push/CI).
10. README + CHANGELOG document new commands under `[Unreleased] ### Added` (top bullet).
11. `tests/test_graph_indexer.py` ≥10 tests with HTTP seam mocked; no live network.
12. `backend/axon-service/axon_service_tests/test_reindex_status.py` ≥3 tests: ready, missing, auth.
13. `graph_indexer` separates write (index) from read argv paths; no POST on placeholder query/impact argv (test asserts).
14. Integration test satisfies backlog done_signal: POST index then GET reindex-status returns `status=ready`.
15. No edits under backend/state-api/**, backend/knowledge-api/**, backend/shared/**, .cursor/rules/**, .cursor/plans/**.
16. No modifications to existing test function bodies; append-only.
17. No modifications to checkpoint_cli.py, flow_audit.py, qa_validate.py, memory_health.py, checkpoints.py.
18. FastAPI `detail` unwrap pattern from checkpoint_cli mirrored.
19. Env fallbacks: `--base-url`/`--service-token` resolve to `AXON_SERVICE_URL`/`AXON_SERVICE_TOKEN` when CLI flags omitted.
20. `--full` flag builds full-repo payload (stub: `git ls-files` output); `--changed-files` accepts a space-separated list.
21. `--help` prints usage for `canon graph index` and `canon graph reindex-status` (two distinct help blocks).

### Repository
- primaryLanguages: Python
- testFramework: pytest
- relevantFiles: src/canon_systems/{graph_indexer.py,cli.py,checkpoint_cli.py}, backend/axon-service/axon_service/{routers/{status.py,index.py},api.py,storage.py,auth.py}, backend/axon-service/axon_service_tests/test_reindex_status.py, tests/test_graph_indexer.py, scripts/hooks/pre-push-graph-index.sh, .github/workflows/axon-reindex.yml, docs/SYSTEM-WORKFLOW.md, README.md, backend/axon-service/README.md, CHANGELOG.md

### Constraints
- dependencies: E3-T1 (axon-service /index, AxonStore, bearer_auth)
- mustNotBreak: canon checkpoint CLI, existing axon /index /query /impact /healthz, root pytest + axon_service_tests

### Prior work references
- peer:backend/axon-service (E3-T1) — POST /index, AxonStore, bearer_auth
- peer:src/canon_systems/checkpoint_cli.py — REMAINDER CLI + HTTP seam + detail unwrap + run(argv)->int

### ac_traceability (21 ACs)

| # | Criterion | Target | Test |
|---|---|---|---|
| 1 | Stub payload POST | graph_indexer.py | tests/test_graph_indexer.py (payload shape + full/changed) |
| 2 | 60s warning | graph_indexer.py | tests/test_graph_indexer.py (mocked slow response) |
| 3 | Exit codes 0-5 | graph_indexer.py | tests/test_graph_indexer.py (per-code tests) |
| 4 | cli.py REMAINDER | cli.py, graph_indexer.py | tests/test_graph_indexer.py (help/delegation) |
| 5 | reindex-status endpoint | routers/status.py, storage.py | axon_service_tests/test_reindex_status.py (ready/missing/auth) |
| 6 | reindex-status CLI | graph_indexer.py, api.py | tests/test_graph_indexer.py (subcommand) |
| 7 | pre-push script | scripts/hooks/pre-push-graph-index.sh | grep + exec bit check |
| 8 | axon-reindex.yml | .github/workflows/axon-reindex.yml | static YAML inspection |
| 9 | Docs invariant | docs/SYSTEM-WORKFLOW.md, backend/axon-service/README.md | grep |
| 10 | Living spec | README.md, CHANGELOG.md | grep |
| 11 | CLI tests ≥10 | tests/test_graph_indexer.py | pytest count |
| 12 | Service tests ≥3 | axon_service_tests/test_reindex_status.py | pytest count |
| 13 | Read/write separation | graph_indexer.py | tests/test_graph_indexer.py (query argv no POST) |
| 14 | Integration done_signal | axon_service_tests/test_reindex_status.py | named integration test |
| 15 | Forbidden surfaces | (process) | git diff allowlist |
| 16 | Append-only tests | all tests | diff review |
| 17 | Stable modules untouched | (process) | git diff allowlist |
| 18 | detail unwrap | graph_indexer.py | tests/test_graph_indexer.py (422/400 detail) |
| 19 | Env fallbacks | graph_indexer.py | tests/test_graph_indexer.py (env-only) |
| 20 | --full / --changed-files | graph_indexer.py | tests/test_graph_indexer.py (both modes) |
| 21 | --help output | graph_indexer.py | tests/test_graph_indexer.py (help) |

## HANDOFF_TO_CURSOR_PILOT

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: E3-T2 adds a stdlib-only canon graph CLI that POSTs stub graph snapshots to the existing axon index API, exposes a new GET reindex-status API backed by existing AxonStore metadata, documents pure-RPC reads, and ships a pre-push hook + non-gating GitHub workflow scaffold. Mocked HTTP + axon tests prove behavior without touching forbidden backends or stable CLI modules.
  scope_packet:
    identifiers:
      handoff_id: "handoff_20260422_e3t2_indexer_pipeline"
    story:
      title: "Indexer pipeline for repo changes"
      acceptanceCriteria:
        - "Stub indexer POSTs bearer-auth'd index requests with AXON_SERVICE_URL/AXON_SERVICE_TOKEN env fallbacks and deterministic minimal nodes/edges."
        - "Elapsed > 60s emits stderr warning; success still exit 0; stub tests complete <1s; warning path covered via mocked slow response."
        - "Exit codes: 0/1/2/3/4/5 per spec."
        - "canon graph registered in cli.py REMAINDER delegating to graph_indexer.run; subcommands index and reindex-status."
        - "GET /axon/{c}/{r}/reindex-status?commit_sha= returns specified JSON; missing→'missing'; Bearer-gated."
        - "reindex-status CLI + router wired in api.py."
        - "scripts/hooks/pre-push-graph-index.sh exists + executable + documented; not auto-installed."
        - ".github/workflows/axon-reindex.yml scaffold with workflow_dispatch + AXON_* secrets; not required check."
        - "docs/SYSTEM-WORKFLOW.md and backend/axon-service/README.md enforce pure-RPC read invariant."
        - "README + CHANGELOG additive."
        - "tests/test_graph_indexer.py ≥10 tests; HTTP mocked."
        - "axon_service_tests/test_reindex_status.py ≥3 tests (ready, missing, auth)."
        - "graph_indexer separates write/read argv; placeholder query/impact argv do not POST."
        - "Integration test: POST index then GET reindex-status ready (done_signal)."
        - "Forbidden surfaces untouched."
        - "Append-only tests; no modification of existing test bodies."
        - "Do not touch checkpoint_cli.py, flow_audit.py, qa_validate.py, memory_health.py, checkpoints.py."
    constraints:
      dependencies: ["E3-T1"]
      mustNotBreak: ["canon checkpoint CLI", "existing axon routes", "root pytest + axon_service_tests"]
    dor_checklist:
      repo_ref_verification: "pass"
      ac_traceability: "pass"
END_HANDOFF_TO_CURSOR_PILOT
```
