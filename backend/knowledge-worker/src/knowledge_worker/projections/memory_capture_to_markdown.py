"""Render structured short-session memory captures into markdown."""

from __future__ import annotations

from knowledge_worker.models import MemoryCaptureRequest


def render_memory_capture(request: MemoryCaptureRequest) -> str:
    sections: list[str] = [f"# {request.title}", ""]

    if request.summary:
        sections.extend(["## Summary", "", request.summary.strip(), ""])

    if request.decisions:
        sections.extend(["## Decisions", ""])
        sections.extend(f"- {item}" for item in request.decisions)
        sections.append("")

    if request.next_actions:
        sections.extend(["## Next Actions", ""])
        sections.extend(f"- {item}" for item in request.next_actions)
        sections.append("")

    if request.open_questions:
        sections.extend(["## Open Questions", ""])
        sections.extend(f"- {item}" for item in request.open_questions)
        sections.append("")

    sections.extend(["## Transcript", "", request.transcript_text.strip(), ""])
    return "\n".join(sections).strip() + "\n"
