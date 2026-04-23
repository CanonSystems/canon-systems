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
        end = min(len(body), idx + len(needle) + 40)
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
