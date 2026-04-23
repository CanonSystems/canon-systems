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
    body = md[m.end() :].decode("utf-8", errors="replace")
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

    def _sub(m: re.Match[str]) -> str:
        kind, ident = m.group(1), m.group(2)
        target = f"{kind}:{ident}"
        url = resolve_wikilink(target, current_page) or ""
        idx = len(placeholders)
        token = f"@@CANONWL{idx:05d}@@"
        if url:
            placeholders[token] = (
                f'<a class="wikilink" href="{_html_attr_escape(url)}">'
                f"{_html_text_escape(target)}</a>"
            )
        else:
            placeholders[token] = (
                f'<span class="wikilink-unresolved">' f"[[{_html_text_escape(target)}]]</span>"
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
