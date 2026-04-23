"""Deterministic CanonicalEvent → VaultBundle generator. Pure; no network/S3/wallclock."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Set, Tuple

from canon_backend_shared.events import CanonicalEvent

from synthesis.redaction import (
    FRONTMATTER_ANCHOR_ORDER,
    SafeEvent,
    project_safe,
    shorthash,
)

_PHASE_FILES: dict[str, str] = {
    "scoper": "scoper.md",
    "cursor-pilot": "cursor-pilot.md",
    "implementer": "implementer.md",
    "qa-gate": "qa-gate.md",
    "release-orchestrator": "release-orchestrator.md",
}


def _phase_filename(phase: str) -> str:
    return _PHASE_FILES.get(phase, "implementer.md")


@dataclass(frozen=True)
class VaultBundle:
    pages: dict[str, bytes]
    write_once_keys: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                ".obsidian/app.json",
                ".obsidian/workspace.json",
                ".obsidian/graph.json",
            }
        )
    )

    def keys(self) -> Iterable[str]:
        return self.pages.keys()


def render_frontmatter(safe: SafeEvent) -> str:
    data = {**safe.frontmatter}
    lines = []
    for k in FRONTMATTER_ANCHOR_ORDER:
        if k in data:
            lines.append(f"{k}: {_yaml_primitives(data[k])}")
    for k in sorted(x for x in data if x not in FRONTMATTER_ANCHOR_ORDER):
        lines.append(f"{k}: {_yaml_primitives(data[k])}")
    inner = "\n".join(lines)
    return f"---\n{inner}\n---\n"


def _yaml_primitives(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v)
    s = str(v)
    if any(c in s for c in (":", "#", "\n", '"', "'")) or s.strip() != s or not s:
        return json.dumps(s, ensure_ascii=True)
    return s


def _md_body(frontmatter: str, body: str) -> str:
    b = body if body.endswith("\n") else body + "\n"
    if not frontmatter.endswith("\n"):
        frontmatter += "\n"
    if not b.endswith("\n"):
        b += "\n"
    return f"{frontmatter}{b}"


def primary_vault_key(event: CanonicalEvent) -> str:
    et = event.event_type
    if et == "retrieval_breakdown":
        return f"events/retrieval-breakdown/{event.plan_id}/{event.task_id}.md"
    if et == "lease_stall_detected":
        return f"events/stall-watchdog/{event.plan_id}/{event.task_id}.md"
    if et == "checkpoint_write":
        p = event.payload
        if isinstance(p, dict) and "phase" in p:
            return (
                f"plans/{event.plan_id}/tasks/{event.task_id}/"
                f"{_phase_filename(str(p.get('phase', 'implementer')))}"
            )
        return f"plans/{event.plan_id}/tasks/{event.task_id}/implementer.md"
    return f"events/opaque/{event.event_id}.md"


def _attachment_json(safe: SafeEvent) -> str:
    env = {**{k: safe.frontmatter[k] for k in sorted(safe.frontmatter)}}
    pl = {**safe.payload}
    blob = {**env, "payload": pl}
    return (
        json.dumps(
            blob,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


def _render_readme(company_shorthash: str, repo_shorthash: str, cutoff: str) -> str:
    fm = f"---\nschema_version: 1\ncutoff_timestamp: {json.dumps(cutoff, ensure_ascii=True)}\n---\n"
    body = (
        f"Synthesis vault — company `{company_shorthash}` / repo `{repo_shorthash}`. "
        f"Start under `plans/` (see by-plan index in `_index/`).\n"
    )
    return _md_body(fm, body)


def _obsidian_seeds() -> dict[str, str]:
    a = {
        "alwaysUpdateLinks": True,
        "showLineNumber": False,
        "attachmentFolderPath": "attachments",
    }
    w = {
        "main": {
            "id": "default",
            "type": "split",
            "children": [],
        }
    }
    g = {
        "search": "true",
        "showOrphans": "false",
        "showAttachments": "true",
    }
    return {
        ".obsidian/app.json": json.dumps(
            a, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        + "\n",
        ".obsidian/workspace.json": json.dumps(
            w, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        + "\n",
        ".obsidian/graph.json": json.dumps(
            g, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        + "\n",
    }


def _render_retrieval_page(safe: SafeEvent) -> str:
    fm = render_frontmatter(safe)
    p = safe.payload
    pline = f"Retrieval {safe.event_id} (phase: {p.get('phase', '')}). [[event:{safe.event_id}]]\n"
    return _md_body(fm, pline)


def _render_stall_page(safe: SafeEvent) -> str:
    fm = render_frontmatter(safe)
    pline = f"Stall {safe.event_id} owner_suffix. [[event:{safe.event_id}]]\n"
    return _md_body(fm, pline)


def _render_opaque_page(safe: SafeEvent) -> str:
    fm = render_frontmatter(safe)
    b = f"dropped_payload: true\n\nUnknown type — [[event:{safe.event_id}]]\n"
    return _md_body(fm, b)


def _render_agent_run(safe: SafeEvent) -> str:
    fm = render_frontmatter(safe)
    suf = safe.path_shorthashes.get("agent_run_suffix", "00000000")
    b = f"Run [[event:{safe.event_id}]] suffix `{suf}`.\n"
    return _md_body(fm, b)


def _task_index_for_task(
    plan_id: str, task_id: str, for_events: List[SafeEvent]
) -> str:
    e0 = for_events[0]
    lines = [
        render_frontmatter(e0)
        + f"## Task [[task:{task_id}]]\nIn plan [[plan:{plan_id}]].\n"
    ]
    for s in for_events:
        lines.append(
            f"- Noted [[event:{s.event_id}]] ({s.event_type}).\n"
        )
    return "".join(lines)


def _plan_index_for_plan(plan_id: str, for_events: List[SafeEvent], tasks: Set[str]) -> str:
    e0 = for_events[0]
    part = [render_frontmatter(e0) + f"## Plan [[plan:{plan_id}]]\n\n"]
    part.append(
        f"Reference [[event:{e0.event_id}]]; tasks for this plan are listed below.\n"
    )
    for t in sorted(tasks):
        part.append(f"- [[task:{t}]]\n")
    return "".join(part)


def _index_by_type(safes: List[SafeEvent]) -> str:
    out = ["# By event type\n\n"]
    by_t: dict[str, List[SafeEvent]] = {}
    for s in safes:
        by_t.setdefault(s.event_type, []).append(s)
    for t in sorted(by_t):
        out.append(f"## {t}\n\n")
        for s in by_t[t]:
            out.append(
                f"- [[event:{s.event_id}]] (plan {s.frontmatter.get('plan_id', '')}, "
                f"task {s.frontmatter.get('task_id', '')})\n"
            )
    return "".join(out)


def _index_by_plan(safes: List[SafeEvent]) -> str:
    out = ["# By plan\n\n"]
    by_p: dict[str, List[SafeEvent]] = {}
    for s in safes:
        by_p.setdefault(s.frontmatter.get("plan_id", ""), []).append(s)
    for p in sorted(by_p):
        out.append(f"## {p}\n\n")
        for s in by_p[p]:
            out.append(f"- [[event:{s.event_id}]]\n")
    return "".join(out)


def _index_by_agent(safes: List[SafeEvent]) -> str:
    out = ["# By agent\n\n"]
    by_a: dict[str, List[SafeEvent]] = {}
    for s in safes:
        by_a.setdefault(s.frontmatter.get("agent_name", ""), []).append(s)
    for a in sorted(by_a):
        out.append(f"## {a}\n\n")
        for s in by_a[a]:
            out.append(f"- [[event:{s.event_id}]]\n")
    return "".join(out)


def generate_vault(
    events: Iterable[CanonicalEvent],
    *,
    company_id: str,
    repository_id: str,
    cutoff_timestamp: str,
) -> VaultBundle:
    company_h = shorthash(company_id)
    repo_h = shorthash(repository_id)
    all_events = list(events)
    sorted_e = sorted(all_events, key=lambda e: (e.timestamp, e.event_id))
    in_cutoff: list[CanonicalEvent] = [e for e in sorted_e if e.timestamp <= cutoff_timestamp]
    safes: list[SafeEvent] = [project_safe(e) for e in in_cutoff]
    pages: dict[str, bytes] = {}

    # README + .obsidian
    pages["README.md"] = _render_readme(company_h, repo_h, cutoff_timestamp).encode("utf-8")
    for rel, s in _obsidian_seeds().items():
        pages[rel] = s.encode("utf-8")

    by_plan_task: dict[Tuple[str, str], list[SafeEvent]] = {}
    for s in safes:
        pid = s.frontmatter.get("plan_id", "")
        tid = s.frontmatter.get("task_id", "")
        by_plan_task.setdefault((str(pid), str(tid)), []).append(s)
    for s in safes:
        eid = s.event_id
        pages[f"attachments/{eid}.json"] = _attachment_json(s).encode("utf-8")
        if s.event_type == "retrieval_breakdown":
            p = s.frontmatter.get("plan_id", "")
            t = s.frontmatter.get("task_id", "")
            k = f"events/retrieval-breakdown/{p}/{t}.md"
            pages[k] = _render_retrieval_page(s).encode("utf-8")
        elif s.event_type == "lease_stall_detected":
            p = s.frontmatter.get("plan_id", "")
            t = s.frontmatter.get("task_id", "")
            k = f"events/stall-watchdog/{p}/{t}.md"
            pages[k] = _render_stall_page(s).encode("utf-8")
        elif s.event_type == "checkpoint_write":
            p = s.frontmatter.get("plan_id", "")
            t = s.frontmatter.get("task_id", "")
            ph = str(s.payload.get("phase", "implementer"))
            fn = _phase_filename(ph)
            body_add = f"Checkpoint state_version {s.payload.get('state_version', s.frontmatter.get('state_version', ''))} — [[event:{eid}]]\n"
            k = f"plans/{p}/tasks/{t}/{fn}"
            if k in pages:
                old = pages[k].decode("utf-8")
                if not old.endswith("\n"):
                    old += "\n"
                pages[k] = (old + body_add).encode("utf-8")
            else:
                fm0 = render_frontmatter(s)
                pages[k] = _md_body(fm0, body_add).encode("utf-8")
        else:
            k = f"events/opaque/{eid}.md"
            pages[k] = _render_opaque_page(s).encode("utf-8")
        an = s.frontmatter.get("agent_name", "agent")
        rsuf = s.path_shorthashes.get("agent_run_suffix", "00000000")
        rkey = f"agents/{an}/runs/{rsuf}.md"
        if rkey not in pages:
            pages[rkey] = _render_agent_run(s).encode("utf-8")
        else:
            prev = pages[rkey].decode("utf-8")
            nline = f"Ref [[event:{eid}]]\n"
            if nline not in prev:
                pr = prev if prev.endswith("\n") else prev + "\n"
                pages[rkey] = (pr + nline).encode("utf-8")

    for (pid, tid), g in sorted(by_plan_task.items()):
        k = f"plans/{pid}/tasks/{tid}/index.md"
        body = _task_index_for_task(pid, tid, g)
        pages[k] = body.encode("utf-8")
    for pid in sorted({s.frontmatter.get("plan_id", "") for s in safes}):
        tset: Set[str] = set()
        for s in safes:
            if s.frontmatter.get("plan_id", "") == pid:
                tset.add(str(s.frontmatter.get("task_id", "")))
        g = [s for s in safes if s.frontmatter.get("plan_id", "") == pid]
        if g:
            pages[f"plans/{pid}/index.md"] = _plan_index_for_plan(
                str(pid), g, tset
            ).encode("utf-8")

    if safes:
        pages["_index/by-event-type.md"] = _index_by_type(safes).encode("utf-8")
        pages["_index/by-plan.md"] = _index_by_plan(safes).encode("utf-8")
        pages["_index/by-agent.md"] = _index_by_agent(safes).encode("utf-8")

    return VaultBundle(pages=pages)


# --- exposed render fns (spec) ---
def render_task_page(safe: SafeEvent, context: str) -> str:
    _ = context
    return _task_index_for_task(
        str(safe.frontmatter.get("plan_id", "")),
        str(safe.frontmatter.get("task_id", "")),
        [safe],
    )


def render_plan_page(plan_id: str, safe_events: list[SafeEvent]) -> str:
    ts = {str(s.frontmatter.get("task_id", "")) for s in safe_events}
    return _plan_index_for_plan(plan_id, safe_events, ts)


def render_agent_run_page(safe: SafeEvent) -> str:
    return _render_agent_run(safe)


def render_retrieval_breakdown_page(safe: SafeEvent) -> str:
    return _render_retrieval_page(safe)


def render_stall_page(safe: SafeEvent) -> str:
    return _render_stall_page(safe)


def render_opaque_page(safe: SafeEvent) -> str:
    return _render_opaque_page(safe)


def _render_indices(safe_events: list[SafeEvent]) -> dict[str, bytes]:
    if not safe_events:
        return {}
    return {
        "_index/by-event-type.md": _index_by_type(safe_events).encode("utf-8"),
        "_index/by-plan.md": _index_by_plan(safe_events).encode("utf-8"),
        "_index/by-agent.md": _index_by_agent(safe_events).encode("utf-8"),
    }
