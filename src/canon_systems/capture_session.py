"""Capture session output into canonical memory artifacts (AWS-backed)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .shared import (
    artifact_identity,
    first_text,
    load_identity_context,
    load_repo_context,
    parse_hook_payload,
    request_json,
)


def _extract_text(hook_payload: dict[str, Any]) -> tuple[str, str]:
    user_text = first_text(
        hook_payload,
        ("prompt", "user_prompt", "user_message", "message", "input", "text"),
    )
    assistant_text = first_text(
        hook_payload,
        ("response", "assistant_response", "agent_response", "output", "final", "text"),
    )
    return user_text, assistant_text


def _parse_json_list(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [line.strip() for line in raw.splitlines() if line.strip()]
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, str):
        return [parsed.strip()] if parsed.strip() else []
    return []


def _fallback_capture_via_knowledge_api(
    *,
    repo_ctx: Any,
    identity: Any,
    body: dict[str, Any],
    transcript_text: str,
) -> tuple[int, dict[str, Any] | list[Any] | str]:
    artifact_id = str(body["artifact_id"])
    version_id = str(body["version_id"])
    key = f"artifacts/{artifact_id}/{version_id}/body.md"
    payload = {
        "artifact_id": artifact_id,
        "version_id": version_id,
        "artifact_type": "memory_capture",
        "title": body["title"],
        "visibility": "team",
        "source_system": body["source_system"],
        "created_by": body["created_by"],
        "body_ref": {
            "storage": "s3",
            "bucket": body["body_bucket"],
            "key": key,
            "content_type": "text/markdown",
        },
        "body_text": transcript_text,
        "summary": body["summary"],
        "decisions": body.get("decisions", []),
        "next_actions": body.get("next_actions", []),
        "open_questions": body.get("open_questions", []),
        "owners": body.get("owners", []),
        "scope_ids": body.get("scope_ids", []),
        "repo_ids": body.get("repo_ids", []),
        "conversation_ids": body.get("conversation_ids", []),
        "work_item_ids": body.get("work_item_ids", []),
    }
    return request_json(
        url=f"{repo_ctx.knowledge_api_url}/api/v1/artifacts",
        method="POST",
        body=payload,
        actor_id=identity.actor_id,
        company_id=repo_ctx.company_id,
        timeout_s=30,
        auth_profile="knowledge_api",
    )


def _build_capture_body(
    *,
    actor_id: str,
    display_name: str,
    company_id: str,
    repository_id: str,
    artifact_bucket: str,
    summary: str,
    transcript_text: str,
    conversation_id: str,
    decisions: list[str],
    next_actions: list[str],
    open_questions: list[str],
) -> dict[str, Any]:
    artifact_id, version_id = artifact_identity(prefix="art_memcap", actor_id=actor_id)
    return {
        "artifact_id": artifact_id,
        "version_id": version_id,
        "title": f"Session memory capture ({display_name})",
        "transcript_text": transcript_text,
        "created_by": actor_id,
        "source_system": "cursor-memory-hooks",
        "body_bucket": artifact_bucket,
        "summary": summary,
        "decisions": decisions,
        "next_actions": next_actions,
        "open_questions": open_questions,
        "owners": [actor_id],
        "scope_ids": [company_id],
        "repo_ids": [repository_id],
        "conversation_ids": [conversation_id] if conversation_id else [],
    }


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture prompt/response into AWS-backed memory artifacts.",
    )
    parser.add_argument("--hook-input", default="", help="Path to hook JSON payload.")
    parser.add_argument("--summary", default="", help="Optional explicit summary text.")
    parser.add_argument("--user-text", default="", help="Explicit user text override.")
    parser.add_argument("--assistant-text", default="", help="Explicit assistant text override.")
    parser.add_argument("--conversation-id", default="", help="Optional conversation id.")
    parser.add_argument(
        "--pending-user-file",
        default="",
        help="Optional path to pending user prompt JSON from preflight hook.",
    )
    parser.add_argument(
        "--decisions",
        default="",
        help="Optional JSON array or newline list of distilled decisions.",
    )
    parser.add_argument(
        "--next-actions",
        default="",
        help="Optional JSON array or newline list of distilled next actions.",
    )
    parser.add_argument(
        "--open-questions",
        default="",
        help="Optional JSON array or newline list of distilled open questions.",
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce stderr output.")
    args = parser.parse_args(argv)

    payload = parse_hook_payload(args.hook_input)
    user_text, assistant_text = _extract_text(payload)
    if args.user_text.strip():
        user_text = args.user_text.strip()
    if args.assistant_text.strip():
        assistant_text = args.assistant_text.strip()

    pending_used = False
    pending_path = args.pending_user_file.strip()
    conversation_id_override = args.conversation_id.strip()
    if not user_text and pending_path:
        p = Path(pending_path)
        if p.exists():
            try:
                pending_payload = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pending_payload = {}
            if isinstance(pending_payload, dict):
                user_text = str(pending_payload.get("user_text", "")).strip() or user_text
                if not conversation_id_override:
                    pc = str(pending_payload.get("conversation_id", "")).strip()
                    if pc:
                        conversation_id_override = pc
                pending_used = True

    if not user_text and not assistant_text and not args.summary.strip():
        return 0

    identity = load_identity_context()
    repo_ctx = load_repo_context(identity)

    summary = args.summary.strip() or user_text[:240] or "Assistant session update"
    conversation_id = (
        conversation_id_override
        or first_text(payload, ("conversation_id", "source_conversation_id", "thread_id"))
        or ""
    )
    decisions = _parse_json_list(args.decisions)
    next_actions = _parse_json_list(args.next_actions)
    open_questions = _parse_json_list(args.open_questions)

    transcript_sections: list[str] = []
    if user_text:
        transcript_sections.append(f"## User Prompt\n\n{user_text}")
    if assistant_text:
        transcript_sections.append(f"## Assistant Output\n\n{assistant_text}")
    if decisions:
        transcript_sections.append(
            "## Decisions\n\n" + "\n".join(f"- {item}" for item in decisions)
        )
    if next_actions:
        transcript_sections.append(
            "## Next Actions\n\n" + "\n".join(f"- {item}" for item in next_actions)
        )
    if open_questions:
        transcript_sections.append(
            "## Open Questions\n\n" + "\n".join(f"- {item}" for item in open_questions)
        )
    transcript_sections.append(
        "## Metadata\n\n"
        f"- actor_id: {identity.actor_id}\n"
        f"- actor_display_name: {identity.display_name}\n"
        f"- company_id: {repo_ctx.company_id}\n"
        f"- repository_id: {repo_ctx.repository_id}\n"
        f"- source_surface: cursor\n"
    )
    transcript_text = "\n\n".join(transcript_sections)

    body = _build_capture_body(
        actor_id=identity.actor_id,
        display_name=identity.display_name,
        company_id=repo_ctx.company_id,
        repository_id=repo_ctx.repository_id,
        artifact_bucket=repo_ctx.artifact_bucket,
        summary=summary,
        transcript_text=transcript_text,
        conversation_id=conversation_id,
        decisions=decisions,
        next_actions=next_actions,
        open_questions=open_questions,
    )

    status, response_payload = request_json(
        url=f"{repo_ctx.knowledge_worker_url}/jobs/capture-memory",
        method="POST",
        body=body,
        actor_id=identity.actor_id,
        company_id=repo_ctx.company_id,
        timeout_s=30,
        auth_profile="knowledge_worker",
    )
    if status not in (200, 201):
        fb_status, fb_payload = _fallback_capture_via_knowledge_api(
            repo_ctx=repo_ctx,
            identity=identity,
            body=body,
            transcript_text=transcript_text,
        )
        if fb_status in (200, 201):
            status = fb_status
            response_payload = {
                "fallback": "knowledge_api.create_artifact",
                "payload": fb_payload,
            }

    audit_path = repo_ctx.context_dir / "capture-latest.json"
    audit_body = {
        "request": body,
        "response_status": status,
        "response_payload": response_payload,
    }
    audit_path.write_text(json.dumps(audit_body, indent=2) + "\n", encoding="utf-8")

    if status not in (200, 201):
        failure_path = repo_ctx.context_dir / "capture-failures.log"
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        failure_path.write_text(
            (failure_path.read_text(encoding="utf-8") if failure_path.exists() else "")
            + json.dumps(audit_body, ensure_ascii=True)
            + "\n",
            encoding="utf-8",
        )

    if pending_used and pending_path:
        try:
            os.remove(pending_path)
        except OSError:
            pass

    if not args.quiet:
        print(
            "memory-layer capture: "
            f"actor={identity.actor_id} company={repo_ctx.company_id} "
            f"repo={repo_ctx.repository_id} http={status}",
            file=sys.stderr,
        )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
