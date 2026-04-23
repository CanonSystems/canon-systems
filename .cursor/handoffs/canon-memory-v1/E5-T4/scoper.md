<!-- SCOPER_PACKET: E5-T4 -->

# SCOPE_PACKET — E5-T4: Read path 1 — `backend/synthesis-web` browser renderer

## SCOPE_SUMMARY

Introduce a new read-only FastAPI service `backend/synthesis-web/` that serves an HTML browser view over the S3 vault produced by E5-T2/E5-T3. It exposes a vault index, per-page markdown→HTML rendering with wikilink + backlink resolution, a deterministic JSON graph endpoint, and a capped substring search endpoint — all request-time SSR against the live S3 vault via a read-only `S3VaultReader` (HEAD-driven `x-amz-meta-content-hash` ETags). The service has zero external CDN dependencies (inline CSS, no JS initially), is tenant-scoped by `company_shorthash`/`repo_shorthash` per E5-T1, and never writes to S3. A short design spike is recorded in this packet: **request-time SSR (Option A) chosen** over static rebuild-on-publish.

State-mandate verification: `.cursor/rules/memory-platform-build-discipline.mdc` §§1–10 unchanged since E5-T3; `docs/SYSTEM-WORKFLOW.md` §§3–5 intact; `docs/VAULT-LAYOUT.md` locked at `schema_version: 1`; no backlog or rule drift detected. Current wave tip `dd13487` (E5-T3 READY_TO_MERGE) on `wave/5/canon-memory-v1`; suite baseline 390 passed.

## 1) Design spike — SSR vs. static rebuild

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Request-time SSR (per-key cache + content-hash ETag)** | Read-only; no new build pipeline; reflects publisher state immediately; `x-amz-meta-content-hash` already provides idempotent cache key; graph/backlink/search logic can evolve without re-publishing; simplest infra (single stateless service). | Cold-start latency on first hit per page; backlink index must be built on demand. | **CHOSEN** |
| B. Rebuild-on-publish (pre-rendered static HTML in S3) | Fastest page loads; trivially CDN-cacheable. | Adds a second build step to the E5-T7 auto-publish hook; doubles storage; forces publisher+renderer lockstep on version bumps; breaks if reader logic (e.g., backlink algorithm) evolves without a full re-publish. | Rejected |

**Rationale**: the S3 vault is already an idempotent, content-addressed artifact. A request-time SSR with (a) per-key in-process LRU keyed on `(rel, content_hash)`, and (b) a whole-vault backlink index refreshed when any page's content-hash changes, gives the same steady-state behavior as option B without the build-pipeline coupling. E5-T7 already re-triggers publish on RELEASE_STATUS PASS; adding a duplicate static-build step is wasted motion. SSR also keeps the renderer evolvable: when backlink/graph algorithms improve in later waves, no re-publish is required.

## 2) Scope — core backend service

### 2.1 Service layout (authoritative)

```
backend/synthesis-web/
├── pyproject.toml
├── README.md
└── synthesis_web/
    ├── __init__.py
    ├── main.py              # FastAPI app, routes, dependency wiring
    ├── reader.py            # S3VaultReader (read-only, HEAD for hash, GET for body)
    ├── renderer.py          # md→HTML; wikilink + backlink + frontmatter handling
    ├── search.py            # in-memory substring search + graph builder
    ├── cache.py             # (optional) per-key LRU keyed on content_hash
    └── templates/
        ├── base.html        # inline CSS, zero external refs
        ├── index.html       # vault-of-vaults landing
        ├── vault_home.html  # single-vault landing
        ├── page.html        # single markdown page + backlinks sidebar
        ├── graph.html       # (optional; MAY be JSON-only in v1)
        └── not_found.html   # 404 body with useful breadcrumb
synthesis_web_tests/
├── __init__.py
├── conftest.py              # mirrors backend/synthesis/synthesis_tests/conftest.py
├── _fakes.py                # DictS3Client (local; avoid cross-backend import)
├── test_healthz.py
├── test_index.py
├── test_vault_home.py
├── test_page_render.py
├── test_backlinks.py
├── test_graph.py
├── test_search.py
├── test_404.py
├── test_etag.py
└── test_zero_install.py
```

