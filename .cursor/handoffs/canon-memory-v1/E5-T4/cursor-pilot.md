<!-- CURSOR_PILOT_PROMPT: E5-T4 synthesis-web browser renderer -->

# CURSOR_PILOT_PROMPT — E5-T4 `backend/synthesis-web` browser renderer

## ROLE
You are the `implementer` subagent. Execute in-repo; do not plan or ask clarifying questions. Ground truth for any ambiguity: `.cursor/handoffs/canon-memory-v1/E5-T4/scoper.md`.

## TASK
Ship `backend/synthesis-web/` — a new read-only FastAPI service that SSRs HTML over the E5-T2 S3 vault. Six routes (healthz, index, vault_home, page, _graph, _search). Tenant-scoped by `company_shorthash`/`repo_shorthash`. Zero external CDN refs. Never writes to S3.

## ACCEPTANCE_CRITERIA
- AC1 — Zero install; pages/backlinks/graph/search all browsable. Enforced by tests 2–10 + bonus 11/12.
- AC2 — SSR-vs-static spike recorded. Recorded in scoper §1 and restated in `backend/synthesis-web/README.md`; test 9 (`test_etag.py`) exercises the SSR cache path.

## CONTEXT
- plan_id: canon-memory-v1; task_id: E5-T4; handoff_id: handoff_20260423T1530Z_E5-T4_synthesis_web
- branch: `wave/5/canon-memory-v1`; base_commit: `dd13487` (E5-T3 tip)
- Suite baseline: 390 passed → target ≥ 402 passed (+12).
- LOCKED (do NOT edit): `backend/synthesis/synthesis/*.py`, `backend/synthesis/synthesis_tests/*.py`, `docs/VAULT-LAYOUT.md`, `backend/shared/canon_backend_shared/events.py`, `src/canon_systems/*.py`, existing terraform modules (including `infra/terraform/modules/synthesis-vault/`), root `infra/terraform/main.tf`.

## REPOSITORY
- Python 3.10+, pytest 8.x, FastAPI `TestClient`, `DictS3Client` local fake.
- Test package name MUST be `synthesis_web_tests/` (not `tests/`) — avoids pytest collection collision (E5-T2 precedent).
- New service deps (in `backend/synthesis-web/pyproject.toml`):
  prod: `canon-backend-shared`, `fastapi>=0.115,<1`, `uvicorn>=0.30,<1`, `pydantic>=2.7,<3`, `boto3>=1.35,<2`, `botocore>=1.35,<2`, `jinja2>=3.1,<4`, `markdown-it-py>=3.0,<4`.
  test: `pytest>=8.2,<9`, `moto[s3]>=5.0,<6`, `httpx>=0.27,<1`.

