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
        vault_rel = full_rel[len(scope_prefix) :]
        out[vault_rel] = reader.read_page(full_rel)
    return out


def _make_resolver(c: str, r: str, known_pages: frozenset[str]):
    def _f(target: str, current_page: str) -> str:
        return _resolve_wikilink(
            target,
            current_page,
            company_shorthash=c,
            repo_shorthash=r,
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
    html = templates.TemplateResponse(request, "index.html", {"vaults": vaults})
    html.headers["ETag"] = _quoted(etag)
    return html


@app.get("/v/{company_shorthash}/{repo_shorthash}/_graph")
def vault_graph(
    company_shorthash: str,
    repo_shorthash: str,
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
    company_shorthash: str,
    repo_shorthash: str,
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
    request: Request,
    company_shorthash: str,
    repo_shorthash: str,
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
        request,
        "vault_home.html",
        {
            "company_shorthash": company_shorthash,
            "repo_shorthash": repo_shorthash,
            "plan_entries": plan_entries,
            "index_entries": index_entries,
        },
    )
    html.headers["ETag"] = _quoted(etag)
    return html


@app.get("/v/{company_shorthash}/{repo_shorthash}/{page_path:path}", response_class=HTMLResponse)
def vault_page(
    request: Request,
    company_shorthash: str,
    repo_shorthash: str,
    page_path: str,
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
    html_page = templates.get_template("page.html").render(
        request=request,
        company_shorthash=company_shorthash,
        repo_shorthash=repo_shorthash,
        page_path=page_path,
        html_body=html_body,
        backlinks=backlinks,
        frontmatter=fm,
    )
    rendered_bytes = html_page.encode("utf-8")
    _RENDER_CACHE.set(full_rel, content_hash, rendered_bytes)
    out = Response(content=rendered_bytes, media_type="text/html; charset=utf-8")
    out.headers["ETag"] = _quoted(etag)
    return out


def _render_404(request: Request, c: str, r: str, *, requested_path: str) -> Response:
    return templates.TemplateResponse(
        request,
        "not_found.html",
        {
            "company_shorthash": c,
            "repo_shorthash": r,
            "requested_path": requested_path,
        },
        status_code=404,
    )


_mangum: object | None = None


def handler(event: object, context: object) -> object:
    """AWS Lambda entry (Mangum); created lazily to avoid import-time side effects in tests."""
    global _mangum
    if _mangum is None:
        from mangum import Mangum

        _mangum = Mangum(app, lifespan="off")
    return _mangum(event, context)  # type: ignore[misc]