**Test-directory naming**: `synthesis_web_tests/` (NOT `tests/`) — mirrors E5-T2 precedent; prevents pytest import-path collision with repo-root `tests/` and `backend/state-api/tests/`. The backlog `done_signal` "`backend/synthesis-web/tests PASS`" is interpreted semantically (the test suite for this service passes); this deviation MUST be documented in the README and CHANGELOG per §6.

### 2.2 Route catalog

| Method | Path | Purpose | Content-Type | ETag |
|---|---|---|---|---|
| `GET` | `/healthz` | Liveness | `application/json` | — |
| `GET` | `/` | Vault-of-vaults index; lists `(company_shorthash, repo_shorthash)` pairs discovered in bucket | `text/html; charset=utf-8` | weak, deterministic over list |
| `GET` | `/v/{company_shorthash}/{repo_shorthash}/` | Vault home: link to plans, _index, graph, search | `text/html; charset=utf-8` | `x-amz-meta-content-hash` of `README.md` |
| `GET` | `/v/{company_shorthash}/{repo_shorthash}/{page_path:path}` | Render markdown page with sidebar backlinks; resolves `[[wikilinks]]` to live internal URLs | `text/html; charset=utf-8` | `x-amz-meta-content-hash` of `<prefix>/<page_path>` |
| `GET` | `/v/{company_shorthash}/{repo_shorthash}/_graph` | JSON graph `{"nodes":[{"id","label","path"}], "edges":[{"from","to"}]}` deterministic | `application/json` | hash of sorted nodes+edges |
| `GET` | `/v/{company_shorthash}/{repo_shorthash}/_search?q=...&limit=N` | JSON matches `{"q","matches":[{"path","snippet"}],"truncated":bool}`; substring over bodies; `limit` capped (default 25, max 100) | `application/json` | — |

**Path scoping rule (from E5-T1 §2)**: the two path segments after `/v/` MUST be the 8-char hex `company_shorthash` / `repo_shorthash` — never raw `company_id`/`repository_id`. The S3 prefix is `vault/<company_shorthash>/<repo_shorthash>/` (matching the publisher layout).

**ETag contract**: for any page response backed by a single S3 object, the service returns `ETag: "<x-amz-meta-content-hash>"` (quoted). On `If-None-Match` match, respond `304 Not Modified` with empty body. For aggregate responses (index, `_graph`), the ETag is the SHA-256 of the deterministically serialized payload.

### 2.3 Reader surface (`reader.py`)

Pure S3 read boundary. Signature:

```python
class S3VaultReader:
    def __init__(self, *, bucket: str, prefix: str, s3_client) -> None: ...
    def list_pages(self) -> list[str]: ...                     # relative keys
    def read_page(self, rel: str) -> bytes: ...                # raise NotFound
    def read_hash(self, rel: str) -> str: ...                  # HEAD; '' if missing
    def list_vaults(self) -> list[tuple[str, str]]: ...        # (company_shorthash, repo_shorthash)
```

Reader MUST NOT call `put_object`, `delete_object`, or `copy_object`. A test asserts this by grepping `reader.py` source for forbidden boto3 method names.

### 2.4 Renderer surface (`renderer.py`)

```python
def strip_frontmatter(md: bytes) -> tuple[dict, str]: ...
def render_markdown(md: str, *, resolve_wikilink) -> str: ...     # sanitized HTML
def resolve_wikilink(target: str, current_page: str) -> str: ...  # [[plan:x]]/[[task:y]]/[[event:z]] → URL
def build_backlink_index(pages: dict[str, bytes]) -> dict[str, list[str]]: ...
```

**Sanitization**: either use `markdown-it-py` with `html=False` (no inline HTML pass-through) or a small internal converter covering headings, paragraphs, `**bold**`/`*italic*`, inline code, fenced code blocks, unordered lists, and links — whichever the pilot chooses — but the output MUST never echo raw user-supplied HTML, and MUST never expose `<script>` tags. If a third-party library is introduced it MUST be declared in `pyproject.toml` and referenced in the README.

**Wikilink resolution**: `[[plan:<id>]]` → `/v/{c}/{r}/plans/<id>/index.md` (rendered HTML), `[[task:<id>]]` → `.../tasks/<id>/index.md`, `[[event:<id>]]` → `.../attachments/<id>.json` (raw JSON attachment); unresolved targets render as inactive styled text (class `wikilink-unresolved`), not as broken anchors.

