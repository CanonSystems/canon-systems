"""Send structured DoR failure telemetry to remote service."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .shared import (
    artifact_identity,
    load_env_file,
    load_identity_context,
    load_repo_context,
    now_stamp,
    repo_root,
    resolve_auth_bearer,
)


def _queue_path() -> Path:
    path = repo_root() / ".canon" / "memory" / "dor-failure-queue.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _parse_event(args: argparse.Namespace) -> dict[str, Any]:
    raw = ""
    if args.event_json:
        raw = args.event_json
    elif args.event_file:
        p = Path(args.event_file)
        if not p.exists():
            raise ValueError(f"event file not found: {p}")
        raw = p.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()

    if not raw.strip():
        raise ValueError("missing event payload (use --event-json, --event-file, or stdin)")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("event payload must be a JSON object")
    return parsed


def _base_url_from_env() -> str:
    explicit = os.environ.get("CANON_DOR_LOG_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    local = load_env_file(repo_root() / ".canon" / "memory-layer.local.env")
    return (
        os.environ.get("KNOWLEDGE_API_URL", "").strip()
        or local.get("KNOWLEDGE_API_URL", "").strip()
        or "https://memory.canon-systems.com"
    ).rstrip("/")


def _candidate_urls() -> list[str]:
    explicit = os.environ.get("CANON_DOR_LOG_URL", "").strip()
    if explicit:
        return [explicit]
    base = _base_url_from_env()
    return [
        f"{base}/api/v1/agent-events/dor-failures",
        f"{base}/api/v1/artifacts",
    ]


def _post_json(url: str, payload: dict[str, Any], *, timeout_s: int = 8) -> tuple[int, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    bearer = resolve_auth_bearer("knowledge_api")
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    else:
        api_key = os.environ.get("KNOWLEDGE_API_KEY", "").strip()
        if api_key:
            headers["X-API-Key"] = api_key
    req = urllib.request.Request(
        url=url,
        method="POST",
        headers=headers,
        data=json.dumps(payload).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except urllib.error.URLError as exc:
        return 0, f"request failed: {exc.reason!s}"


def _artifact_payload(event: dict[str, Any]) -> dict[str, Any]:
    identity = load_identity_context()
    try:
        repo_ctx = load_repo_context(identity)
        company_id = repo_ctx.company_id
        repository_id = repo_ctx.repository_id
    except Exception:
        company_id = os.environ.get("COMPANY_ID", "UNKNOWN_COMPANY")
        repository_id = os.environ.get("REPOSITORY_ID", "unknown-repo")

    stage = str(event.get("stage", "unknown")).strip() or "unknown"
    root_causes = event.get("root_causes", [])
    if not isinstance(root_causes, list):
        root_causes = []
    decisions = [str(x).strip() for x in root_causes if str(x).strip()]
    artifact_id, version_id = artifact_identity(prefix="art_dor_failure", actor_id=identity.actor_id)
    summary = (
        str(event.get("summary", "")).strip()
        or str(event.get("quality_failures", "")).strip()
        or f"DoR failure at stage={stage}"
    )
    return {
        "artifact_id": artifact_id,
        "version_id": version_id,
        "artifact_type": "agent_dor_failure",
        "title": f"DoR failure ({stage})",
        "visibility": "team",
        "source_system": "cursor-agent-dor",
        "created_by": identity.actor_id,
        "summary": summary,
        "body_text": json.dumps(event, indent=2, ensure_ascii=True),
        "decisions": decisions,
        "next_actions": [str(x).strip() for x in event.get("remediation_steps", []) if str(x).strip()],
        "open_questions": [str(x).strip() for x in event.get("open_questions", []) if str(x).strip()],
        "scope_ids": [company_id],
        "repo_ids": [repository_id],
    }


def _agent_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(event)
    enriched.setdefault("event_type", "dor_failure")
    enriched.setdefault("captured_at", now_stamp())
    enriched.setdefault("source", "canon-cli")
    return enriched


def _enqueue_failed_event(event: dict[str, Any], *, attempted_urls: list[str], status: int, response: str) -> None:
    record = {
        "queued_at": now_stamp(),
        "event": event,
        "attempted_urls": attempted_urls,
        "last_status": status,
        "last_response": response[:4000],
    }
    path = _queue_path()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(existing + json.dumps(record, ensure_ascii=True) + "\n", encoding="utf-8")


def _iter_queue(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            out.append(parsed)
    return out


def _ship_event(event: dict[str, Any]) -> tuple[bool, str]:
    urls = _candidate_urls()
    last_status = 0
    last_response = "no response"
    for url in urls:
        if url.rstrip("/").endswith("/api/v1/artifacts"):
            payload = _artifact_payload(event)
        else:
            payload = _agent_event_payload(event)
        status, response = _post_json(url, payload)
        if status in (200, 201, 202):
            return True, f"sent to {url} status={status}"
        last_status, last_response = status, response
    _enqueue_failed_event(event, attempted_urls=urls, status=last_status, response=last_response)
    return False, f"queued locally after failures (status={last_status}, response={last_response})"


def _flush_queue(*, quiet: bool) -> tuple[int, int]:
    path = _queue_path()
    rows = _iter_queue(path)
    if not rows:
        return 0, 0
    kept: list[dict[str, Any]] = []
    sent = 0
    for row in rows:
        event = row.get("event")
        if not isinstance(event, dict):
            continue
        ok, _msg = _ship_event(event)
        if ok:
            sent += 1
        else:
            kept.append(row)
    if kept:
        body = "\n".join(json.dumps(item, ensure_ascii=True) for item in kept) + "\n"
        path.write_text(body, encoding="utf-8")
    elif path.exists():
        path.unlink()
    if not quiet:
        print(f"dor-log flush: sent={sent} remaining={len(kept)}")
    return sent, len(kept)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="canon dor-log")
    parser.add_argument("--event-json", default="")
    parser.add_argument("--event-file", default="")
    parser.add_argument("--flush-queue", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.flush_queue:
        _flush_queue(quiet=args.quiet)

    try:
        event = _parse_event(args)
    except (ValueError, json.JSONDecodeError) as exc:
        if not args.quiet:
            print(f"dor-log error: {exc}", file=sys.stderr)
        return 2

    ok, msg = _ship_event(event)
    if not args.quiet:
        print(f"dor-log: {msg}")
    if ok:
        return 0
    return 1 if args.strict else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
