# E3-T3 Cursor-Pilot Prompt

<!-- CURSOR_PILOT_PROMPT: canon-memory-v1/E3-T3 (flow-audit required token) -->

## ROLE
You are the implementer for Canon Memory Platform v1, Wave 3, Task E3-T3. Work on branch `wave/3/canon-memory-v1` (tip 35af637).

## TASK
Replace the stub `_cmd_query`/`_cmd_impact` placeholders in `src/canon_systems/graph_indexer.py` with real stdlib-only HTTP GET implementations that call the existing axon-service `/query` and `/impact` routes. Update `build_parser()` to expose real argparse options. Refactor the two E3-T2 placeholder tests into real behavioral tests, and add enough new tests to cover both commands. Update additive living-spec surfaces (CHANGELOG, README, SYSTEM-WORKFLOW).

## CONTEXT

### HTTP seam (already in graph_indexer.py)
- `_http_request(url, *, method, headers=None, body=None, timeout=30.0) -> (status, bytes, headers)`
- `TransportError` raised on urllib transport failure
- `_resolve_base_url(args)` → CLI flag or `AXON_SERVICE_URL` env
- `_resolve_token(args)` → CLI flag or `AXON_SERVICE_TOKEN` env
- `_unwrap_detail(body: bytes) -> str` → FastAPI `{"detail": "..."}` unwrap
- `_print_stdout_raw(body: bytes) -> None` → raw bytes to stdout
- `EXIT_OK=0, EXIT_SERVER=1, EXIT_USAGE=2, EXIT_HTTP_4XX=3, EXIT_HTTP_5XX=4, EXIT_TRANSPORT=5`

### Axon-service wire shape (READ-ONLY — do not modify)
- `GET /axon/{company_id}/{repository_id}/query?q=<str>&commit_sha=<str>[&limit=<int>]`
  - 200 body: `{"company_id", "repository_id", "commit_sha", "query", "limit", "results": [{"id","score","source_spans":[...]}]}` (authoritative shape in `backend/axon-service/axon_service/routers/query.py`; CLI treats as opaque JSON and prints raw bytes).
- `GET /axon/{company_id}/{repository_id}/impact?symbol=<str>&commit_sha=<str>[&depth=<int>]`
  - 200 body: `{"company_id","repository_id","commit_sha","symbol","depth","upstream":[...],"downstream":[...]}`.
- Both require `Authorization: Bearer <AXON_SERVICE_TOKEN>`; 401 on missing, 403 on mismatched token.

### Invariants
1. **Pure RPC, no local inspection**: These commands call HTTP only — no repo walks, no file I/O.
2. **Stdlib only**: No requests/httpx/etc. Use `urllib.request` via the `_http_request` seam.
3. **Raw stdout on 200**: print the response bytes verbatim (the service already returns JSON; do not re-encode).
4. **No HTTP on usage error**: If base-url or token missing, print error to stderr and return `EXIT_USAGE` before any `_http_request` call.
5. **Env inheritance**: Flags override env; env is the fallback for both `--base-url` and `--service-token`.

## REPOSITORY

### Files to modify
- `src/canon_systems/graph_indexer.py` — replace `_cmd_query`, `_cmd_impact`, and the two `sp.add_parser("query")` / `sp.add_parser("impact")` lines in `build_parser()`.
- `tests/test_graph_indexer.py` — replace the two placeholder tests with real tests and add more.
- `README.md` — additive rows in the canon commands table.
- `CHANGELOG.md` — prepend E3-T3 bullet at top of `[Unreleased] ### Added`.
- `docs/SYSTEM-WORKFLOW.md` — additive bullet in §6 on graph reads.

