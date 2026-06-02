"""Local live-meeting planning workflow for Canon.

This module is the credential-free core behind a future meeting participant
bot. It stores durable meeting state, references, verified plan items, and a
Cursor handoff artifact without requiring Google Meet or OpenAI credentials.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import email.policy
import hashlib
import http.server
import json
import mimetypes
import os
import re
import secrets
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from email.parser import BytesParser

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_MALFORMED = 4

_ITEM_TYPES = ("task", "decision", "open_question", "assumption")
_ITEM_STATUSES = ("draft", "read_back_pending", "confirmed", "amended", "rejected")
_MODES = ("prompted", "independent-hand-raise")
_REFERENCE_TYPES = ("image", "file", "url", "repo", "memory", "meeting")
_HAND_RAISE_STATUS = ("pending", "approved", "dismissed")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(raw: str) -> datetime | None:
    if not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _slug(value: str, *, fallback: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return s[:80] or fallback


def _repo_root() -> Path:
    raw = os.environ.get("CANON_SYSTEMS_REPO_ROOT", "")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.cwd().resolve()


def _state_dir(root: Path, session_id: str) -> Path:
    return root / ".canon" / "live-plan" / session_id


def _state_path(root: Path, session_id: str) -> Path:
    return _state_dir(root, session_id) / "session.json"


def _plan_path(root: Path, plan_id: str) -> Path:
    return root / ".cursor" / "plans" / f"{plan_id}.plan.md"


def _handoff_path(root: Path, session_id: str) -> Path:
    return root / ".cursor" / "handoffs" / session_id / "meeting-plan-handoff.md"


def _index_path(root: Path) -> Path:
    return root / ".canon" / "live-plan" / "index.json"


def _registry_path(root: Path) -> Path:
    return root / ".canon" / "live-plan" / "participants.json"


def _session_handoff_path(root: Path, session_id: str) -> Path:
    return _state_dir(root, session_id) / "session-handoff.md"


def _transcript_path(root: Path, session_id: str) -> Path:
    return _state_dir(root, session_id) / "transcript.md"


def _references_path(root: Path, session_id: str) -> Path:
    return _state_dir(root, session_id) / "references.md"


def _panel_manifest_path(root: Path, session_id: str) -> Path:
    return _state_dir(root, session_id) / "panel-manifest.json"


def _session_upload_dir(root: Path, session_id: str) -> Path:
    return _state_dir(root, session_id) / "uploads"


def _live_panel_static_dir() -> Path:
    return Path(__file__).resolve().parent / "static" / "live_plan_panel"


def _load_state(root: Path, session_id: str) -> dict[str, Any]:
    path = _state_path(root, session_id)
    if not path.exists():
        raise FileNotFoundError(f"live-plan session not found: {session_id}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed live-plan state: {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"malformed live-plan state: {path}: expected object")
    return parsed


def _write_state(root: Path, state: dict[str, Any]) -> Path:
    session_id = str(state["session_id"])
    path = _state_path(root, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_json_file(path: Path, *, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON file: {path}: {exc}") from exc


def _write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sanitize_filename(name: str) -> str:
    base = Path(name or "upload.bin").name
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", base).strip(".-")
    return cleaned[:120] or "upload.bin"


def _parse_participant(raw: str) -> dict[str, str]:
    parts = [p.strip() for p in raw.split(":")]
    name = parts[0] if parts else ""
    email = parts[1] if len(parts) > 1 else ""
    voice = parts[2] if len(parts) > 2 else "unknown"
    return {
        "name": name,
        "email": email,
        "voice_profile_status": voice or "unknown",
    }


def _participant_key(name: str, email: str) -> str:
    return (email or name).strip().lower()


def _load_registry(root: Path) -> dict[str, Any]:
    parsed = _load_json_file(_registry_path(root), default={"schema_version": 1, "participants": []})
    if not isinstance(parsed, dict):
        raise ValueError("participant registry must be a JSON object")
    parsed.setdefault("schema_version", 1)
    parsed.setdefault("participants", [])
    return parsed


def _registry_lookup(root: Path) -> dict[str, dict[str, Any]]:
    registry = _load_registry(root)
    out: dict[str, dict[str, Any]] = {}
    for person in registry.get("participants", []):
        if not isinstance(person, dict):
            continue
        key = _participant_key(str(person.get("name", "")), str(person.get("email", "")))
        if key:
            out[key] = person
    return out


def _hydrate_participants(root: Path, raw_people: list[str]) -> list[dict[str, Any]]:
    registry = _registry_lookup(root)
    people: list[dict[str, Any]] = []
    for raw in raw_people:
        parsed = _parse_participant(raw)
        key = _participant_key(parsed["name"], parsed["email"])
        registered = registry.get(key, {})
        voice_refs = registered.get("voice_refs", []) if isinstance(registered, dict) else []
        people.append({
            **parsed,
            "person_id": registered.get("person_id", _slug(key, fallback=parsed["name"] or "participant")),
            "voice_refs": voice_refs,
            "voice_profile_status": (
                parsed.get("voice_profile_status")
                if parsed.get("voice_profile_status") != "unknown"
                else ("has_voice" if voice_refs else "missing_voice")
            ),
        })
    return people


def _next_id(items: list[dict[str, Any]], prefix: str) -> str:
    id_field = {
        "item": "item_id",
        "ref": "ref_id",
        "seg": "segment_id",
        "hand": "hand_raise_id",
    }.get(prefix, f"{prefix}_id")
    n = len(items) + 1
    while any(str(item.get(id_field, "")) == f"{prefix}-{n:03d}" for item in items):
        n += 1
    return f"{prefix}-{n:03d}"


def _render_plan_md(state: dict[str, Any]) -> str:
    plan_id = str(state["plan_id"])
    title = str(state.get("topic") or plan_id)
    confirmed = [
        item for item in state.get("plan_items", [])
        if item.get("status") in ("confirmed", "amended")
    ]
    unconfirmed = [
        item for item in state.get("plan_items", [])
        if item.get("status") not in ("confirmed", "amended")
    ]
    todos = [
        item for item in confirmed
        if item.get("type") in ("task", "open_question")
    ]
    lines: list[str] = [
        "---",
        f"name: {title}",
        "overview: Meeting-derived Canon execution plan with verified plan items and cited references.",
        "todos:",
    ]
    if todos:
        for item in todos:
            lines += [
                f"  - id: {item['item_id']}",
                f"    content: {json.dumps(str(item.get('title') or item.get('content') or item['item_id']))}",
                "    status: pending",
            ]
    else:
        lines += [
            "  - id: review_meeting_plan",
            "    content: Review meeting-derived plan and confirm implementation scope",
            "    status: pending",
        ]
    lines += [
        "isProject: false",
        "---",
        "",
        f"# {title}",
        "",
        "## Build Kickoff",
        "",
        "If the user pressed Build on this plan, hydrate from Canon artifacts before coding.",
        "",
        "1. Read this plan file in full.",
        f"2. Read `.canon/live-plan/{state['session_id']}/session.json` for the verbatim meeting record, verification states, and evidence references.",
        "3. Run `canon ask` for prior memory on the plan topic before scoping implementation.",
        "4. Do not implement unconfirmed items unless the user explicitly approves them in this Cursor session.",
        "5. Start the normal Canon chain: `project-planner -> scoper -> cursor-pilot -> implementer -> qa-gate`.",
        "",
        "## Session",
        "",
        f"- plan_id: {plan_id}",
        f"- session_id: {state['session_id']}",
        f"- company_id: {state.get('company_id', '')}",
        f"- primary_repository_id: {state.get('primary_repository_id', '')}",
        f"- repository_ids: {', '.join(state.get('repository_ids', []))}",
        f"- meeting_ref: {state.get('meeting_ref', '')}",
        f"- participation_mode: {state.get('mode', '')}",
        f"- session_handoff: `.canon/live-plan/{state['session_id']}/session-handoff.md`",
        f"- transcript: `.canon/live-plan/{state['session_id']}/transcript.md`",
        f"- references: `.canon/live-plan/{state['session_id']}/references.md`",
        "",
        "## Confirmed Items",
        "",
    ]
    if confirmed:
        for item in confirmed:
            refs = ", ".join(item.get("evidence_refs", [])) or "none"
            lines += [
                f"### {item['item_id']} - {item.get('title', '')}",
                "",
                f"- type: {item.get('type', '')}",
                f"- status: {item.get('status', '')}",
                f"- evidence_refs: {refs}",
                "",
                str(item.get("content", "")).strip(),
                "",
            ]
    else:
        lines += ["No confirmed items yet.", ""]
    lines += ["## Unconfirmed Or Rejected Items", ""]
    if unconfirmed:
        for item in unconfirmed:
            lines += [
                f"- {item['item_id']} [{item.get('status', '')}] {item.get('title', '')}",
            ]
    else:
        lines += ["None.", ""]
    lines += ["", "## References", ""]
    refs = state.get("references", [])
    if refs:
        for ref in refs:
            loc = ref.get("path") or ref.get("uri") or ""
            lines += [
                f"- {ref['ref_id']} [{ref.get('type', '')}] {ref.get('title', '')} - {loc}",
            ]
    else:
        lines += ["No references captured.", ""]
    lines += [
        "",
        "## Hand Raises",
        "",
    ]
    hand_raises = state.get("hand_raises", [])
    if hand_raises:
        for event in hand_raises:
            lines += [
                f"- {event['hand_raise_id']} [{event.get('status', '')}] {event.get('reason', '')}",
            ]
    else:
        lines += ["None.", ""]
    lines += [
        "",
        "## Cursor Resume Prompt",
        "",
        "Use this if Cursor does not reopen the saved markdown as a Build-capable plan:",
        "",
        "```text",
        f"Load Canon live meeting plan `{plan_id}` from `.canon/live-plan/{state['session_id']}/session.json` and `.cursor/plans/{plan_id}.plan.md`.",
        "Hydrate the meeting evidence, confirmed items, and unresolved questions. Then present the plan in Cursor Plan Mode with a Build action.",
        "```",
        "",
    ]
    return "\n".join(lines)


def _render_handoff_md(state: dict[str, Any], plan_file: Path) -> str:
    return "\n".join([
        f"# Live Meeting Handoff - {state['plan_id']}",
        "",
        f"- session_id: {state['session_id']}",
        f"- plan_id: {state['plan_id']}",
        f"- plan_file: {plan_file}",
        f"- state_file: {_state_path(_repo_root(), state['session_id'])}",
        "",
        "## Open In Cursor Plan",
        "",
        "If Cursor shows this markdown without a Build button, start a fresh Cursor Plan Mode session with this prompt:",
        "",
        "```text",
        f"Resume Canon plan `{state['plan_id']}` for repository `{state.get('primary_repository_id', '')}`.",
        f"Read `.cursor/plans/{state['plan_id']}.plan.md` and `.canon/live-plan/{state['session_id']}/session.json`.",
        "Use only confirmed or amended meeting items by default, preserve citations to meeting references, and ask before including any unconfirmed item.",
        "Show the implementation plan in Cursor Plan Mode with a Build action.",
        "```",
        "",
    ])


def _render_session_handoff_md(state: dict[str, Any]) -> str:
    confirmed = [
        item for item in state.get("plan_items", [])
        if item.get("status") in ("confirmed", "amended")
    ]
    open_items = [
        item for item in state.get("plan_items", [])
        if item.get("status") not in ("confirmed", "amended", "rejected")
    ]
    lines = [
        f"# Session Handoff - {state.get('topic') or state['plan_id']}",
        "",
        f"- session_id: {state['session_id']}",
        f"- plan_id: {state['plan_id']}",
        f"- company_id: {state.get('company_id', '')}",
        f"- repository_ids: {', '.join(state.get('repository_ids', []))}",
        f"- status: {state.get('status', '')}",
        "",
        "## Where We Left Off",
        "",
        f"Confirmed {len(confirmed)} item(s); {len(open_items)} item(s) still need confirmation or disposition.",
        "",
        "## Confirmed Items",
        "",
    ]
    if confirmed:
        for item in confirmed:
            lines.append(f"- {item['item_id']} [{item.get('type', '')}] {item.get('title', '')}")
    else:
        lines.append("None.")
    lines += ["", "## Open Items", ""]
    if open_items:
        for item in open_items:
            lines.append(f"- {item['item_id']} [{item.get('status', '')}] {item.get('title', '')}")
    else:
        lines.append("None.")
    lines += ["", "## Evidence", ""]
    refs = state.get("references", [])
    if refs:
        for ref in refs:
            loc = ref.get("path") or ref.get("uri") or ""
            lines.append(f"- {ref['ref_id']} [{ref.get('type', '')}] {ref.get('title', '')} - {loc}")
    else:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def _render_transcript_md(state: dict[str, Any]) -> str:
    lines = [f"# Transcript - {state['session_id']}", ""]
    for seg in state.get("transcript_segments", []):
        lines += [
            f"## {seg.get('timestamp', '')} - {seg.get('speaker', 'unknown')}",
            "",
            str(seg.get("text", "")).strip(),
            "",
        ]
    if len(lines) == 2:
        lines.append("No transcript segments captured.")
        lines.append("")
    return "\n".join(lines)


def _render_references_md(state: dict[str, Any]) -> str:
    lines = [f"# References - {state['session_id']}", ""]
    for ref in state.get("references", []):
        lines += [
            f"## {ref['ref_id']} - {ref.get('title', '')}",
            "",
            f"- type: {ref.get('type', '')}",
            f"- path: {ref.get('path', '')}",
            f"- uri: {ref.get('uri', '')}",
            f"- shared_to_meeting: {ref.get('shared_to_meeting', False)}",
            f"- meeting_chat_status: {ref.get('meeting_chat_status', '')}",
            "",
            str(ref.get("summary", "")).strip() or "No summary.",
            "",
        ]
    if len(lines) == 2:
        lines.append("No references captured.")
        lines.append("")
    return "\n".join(lines)


def _runtime_manifest_path(root: Path, session_id: str) -> Path:
    return _state_dir(root, session_id) / "runtime-manifest.json"


def _google_token_cache_path(root: Path) -> Path:
    return root / ".canon" / "live-plan" / "google-oauth-token.json"


def _google_oauth_session_path(root: Path) -> Path:
    return root / ".canon" / "live-plan" / "google-oauth-session.json"


def _google_media_session_dir(root: Path) -> Path:
    return root / ".canon" / "live-plan" / "media"


def _google_media_session_path(root: Path, session_id: str) -> Path:
    return _google_media_session_dir(root) / f"{session_id}.json"


def _load_google_media_session(root: Path, session_id: str) -> dict[str, Any]:
    path = _google_media_session_path(root, session_id)
    if not path.exists():
        raise FileNotFoundError(f"Google Meet media session not found: {path}")
    parsed = _load_json_file(path, default={})
    if not isinstance(parsed, dict):
        raise ValueError(f"malformed Google Meet media session: {path}")
    return parsed


def _append_reference_to_state(
    state: dict[str, Any],
    *,
    ref_type: str,
    title: str,
    path: str = "",
    uri: str = "",
    summary: str = "",
    shared_to_meeting: bool = False,
    meeting_chat_status: str = "not_requested",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    refs = list(state.get("references", []))
    ref = {
        "ref_id": _next_id(refs, "ref"),
        "type": ref_type,
        "title": title,
        "path": path,
        "uri": uri,
        "summary": summary,
        "shared_to_meeting": bool(shared_to_meeting),
        "meeting_chat_status": meeting_chat_status,
        "added_at": _now(),
        "metadata": dict(metadata or {}),
    }
    refs.append(ref)
    state["references"] = refs
    return ref


def _append_transcript_to_state(
    state: dict[str, Any],
    *,
    speaker: str,
    text: str,
    source: str = "manual",
    timestamp: str = "",
) -> dict[str, Any]:
    segs = list(state.get("transcript_segments", []))
    seg = {
        "segment_id": _next_id(segs, "seg"),
        "speaker": speaker,
        "text": text,
        "source": source,
        "timestamp": timestamp or _now(),
    }
    segs.append(seg)
    state["transcript_segments"] = segs
    return seg


def _append_plan_item_to_state(
    state: dict[str, Any],
    *,
    item_type: str,
    title: str,
    content: str,
    evidence_refs: list[str] | None = None,
    requires_confirmation: bool = True,
) -> dict[str, Any]:
    items = list(state.get("plan_items", []))
    item = {
        "item_id": _next_id(items, "item"),
        "type": item_type,
        "title": title,
        "content": content,
        "status": "read_back_pending" if requires_confirmation else "draft",
        "evidence_refs": list(evidence_refs or []),
        "created_at": _now(),
        "verified_at": "",
        "verification_prompt": f"So the item reads like this: {title}. {content}".strip(),
    }
    items.append(item)
    state["plan_items"] = items
    return item


def _confirm_plan_item_in_state(
    state: dict[str, Any],
    *,
    item_id: str,
    status: str,
    title: str = "",
    content: str = "",
) -> dict[str, Any]:
    for item in state.get("plan_items", []):
        if item.get("item_id") == item_id:
            item["status"] = status
            if title:
                item["title"] = title
            if content:
                item["content"] = content
            item["verified_at"] = _now() if status in ("confirmed", "amended") else ""
            return item
    raise FileNotFoundError(f"item not found: {item_id}")


def _raise_hand_in_state(state: dict[str, Any], *, reason: str, item_id: str = "") -> dict[str, Any]:
    events = list(state.get("hand_raises", []))
    event = {
        "hand_raise_id": _next_id(events, "hand"),
        "reason": reason,
        "item_id": item_id,
        "status": "pending",
        "created_at": _now(),
        "resolved_at": "",
    }
    events.append(event)
    state["hand_raises"] = events
    return event


def _raise_hand_for_plan_item(state: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    item_id = str(item.get("item_id", "")).strip()
    title = str(item.get("title", "")).strip() or item_id or "pending item"
    return _raise_hand_in_state(
        state,
        reason=f"Read back and confirm: {title}",
        item_id=item_id,
    )


def _resolve_hand_in_state(state: dict[str, Any], *, hand_raise_id: str, status: str) -> dict[str, Any]:
    for event in state.get("hand_raises", []):
        if event.get("hand_raise_id") == hand_raise_id:
            event["status"] = status
            event["resolved_at"] = _now()
            return event
    raise FileNotFoundError(f"hand raise not found: {hand_raise_id}")


def _resolve_pending_hand_for_item(state: dict[str, Any], *, item_id: str, status: str) -> dict[str, Any] | None:
    for event in state.get("hand_raises", []):
        if event.get("item_id") == item_id and event.get("status") == "pending":
            event["status"] = status
            event["resolved_at"] = _now()
            return event
    return None


def _set_mode_in_state(state: dict[str, Any], *, mode: str) -> tuple[str, str]:
    old = str(state.get("mode", ""))
    state["mode"] = mode
    return old, mode


def _google_oauth_client_path() -> str:
    return os.environ.get("CANON_GOOGLE_OAUTH_CLIENT_JSON", "").strip()


def _google_service_account_path() -> str:
    return os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()


def _google_meet_token() -> str:
    return os.environ.get("GOOGLE_MEET_MEDIA_API_TOKEN", "").strip()


def _google_credentials_status() -> tuple[bool, list[str]]:
    present: list[str] = []
    oauth_client = _google_oauth_client_path()
    service_account = _google_service_account_path()
    meet_token = _google_meet_token()
    if oauth_client:
        present.append("CANON_GOOGLE_OAUTH_CLIENT_JSON")
    if service_account:
        present.append("GOOGLE_APPLICATION_CREDENTIALS")
    if meet_token:
        present.append("GOOGLE_MEET_MEDIA_API_TOKEN")
    return bool(present), present


def _load_google_oauth_client() -> dict[str, Any]:
    raw = _google_oauth_client_path()
    if not raw:
        raise FileNotFoundError("CANON_GOOGLE_OAUTH_CLIENT_JSON is not set")
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Google OAuth client JSON not found: {path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed Google OAuth client JSON: {path}: {exc}") from exc
    installed = parsed.get("installed")
    if not isinstance(installed, dict):
        raise ValueError(f"Google OAuth client JSON missing installed client config: {path}")
    client_id = str(installed.get("client_id", "")).strip()
    client_secret = str(installed.get("client_secret", "")).strip()
    if not client_id or not client_secret:
        raise ValueError(f"Google OAuth client JSON missing client_id/client_secret: {path}")
    return {
        "path": str(path),
        "client_type": "installed",
        "client_id": client_id,
        "client_secret": client_secret,
        "project_id": str(installed.get("project_id", "")).strip(),
        "auth_uri": str(installed.get("auth_uri", "")).strip(),
        "token_uri": str(installed.get("token_uri", "")).strip(),
        "redirect_uris": [
            str(uri).strip() for uri in installed.get("redirect_uris", [])
            if str(uri).strip()
        ],
    }


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _post_form_json(url: str, form: dict[str, str]) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    ssl_context = None
    try:
        import certifi

        ssl_context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ssl_context = None
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"Google token exchange failed: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Google token exchange connection failed: {exc}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Google token exchange returned non-JSON response: {body}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Google token exchange returned a non-object payload")
    return parsed


def _http_json_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    final_headers = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        final_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=final_headers, method=method)
    ssl_context = None
    try:
        import certifi

        ssl_context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ssl_context = None
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"HTTP {method} {url} failed: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"HTTP {method} {url} connection failed: {exc}") from exc
    try:
        parsed = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"HTTP {method} {url} returned non-JSON response: {body}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"HTTP {method} {url} returned a non-object payload")
    return parsed


def _load_google_token_cache(root: Path) -> dict[str, Any]:
    path = _google_token_cache_path(root)
    if not path.exists():
        raise FileNotFoundError(f"Google OAuth token cache not found: {path}")
    parsed = _load_json_file(path, default={})
    if not isinstance(parsed, dict):
        raise ValueError(f"malformed Google OAuth token cache: {path}")
    return parsed


def _token_scopes(token_payload: dict[str, Any]) -> set[str]:
    raw = str(token_payload.get("scope", "")).strip()
    return {part for part in raw.split() if part}


def _read_sdp_offer(args: argparse.Namespace) -> str:
    if getattr(args, "offer", ""):
        return str(args.offer)
    offer_file = str(getattr(args, "offer_file", "")).strip()
    if offer_file:
        return Path(offer_file).expanduser().resolve().read_text(encoding="utf-8")
    raise ValueError("Provide --offer or --offer-file")


async def _async_generate_meet_sdp_offer(
    *,
    audio_streams: int,
    video_streams: int,
    wait_for_ice_seconds: float,
) -> str:
    try:
        from aiortc import RTCPeerConnection
    except ModuleNotFoundError as exc:
        raise ValueError(
            "aiortc is required to generate a Meet Media API SDP offer. "
            "Install it with `python3 -m pip install aiortc`."
        ) from exc

    if audio_streams < 1:
        raise ValueError("audio_streams must be at least 1")
    if video_streams < 0:
        raise ValueError("video_streams cannot be negative")
    if wait_for_ice_seconds <= 0:
        raise ValueError("wait_for_ice_seconds must be positive")

    pc = RTCPeerConnection()
    try:
        for _ in range(audio_streams):
            pc.addTransceiver("audio", direction="recvonly")
        for _ in range(video_streams):
            pc.addTransceiver("video", direction="recvonly")
        data_channel_config = {"ordered": True}
        pc.createDataChannel("session-control", **data_channel_config)
        pc.createDataChannel("media-stats", **data_channel_config)
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        deadline = asyncio.get_running_loop().time() + wait_for_ice_seconds
        while pc.iceGatheringState != "complete":
            if asyncio.get_running_loop().time() >= deadline:
                raise ValueError(
                    "Timed out while gathering ICE candidates for the Meet SDP offer"
                )
            await asyncio.sleep(0.1)

        local = pc.localDescription
        if local is None or not str(local.sdp).strip():
            raise ValueError("Meet SDP offer generation produced an empty local description")
        return str(local.sdp)
    finally:
        await pc.close()


def _generate_meet_sdp_offer(
    *,
    audio_streams: int,
    video_streams: int,
    wait_for_ice_seconds: float,
) -> str:
    return asyncio.run(_async_generate_meet_sdp_offer(
        audio_streams=audio_streams,
        video_streams=video_streams,
        wait_for_ice_seconds=wait_for_ice_seconds,
    ))


def _token_expired(token_payload: dict[str, Any], *, skew_seconds: int = 60) -> bool:
    obtained = _parse_timestamp(str(token_payload.get("obtained_at", "")))
    expires_in = int(token_payload.get("expires_in", 0) or 0)
    if not obtained or expires_in <= 0:
        return True
    age = (datetime.now(timezone.utc) - obtained).total_seconds()
    return age >= max(0, expires_in - skew_seconds)


def _refresh_google_token(root: Path, *, force: bool = False) -> dict[str, Any]:
    client = _load_google_oauth_client()
    token_payload = _load_google_token_cache(root)
    refresh_token = str(token_payload.get("refresh_token", "")).strip()
    if not refresh_token:
        raise ValueError("Google OAuth token cache is missing a refresh_token")
    if not force and not _token_expired(token_payload):
        return token_payload
    refreshed = _post_form_json(client["token_uri"], {
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    refreshed["refresh_token"] = refresh_token
    refreshed["client_id"] = client["client_id"]
    refreshed["scope"] = refreshed.get("scope") or token_payload.get("scope", "")
    refreshed["obtained_at"] = _now()
    _write_json_file(_google_token_cache_path(root), refreshed)
    return refreshed


def _require_google_scopes(root: Path, required_scopes: list[str]) -> dict[str, Any]:
    token_payload = _refresh_google_token(root)
    have = _token_scopes(token_payload)
    missing = [scope for scope in required_scopes if scope not in have]
    if missing:
        raise ValueError(
            "Google OAuth token cache is missing required scopes: "
            + ", ".join(missing)
            + ". Re-run canon live-plan google-oauth-authorize with those scopes."
        )
    return token_payload


def _google_auth_headers(root: Path, required_scopes: list[str]) -> dict[str, str]:
    token_payload = _require_google_scopes(root, required_scopes)
    return {
        "Authorization": f"Bearer {token_payload['access_token']}",
        "Accept": "application/json",
    }


def _build_runtime_manifest(state: dict[str, Any]) -> dict[str, Any]:
    transport = state.get("transport", {})
    adapter = str(transport.get("adapter", "manual")) if isinstance(transport, dict) else "manual"
    google_required = adapter == "meet-participant"
    meet_state = state.get("google_meet", {}) if isinstance(state.get("google_meet", {}), dict) else {}
    media_state = meet_state.get("media_session", {}) if isinstance(meet_state.get("media_session", {}), dict) else {}
    return {
        "schema_version": 1,
        "session_id": state["session_id"],
        "plan_id": state["plan_id"],
        "meeting": {
            "transport": state.get("transport", {}),
            "meeting_ref": state.get("meeting_ref", ""),
            "participant_mode": state.get("mode", ""),
            "bot_identity": {
                "display_name": "Canon Planning Bot",
                "must_disclose_ai": True,
                "speaking_policy": "raise-hand-before-autonomous-speech",
            },
        },
        "audio": {
            "realtime_provider": "openai",
            "required_env": ["OPENAI_API_KEY"],
            "diarization": {
                "mode": "sidecar",
                "speaker_registry": str(_registry_path(_repo_root())),
                "voice_refs_sent_per_request": True,
            },
        },
        "google_meet": {
            "adapter": "meet-participant" if google_required else "deferred",
            "status": (
                "media_attached"
                if google_required and media_state
                else ("configured" if google_required else "deferred")
            ),
            "required_env": (
                [
                    "CANON_GOOGLE_OAUTH_CLIENT_JSON",
                    "GOOGLE_APPLICATION_CREDENTIALS",
                    "GOOGLE_MEET_MEDIA_API_TOKEN",
                ]
                if google_required
                else []
            ),
            "media_ingest": (
                "meet-media-api-when-available-otherwise-participant-audio"
                if google_required
                else "not_used_for_local_participant"
            ),
            "oauth_client": {
                "env": "CANON_GOOGLE_OAUTH_CLIENT_JSON",
                "token_cache": str(_google_token_cache_path(_repo_root())),
            },
            "space": {
                "name": meet_state.get("space", ""),
                "meeting_uri": meet_state.get("meeting_uri", ""),
                "meeting_code": meet_state.get("meeting_code", ""),
            },
            "media_session": {
                "session_id": media_state.get("session_id", ""),
                "trace_id": media_state.get("trace_id", ""),
                "media_session_file": media_state.get("media_session_file", ""),
                "audio_streams": media_state.get("audio_streams", 0),
                "video_streams": media_state.get("video_streams", 0),
            },
            "speech_output": (
                "bot-participant-audio-output"
                if google_required
                else "local-audio-output"
            ),
            "blocker": "",
        },
        "local_participant": {
            "enabled": adapter == "local-participant",
            "required_env": ["OPENAI_API_KEY"] if adapter == "local-participant" else [],
            "audio_ingest": "local_microphone_or_manual_audio_source",
            "speech_output": "local_system_audio_or_virtual_microphone",
        },
        "visuals": {
            "mode": "explicit-send-only",
            "meeting_chat_posting": "requested-per-reference",
            "full_video_processing": False,
        },
        "tool_broker": {
            "repo_tools": [
                "search_repo",
                "open_file",
                "summarize_code_area",
                "query_prior_decisions",
            ],
            "planning_tools": [
                "add_reference",
                "add_transcript",
                "propose_item",
                "confirm_item",
                "raise_hand",
                "finalize",
            ],
        },
        "artifact_outputs": {
            "state": f".canon/live-plan/{state['session_id']}/session.json",
            "runtime_manifest": f".canon/live-plan/{state['session_id']}/runtime-manifest.json",
            "session_handoff": f".canon/live-plan/{state['session_id']}/session-handoff.md",
            "cursor_plan": f".cursor/plans/{state['plan_id']}.plan.md",
            "cursor_handoff": f".cursor/handoffs/{state['session_id']}/meeting-plan-handoff.md",
        },
    }


def _build_panel_manifest(state: dict[str, Any]) -> dict[str, Any]:
    meet_state = state.get("google_meet", {}) if isinstance(state.get("google_meet", {}), dict) else {}
    media_state = meet_state.get("media_session", {}) if isinstance(meet_state.get("media_session", {}), dict) else {}
    pending_items = [
        item for item in state.get("plan_items", [])
        if item.get("status") in ("draft", "read_back_pending")
    ]
    pending_hands = [
        event for event in state.get("hand_raises", [])
        if event.get("status") == "pending"
    ]
    return {
        "schema_version": 1,
        "session_id": state["session_id"],
        "plan_id": state["plan_id"],
        "meeting": {
            "meeting_ref": state.get("meeting_ref", ""),
            "space": meet_state.get("space", ""),
            "meeting_uri": meet_state.get("meeting_uri", ""),
            "participant_mode": state.get("mode", ""),
            "transport_adapter": state.get("transport", {}).get("adapter", ""),
            "media_attached": bool(media_state),
        },
        "status": {
            "pending_plan_items": len(pending_items),
            "pending_hand_raises": len(pending_hands),
            "reference_count": len(state.get("references", [])),
            "transcript_segment_count": len(state.get("transcript_segments", [])),
        },
        "participants": [
            {
                "name": person.get("name", ""),
                "email": person.get("email", ""),
                "voice_profile_status": person.get("voice_profile_status", "unknown"),
            }
            for person in state.get("participants", [])
            if isinstance(person, dict)
        ],
        "recent_references": [
            {
                "ref_id": ref.get("ref_id", ""),
                "type": ref.get("type", ""),
                "title": ref.get("title", ""),
                "path": ref.get("path", ""),
                "uri": ref.get("uri", ""),
                "shared_to_meeting": bool(ref.get("shared_to_meeting", False)),
                "meeting_chat_status": ref.get("meeting_chat_status", ""),
                "metadata": ref.get("metadata", {}),
            }
            for ref in list(state.get("references", []))[-5:][::-1]
            if isinstance(ref, dict)
        ],
        "recent_transcript_segments": [
            {
                "segment_id": seg.get("segment_id", ""),
                "speaker": seg.get("speaker", ""),
                "text": seg.get("text", ""),
                "timestamp": seg.get("timestamp", ""),
            }
            for seg in list(state.get("transcript_segments", []))[-5:][::-1]
            if isinstance(seg, dict)
        ],
        "pending_items": [
            {
                "item_id": item.get("item_id", ""),
                "type": item.get("type", ""),
                "title": item.get("title", ""),
                "status": item.get("status", ""),
                "verification_prompt": item.get("verification_prompt", ""),
            }
            for item in pending_items
        ],
        "pending_hand_raises": [
            {
                "hand_raise_id": event.get("hand_raise_id", ""),
                "reason": event.get("reason", ""),
                "status": event.get("status", ""),
                "item_id": event.get("item_id", ""),
            }
            for event in pending_hands
        ],
        "actions": [
            {"id": "submit_reference", "label": "Send Image Or File", "event_type": "reference.add"},
            {"id": "append_transcript", "label": "Add Transcript Segment", "event_type": "transcript.segment"},
            {"id": "propose_item", "label": "Propose Plan Item", "event_type": "item.propose"},
            {"id": "confirm_item", "label": "Confirm Or Amend Item", "event_type": "item.confirm"},
            {"id": "raise_hand", "label": "Raise Bot Hand", "event_type": "hand.raise"},
            {"id": "resolve_hand", "label": "Resolve Hand Raise", "event_type": "hand.resolve"},
            {"id": "set_mode", "label": "Switch Participation Mode", "event_type": "mode.set"},
        ],
        "event_types": [
            "transcript.segment",
            "reference.add",
            "item.propose",
            "item.confirm",
            "hand.raise",
            "hand.resolve",
            "mode.set",
        ],
        "verification_policy": {
            "default_item_status": "read_back_pending",
            "spoken_read_back_required": True,
            "confirmable_statuses": ["confirmed", "amended", "rejected"],
        },
    }


def _update_index(root: Path, state: dict[str, Any], plan_file: Path, handoff_file: Path) -> None:
    idx = _load_json_file(_index_path(root), default={"schema_version": 1, "sessions": []})
    sessions = [
        s for s in idx.get("sessions", [])
        if not (
            isinstance(s, dict)
            and s.get("session_id") == state["session_id"]
        )
    ]
    sessions.append({
        "session_id": state["session_id"],
        "plan_id": state["plan_id"],
        "company_id": state.get("company_id", ""),
        "repository_ids": state.get("repository_ids", []),
        "primary_repository_id": state.get("primary_repository_id", ""),
        "topic": state.get("topic", ""),
        "status": state.get("status", ""),
        "updated_at": state.get("updated_at", ""),
        "plan_file": str(plan_file),
        "handoff_file": str(handoff_file),
    })
    idx["sessions"] = sorted(sessions, key=lambda s: str(s.get("updated_at", "")))
    _write_json_file(_index_path(root), idx)


def _find_session(
    root: Path,
    *,
    session_id: str = "",
    plan_id: str = "",
    latest: bool = False,
    repo: str = "",
    topic: str = "",
) -> str:
    if session_id:
        return session_id
    idx = _load_json_file(_index_path(root), default={"sessions": []})
    matches: list[dict[str, Any]] = []
    for entry in idx.get("sessions", []):
        if not isinstance(entry, dict):
            continue
        if plan_id and entry.get("plan_id") != plan_id:
            continue
        if repo and repo not in entry.get("repository_ids", []):
            continue
        if topic and topic.lower() not in str(entry.get("topic", "")).lower():
            continue
        matches.append(entry)
    if latest and matches:
        matches.sort(key=lambda s: str(s.get("updated_at", "")), reverse=True)
        return str(matches[0].get("session_id", ""))
    if plan_id and matches:
        matches.sort(key=lambda s: str(s.get("updated_at", "")), reverse=True)
        return str(matches[0].get("session_id", ""))
    raise FileNotFoundError("matching live-plan session not found")


def _json_out(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _cmd_start(args: argparse.Namespace, root: Path) -> int:
    repos = [args.repo] + list(args.additional_repo or [])
    session_base = args.session_id or f"meeting-{_slug(args.topic or args.repo, fallback='plan')}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    session_id = _slug(session_base, fallback="meeting-plan")
    plan_id = args.plan_id or f"{_slug(args.topic or args.repo, fallback='meeting-plan')}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    state = {
        "schema_version": 1,
        "session_id": session_id,
        "plan_id": plan_id,
        "company_id": args.company_id,
        "primary_repository_id": args.repo,
        "repository_ids": repos,
        "topic": args.topic,
        "meeting_ref": args.meeting_ref,
        "mode": args.mode,
        "status": "active",
        "participants": _hydrate_participants(root, list(args.participant or [])),
        "transport": {
            "adapter": args.transport,
            "credential_status": "unchecked",
            "bot_can_speak": args.transport in ("meet-participant", "local-participant"),
            "visual_mode": "explicit-send-only",
        },
        "references": [],
        "transcript_segments": [],
        "plan_items": [],
        "hand_raises": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    path = _write_state(root, state)
    _update_index(root, state, _plan_path(root, state["plan_id"]), _handoff_path(root, state["session_id"]))
    payload = {"session_id": session_id, "plan_id": plan_id, "state_file": str(path)}
    if args.json:
        _json_out(payload)
    else:
        print(f"Started live-plan session {session_id} (plan {plan_id})")
    return EXIT_OK


def _cmd_add_reference(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    ref = _append_reference_to_state(
        state,
        ref_type=args.type,
        title=args.title,
        path=args.path,
        uri=args.uri,
        summary=args.summary,
        shared_to_meeting=bool(args.shared_to_meeting),
        meeting_chat_status=args.meeting_chat_status,
    )
    _write_state(root, state)
    _json_out({"reference": ref})
    return EXIT_OK


def _cmd_add_transcript(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    seg = _append_transcript_to_state(
        state,
        speaker=args.speaker,
        text=args.text,
        source=args.source,
        timestamp=args.timestamp,
    )
    _write_state(root, state)
    _json_out({"transcript_segment": seg})
    return EXIT_OK


def _cmd_propose_item(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    item = _append_plan_item_to_state(
        state,
        item_type=args.type,
        title=args.title,
        content=args.content,
        evidence_refs=list(args.evidence_ref or []),
        requires_confirmation=bool(args.requires_confirmation),
    )
    hand = _raise_hand_for_plan_item(state, item) if bool(args.requires_confirmation) else None
    _write_state(root, state)
    _json_out({
        "hand_raise": bool(args.requires_confirmation),
        "hand_raise_event": hand,
        "item": item,
        "next_action": "confirm, amend, or reject this item before final execution",
    })
    return EXIT_OK


def _cmd_confirm_item(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    try:
        item = _confirm_plan_item_in_state(
            state,
            item_id=args.item_id,
            status=args.status,
            title=args.title,
            content=args.content,
        )
    except FileNotFoundError:
        print(f"item not found: {args.item_id}", file=sys.stderr)
        return EXIT_NOT_FOUND
    linked_hand = _resolve_pending_hand_for_item(
        state,
        item_id=str(item.get("item_id", "")),
        status="approved" if args.status in ("confirmed", "amended") else "dismissed",
    )
    _write_state(root, state)
    _json_out({"item_id": args.item_id, "status": args.status, "linked_hand_raise": linked_hand})
    return EXIT_OK


def _cmd_raise_hand(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    event = _raise_hand_in_state(state, reason=args.reason, item_id=args.item_id)
    _write_state(root, state)
    _json_out({"hand_raise": event})
    return EXIT_OK


def _cmd_resolve_hand(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    try:
        _resolve_hand_in_state(state, hand_raise_id=args.hand_raise_id, status=args.status)
    except FileNotFoundError:
        print(f"hand raise not found: {args.hand_raise_id}", file=sys.stderr)
        return EXIT_NOT_FOUND
    _write_state(root, state)
    _json_out({"hand_raise_id": args.hand_raise_id, "status": args.status})
    return EXIT_OK


def _cmd_set_mode(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    old, _ = _set_mode_in_state(state, mode=args.mode)
    _write_state(root, state)
    _json_out({"session_id": args.session_id, "old_mode": old, "mode": args.mode})
    return EXIT_OK


def _cmd_upsert_participant(args: argparse.Namespace, root: Path) -> int:
    registry = _load_registry(root)
    target_key = _participant_key(args.name, args.email)
    existing = next(
        (
            p for p in registry.get("participants", [])
            if isinstance(p, dict)
            and _participant_key(str(p.get("name", "")), str(p.get("email", ""))) == target_key
        ),
        {},
    )
    people = [
        p for p in registry.get("participants", [])
        if isinstance(p, dict)
        and _participant_key(str(p.get("name", "")), str(p.get("email", "")))
        != target_key
    ]
    voice_refs = list(existing.get("voice_refs", [])) if isinstance(existing, dict) else []
    for raw_path in args.voice_ref or []:
        path = Path(raw_path).expanduser().resolve()
        voice_refs.append({
            "path": str(path),
            "sha256": _file_sha256(path) if path.exists() and path.is_file() else "",
            "status": "available" if path.exists() and path.is_file() else "missing",
            "added_at": _now(),
        })
    person = {
        "person_id": args.person_id or _slug(args.email or args.name, fallback="participant"),
        "name": args.name,
        "email": args.email,
        "voice_refs": voice_refs,
        "updated_at": _now(),
    }
    people.append(person)
    registry["participants"] = sorted(people, key=lambda p: str(p.get("name", "")).lower())
    _write_json_file(_registry_path(root), registry)
    _json_out({"participant": person})
    return EXIT_OK


def _cmd_list_participants(args: argparse.Namespace, root: Path) -> int:
    registry = _load_registry(root)
    if args.json:
        _json_out(registry)
    else:
        for person in registry.get("participants", []):
            refs = person.get("voice_refs", []) if isinstance(person, dict) else []
            print(f"{person.get('name', '')}\t{person.get('email', '')}\tvoice_refs={len(refs)}")
    return EXIT_OK


def _cmd_check_credentials(args: argparse.Namespace, root: Path) -> int:
    openai_ok = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    google_ok, google_present_env = _google_credentials_status()
    google_oauth_client: dict[str, Any] | None = None
    google_oauth_error = ""
    oauth_env = "CANON_GOOGLE_OAUTH_CLIENT_JSON" in google_present_env
    if oauth_env:
        try:
            google_oauth_client = _load_google_oauth_client()
        except (FileNotFoundError, ValueError) as exc:
            google_ok = False
            google_oauth_error = str(exc)
    report = {
        "openai_realtime": {
            "required": args.transport in ("meet-participant", "local-participant"),
            "env": "OPENAI_API_KEY",
            "status": "present" if openai_ok else "missing",
        },
        "google_meet": {
            "required": args.transport == "meet-participant",
            "env": "CANON_GOOGLE_OAUTH_CLIENT_JSON or GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_MEET_MEDIA_API_TOKEN",
            "status": "present" if google_ok else "missing",
            "present_env": google_present_env,
            "oauth_client": google_oauth_client,
            "oauth_client_error": google_oauth_error,
        },
        "transport": args.transport,
        "ready": openai_ok and (google_ok if args.transport == "meet-participant" else True),
        "repo_root": str(root),
    }
    _json_out(report)
    return EXIT_OK if report["ready"] or not args.require_ready else EXIT_USAGE


def _cmd_runtime_manifest(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    manifest = _build_runtime_manifest(state)
    path = _runtime_manifest_path(root, args.session_id)
    if args.write:
        _write_json_file(path, manifest)
    payload = {"runtime_manifest": manifest, "runtime_manifest_file": str(path)}
    _json_out(payload)
    return EXIT_OK


def _cmd_google_oauth_config(args: argparse.Namespace, root: Path) -> int:
    client = _load_google_oauth_client()
    payload = {
        "google_oauth_client": client,
        "token_cache_file": str(_google_token_cache_path(root)),
        "auth_flow": {
            "type": "desktop-installed-app",
            "requires_test_user_until_published": True,
            "test_user_email": args.test_user or "",
        },
    }
    _json_out(payload)
    return EXIT_OK


def _cmd_google_oauth_authorize(args: argparse.Namespace, root: Path) -> int:
    client = _load_google_oauth_client()
    redirect_uri = args.redirect_uri or (client["redirect_uris"][0] if client["redirect_uris"] else "http://localhost")
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(24)
    session = {
        "created_at": _now(),
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "scope": list(args.scope or []),
        "state": state,
        "code_verifier": verifier,
        "token_uri": client["token_uri"],
    }
    _write_json_file(_google_oauth_session_path(root), session)
    query = urllib.parse.urlencode({
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(args.scope or []),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": _pkce_challenge(verifier),
        "code_challenge_method": "S256",
    })
    auth_url = f"{client['auth_uri']}?{query}"
    _json_out({
        "authorization_url": auth_url,
        "oauth_session_file": str(_google_oauth_session_path(root)),
        "redirect_uri": redirect_uri,
        "scope": list(args.scope or []),
        "next_step": "Open the authorization URL, complete consent, then run canon live-plan google-oauth-exchange --code <code> --state <state>.",
        "state": state,
    })
    return EXIT_OK


def _cmd_google_oauth_exchange(args: argparse.Namespace, root: Path) -> int:
    client = _load_google_oauth_client()
    session = _load_json_file(_google_oauth_session_path(root), default={})
    if not isinstance(session, dict) or not session:
        raise FileNotFoundError(f"Google OAuth session not found: {_google_oauth_session_path(root)}")
    expected_state = str(session.get("state", "")).strip()
    if args.state and expected_state and args.state != expected_state:
        raise ValueError("OAuth state does not match the pending Google OAuth session")
    form = {
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "code": args.code,
        "code_verifier": str(session.get("code_verifier", "")).strip(),
        "grant_type": "authorization_code",
        "redirect_uri": str(session.get("redirect_uri", "")).strip(),
    }
    token_payload = _post_form_json(client["token_uri"], form)
    token_payload["obtained_at"] = _now()
    token_payload["client_id"] = client["client_id"]
    token_payload["scope"] = token_payload.get("scope") or " ".join(session.get("scope", []))
    _write_json_file(_google_token_cache_path(root), token_payload)
    _json_out({
        "token_cache_file": str(_google_token_cache_path(root)),
        "scope": token_payload.get("scope", ""),
        "has_refresh_token": bool(str(token_payload.get("refresh_token", "")).strip()),
        "token_type": token_payload.get("token_type", ""),
    })
    return EXIT_OK


def _cmd_google_oauth_refresh(args: argparse.Namespace, root: Path) -> int:
    token_payload = _refresh_google_token(root, force=args.force)
    _json_out({
        "token_cache_file": str(_google_token_cache_path(root)),
        "scope": token_payload.get("scope", ""),
        "expires_in": token_payload.get("expires_in", 0),
        "obtained_at": token_payload.get("obtained_at", ""),
        "has_refresh_token": bool(str(token_payload.get("refresh_token", "")).strip()),
    })
    return EXIT_OK


def _cmd_google_meet_probe(args: argparse.Namespace, root: Path) -> int:
    headers = _google_auth_headers(root, list(args.scope or []))
    userinfo = _http_json_request(
        "GET",
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers=headers,
    )
    payload: dict[str, Any] = {
        "google_userinfo": {
            "email": userinfo.get("email", ""),
            "email_verified": userinfo.get("email_verified", False),
            "hd": userinfo.get("hd", ""),
            "sub": userinfo.get("sub", ""),
        },
        "scopes": list(args.scope or []),
    }
    if args.space:
        space = _http_json_request(
            "GET",
            f"https://meet.googleapis.com/v2/{args.space}",
            headers=headers,
        )
        payload["space"] = space
    _json_out(payload)
    return EXIT_OK


def _cmd_google_meet_create_space(args: argparse.Namespace, root: Path) -> int:
    headers = _google_auth_headers(root, ["https://www.googleapis.com/auth/meetings.space.created"])
    body: dict[str, Any] = {}
    if args.access_type:
        body.setdefault("config", {})
        body["config"]["accessType"] = args.access_type
    space = _http_json_request(
        "POST",
        "https://meet.googleapis.com/v2/spaces",
        headers=headers,
        json_body=body,
    )
    _json_out({"space": space})
    return EXIT_OK


def _cmd_google_meet_get_space(args: argparse.Namespace, root: Path) -> int:
    headers = _google_auth_headers(root, list(args.scope or []))
    space = _http_json_request(
        "GET",
        f"https://meet.googleapis.com/v2/{args.name}",
        headers=headers,
    )
    _json_out({"space": space})
    return EXIT_OK


def _cmd_google_meet_bind_space(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    scope_list = list(args.scope or [])
    headers = _google_auth_headers(root, scope_list)
    space = _http_json_request(
        "GET",
        f"https://meet.googleapis.com/v2/{args.name}",
        headers=headers,
    )
    google_meet = state.get("google_meet", {}) if isinstance(state.get("google_meet", {}), dict) else {}
    google_meet.update({
        "space": space.get("name", args.name),
        "meeting_uri": space.get("meetingUri", ""),
        "meeting_code": space.get("meetingCode", ""),
        "bound_at": _now(),
        "phone_access": space.get("phoneAccess", []),
        "space_payload": space,
    })
    state["google_meet"] = google_meet
    state["meeting_ref"] = space.get("meetingUri", state.get("meeting_ref", ""))
    transport = state.get("transport", {}) if isinstance(state.get("transport", {}), dict) else {}
    transport["credential_status"] = "configured"
    state["transport"] = transport
    _write_state(root, state)
    _write_json_file(_runtime_manifest_path(root, state["session_id"]), _build_runtime_manifest(state))
    _json_out({
        "session_id": state["session_id"],
        "space": google_meet["space"],
        "meeting_uri": google_meet["meeting_uri"],
        "meeting_code": google_meet["meeting_code"],
        "state_file": str(_state_path(root, state["session_id"])),
    })
    return EXIT_OK


def _cmd_google_meet_generate_offer(args: argparse.Namespace, root: Path) -> int:
    offer = _generate_meet_sdp_offer(
        audio_streams=args.audio_streams,
        video_streams=args.video_streams,
        wait_for_ice_seconds=args.wait_for_ice_seconds,
    )
    output_file = str(args.output_file).strip()
    if output_file:
        path = Path(output_file).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(offer, encoding="utf-8")
    payload = {
        "audio_streams": args.audio_streams,
        "video_streams": args.video_streams,
        "offer": offer,
        "offer_length": len(offer),
    }
    if output_file:
        payload["output_file"] = str(Path(output_file).expanduser().resolve())
    _json_out(payload)
    return EXIT_OK


def _cmd_google_meet_connect_active_conference(args: argparse.Namespace, root: Path) -> int:
    required_scopes = [
        "https://www.googleapis.com/auth/meetings.space.readonly",
        args.media_scope,
    ]
    headers = _google_auth_headers(root, required_scopes)
    offer = (
        _generate_meet_sdp_offer(
            audio_streams=args.audio_streams,
            video_streams=args.video_streams,
            wait_for_ice_seconds=args.wait_for_ice_seconds,
        )
        if args.generate_offer
        else _read_sdp_offer(args)
    )
    response = _http_json_request(
        "POST",
        f"https://meet.googleapis.com/v2beta/{args.name}:connectActiveConference",
        headers=headers,
        json_body={"offer": offer},
    )
    session_id = args.session_id or _slug(args.name.replace("/", "-"), fallback="media-session")
    artifact = {
        "session_id": session_id,
        "space": args.name,
        "media_scope": args.media_scope,
        "created_at": _now(),
        "generated_offer": bool(args.generate_offer),
        "audio_streams": args.audio_streams,
        "video_streams": args.video_streams,
        "offer": offer,
        "answer": response.get("answer", ""),
        "trace_id": response.get("traceId", ""),
    }
    path = _google_media_session_path(root, session_id)
    _write_json_file(path, artifact)
    _json_out({
        "media_session_file": str(path),
        "session_id": session_id,
        "trace_id": artifact["trace_id"],
        "answer_length": len(artifact["answer"]),
    })
    return EXIT_OK


def _cmd_google_meet_attach_media(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    artifact = _load_google_media_session(root, args.media_session_id)
    google_meet = state.get("google_meet", {}) if isinstance(state.get("google_meet", {}), dict) else {}
    space_name = str(artifact.get("space", "")).strip()
    if space_name:
        google_meet["space"] = space_name
    google_meet["media_session"] = {
        "session_id": artifact.get("session_id", args.media_session_id),
        "trace_id": artifact.get("trace_id", ""),
        "media_session_file": str(_google_media_session_path(root, args.media_session_id)),
        "audio_streams": int(artifact.get("audio_streams", 0) or 0),
        "video_streams": int(artifact.get("video_streams", 0) or 0),
        "attached_at": _now(),
        "generated_offer": bool(artifact.get("generated_offer", False)),
    }
    if args.answer_file:
        answer_path = Path(args.answer_file).expanduser().resolve()
        answer_path.parent.mkdir(parents=True, exist_ok=True)
        answer_path.write_text(str(artifact.get("answer", "")), encoding="utf-8")
        google_meet["media_session"]["answer_file"] = str(answer_path)
    state["google_meet"] = google_meet
    transport = state.get("transport", {}) if isinstance(state.get("transport", {}), dict) else {}
    transport["credential_status"] = "attached"
    state["transport"] = transport
    _write_state(root, state)
    _write_json_file(_runtime_manifest_path(root, state["session_id"]), _build_runtime_manifest(state))
    _json_out({
        "session_id": state["session_id"],
        "media_session_id": artifact.get("session_id", args.media_session_id),
        "trace_id": artifact.get("trace_id", ""),
        "state_file": str(_state_path(root, state["session_id"])),
        "runtime_manifest_file": str(_runtime_manifest_path(root, state["session_id"])),
    })
    return EXIT_OK


def _ingest_live_event(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    event_type = str(event.get("type", "")).strip()
    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError(f"event payload must be an object for type {event_type}")
    if event_type == "transcript.segment":
        seg = _append_transcript_to_state(
            state,
            speaker=str(payload.get("speaker", "")).strip() or "unknown",
            text=str(payload.get("text", "")).strip(),
            source=str(payload.get("source", "meeting-pane")).strip() or "meeting-pane",
            timestamp=str(payload.get("timestamp", "")).strip(),
        )
        return {"event_type": event_type, "transcript_segment": seg}
    if event_type == "reference.add":
        ref = _append_reference_to_state(
            state,
            ref_type=str(payload.get("type", "")).strip() or "file",
            title=str(payload.get("title", "")).strip() or "Untitled reference",
            path=str(payload.get("path", "")).strip(),
            uri=str(payload.get("uri", "")).strip(),
            summary=str(payload.get("summary", "")).strip(),
            shared_to_meeting=bool(payload.get("shared_to_meeting", False)),
            meeting_chat_status=str(payload.get("meeting_chat_status", "not_requested")).strip() or "not_requested",
        )
        return {"event_type": event_type, "reference": ref}
    if event_type == "item.propose":
        item = _append_plan_item_to_state(
            state,
            item_type=str(payload.get("item_type", "")).strip() or str(payload.get("type", "")).strip() or "task",
            title=str(payload.get("title", "")).strip() or "Untitled item",
            content=str(payload.get("content", "")).strip(),
            evidence_refs=[
                str(ref).strip() for ref in payload.get("evidence_refs", []) if str(ref).strip()
            ],
            requires_confirmation=bool(payload.get("requires_confirmation", True)),
        )
        hand = _raise_hand_for_plan_item(state, item) if item.get("status") == "read_back_pending" else None
        return {"event_type": event_type, "item": item, "hand_raise": hand}
    if event_type == "item.confirm":
        item = _confirm_plan_item_in_state(
            state,
            item_id=str(payload.get("item_id", "")).strip(),
            status=str(payload.get("status", "")).strip(),
            title=str(payload.get("title", "")).strip(),
            content=str(payload.get("content", "")).strip(),
        )
        linked_hand = _resolve_pending_hand_for_item(
            state,
            item_id=str(item.get("item_id", "")).strip(),
            status="approved" if str(payload.get("status", "")).strip() in ("confirmed", "amended") else "dismissed",
        )
        return {"event_type": event_type, "item": item, "hand_raise": linked_hand}
    if event_type == "hand.raise":
        hand = _raise_hand_in_state(
            state,
            reason=str(payload.get("reason", "")).strip() or "Clarification requested",
            item_id=str(payload.get("item_id", "")).strip(),
        )
        return {"event_type": event_type, "hand_raise": hand}
    if event_type == "hand.resolve":
        hand = _resolve_hand_in_state(
            state,
            hand_raise_id=str(payload.get("hand_raise_id", "")).strip(),
            status=str(payload.get("status", "")).strip(),
        )
        return {"event_type": event_type, "hand_raise": hand}
    if event_type == "mode.set":
        old_mode, new_mode = _set_mode_in_state(
            state,
            mode=str(payload.get("mode", "")).strip(),
        )
        return {"event_type": event_type, "old_mode": old_mode, "mode": new_mode}
    raise ValueError(f"unsupported live-plan event type: {event_type}")


def _load_event_objects(args: argparse.Namespace) -> list[dict[str, Any]]:
    if str(getattr(args, "event_json", "")).strip():
        parsed = json.loads(str(args.event_json))
        if not isinstance(parsed, dict):
            raise ValueError("--event-json must decode to an object")
        return [parsed]
    path = str(getattr(args, "events_file", "")).strip()
    if path:
        lines = Path(path).expanduser().resolve().read_text(encoding="utf-8").splitlines()
    elif getattr(args, "stdin", False):
        lines = sys.stdin.read().splitlines()
    else:
        raise ValueError("Provide --event-json, --events-file, or --stdin")
    events: list[dict[str, Any]] = []
    for idx, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError(f"event line {idx} did not decode to an object")
        events.append(parsed)
    return events


def _cmd_ingest_events(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    events = _load_event_objects(args)
    applied: list[dict[str, Any]] = []
    for event in events:
        applied.append(_ingest_live_event(state, event))
    _write_state(root, state)
    _write_json_file(_runtime_manifest_path(root, state["session_id"]), _build_runtime_manifest(state))
    _write_json_file(_panel_manifest_path(root, state["session_id"]), _build_panel_manifest(state))
    _json_out({
        "session_id": state["session_id"],
        "applied_count": len(applied),
        "applied": applied,
    })
    return EXIT_OK


def _cmd_panel_manifest(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    manifest = _build_panel_manifest(state)
    path = _panel_manifest_path(root, args.session_id)
    if args.write:
        _write_json_file(path, manifest)
    _json_out({
        "panel_manifest": manifest,
        "panel_manifest_file": str(path),
    })
    return EXIT_OK


def _parse_bridge_path(path: str) -> tuple[str, str]:
    parsed = urlparse(path)
    clean = parsed.path.strip("/")
    parts = clean.split("/") if clean else []
    if clean == "health":
        return "health", ""
    if clean == "app":
        return "app", ""
    if clean == "resolve-session":
        return "resolve-session", ""
    if len(parts) == 3 and parts[0] == "static" and parts[1] == "live-plan-panel":
        return f"asset:{parts[2]}", ""
    if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "panel-manifest":
        return "panel-manifest", parts[1]
    if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "runtime-manifest":
        return "runtime-manifest", parts[1]
    if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "events":
        return "events", parts[1]
    if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "upload-reference":
        return "upload-reference", parts[1]
    return "", ""


def _decode_bridge_body(handler: http.server.BaseHTTPRequestHandler) -> dict[str, Any]:
    raw_len = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(raw_len) if raw_len > 0 else b"{}"
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON body: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("request body must be a JSON object")
    return parsed


def _bridge_query_param(path: str, key: str) -> str:
    parsed = urlparse(path)
    values = urllib.parse.parse_qs(parsed.query).get(key, [])
    return str(values[0]).strip() if values else ""


def _bridge_ingest_payload(state: dict[str, Any], body: dict[str, Any]) -> list[dict[str, Any]]:
    if "events" in body:
        events = body.get("events", [])
        if not isinstance(events, list):
            raise ValueError("events must be a list")
        payloads = events
    else:
        payloads = [body]
    applied: list[dict[str, Any]] = []
    for idx, event in enumerate(payloads, start=1):
        if not isinstance(event, dict):
            raise ValueError(f"event {idx} must be an object")
        applied.append(_ingest_live_event(state, event))
    return applied


def _lookup_session_by_meeting_hint(root: Path, meeting_hint: str) -> dict[str, Any]:
    hint = meeting_hint.strip().lower()
    if not hint:
        raise ValueError("meeting_code is required")
    live_plan_root = root / ".canon" / "live-plan"
    candidates: list[dict[str, Any]] = []
    if not live_plan_root.exists():
        raise FileNotFoundError("no live-plan sessions exist yet")
    for child in live_plan_root.iterdir():
        if not child.is_dir():
            continue
        state_path = child / "session.json"
        if not state_path.exists():
            continue
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(state, dict):
            continue
        meeting_ref = str(state.get("meeting_ref", "")).lower()
        google_meet = state.get("google_meet", {}) if isinstance(state.get("google_meet", {}), dict) else {}
        meeting_uri = str(google_meet.get("meeting_uri", "")).lower()
        meeting_code = str(google_meet.get("meeting_code", "")).lower()
        if hint in {meeting_code, meeting_ref, meeting_uri} or hint in meeting_ref or hint in meeting_uri:
            candidates.append(state)
    if not candidates:
        raise FileNotFoundError(f"no live-plan session found for meeting code: {meeting_hint}")
    candidates.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
    chosen = candidates[0]
    return {
        "session_id": chosen.get("session_id", ""),
        "plan_id": chosen.get("plan_id", ""),
        "meeting_ref": chosen.get("meeting_ref", ""),
        "updated_at": chosen.get("updated_at", ""),
    }


def _decode_bridge_multipart(
    handler: http.server.BaseHTTPRequestHandler,
) -> tuple[dict[str, str], bytes, str]:
    content_type = handler.headers.get("Content-Type", "")
    raw_len = int(handler.headers.get("Content-Length", "0") or "0")
    raw_body = handler.rfile.read(raw_len) if raw_len > 0 else b""
    if not content_type.lower().startswith("multipart/form-data"):
        raise ValueError("upload-reference requires multipart/form-data")
    message = BytesParser(policy=email.policy.default).parsebytes(
        (
            f"Content-Type: {content_type}\r\n"
            "MIME-Version: 1.0\r\n\r\n"
        ).encode("utf-8") + raw_body
    )
    if not message.is_multipart():
        raise ValueError("upload-reference requires a multipart payload")
    fields: dict[str, str] = {
        "type": "",
        "title": "",
        "summary": "",
        "shared_to_meeting": "",
        "meeting_chat_status": "",
    }
    file_name = ""
    file_bytes = b""
    for part in message.iter_parts():
        name = str(part.get_param("name", header="content-disposition") or "").strip()
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        if name == "file":
            file_name = _sanitize_filename(
                str(part.get_filename() or part.get_param("filename", header="content-disposition") or "upload.bin")
            )
            file_bytes = payload
            continue
        fields[name] = payload.decode("utf-8", errors="replace").strip()
    if not file_bytes:
        raise ValueError("upload-reference requires a file field")
    return fields, file_bytes, file_name or "upload.bin"


def _store_uploaded_reference(
    root: Path,
    state: dict[str, Any],
    *,
    fields: dict[str, str],
    raw: bytes,
    filename: str,
) -> dict[str, Any]:
    upload_dir = _session_upload_dir(root, str(state["session_id"]))
    upload_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_name = _sanitize_filename(filename)
    stored_name = f"{stamp}-{secrets.token_hex(4)}-{safe_name}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(raw)
    content_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    ref_type = fields["type"] or ("image" if content_type.startswith("image/") else "file")
    title = fields["title"] or Path(safe_name).stem.replace("-", " ").replace("_", " ").strip() or safe_name
    shared = fields["shared_to_meeting"].lower() in {"1", "true", "yes", "on"}
    meeting_chat_status = fields["meeting_chat_status"] or ("posted" if shared else "not_requested")
    ref = _append_reference_to_state(
        state,
        ref_type=ref_type,
        title=title,
        path=str(stored_path),
        summary=fields["summary"],
        shared_to_meeting=shared,
        meeting_chat_status=meeting_chat_status,
        metadata={
            "content_type": content_type,
            "file_size_bytes": len(raw),
            "original_name": filename,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "upload_kind": "multipart",
        },
    )
    return ref


def _build_panel_bridge_handler(root: Path) -> type[http.server.BaseHTTPRequestHandler]:
    class PanelBridgeHandler(http.server.BaseHTTPRequestHandler):
        server_version = "CanonLivePlanPanelBridge/1.0"

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.end_headers()
            self.wfile.write(encoded)

        def _send_bytes(self, status: int, payload: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send_json(200, {"ok": True})

        def do_GET(self) -> None:  # noqa: N802
            route, session_id = _parse_bridge_path(self.path)
            try:
                if route == "health":
                    self._send_json(200, {"ok": True, "service": "canon-live-plan-panel-bridge"})
                    return
                if route == "app":
                    html = (_live_panel_static_dir() / "index.html").read_text(encoding="utf-8").encode("utf-8")
                    self._send_bytes(200, html, "text/html; charset=utf-8")
                    return
                if route == "resolve-session":
                    meeting_code = _bridge_query_param(self.path, "meeting_code")
                    self._send_json(200, {
                        "match": _lookup_session_by_meeting_hint(root, meeting_code),
                    })
                    return
                if route.startswith("asset:"):
                    asset_name = route.split(":", 1)[1]
                    asset_path = _live_panel_static_dir() / asset_name
                    if not asset_path.exists():
                        self._send_json(404, {"error": "asset_not_found"})
                        return
                    content_type = {
                        "app.js": "text/javascript; charset=utf-8",
                        "styles.css": "text/css; charset=utf-8",
                    }.get(asset_name, "application/octet-stream")
                    self._send_bytes(200, asset_path.read_bytes(), content_type)
                    return
                if route == "panel-manifest":
                    state = _load_state(root, session_id)
                    self._send_json(200, {"panel_manifest": _build_panel_manifest(state)})
                    return
                if route == "runtime-manifest":
                    state = _load_state(root, session_id)
                    self._send_json(200, {"runtime_manifest": _build_runtime_manifest(state)})
                    return
                self._send_json(404, {"error": "not_found"})
            except FileNotFoundError as exc:
                self._send_json(404, {"error": str(exc)})
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            route, session_id = _parse_bridge_path(self.path)
            try:
                if route == "upload-reference":
                    state = _load_state(root, session_id)
                    fields, raw, filename = _decode_bridge_multipart(self)
                    ref = _store_uploaded_reference(root, state, fields=fields, raw=raw, filename=filename)
                    _write_state(root, state)
                    _write_json_file(_runtime_manifest_path(root, state["session_id"]), _build_runtime_manifest(state))
                    _write_json_file(_panel_manifest_path(root, state["session_id"]), _build_panel_manifest(state))
                    self._send_json(200, {
                        "session_id": state["session_id"],
                        "reference": ref,
                    })
                    return
                if route != "events":
                    self._send_json(404, {"error": "not_found"})
                    return
                state = _load_state(root, session_id)
                body = _decode_bridge_body(self)
                applied = _bridge_ingest_payload(state, body)
                _write_state(root, state)
                _write_json_file(_runtime_manifest_path(root, state["session_id"]), _build_runtime_manifest(state))
                _write_json_file(_panel_manifest_path(root, state["session_id"]), _build_panel_manifest(state))
                self._send_json(200, {
                    "session_id": state["session_id"],
                    "applied_count": len(applied),
                    "applied": applied,
                })
            except FileNotFoundError as exc:
                self._send_json(404, {"error": str(exc)})
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            return

    return PanelBridgeHandler


def _cmd_panel_http_bridge(args: argparse.Namespace, root: Path) -> int:
    server = http.server.ThreadingHTTPServer(
        (args.host, args.port),
        _build_panel_bridge_handler(root),
    )
    payload = {
        "service": "canon-live-plan-panel-bridge",
        "host": server.server_address[0],
        "port": server.server_address[1],
        "repo_root": str(root),
        "health_url": f"http://{server.server_address[0]}:{server.server_address[1]}/health",
    }
    _json_out(payload)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return EXIT_OK


def _cmd_show(args: argparse.Namespace, root: Path) -> int:
    sid = _find_session(
        root,
        session_id=args.session_id,
        plan_id=args.plan_id,
        latest=args.latest,
        repo=args.repo,
        topic=args.topic,
    )
    state = _load_state(root, sid)
    if args.json:
        _json_out(state)
    else:
        print(f"{state['session_id']} -> {state['plan_id']} ({state.get('status', '')})")
        print(f"items: {len(state.get('plan_items', []))}; references: {len(state.get('references', []))}")
    return EXIT_OK


def _cmd_finalize(args: argparse.Namespace, root: Path) -> int:
    state = _load_state(root, args.session_id)
    state["status"] = "finalized"
    state["finalized_at"] = _now()
    plan_file = Path(args.output_plan).expanduser().resolve() if args.output_plan else _plan_path(root, state["plan_id"])
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text(_render_plan_md(state), encoding="utf-8")
    handoff_file = _handoff_path(root, state["session_id"])
    handoff_file.parent.mkdir(parents=True, exist_ok=True)
    handoff_file.write_text(_render_handoff_md(state, plan_file), encoding="utf-8")
    _session_handoff_path(root, state["session_id"]).write_text(
        _render_session_handoff_md(state),
        encoding="utf-8",
    )
    _transcript_path(root, state["session_id"]).write_text(
        _render_transcript_md(state),
        encoding="utf-8",
    )
    _references_path(root, state["session_id"]).write_text(
        _render_references_md(state),
        encoding="utf-8",
    )
    _write_json_file(_runtime_manifest_path(root, state["session_id"]), _build_runtime_manifest(state))
    _write_state(root, state)
    state = _load_state(root, state["session_id"])
    _update_index(root, state, plan_file, handoff_file)
    _json_out({
        "session_id": state["session_id"],
        "plan_id": state["plan_id"],
        "plan_file": str(plan_file),
        "handoff_file": str(handoff_file),
        "session_handoff_file": str(_session_handoff_path(root, state["session_id"])),
        "transcript_file": str(_transcript_path(root, state["session_id"])),
        "references_file": str(_references_path(root, state["session_id"])),
        "runtime_manifest_file": str(_runtime_manifest_path(root, state["session_id"])),
        "confirmed_items": len([
            item for item in state.get("plan_items", [])
            if item.get("status") in ("confirmed", "amended")
        ]),
    })
    return EXIT_OK


def _cmd_list_sessions(args: argparse.Namespace, root: Path) -> int:
    idx = _load_json_file(_index_path(root), default={"schema_version": 1, "sessions": []})
    sessions = []
    for entry in idx.get("sessions", []):
        if not isinstance(entry, dict):
            continue
        if args.repo and args.repo not in entry.get("repository_ids", []):
            continue
        if args.plan_id and args.plan_id != entry.get("plan_id"):
            continue
        if args.topic and args.topic.lower() not in str(entry.get("topic", "")).lower():
            continue
        sessions.append(entry)
    if args.json:
        _json_out({"sessions": sessions})
    else:
        for entry in sessions:
            print(f"{entry.get('updated_at', '')}\t{entry.get('plan_id', '')}\t{entry.get('session_id', '')}\t{entry.get('topic', '')}")
    return EXIT_OK


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon live-plan",
        description="Capture and verify a live meeting plan before handing it to Cursor.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start a local live meeting planning session.")
    start.add_argument("--company-id", required=True)
    start.add_argument("--repo", required=True, help="Primary repository id.")
    start.add_argument("--additional-repo", action="append", default=[])
    start.add_argument("--topic", required=True)
    start.add_argument("--meeting-ref", default="")
    start.add_argument("--mode", choices=_MODES, default="prompted")
    start.add_argument(
        "--transport",
        choices=("manual", "local-participant", "meet-participant"),
        default="manual",
        help="Meeting transport adapter target. External adapters are credential-gated.",
    )
    start.add_argument("--participant", action="append", default=[], help="name[:email[:voice_profile_status]]")
    start.add_argument("--session-id", default="")
    start.add_argument("--plan-id", default="")
    start.add_argument("--json", action="store_true")

    ref = sub.add_parser("add-reference", help="Attach an explicit image/file/repo/memory reference.")
    ref.add_argument("--session-id", required=True)
    ref.add_argument("--type", choices=_REFERENCE_TYPES, required=True)
    ref.add_argument("--title", required=True)
    ref.add_argument("--path", default="")
    ref.add_argument("--uri", default="")
    ref.add_argument("--summary", default="")
    ref.add_argument("--shared-to-meeting", action="store_true")
    ref.add_argument(
        "--meeting-chat-status",
        choices=("not_requested", "requested", "posted", "unavailable", "failed"),
        default="not_requested",
    )

    seg = sub.add_parser("add-transcript", help="Append a verbatim transcript segment.")
    seg.add_argument("--session-id", required=True)
    seg.add_argument("--speaker", required=True)
    seg.add_argument("--text", required=True)
    seg.add_argument("--source", default="manual")
    seg.add_argument("--timestamp", default="")

    prop = sub.add_parser("propose-item", help="Add a plan item requiring read-back verification.")
    prop.add_argument("--session-id", required=True)
    prop.add_argument("--type", choices=_ITEM_TYPES, required=True)
    prop.add_argument("--title", required=True)
    prop.add_argument("--content", required=True)
    prop.add_argument("--evidence-ref", action="append", default=[])
    prop.add_argument("--requires-confirmation", action=argparse.BooleanOptionalAction, default=True)

    conf = sub.add_parser("confirm-item", help="Confirm, amend, or reject a proposed item.")
    conf.add_argument("--session-id", required=True)
    conf.add_argument("--item-id", required=True)
    conf.add_argument("--status", choices=("confirmed", "amended", "rejected"), required=True)
    conf.add_argument("--title", default="")
    conf.add_argument("--content", default="")

    hand = sub.add_parser("raise-hand", help="Record that the bot wants to speak.")
    hand.add_argument("--session-id", required=True)
    hand.add_argument("--reason", required=True)
    hand.add_argument("--item-id", default="")

    rh = sub.add_parser("resolve-hand", help="Approve or dismiss a hand raise.")
    rh.add_argument("--session-id", required=True)
    rh.add_argument("--hand-raise-id", required=True)
    rh.add_argument("--status", choices=("approved", "dismissed"), required=True)

    mode = sub.add_parser("set-mode", help="Switch prompted vs independent hand-raise mode.")
    mode.add_argument("--session-id", required=True)
    mode.add_argument("--mode", choices=_MODES, required=True)

    people = sub.add_parser("upsert-participant", help="Store participant and reusable voice reference metadata.")
    people.add_argument("--name", required=True)
    people.add_argument("--email", default="")
    people.add_argument("--person-id", default="")
    people.add_argument("--voice-ref", action="append", default=[])

    list_people = sub.add_parser("list-participants", help="List stored participant profiles.")
    list_people.add_argument("--json", action="store_true")

    creds = sub.add_parser("check-credentials", help="Check external transport credential readiness.")
    creds.add_argument(
        "--transport",
        choices=("manual", "local-participant", "meet-participant"),
        default="meet-participant",
    )
    creds.add_argument("--require-ready", action="store_true")

    runtime = sub.add_parser("runtime-manifest", help="Emit the external meeting bot runtime contract.")
    runtime.add_argument("--session-id", required=True)
    runtime.add_argument("--write", action="store_true")

    panel = sub.add_parser("panel-manifest", help="Emit the meeting pane contract for the browser extension or local panel.")
    panel.add_argument("--session-id", required=True)
    panel.add_argument("--write", action="store_true")

    panel_http = sub.add_parser(
        "panel-http-bridge",
        help="Serve a localhost HTTP bridge for a meeting pane or browser extension.",
    )
    panel_http.add_argument("--host", default="127.0.0.1")
    panel_http.add_argument("--port", type=int, default=8765)

    oauth = sub.add_parser("google-oauth-config", help="Inspect the configured Google desktop OAuth client.")
    oauth.add_argument("--test-user", default="")

    oauth_authorize = sub.add_parser("google-oauth-authorize", help="Create a Google desktop OAuth authorization URL.")
    oauth_authorize.add_argument("--scope", action="append", required=True)
    oauth_authorize.add_argument("--redirect-uri", default="")

    oauth_exchange = sub.add_parser("google-oauth-exchange", help="Exchange a Google OAuth authorization code for tokens.")
    oauth_exchange.add_argument("--code", required=True)
    oauth_exchange.add_argument("--state", default="")

    oauth_refresh = sub.add_parser("google-oauth-refresh", help="Refresh the cached Google OAuth access token.")
    oauth_refresh.add_argument("--force", action="store_true")

    meet_probe = sub.add_parser("google-meet-probe", help="Verify Google OAuth tokens and optionally fetch a Meet space.")
    meet_probe.add_argument("--scope", action="append", default=["openid", "https://www.googleapis.com/auth/userinfo.email"])
    meet_probe.add_argument("--space", default="", help="Optional space resource like spaces/abc-defg-hij.")

    meet_create = sub.add_parser("google-meet-create-space", help="Create a Google Meet space using the cached OAuth token.")
    meet_create.add_argument("--access-type", choices=("OPEN", "TRUSTED", "RESTRICTED"), default="")

    meet_get = sub.add_parser("google-meet-get-space", help="Fetch a Google Meet space using the cached OAuth token.")
    meet_get.add_argument("--name", required=True, help="Space resource like spaces/abc-defg-hij or spaces/<id>.")
    meet_get.add_argument(
        "--scope",
        action="append",
        default=["https://www.googleapis.com/auth/meetings.space.created"],
    )

    meet_bind = sub.add_parser(
        "google-meet-bind-space",
        help="Bind a Google Meet space to a live-plan session and persist its meeting metadata.",
    )
    meet_bind.add_argument("--session-id", required=True)
    meet_bind.add_argument("--name", required=True, help="Space resource like spaces/<id>.")
    meet_bind.add_argument(
        "--scope",
        action="append",
        default=["https://www.googleapis.com/auth/meetings.space.readonly"],
    )

    meet_offer = sub.add_parser(
        "google-meet-generate-offer",
        help="Generate a local WebRTC SDP offer for the Meet Media API using aiortc.",
    )
    meet_offer.add_argument("--audio-streams", type=int, default=3)
    meet_offer.add_argument("--video-streams", type=int, default=0)
    meet_offer.add_argument("--wait-for-ice-seconds", type=float, default=5.0)
    meet_offer.add_argument("--output-file", default="")

    meet_connect = sub.add_parser(
        "google-meet-connect-active-conference",
        help="Send a WebRTC SDP offer to Google Meet Media API and store the SDP answer.",
    )
    meet_connect.add_argument("--name", required=True, help="Space resource like spaces/<id>.")
    meet_connect.add_argument("--session-id", default="")
    meet_connect.add_argument("--generate-offer", action="store_true")
    meet_connect.add_argument("--offer", default="", help="Inline SDP offer.")
    meet_connect.add_argument("--offer-file", default="", help="Path to a file containing the SDP offer.")
    meet_connect.add_argument("--audio-streams", type=int, default=3)
    meet_connect.add_argument("--video-streams", type=int, default=0)
    meet_connect.add_argument("--wait-for-ice-seconds", type=float, default=5.0)
    meet_connect.add_argument(
        "--media-scope",
        default="https://www.googleapis.com/auth/meetings.conference.media.audio.readonly",
        choices=(
            "https://www.googleapis.com/auth/meetings.conference.media.readonly",
            "https://www.googleapis.com/auth/meetings.conference.media.audio.readonly",
            "https://www.googleapis.com/auth/meetings.conference.media.video.readonly",
        ),
    )

    meet_attach = sub.add_parser(
        "google-meet-attach-media",
        help="Attach a successful Google Meet media session artifact to a live-plan session.",
    )
    meet_attach.add_argument("--session-id", required=True)
    meet_attach.add_argument("--media-session-id", required=True)
    meet_attach.add_argument("--answer-file", default="")

    ingest = sub.add_parser(
        "ingest-events",
        help="Apply meeting pane or runtime events to a live-plan session in one serialized write.",
    )
    ingest.add_argument("--session-id", required=True)
    ingest.add_argument("--event-json", default="")
    ingest.add_argument("--events-file", default="")
    ingest.add_argument("--stdin", action="store_true")

    show = sub.add_parser("show", help="Show a live-plan session.")
    show.add_argument("--session-id", default="")
    show.add_argument("--plan-id", default="")
    show.add_argument("--repo", default="")
    show.add_argument("--topic", default="")
    show.add_argument("--latest", action="store_true")
    show.add_argument("--json", action="store_true")

    fin = sub.add_parser("finalize", help="Write the Cursor plan file and Canon handoff.")
    fin.add_argument("--session-id", required=True)
    fin.add_argument("--output-plan", default="")

    ls = sub.add_parser("list", help="List finalized live-plan sessions.")
    ls.add_argument("--repo", default="")
    ls.add_argument("--plan-id", default="")
    ls.add_argument("--topic", default="")
    ls.add_argument("--json", action="store_true")

    return p


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    root = _repo_root()
    try:
        if args.command == "start":
            return _cmd_start(args, root)
        if args.command == "add-reference":
            return _cmd_add_reference(args, root)
        if args.command == "add-transcript":
            return _cmd_add_transcript(args, root)
        if args.command == "propose-item":
            return _cmd_propose_item(args, root)
        if args.command == "confirm-item":
            return _cmd_confirm_item(args, root)
        if args.command == "raise-hand":
            return _cmd_raise_hand(args, root)
        if args.command == "resolve-hand":
            return _cmd_resolve_hand(args, root)
        if args.command == "set-mode":
            return _cmd_set_mode(args, root)
        if args.command == "upsert-participant":
            return _cmd_upsert_participant(args, root)
        if args.command == "list-participants":
            return _cmd_list_participants(args, root)
        if args.command == "check-credentials":
            return _cmd_check_credentials(args, root)
        if args.command == "runtime-manifest":
            return _cmd_runtime_manifest(args, root)
        if args.command == "panel-manifest":
            return _cmd_panel_manifest(args, root)
        if args.command == "panel-http-bridge":
            return _cmd_panel_http_bridge(args, root)
        if args.command == "google-oauth-config":
            return _cmd_google_oauth_config(args, root)
        if args.command == "google-oauth-authorize":
            return _cmd_google_oauth_authorize(args, root)
        if args.command == "google-oauth-exchange":
            return _cmd_google_oauth_exchange(args, root)
        if args.command == "google-oauth-refresh":
            return _cmd_google_oauth_refresh(args, root)
        if args.command == "google-meet-probe":
            return _cmd_google_meet_probe(args, root)
        if args.command == "google-meet-create-space":
            return _cmd_google_meet_create_space(args, root)
        if args.command == "google-meet-get-space":
            return _cmd_google_meet_get_space(args, root)
        if args.command == "google-meet-bind-space":
            return _cmd_google_meet_bind_space(args, root)
        if args.command == "google-meet-generate-offer":
            return _cmd_google_meet_generate_offer(args, root)
        if args.command == "google-meet-connect-active-conference":
            return _cmd_google_meet_connect_active_conference(args, root)
        if args.command == "google-meet-attach-media":
            return _cmd_google_meet_attach_media(args, root)
        if args.command == "ingest-events":
            return _cmd_ingest_events(args, root)
        if args.command == "show":
            return _cmd_show(args, root)
        if args.command == "finalize":
            return _cmd_finalize(args, root)
        if args.command == "list":
            return _cmd_list_sessions(args, root)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_NOT_FOUND
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_MALFORMED
    return EXIT_USAGE