## REASONING
1. `S3VaultReader` is a pure read boundary: HEAD for `x-amz-meta-content-hash`, GET for body, paginated LIST for enumeration. No put/delete/copy; enforced by source-scan test (#12).
2. `renderer.py` uses `markdown-it-py` with `html=False`. Wikilinks are pre-extracted into placeholder tokens (`@@CANONWL{n}@@`) that markdown-it will not touch, then post-replaced. Unresolved wikilinks render as `<span class="wikilink-unresolved">` (no anchor).
3. `build_backlink_index(pages)` scans every page body for `[[kind:ident]]` references, resolves each to its canonical vault-relative key, returns `{target_rel: [linker_rel, ...]}` (sorted).
4. `search.substring_search` is case-insensitive substring over frontmatter-stripped bodies, sorted by path, capped at `min(limit, 100)` with `truncated: true` iff the underlying match set exceeds the cap.
5. `search.build_graph` produces nodes sorted by path and edges sorted by `(from, to)` — byte-identical output.
6. `cache.ContentHashCache` is a per-key LRU keyed on `(rel, content_hash)`.
7. `main.py` wires 6 routes. Route order: `/v/{c}/{r}/_graph` + `_search` BEFORE the `{page_path:path}` catchall. `S3VaultReader` resolved via `get_reader()` dependency (env: `SYNTHESIS_WEB_BUCKET`, `SYNTHESIS_WEB_PREFIX`). Tests override via `app.dependency_overrides[get_reader]`.
8. ETag: for single-object responses use `x-amz-meta-content-hash` quoted; for aggregates (index, _graph) use `sha256(deterministic_payload).hexdigest()`. On `If-None-Match` match → `304` empty body.
9. Templates: inline CSS only in `base.html`. Zero `<script>`/`<link>`/`<img>` in v1. Test 10 regex-asserts.
10. Terraform stub: Lambda + API Gateway + CloudFront + read-only IAM to `synthesis-vault` bucket. Each file starts with `# NOT wired into infra/terraform/main.tf (Precedent §1 cloud_execution_deferred waiver).`. Root main.tf untouched.
11. Living-spec edits additive-only: one CHANGELOG bullet at TOP of `[Unreleased] ### Added`, one SYSTEM-WORKFLOW §3 bullet, one sentence in README "Backend monorepo" paragraph.

## OUTPUT FORMAT (skeletons are authoritative — copy verbatim)

### 1. `backend/synthesis-web/pyproject.toml`
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
  "markdown-it-py>=3.0,<4",
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

### 2. `backend/synthesis-web/synthesis_web/__init__.py`
```python
"""synthesis-web — read-only SSR browser over the E5-T2 S3 vault (Wave 5 / E5-T4)."""
```

### 3. `backend/synthesis-web/synthesis_web/reader.py`
```python
"""Read-only S3 vault reader.

MUST NOT call put_object / delete_object / copy_object (verified by
synthesis_web_tests/test_reader_source_scan.py).
"""
from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError


class NotFound(Exception):
    """Raised when a requested vault key is missing."""


class S3VaultReader:
    def __init__(self, *, bucket: str, prefix: str, s3_client: Any) -> None:
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        self._s3 = s3_client

    def _full_key(self, rel: str) -> str:
        r = rel.lstrip("/")
        if not self._prefix:
            return r
        return f"{self._prefix}/{r}"

    def _strip_prefix(self, full_key: str) -> str:
        if not self._prefix:
            return full_key
        p = f"{self._prefix}/"
        return full_key[len(p):] if full_key.startswith(p) else full_key

    def list_pages(self) -> list[str]:
        paginator = self._s3.get_paginator("list_objects_v2")
        kwargs: dict[str, Any] = {"Bucket": self._bucket}
        if self._prefix:
            kwargs["Prefix"] = f"{self._prefix}/"
        out: list[str] = []
        for page in paginator.paginate(**kwargs):
            for obj in page.get("Contents", []) or []:
                key = obj.get("Key", "")
                if not key:
                    continue
                out.append(self._strip_prefix(key))
        return sorted(out)

    def read_page(self, rel: str) -> bytes:
        try:
            resp = self._s3.get_object(Bucket=self._bucket, Key=self._full_key(rel))
        except ClientError as e:
            code = (e.response.get("Error", {}) or {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                raise NotFound(rel) from e
            raise
        body = resp.get("Body")
        if hasattr(body, "read"):
            return body.read()
        return bytes(body or b"")

    def read_hash(self, rel: str) -> str:
        try:
            h = self._s3.head_object(Bucket=self._bucket, Key=self._full_key(rel))
        except ClientError as e:
            code = (e.response.get("Error", {}) or {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                return ""
            raise
        return (h.get("Metadata", {}) or {}).get("content-hash", "")

    def list_vaults(self) -> list[tuple[str, str]]:
        seen: set[tuple[str, str]] = set()
        for rel in self.list_pages():
            parts = rel.split("/", 2)
            if len(parts) < 2:
                continue
            c, r = parts[0], parts[1]
            if len(c) == 8 and len(r) == 8 and all(ch in "0123456789abcdef" for ch in c + r):
                seen.add((c, r))
        return sorted(seen)
```

### 4. `backend/synthesis-web/synthesis_web/renderer.py`
```python
"""Markdown → sanitized HTML, wikilink resolution, backlink index."""
from __future__ import annotations

import re
from typing import Callable

from markdown_it import MarkdownIt

_FRONTMATTER_RE = re.compile(rb"^---\n(.*?)\n---\n", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([a-z]+):([^\]\n]+)\]\]")


def strip_frontmatter(md: bytes) -> tuple[dict, str]:
    m = _FRONTMATTER_RE.match(md)
    fm: dict = {}
    if not m:
        return fm, md.decode("utf-8", errors="replace")
    block = m.group(1).decode("utf-8", errors="replace")
    body = md[m.end():].decode("utf-8", errors="replace")
    for line in block.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, body


def resolve_wikilink(
    target: str,
    current_page: str,
    *,
    company_shorthash: str,
    repo_shorthash: str,
    known_pages: frozenset[str],
) -> str:
    if ":" not in target:
        return ""
    kind, ident = target.split(":", 1)
    kind = kind.strip()
    ident = ident.strip()
    if not kind or not ident:
        return ""
    if kind == "plan":
        rel = f"plans/{ident}/index.md"
    elif kind == "task":
        plan_id = ""
        if current_page.startswith("plans/"):
            parts = current_page.split("/")
            if len(parts) >= 2:
                plan_id = parts[1]
        if plan_id:
            rel = f"plans/{plan_id}/tasks/{ident}/index.md"
        else:
            candidates = [p for p in known_pages if p.endswith(f"/tasks/{ident}/index.md")]
            if not candidates:
                return ""
            rel = sorted(candidates)[0]
    elif kind == "event":
        rel = f"attachments/{ident}.json"
    else:
        return ""
    if rel not in known_pages:
        return ""
    return f"/v/{company_shorthash}/{repo_shorthash}/{rel}"


def render_markdown(md: str, *, resolve_wikilink: Callable[[str, str], str], current_page: str = "") -> str:
    placeholders: dict[str, str] = {}

    def _sub(m: re.Match) -> str:
        kind, ident = m.group(1), m.group(2)
        target = f"{kind}:{ident}"
        url = resolve_wikilink(target, current_page) or ""
        idx = len(placeholders)
        token = f"@@CANONWL{idx:05d}@@"
        if url:
            placeholders[token] = (
                f'<a class="wikilink" href="{_html_attr_escape(url)}">'
                f'{_html_text_escape(target)}</a>'
            )
        else:
            placeholders[token] = (
                f'<span class="wikilink-unresolved">'
                f'[[{_html_text_escape(target)}]]</span>'
            )
        return token

    prepared = _WIKILINK_RE.sub(_sub, md)
    md_parser = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    html = md_parser.render(prepared)
    for token, frag in placeholders.items():
        html = html.replace(token, frag)
    return html


def build_backlink_index(pages: dict[str, bytes]) -> dict[str, list[str]]:
    out: dict[str, set[str]] = {}
    for linker_rel, body in pages.items():
        if not linker_rel.endswith(".md"):
            continue
        _, text = strip_frontmatter(body)
        for m in _WIKILINK_RE.finditer(text):
            kind, ident = m.group(1), m.group(2)
            target_rel = _kind_to_rel(kind, ident, linker_rel)
            if target_rel is None:
                continue
            out.setdefault(target_rel, set()).add(linker_rel)
    return {k: sorted(v) for k, v in sorted(out.items())}


def _kind_to_rel(kind: str, ident: str, linker_rel: str) -> str | None:
    if kind == "plan":
        return f"plans/{ident}/index.md"
    if kind == "task":
        if linker_rel.startswith("plans/"):
            parts = linker_rel.split("/")
            if len(parts) >= 2:
                return f"plans/{parts[1]}/tasks/{ident}/index.md"
        return None
    if kind == "event":
        return f"attachments/{ident}.json"
    return None


def _html_text_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _html_attr_escape(s: str) -> str:
    return _html_text_escape(s).replace('"', "&quot;")
```

### 5. `backend/synthesis-web/synthesis_web/search.py`
```python
"""In-memory substring search + deterministic graph builder."""
from __future__ import annotations

from synthesis_web.renderer import _WIKILINK_RE, _kind_to_rel, strip_frontmatter


def substring_search(pages: dict[str, bytes], q: str, limit: int) -> dict:
    if limit < 0:
        limit = 0
    cap = min(limit, 100)
    needle = (q or "").casefold()
    if not needle:
        return {"q": q, "matches": [], "truncated": False}
    matched: list[dict] = []
    for rel in sorted(pages.keys()):
        if not rel.endswith(".md"):
            continue
        _, body = strip_frontmatter(pages[rel])
        hay = body.casefold()
        idx = hay.find(needle)
        if idx == -1:
            continue
        start = max(0, idx - 40)
        end = min(len(body), idx + len(q) + 40)
        snippet = body[start:end].replace("\n", " ").strip()
        matched.append({"path": rel, "snippet": snippet})
    truncated = len(matched) > cap
    return {"q": q, "matches": matched[:cap], "truncated": truncated}


def build_graph(pages: dict[str, bytes]) -> dict:
    nodes: list[dict] = []
    edges_set: set[tuple[str, str]] = set()
    for rel in sorted(pages.keys()):
        if not rel.endswith(".md"):
            continue
        label = rel.rsplit("/", 1)[-1].removesuffix(".md")
        nodes.append({"id": rel, "label": label, "path": rel})
        _, body = strip_frontmatter(pages[rel])
        for m in _WIKILINK_RE.finditer(body):
            kind, ident = m.group(1), m.group(2)
            target_rel = _kind_to_rel(kind, ident, rel)
            if target_rel is None:
                continue
            edges_set.add((rel, target_rel))
    edges = [{"from": a, "to": b} for (a, b) in sorted(edges_set)]
    return {"nodes": nodes, "edges": edges}
```

### 6. `backend/synthesis-web/synthesis_web/cache.py`
```python
"""Per-key LRU cache keyed on (relative_path, content_hash)."""
from __future__ import annotations

from collections import OrderedDict
from typing import Any


class ContentHashCache:
    def __init__(self, max_size: int = 512) -> None:
        self._max = max_size
        self._data: "OrderedDict[tuple[str, str], Any]" = OrderedDict()

    def get(self, rel: str, content_hash: str) -> Any | None:
        key = (rel, content_hash)
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def set(self, rel: str, content_hash: str, value: Any) -> None:
        key = (rel, content_hash)
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self._max:
            self._data.popitem(last=False)
```

### 7. `backend/synthesis-web/synthesis_web/main.py`
```python
"""FastAPI entrypoint for synthesis-web."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import boto3
from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from synthesis_web.cache import ContentHashCache
from synthesis_web.reader import NotFound, S3VaultReader
from synthesis_web.renderer import (
    build_backlink_index,
    render_markdown,
    resolve_wikilink as _resolve_wikilink,
    strip_frontmatter,
)
from synthesis_web.search import build_graph, substring_search

app = FastAPI(title="synthesis-web", version="0.1.0")

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
_RENDER_CACHE = ContentHashCache(max_size=512)


def get_reader() -> S3VaultReader:
    bucket = os.environ.get("SYNTHESIS_WEB_BUCKET", "synthesis-web-bucket")
    prefix = os.environ.get("SYNTHESIS_WEB_PREFIX", "vault")
    s3 = boto3.client("s3")
    return S3VaultReader(bucket=bucket, prefix=prefix, s3_client=s3)


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _quoted(etag: str) -> str:
    if not etag:
        return ""
    if etag.startswith('"') and etag.endswith('"'):
        return etag
    return f'"{etag}"'


def _match_etag(if_none_match: str | None, etag: str) -> bool:
    if not etag or not if_none_match:
        return False
    return if_none_match.strip() in (etag, _quoted(etag))


def _scoped_pages(reader: S3VaultReader, c: str, r: str) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    scope_prefix = f"{c}/{r}/"
    for full_rel in reader.list_pages():
        if not full_rel.startswith(scope_prefix):
            continue
        vault_rel = full_rel[len(scope_prefix):]
        out[vault_rel] = reader.read_page(full_rel)
    return out


def _make_resolver(c: str, r: str, known_pages: frozenset[str]):
    def _f(target: str, current_page: str) -> str:
        return _resolve_wikilink(
            target, current_page,
            company_shorthash=c, repo_shorthash=r,
            known_pages=known_pages,
        )
    return _f


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "synthesis-web"}


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    reader: S3VaultReader = Depends(get_reader),
) -> Response:
    vaults = reader.list_vaults()
    payload = json.dumps([{"c": c, "r": r} for (c, r) in vaults], sort_keys=True).encode("utf-8")
    etag = _sha256_hex(payload)
    if _match_etag(if_none_match, etag):
        return Response(status_code=304)
    html = templates.TemplateResponse("index.html", {"request": request, "vaults": vaults})
    html.headers["ETag"] = _quoted(etag)
    return html


@app.get("/v/{company_shorthash}/{repo_shorthash}/_graph")
def vault_graph(
    company_shorthash: str, repo_shorthash: str,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    reader: S3VaultReader = Depends(get_reader),
) -> Response:
    pages = _scoped_pages(reader, company_shorthash, repo_shorthash)
    graph = build_graph(pages)
    payload = json.dumps(graph, sort_keys=True, separators=(",", ":")).encode("utf-8")
    etag = _sha256_hex(payload)
    if _match_etag(if_none_match, etag):
        return Response(status_code=304)
    return Response(content=payload, media_type="application/json", headers={"ETag": _quoted(etag)})


@app.get("/v/{company_shorthash}/{repo_shorthash}/_search")
def vault_search(
    company_shorthash: str, repo_shorthash: str,
    q: str = Query(default=""),
    limit: int = Query(default=25, ge=0, le=1000),
    reader: S3VaultReader = Depends(get_reader),
) -> Response:
    pages = _scoped_pages(reader, company_shorthash, repo_shorthash)
    result = substring_search(pages, q, limit)
    payload = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return Response(content=payload, media_type="application/json")


@app.get("/v/{company_shorthash}/{repo_shorthash}/", response_class=HTMLResponse)
def vault_home(
    request: Request, company_shorthash: str, repo_shorthash: str,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    reader: S3VaultReader = Depends(get_reader),
) -> Response:
    pages = _scoped_pages(reader, company_shorthash, repo_shorthash)
    if not pages:
        return _render_404(request, company_shorthash, repo_shorthash, requested_path="")
    etag = reader.read_hash(f"{company_shorthash}/{repo_shorthash}/README.md") or _sha256_hex(
        json.dumps(sorted(pages.keys())).encode("utf-8")
    )
    if _match_etag(if_none_match, etag):
        return Response(status_code=304)
    plan_entries = sorted({p.split("/")[1] for p in pages if p.startswith("plans/") and "/" in p[6:]})
    index_entries = sorted(p for p in pages if p.startswith("_index/"))
    html = templates.TemplateResponse(
        "vault_home.html",
        {"request": request, "company_shorthash": company_shorthash,
         "repo_shorthash": repo_shorthash, "plan_entries": plan_entries,
         "index_entries": index_entries},
    )
    html.headers["ETag"] = _quoted(etag)
    return html


@app.get("/v/{company_shorthash}/{repo_shorthash}/{page_path:path}", response_class=HTMLResponse)
def vault_page(
    request: Request, company_shorthash: str, repo_shorthash: str, page_path: str,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    reader: S3VaultReader = Depends(get_reader),
) -> Response:
    full_rel = f"{company_shorthash}/{repo_shorthash}/{page_path}"
    content_hash = reader.read_hash(full_rel)
    if not content_hash:
        return _render_404(request, company_shorthash, repo_shorthash, requested_path=page_path)
    etag = content_hash
    if _match_etag(if_none_match, etag):
        return Response(status_code=304)
    cached = _RENDER_CACHE.get(full_rel, content_hash)
    if cached is not None:
        resp = Response(content=cached, media_type="text/html; charset=utf-8")
        resp.headers["ETag"] = _quoted(etag)
        return resp
    try:
        body = reader.read_page(full_rel)
    except NotFound:
        return _render_404(request, company_shorthash, repo_shorthash, requested_path=page_path)
    pages = _scoped_pages(reader, company_shorthash, repo_shorthash)
    known_pages = frozenset(pages.keys())
    resolver = _make_resolver(company_shorthash, repo_shorthash, known_pages)
    fm, md_text = strip_frontmatter(body)
    html_body = render_markdown(md_text, resolve_wikilink=resolver, current_page=page_path)
    backlinks_idx = build_backlink_index(pages)
    backlinks = backlinks_idx.get(page_path, [])
    rendered = templates.TemplateResponse(
        "page.html",
        {"request": request, "company_shorthash": company_shorthash,
         "repo_shorthash": repo_shorthash, "page_path": page_path,
         "html_body": html_body, "backlinks": backlinks, "frontmatter": fm},
    )
    rendered_bytes = rendered.body
    _RENDER_CACHE.set(full_rel, content_hash, rendered_bytes)
    out = Response(content=rendered_bytes, media_type="text/html; charset=utf-8")
    out.headers["ETag"] = _quoted(etag)
    return out


def _render_404(request: Request, c: str, r: str, *, requested_path: str) -> Response:
    return templates.TemplateResponse(
        "not_found.html",
        {"request": request, "company_shorthash": c, "repo_shorthash": r,
         "requested_path": requested_path},
        status_code=404,
    )
```

### 8. Templates (inline CSS only; zero external refs)
See `backend/synthesis-web/synthesis_web/templates/{base,index,vault_home,page,not_found}.html` — full HTML in the original cursor-pilot response from the subagent at `cfa22cdc-9a02-4281-a705-08d5522214ed`. Copy from there verbatim or use standard Jinja2 templates following these rules:
- `base.html` defines `<style>` inline (body, crumbs, wikilink, wikilink-unresolved, link-list, backlinks sidebar, footer). NO `<link>`, NO `<script>`, NO `<img>`.
- `index.html` extends base; lists `vaults` as `<a href="/v/{c}/{r}/">`.
- `vault_home.html` extends base; shows plans + _index entries + links to `_graph` + `_search`.
- `page.html` extends base; renders `{{ html_body | safe }}` + `<aside class="backlinks">` with `Backlinks` heading.
- `not_found.html` extends base; shows `Page not found`, the requested path, and "Return to vault home" link.

### 9. `backend/synthesis-web/README.md` (overwrite placeholder)
Include `## Design spike: SSR over rebuild-on-publish` section that restates AC2 rationale; list the six routes; document env vars `SYNTHESIS_WEB_BUCKET`/`SYNTHESIS_WEB_PREFIX`; mention `markdown-it-py` with `html=False`; document `synthesis_web_tests/` naming (precedent note); document infra under `infra/terraform/modules/synthesis-web/`.

### 10. Tests (`backend/synthesis-web/synthesis_web_tests/`)
- `__init__.py` — one-line docstring.
- `_fakes.py` — Local copy of E5-T2 `DictS3Client` EXTENDED with `get_object(*, Bucket, Key)` returning `{"Body": io.BytesIO(body), "ContentType", "Metadata"}` or raising `ClientError({"Error":{"Code":"404"}}, "GetObject")`. Keep `put_object`, `head_object`, `get_paginator` identical to the sibling.
- `conftest.py` — fixtures `fake_s3` (seeds two vaults with `README.md`, `_index/plans.md`, `plans/P1/index.md`, `plans/P1/tasks/T1/index.md`, `plans/P1/tasks/T2/index.md`; vault IDs = `sha256("IMC")[:8]`/`sha256("innermost")[:8]` and `sha256("ACME")[:8]`/`sha256("widgets")[:8]`), `vault_ids` (returns the 4 shorthashes), `reader` (S3VaultReader bound to `fake_s3`), `client` (FastAPI TestClient with `app.dependency_overrides[get_reader] = lambda: reader`).
- Tests:
  - `test_healthz.py::test_healthz_ok` — `GET /healthz` returns `{"status":"ok","service":"synthesis-web"}`.
  - `test_index.py::test_index_lists_multiple_vaults` — both vault shorthash links appear in HTML.
  - `test_vault_home.py::test_vault_home_lists_pages_and_links` — plans, _index, _graph, _search all linked.
  - `test_page_render.py::test_page_resolves_wikilinks_to_internal_urls` — T1 page contains `href="/v/{c}/{r}/plans/P1/index.md"` + `class="wikilink"`.
  - `test_page_render.py::test_unknown_wikilink_renders_as_inactive_span` — T2 has `class="wikilink-unresolved"` + `plan:does-not-exist` text + NO anchor.
  - `test_backlinks.py::test_backlinks_section_lists_linking_pages` — plan P1 page lists backlinks to T1 and T2.
  - `test_graph.py::test_graph_endpoint_deterministic_json` — two GETs return byte-identical content; nodes sorted by path; edges sorted by (from,to).
  - `test_search.py::test_search_honors_limit_and_truncation` — seed 30 matching pages, `limit=10` → 10 matches + `truncated=true`.
  - `test_404.py::test_missing_page_returns_404_html` — status 404, HTML breadcrumb includes vault + path, "Return to vault home" present.
  - `test_etag.py::test_content_hash_etag_honors_if_none_match` — first GET returns quoted ETag; second GET with `If-None-Match` → 304 empty body.
  - `test_zero_install.py::test_no_external_cdn_in_rendered_html` — regex `r'<(?:script|link|img)\b[^>]*?\b(?:src|href)\s*=\s*["\']https?://'` finds zero matches on `/`, `/v/{c}/{r}/`, P1/index.md, T1/index.md.
  - `test_reader_source_scan.py::test_reader_source_has_no_write_calls` — `synthesis_web/reader.py` source contains none of `put_object`/`delete_object`/`copy_object`.

### 11. Terraform stubs (`infra/terraform/modules/synthesis-web/`)
Each file MUST start with `# NOT wired into infra/terraform/main.tf (Precedent §1 cloud_execution_deferred waiver).` (or `<!-- ... -->` for README).
- `main.tf` — aws provider `>= 5.0, < 6.0`; Lambda IAM role (`sts:AssumeRole` for `lambda.amazonaws.com`); read-only IAM policy (`s3:GetObject`, `s3:ListBucket` on `vault_bucket_arn` + `/*`); `aws_iam_role_policy_attachment` for `AWSLambdaBasicExecutionRole`; `aws_lambda_function` (python3.11, `synthesis_web.main.handler`, env `SYNTHESIS_WEB_BUCKET`/`SYNTHESIS_WEB_PREFIX`, operator-supplied `filename`/`source_code_hash`); `aws_apigatewayv2_api` + integration + `ANY /{proxy+}` route + `$default` stage; `aws_lambda_permission` grant to API Gateway; `aws_cloudfront_distribution` (origin = API GW endpoint, HTTPS-only, default cert).
- `variables.tf` — `name_prefix`, `vault_bucket_arn`, `vault_bucket_name`, `vault_prefix` (default `vault`), `company_shorthash`, `repo_shorthash`, `domain`, `lambda_package_path`, `lambda_package_hash` — all `string` with `default = ""` except `vault_prefix`.
- `outputs.tf` — `service_url` = `https://${aws_cloudfront_distribution.synthesis_web.domain_name}`, `api_endpoint`, `lambda_role_arn`.
- `README.md` — explain "not wired", list variables + outputs, show deferred `terraform apply` command.

### 12. Living-spec additive edits
- `CHANGELOG.md` — insert a single E5-T4 bullet at TOP of `[Unreleased] ### Added` describing the service, routes, SSR spike, zero-install guarantee, dep list, test-dir note, suite delta (390 → 402), unwired terraform.
- `docs/SYSTEM-WORKFLOW.md` §3 — append one additive bullet describing E5-T4 semantics (no reorder, no reflow).
- `README.md` — append one additive sentence to the "Backend monorepo" paragraph pointing at `backend/synthesis-web/` and mentioning the SSR read path. Do NOT reflow existing sentences.

## STOP_CONDITIONS
- ❌ Any edit to LOCKED files.
- ❌ Root `infra/terraform/main.tf` adds a `module "synthesis_web"` block.
- ❌ Rendered HTML contains `http(s)://` in `<script>`/`<link>`/`<img>` attrs.
- ❌ Reader source contains `put_object`/`delete_object`/`copy_object`.
- ❌ Full suite drops below 390 at any point.

## DONE
- `pytest backend/synthesis-web/synthesis_web_tests -q` → ≥ 12 passed.
- `pytest -q` from repo root → ≥ 402 passed.
- Handoff `HANDOFF_TO_QA` packet written to `.cursor/handoffs/canon-memory-v1/E5-T4/implementer.md` with:
  - `handoff_id: handoff_20260423T1530Z_E5-T4_synthesis_web`
  - `task_id: E5-T4`, `branch: wave/5/canon-memory-v1`
  - `files_created:` 23+ paths
  - `files_modified:` 3 paths (CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md) + overwritten `backend/synthesis-web/README.md` (if it existed as a placeholder)
  - `acceptance_criteria:` AC1 + AC2 each with `status: MET`, block-style YAML `covering_tests:` (bare pytest node IDs or doc paths only)
  - `suite_result: total=<N> passed=<N> skipped=0`