### Files NOT to modify (forbidden surfaces)
- backend/**, infra/**, .cursor/rules/**, .cursor/plans/**, src/canon_systems/cli.py, src/canon_systems/checkpoint_cli.py, src/canon_systems/{flow_audit,qa_validate,memory_health,checkpoints}.py, src/canon_systems/templates/**.

## IMPLEMENTATION SPECIFICATION

### graph_indexer.py — new `_cmd_query`
```python
def _cmd_query(args: argparse.Namespace) -> int:
    base_url = _resolve_base_url(args)
    if not base_url:
        print(f"error: missing --base-url or {ENV_BASE}", file=sys.stderr)
        return EXIT_USAGE
    token = _resolve_token(args)
    if not token:
        print(f"error: missing --service-token or {ENV_TOKEN}", file=sys.stderr)
        return EXIT_USAGE
    params = [f"q={quote(args.q, safe='')}", f"commit_sha={quote(args.commit_sha, safe='')}"]
    if args.limit is not None:
        params.append(f"limit={int(args.limit)}")
    url = f"{base_url}/axon/{args.company_id}/{args.repository_id}/query?{'&'.join(params)}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        status, resp_body, _h = _http_request(url, method="GET", headers=headers, timeout=30.0)
    except TransportError as exc:
        print(f"error: transport: {exc}", file=sys.stderr)
        return EXIT_TRANSPORT
    if status == 200:
        _print_stdout_raw(resp_body)
        return EXIT_OK
    if 400 <= status <= 499:
        print(_unwrap_detail(resp_body), file=sys.stderr)
        return EXIT_HTTP_4XX
    if 500 <= status <= 599:
        return EXIT_HTTP_5XX
    print(f"error: unexpected HTTP {status}", file=sys.stderr)
    return EXIT_SERVER
```

### graph_indexer.py — new `_cmd_impact`
Same structure, with:
- Query params: `symbol=<urlencoded>`, `commit_sha=<urlencoded>`, optional `depth=<int>`.
- URL path: `/axon/{company_id}/{repository_id}/impact`.

### graph_indexer.py — `build_parser()` updates
Replace:
```python
sp.add_parser("query", help="Deferred (E3-T3).")
sp.add_parser("impact", help="Deferred (E3-T3).")
```
With:
```python
pq = sp.add_parser("query", help="GET /axon/.../query (graph retrieval).")
pq.add_argument("--commit-sha", required=True)
pq.add_argument("--company-id", required=True)
pq.add_argument("--repository-id", required=True)
pq.add_argument("--q", required=True, help="Free-text query string.")
pq.add_argument("--limit", type=int, default=None)
pq.add_argument("--base-url", default=None)
pq.add_argument("--service-token", default=None)

pimp = sp.add_parser("impact", help="GET /axon/.../impact (blast radius).")
pimp.add_argument("--commit-sha", required=True)
pimp.add_argument("--company-id", required=True)
pimp.add_argument("--repository-id", required=True)
pimp.add_argument("--symbol", required=True, help="Fully-qualified symbol or file path.")
pimp.add_argument("--depth", type=int, default=None)
pimp.add_argument("--base-url", default=None)
pimp.add_argument("--service-token", default=None)
```

### tests/test_graph_indexer.py — required new tests (minimum 8)

Replace:
- `test_query_placeholder_does_not_call_http` → remove.
- `test_impact_placeholder_does_not_call_http` → remove.

Add (minimum):
1. `test_graph_query_success` — monkeypatch `_http_request` to return 200 with JSON body; assert capsys stdout contains body and exit 0; assert the URL + headers recorded match `/axon/acme/repo1/query?q=hello&commit_sha=abc` and Bearer token.
2. `test_graph_query_with_limit` — verify `limit=25` appended when `--limit 25` given.
3. `test_graph_query_missing_token_returns_2` — unset env + no `--service-token`; assert exit 2 and `_http_request` is never called (counter).
4. `test_graph_query_http_4xx_returns_3_and_unwraps_detail` — return 404 with `{"detail":"no snapshot"}`; assert stderr contains `no snapshot` and exit 3.
5. `test_graph_query_transport_error_returns_5` — seam raises `TransportError`; assert exit 5.
6. `test_graph_impact_success` — happy path with `--symbol foo.bar`; assert URL + Bearer.
7. `test_graph_impact_with_depth` — verify `depth=3` appended.
8. `test_graph_impact_http_5xx_returns_4` — return 503; assert exit 4.

Reuse the monkeypatch pattern already in `tests/test_graph_indexer.py` (the `_Capturer` / direct monkeypatch of `graph_indexer._http_request`).

### README.md additive
Add two rows to the canon commands table, immediately after the `canon graph reindex-status` row:

```
| `canon graph query --commit-sha <sha> --company-id <c> --repository-id <r> --q <str> [--limit N]` | Retrieve graph-backed snippets from axon-service (pure RPC). |
| `canon graph impact --commit-sha <sha> --company-id <c> --repository-id <r> --symbol <sym> [--depth N]` | Return upstream/downstream blast radius from axon-service. |
```

Match the existing table's column structure verbatim.

### CHANGELOG.md additive
Prepend to the TOP of `[Unreleased] ### Added`:
```
- **E3-T3** `canon graph query` and `canon graph impact` CLI subcommands: stdlib-only GET clients over axon-service `/query` and `/impact`, with Bearer auth, env-layered credentials (`AXON_SERVICE_URL`/`AXON_SERVICE_TOKEN`), and exit codes `0/1/2/3/4/5`. Pure RPC — no repo walks, no local caches; tests cover success, 4xx with detail unwrap, 5xx, transport, and usage-error (no-HTTP-on-usage-error) cases.
```

### docs/SYSTEM-WORKFLOW.md additive
Append a new bullet at the end of the §6 graph-retrieval subsection:
```
- **Graph reads**: `canon graph query` and `canon graph impact` are pure-RPC clients over `backend/axon-service` `GET /query` and `GET /impact`. They inherit `AXON_SERVICE_URL`/`AXON_SERVICE_TOKEN` env layering (flag > env > error-with-exit-2) and never touch the repo filesystem. `query` returns a body with `results[].source_spans` so agents can cite graph-backed evidence; `impact` returns `upstream`/`downstream` lists keyed by symbol. Writes remain sole-domain of `canon graph index` (E3-T2).
```

## REASONING

1. Start by reading the current `graph_indexer.py` (lines 1-150) to confirm the helpers and shared exit-code catalog are still identical to what the scoper packet describes.
2. Read `tests/test_graph_indexer.py` to find the `_Capturer` helper / `monkeypatch` shape used for reindex-status tests — reuse it verbatim.
3. Read `backend/axon-service/axon_service/routers/query.py` and `.../impact.py` ONLY to confirm the URL path + query-param names match the wire expectation (do not modify).
4. Edit `graph_indexer.py`: replace `_cmd_query`, `_cmd_impact`, and the two empty placeholder subparsers.
5. Edit `tests/test_graph_indexer.py`: delete the two placeholder tests, add the 8+ new tests.
6. Edit README, CHANGELOG, SYSTEM-WORKFLOW additively.
7. Run `pytest tests/test_graph_indexer.py -q` — expect all prior non-placeholder tests + 8 new tests to PASS.
8. Run `pytest -q` at repo root to confirm no cross-suite regressions.
9. Emit `HANDOFF_TO_QA` with the acceptance criteria checklist mapped to named test functions.

## OUTPUT FORMAT

Emit a HANDOFF_TO_QA block with:
- `handoff_id: handoff_20260422_e3t3_graph_read_cli`
- `branch: wave/3/canon-memory-v1`
- `files_modified:` exact list (5 files)
- `acceptance_criteria:` 17 ACs each with `status: MET`, `evidence`, `run_result`, and `covering_tests:` (YAML block-style list of `tests/test_graph_indexer.py::<test>` entries).
- `suite_result:` pytest final line for both the focused and full runs.

## STOP CONDITIONS

Stop and surface a blocker (do not improvise) if:
- Axon-service query/impact wire shape differs from the scoper packet (e.g., query-param names changed).
- `_resolve_base_url` / `_resolve_token` / `_unwrap_detail` helpers no longer exist at expected signatures.
- Placeholder tests cannot be located for deletion.
- Any forbidden-surface edit would be required (e.g., backend/ or cli.py).