### 2.5 Search/graph surface (`search.py`)

- **Search**: in-memory substring match (case-insensitive) over rendered page bodies (frontmatter stripped). Deterministic ordering: primary key is page path (ASCII-ascending). Cap = min(`limit` param, 100). Returns `truncated: true` iff the underlying matched set exceeds the cap.
- **Graph**: nodes are pages, edges are `[[wikilink]]` references. Output must be byte-identical for identical vault state (sort nodes by path; sort edges by `(from, to)`).

### 2.6 Zero-install / security constraints (AC1)

- No `<script src="https://...">`, no `<link href="https://...">`, no `<img src="http(s)://...">` in any rendered template or renderer output. CSS is **inline** in `base.html`.
- No `eval`, no `exec`, no `subprocess` in service code.
- No user-supplied HTML is rendered; markdown→HTML goes through a sanitizer.
- A dedicated test (`test_zero_install.py`) asserts each HTML response body contains zero `https://`/`http://` references in `<script>`/`<link>`/`<img>` attributes.

## 3) Test matrix (≥10 tests; target suite 390 → ~400+)

| # | Test | AC link |
|---|---|---|
| 1 | `test_healthz.py::test_healthz_ok` — `GET /healthz` returns `{"status":"ok","service":"synthesis-web"}`. | — |
| 2 | `test_index.py::test_index_lists_multiple_vaults` — seed two vaults into fake S3; `GET /` lists both with shorthash links. | AC1 |
| 3 | `test_vault_home.py::test_vault_home_lists_pages_and_links` — `GET /v/<c>/<r>/` surfaces plans and `_index` entries. | AC1 |
| 4 | `test_page_render.py::test_page_resolves_wikilinks_to_internal_urls` — a task page containing `[[plan:P]]` renders an anchor `href="/v/<c>/<r>/plans/P/index.md"`. | AC1 |
| 5 | `test_backlinks.py::test_backlinks_section_lists_linking_pages` — a plan page linked-to by two task pages shows a backlinks list with both links. | AC1 |
| 6 | `test_graph.py::test_graph_endpoint_deterministic_json` — `GET /v/<c>/<r>/_graph` output is byte-identical across two calls on unchanged state. | AC1 |
| 7 | `test_search.py::test_search_honors_limit_and_truncation` — seed 30 pages matching `q=foo`; `limit=10` returns 10 matches + `truncated: true`. | AC1 |
| 8 | `test_404.py::test_missing_page_returns_404_html` — unknown page returns `404` with HTML body containing useful breadcrumb (vault + requested path). | AC1 |
| 9 | `test_etag.py::test_content_hash_etag_honors_if_none_match` — first `GET` returns `200` + `ETag`; second with `If-None-Match: <etag>` returns `304` and empty body. | A+B (SSR caching) |
| 10 | `test_zero_install.py::test_no_external_cdn_in_rendered_html` — crawl a rendered page and `/` index; regex-assert no `https?://` in `<script>/<link>/<img>` attrs. | AC1 |
| 11 (bonus) | `test_page_render.py::test_unknown_wikilink_renders_as_inactive_span` — `[[plan:does-not-exist]]` renders with class `wikilink-unresolved`, no anchor. | AC1 |
| 12 (bonus) | `reader` source-scan test — assert `synthesis_web/reader.py` body contains no `put_object`/`delete_object`/`copy_object`. | AC1 (read-only claim) |

Pilot MUST hit ≥10 of these; bonus tests (11–12) are strongly encouraged.

## 4) pyproject + dependencies

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "synthesis-web"
version = "0.1.0"
description = "Browser-facing SSR read path over the E5-T2 Obsidian vault (Wave 5 / E5-T4)."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "Proprietary" }
dependencies = [
  "canon-backend-shared",
  "fastapi>=0.115,<1",
  "uvicorn>=0.30,<1",
  "pydantic>=2.7,<3",
  "boto3>=1.35,<2",
  "botocore>=1.35,<2",
  "jinja2>=3.1,<4",
  "markdown-it-py>=3.0,<4",   # SAFE markdown→HTML (html=False); pilot MAY swap for stdlib impl if chosen
]

