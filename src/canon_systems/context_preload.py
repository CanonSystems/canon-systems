"""Preload MemPalace + current-truth context for agent sessions."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from .memory_queue import (
    classify_mempalace_response,
    enqueue_mempalace_retry,
    is_degraded,
)
from .shared import (
    artifact_identity,
    first_text,
    load_identity_context,
    load_repo_context,
    now_stamp,
    parse_hook_payload,
    request_json,
)


def _pick_prompt(cli_prompt: str, hook_payload: dict[str, Any]) -> str:
    if cli_prompt.strip():
        return cli_prompt.strip()
    return first_text(
        hook_payload,
        ("prompt", "user_prompt", "message", "user_message", "input", "text"),
    )


def _write_markdown(
    *,
    output_path: Path,
    query: str,
    memory_payload: dict[str, Any] | str,
    current_truth_payload: list[dict[str, Any]] | str,
    company_id: str,
    repository_id: str,
    mempalace_status: dict[str, Any],
) -> None:
    lines = [
        "# Session Memory Context",
        "",
        f"- company_id: `{company_id}`",
        f"- repository_id: `{repository_id}`",
        f"- query: `{query}`",
        "",
        "## MemPalace Status",
    ]
    lines.append(f"- status: `{mempalace_status.get('status', '')}`")
    lines.append(f"- latency_ms: `{mempalace_status.get('latency_ms', '')}`")
    le = str(mempalace_status.get("last_error", ""))
    lines.append(f"- last_error: `{le}`")
    lines.append(f"- endpoint_ref: `{mempalace_status.get('endpoint_ref', '')}`")
    lines.extend(["", "## MemPalace Hits"])
    if isinstance(memory_payload, dict):
        results = memory_payload.get("results") or []
        if results:
            for idx, hit in enumerate(results[:8], start=1):
                text = str(hit.get("text", "")).strip().replace("\n", " ")
                wing = str(hit.get("wing", "unknown"))
                room = str(hit.get("room", "unknown"))
                source = str(hit.get("source_file", "?"))
                lines.append(f"{idx}. {text[:220]}")
                lines.append(f"   - wing/room: `{wing}/{room}` source: `{source}`")
        else:
            lines.append("- no matching memory hits")
    else:
        lines.append(f"- memory query unavailable: `{memory_payload}`")
    lines.extend(["", "## Current Truth Artifacts"])
    if isinstance(current_truth_payload, list) and current_truth_payload:
        for item in current_truth_payload[:10]:
            art_id = str(item.get("artifact_id", ""))
            art_type = str(item.get("artifact_type", ""))
            title = str(item.get("title", ""))
            lines.append(f"- `{art_type}` `{art_id}`: {title}")
    else:
        lines.append("- no current-truth artifacts found for this repo/scope")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load memory and current-truth context.")
    parser.add_argument("prompt", nargs="?", default="", help="Optional prompt text.")
    parser.add_argument("--hook-input", default="", help="Path to hook JSON payload.")
    parser.add_argument("--json-output", default="")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    hook_payload = parse_hook_payload(args.hook_input)
    prompt = _pick_prompt(args.prompt, hook_payload)
    identity = load_identity_context()
    repo_ctx = load_repo_context(identity)

    query = prompt or f"Working context for {repo_ctx.repository_id} at {repo_ctx.company_id}."
    memory_body: dict[str, Any] = {"query": query, "limit": 6}
    import os as _os
    palace_path = _os.environ.get("MEMPALACE_PATH", "").strip()
    if palace_path:
        memory_body["palace_path"] = palace_path
    configured = bool((repo_ctx.memory_adapter_url or "").strip())
    endpoint_ref = f"{repo_ctx.memory_adapter_url}/memory/search" if configured else ""
    if configured:
        t0 = time.perf_counter()
        memory_status, memory_payload = request_json(
            url=endpoint_ref,
            method="POST",
            body=memory_body,
            actor_id=identity.actor_id,
            company_id=repo_ctx.company_id,
            auth_profile="memory_adapter",
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
    else:
        memory_status, memory_payload = 0, ""
        latency_ms = 0
    mempalace_status = classify_mempalace_response(
        status=int(memory_status),
        payload=memory_payload,
        endpoint_ref=endpoint_ref,
        latency_ms=latency_ms,
        configured=configured,
    )
    if is_degraded(mempalace_status):
        enqueue_mempalace_retry(
            {
                "queued_at": now_stamp(),
                "call_site": "context_preload",
                "endpoint_ref": mempalace_status["endpoint_ref"],
                "request_body": memory_body,
                "last_status": int(memory_status),
                "last_error": mempalace_status["last_error"],
                "actor_id": identity.actor_id,
                "company_id": repo_ctx.company_id,
                "repository_id": repo_ctx.repository_id,
            }
        )
    current_truth_status, current_truth_payload = request_json(
        url=f"{repo_ctx.knowledge_api_url}/api/v1/artifacts?repo_id={repo_ctx.repository_id}",
        method="GET",
        actor_id=identity.actor_id,
        company_id=repo_ctx.company_id,
        auth_profile="knowledge_api",
    )

    context_md = repo_ctx.context_dir / "context-latest.md"
    _write_markdown(
        output_path=context_md,
        query=query,
        memory_payload=memory_payload,
        current_truth_payload=current_truth_payload if isinstance(current_truth_payload, list) else [],
        company_id=repo_ctx.company_id,
        repository_id=repo_ctx.repository_id,
        mempalace_status=mempalace_status,
    )
    artifact_id, version_id = artifact_identity(prefix="art_taskctx_preload", actor_id=identity.actor_id)
    output_json = Path(args.json_output) if args.json_output else (repo_ctx.context_dir / "context-latest.json")
    output_json.write_text(
        json.dumps(
            {
                "status": "ok",
                "actor_id": identity.actor_id,
                "company_id": repo_ctx.company_id,
                "repository_id": repo_ctx.repository_id,
                "query": query,
                "memory_status_code": memory_status,
                "mempalace_status": mempalace_status,
                "current_truth_status_code": current_truth_status,
                "context_markdown_path": str(context_md),
                "task_context_artifact_id_hint": artifact_id,
                "task_context_version_id_hint": version_id,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if not args.quiet:
        print(
            "memory-layer preflight: "
            f"actor={identity.actor_id} company={repo_ctx.company_id} "
            f"repo={repo_ctx.repository_id} memory_http={memory_status} "
            f"truth_http={current_truth_status}",
            file=sys.stderr,
        )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
