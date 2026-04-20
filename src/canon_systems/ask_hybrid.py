"""Hybrid memory retrieval: canonical artifacts first, MemPalace second.

Agent-facing Q&A path. Given a question, queries the canonical knowledge API
for memory_capture artifacts scoped to the current repo, then queries the
memory adapter for semantic MemPalace hits. Results are tenant-scoped by
company_id + repository_id via the standard X-Actor-Id / X-Company-Id headers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Any

from .shared import load_identity_context, load_repo_context, request_json


@dataclass(slots=True)
class RetrievedHit:
    source: str
    score: float
    artifact_id: str
    title: str
    excerpt: str
    quote: str
    metadata: dict[str, Any]


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) > 1]


def _score(question: str, text: str) -> float:
    q = _tokens(question)
    if not q:
        return 0.0
    body = text.lower()
    hits = sum(1 for token in q if token in body)
    if hits == 0:
        return 0.0
    return min(1.0, 0.45 + 0.12 * hits)


def _excerpt(text: str, max_len: int = 280) -> str:
    compact = " ".join(text.split())
    return compact[:max_len]


def _best_quote(question: str, text: str, max_len: int = 320) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    best_line = lines[0]
    best_score = _score(question, best_line)
    for line in lines[1:]:
        line_score = _score(question, line)
        if line_score > best_score:
            best_score = line_score
            best_line = line
    return best_line[:max_len]


def _canonical_hits(
    *,
    question: str,
    repo_ctx: Any,
    identity: Any,
    max_artifacts: int = 30,
    max_hits: int = 8,
) -> list[RetrievedHit]:
    url = (
        f"{repo_ctx.knowledge_api_url}/api/v1/artifacts"
        f"?artifact_type=memory_capture&repo_id={repo_ctx.repository_id}"
    )
    status, payload = request_json(
        url=url,
        method="GET",
        actor_id=identity.actor_id,
        company_id=repo_ctx.company_id,
        auth_profile="knowledge_api",
    )
    if status != 200 or not isinstance(payload, list):
        return []
    hits: list[RetrievedHit] = []
    for item in payload[:max_artifacts]:
        if not isinstance(item, dict):
            continue
        artifact_id = str(item.get("artifact_id", "")).strip()
        title = str(item.get("title", "")).strip()
        if not artifact_id:
            continue
        body_status, body_payload = request_json(
            url=f"{repo_ctx.knowledge_api_url}/api/v1/artifacts/{artifact_id}/body",
            method="GET",
            actor_id=identity.actor_id,
            company_id=repo_ctx.company_id,
            timeout_s=25,
            auth_profile="knowledge_api",
        )
        if body_status != 200 or not isinstance(body_payload, dict):
            continue
        body_text = str(body_payload.get("body_text", ""))
        combined = f"{title}\n{body_text}"
        score = _score(question, combined)
        if score <= 0:
            continue
        hits.append(
            RetrievedHit(
                source="canonical",
                score=score,
                artifact_id=artifact_id,
                title=title or artifact_id,
                excerpt=_excerpt(body_text or title),
                quote=_best_quote(question, body_text or title),
                metadata={
                    "repository_id": repo_ctx.repository_id,
                    "company_id": repo_ctx.company_id,
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:max_hits]


def _mempalace_hits(
    *,
    question: str,
    repo_ctx: Any,
    identity: Any,
    max_hits: int = 6,
) -> list[RetrievedHit]:
    body: dict[str, Any] = {"query": question, "limit": max_hits}
    palace_path = os.environ.get("MEMPALACE_PATH", "").strip()
    if palace_path:
        body["palace_path"] = palace_path
    status, payload = request_json(
        url=f"{repo_ctx.memory_adapter_url}/memory/search",
        method="POST",
        body=body,
        actor_id=identity.actor_id,
        company_id=repo_ctx.company_id,
        auth_profile="memory_adapter",
    )
    if status != 200 or not isinstance(payload, dict):
        return []
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    hits: list[RetrievedHit] = []
    for item in results[:max_hits]:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", ""))
        if not text.strip():
            continue
        score = float(item.get("similarity", 0.0) or 0.0)
        hits.append(
            RetrievedHit(
                source="mempalace",
                score=score,
                artifact_id=str(item.get("source_file", "")) or "mempalace-hit",
                title=str(item.get("source_file", "mempalace-hit")),
                excerpt=_excerpt(text),
                quote=_best_quote(question, text),
                metadata={
                    "wing": item.get("wing"),
                    "room": item.get("room"),
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hybrid memory ask: canonical + MemPalace.")
    parser.add_argument("question", help="Natural language memory question.")
    parser.add_argument("--json", action="store_true", dest="json_out")
    args = parser.parse_args(argv)

    identity = load_identity_context()
    repo_ctx = load_repo_context(identity)

    canonical = _canonical_hits(question=args.question, repo_ctx=repo_ctx, identity=identity)
    mempalace = _mempalace_hits(question=args.question, repo_ctx=repo_ctx, identity=identity)
    merged = sorted(
        [*canonical, *mempalace],
        key=lambda hit: (1 if hit.source == "canonical" else 0, hit.score),
        reverse=True,
    )[:10]
    payload = {
        "question": args.question,
        "actor_id": identity.actor_id,
        "company_id": repo_ctx.company_id,
        "repository_id": repo_ctx.repository_id,
        "canonical_hits": [asdict(item) for item in canonical],
        "mempalace_hits": [asdict(item) for item in mempalace],
        "top_hits": [asdict(item) for item in merged],
    }
    if args.json_out:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Memory answer for: {args.question}")
    print(f"(scope: {repo_ctx.company_id} / {repo_ctx.repository_id})")
    if not merged:
        print("- no relevant memory hits found")
        return 0
    for idx, hit in enumerate(merged[:5], start=1):
        print(
            f"{idx}. [{hit.source}] {hit.excerpt} "
            f"(score={hit.score:.2f}, id={hit.artifact_id})"
        )
        if hit.quote:
            print(f'   quote: "{hit.quote}"')
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