[project.optional-dependencies]
test = [
  "pytest>=8.2,<9",
  "moto[s3]>=5.0,<6",
  "httpx>=0.27,<1",
]

[tool.setuptools]
package-dir = { "" = "." }

[tool.setuptools.packages.find]
where = ["."]
include = ["synthesis_web*"]
```

## 5) Unwired terraform (Precedent §1 infra waiver)

```
infra/terraform/modules/synthesis-web/
├── README.md           # operator-applied; defer terraform apply
├── main.tf             # Lambda + API Gateway + CloudFront (simplest)
├── variables.tf        # bucket_arn, company_shorthash, repo_shorthash, domain — all string, default ""
└── outputs.tf          # service_url
```

- MUST NOT be referenced from `infra/terraform/main.tf` (unwired; deferred apply).
- Reads `synthesis-vault` bucket in read-only IAM (GetObject, ListBucket scoped to `vault/<company_shorthash>/<repo_shorthash>/*`).
- Reference, not import: the existing `infra/terraform/modules/synthesis-vault/` module is read-only reference; no edits permitted.

## 6) Living-spec edit plan (additive-only)

- `CHANGELOG.md` — new bullet at TOP of `[Unreleased] ### Added`.
- `docs/SYSTEM-WORKFLOW.md` §3 — single additive bullet describing E5-T4.
- `README.md` — append one sentence to the "Backend monorepo" paragraph (no reflow).
- `backend/synthesis-web/README.md` — overwrite the placeholder with service overview.

Explicitly forbidden: `backend/synthesis/synthesis/*.py`, `docs/VAULT-LAYOUT.md`, `backend/shared/canon_backend_shared/events.py`, `src/canon_systems/*.py`, existing terraform modules, existing service `pyproject.toml`s.

## 7) Acceptance criteria + traceability

| AC | Criterion | Implementation target | Verification test |
|---|---|---|---|
| AC1 | "Zero install for end users; anyone with access browses pages, backlinks, graph view, search." | `synthesis_web/{main,renderer,search}.py`, templates | tests 2–10 (above) |
| AC2 | "Rebuild-on-publish or request-time SSR chosen in a short in-task spike and recorded in the task packet." | This packet §1 + README SSR rationale | test 9 (ETag cache path) + packet presence via flow-audit |

Done signal (interpreted per §2.1 test-dir deviation):
- "Hosted URL responds with rendered sample vault" — covered by tests 2–8 via `TestClient(app)` + `DictS3Client`.
- "backend/synthesis-web/tests PASS" — `pytest backend/synthesis-web/synthesis_web_tests -q` ≥ 10 passed.

## 8) prior_work_references

- `docs/VAULT-LAYOUT.md` (E5-T1) — 15-field allowlist, wikilink forms, shorthash scoping.
- `backend/synthesis/synthesis/publisher.py` + `generator.py` (E5-T2) — S3 layout + `x-amz-meta-content-hash`.
- `.cursor/handoffs/canon-memory-v1/E5-T3/scoper.md` — Wave-5 scope packet precedent.
- `backend/synthesis/synthesis_tests/{conftest,_fakes}.py` (E5-T2) — shape to mirror for `synthesis_web_tests/`.
- `backend/axon-service/axon_service_tests/` (E3-T1) — second precedent for `<service>_tests/` naming.

## 9) DoR checklist — all pass

- story.title, userValue, acceptanceCriteria ✓
- repository.primaryLanguages (Python 3.10+), testFramework (pytest 8.x + httpx + moto) ✓
- constraints.dependencies: must not break `backend/synthesis/**`, `docs/VAULT-LAYOUT.md`, existing 390-test suite ✓
- repo_ref_verification: branch `wave/5/canon-memory-v1` tip `dd13487` ✓
- ac_traceability populated §7 ✓

## 10) Risks & assumptions

- **ASSUMPTION**: current `backend/synthesis-web/README.md` placeholder is writeable (E0-T2 deferred its content to E5-T4).
- **ASSUMPTION**: `markdown-it-py` acceptable as minimal 3rd-party dep; pilot MAY replace with a stdlib subset renderer.
- **RISK**: pytest collision if tests were ever `tests/`. Mitigation: `synthesis_web_tests/`.
- **RISK**: renderer could accidentally write to S3. Mitigation: source-scan test forbids `put_object`/`delete_object`/`copy_object` in `reader.py`.

---

```text
HANDOFF_TO_CURSOR_PILOT

task_id: E5-T4
title: "Read path 1 — backend/synthesis-web browser renderer"
handoff_id: "handoff_20260423T1530Z_E5-T4_synthesis_web"
plan_id: "canon-memory-v1"
workstream_id: "wave-5d"
branch: wave/5/canon-memory-v1
base_commit: dd13487

design_spike:
  option_a_ssr: CHOSEN
  option_b_static: REJECTED
  rationale: >
    S3 vault is already idempotent + content-addressed via x-amz-meta-content-hash.
    Request-time SSR with per-key LRU keyed on (rel, content_hash) plus a whole-vault
    backlink index refreshed on any page's content_hash change yields equivalent
    steady-state performance to static rebuild without a second build pipeline,
    without duplicate storage, and without lockstep publisher↔renderer coupling.
    E5-T7's auto-publish already re-runs on RELEASE_STATUS PASS; a parallel
    static-rebuild step duplicates work. SSR is also easier to evolve (backlink/graph
    algorithm changes require no re-publish).

scope_locked:
  - New backend service: backend/synthesis-web/ with synthesis_web/{main,reader,renderer,search,cache}.py + synthesis_web/templates/*.html + pyproject.toml + README.md (overwrite placeholder).
  - New test tree: backend/synthesis-web/synthesis_web_tests/ (NOT tests/) with conftest.py + _fakes.py + ≥10 test modules (see packet §3).
  - New unwired terraform module: infra/terraform/modules/synthesis-web/ {main.tf, variables.tf, outputs.tf, README.md}. MUST NOT be referenced from infra/terraform/main.tf.
  - Living-spec edits: CHANGELOG.md (top of [Unreleased] ### Added), docs/SYSTEM-WORKFLOW.md §3 (one additive bullet), README.md "Backend monorepo" paragraph (one additive sentence; no reflow).

cursor-pilot MUST:
  - Begin its packet with "<!-- CURSOR_PILOT_PROMPT: E5-T4 synthesis-web browser renderer -->".
  - Provide a verbatim skeleton for synthesis_web/main.py (FastAPI app, 6 routes per packet §2.2, dependency-injectable S3VaultReader + env-layered bucket/prefix resolution).
  - Provide verbatim skeletons for reader.py (S3VaultReader with list_pages/read_page/read_hash/list_vaults; read-only assertion), renderer.py (strip_frontmatter + render_markdown + resolve_wikilink + build_backlink_index), search.py (substring + graph builder with deterministic sort keys), and templates/{base,index,vault_home,page,not_found}.html (inline CSS; zero external refs).
  - Provide verbatim test skeletons for all 10 core tests in packet §3 plus both bonus tests (#11, #12).
  - Provide the verbatim pyproject.toml (packet §4).
  - Provide the verbatim terraform stubs (packet §5), each with a one-line comment confirming "NOT wired into infra/terraform/main.tf (Precedent §1 cloud_execution_deferred waiver)".
  - Provide verbatim CHANGELOG / SYSTEM-WORKFLOW / README / backend/synthesis-web/README.md diffs.
  - State: backend/synthesis/synthesis/*.py, docs/VAULT-LAYOUT.md, backend/shared/canon_backend_shared/events.py, src/canon_systems/*.py are LOCKED for this task.

do_not:
  - Modify any file under backend/synthesis/synthesis/, docs/VAULT-LAYOUT.md, backend/shared/canon_backend_shared/events.py, or src/canon_systems/*.py.
  - Modify or reference any existing terraform module (synthesis-vault read-only).
  - Add external CDN refs (<script src="https://..">, <link href="https://..">, <img src="http(s)://..">) in any template or renderer output; all CSS inline; no JS in v1.
  - Pass raw company_id / repository_id in URLs, filenames, frontmatter, or logs (always shorthash per E5-T1 §2).
  - Let S3VaultReader call put_object / delete_object / copy_object (tested by source-scan).
  - Create tests/ under backend/synthesis-web/ (use synthesis_web_tests/; avoids pytest collection collision per E5-T2 precedent).
  - Introduce new canonical-event types, new CLI commands, or new src/canon_systems/*.py modules this task.

END_HANDOFF_TO_CURSOR_PILOT
```
