"""Render compact markdown from memory search results."""

from __future__ import annotations

from memory_adapter.models import MemorySearchResponse


def render_memory_projection(*, query: str, response: MemorySearchResponse) -> str:
    lines = [
        "# Memory Projection",
        "",
        f"Query: {query}",
        f"Status: {response.status.value}",
        f"Recall source: {response.source}",
        "",
    ]

    if response.error:
        lines.extend(
            [
                "## Adapter Status",
                "",
                f"Error: {response.error}",
            ]
        )
        if response.hint:
            lines.append(f"Hint: {response.hint}")
        lines.append("")

    lines.extend(
        [
            "## Relevant Memory Hits",
            "",
        ]
    )

    if not response.results:
        lines.extend(["No matching memory hits were returned.", ""])
        return "\n".join(lines)

    for index, hit in enumerate(response.results, start=1):
        lines.extend(
            [
                f"### Hit {index}",
                f"- Wing: {hit.wing}",
                f"- Room: {hit.room}",
                f"- Source: {hit.source_file}",
                f"- Similarity: {hit.similarity:.3f}",
                "",
                hit.text,
                "",
            ]
        )

    return "\n".join(lines)


def render_repo_comprehension_note(
    *, query: str, response: MemorySearchResponse, repo_ids: list[str]
) -> str:
    """Markdown for a REPO_NOTE artifact derived from the same memory search as task context."""
    lines = [
        "# Repository comprehension",
        "",
        f"Query: {query}",
        f"Status: {response.status.value}",
        f"Recall source: {response.source}",
        "",
    ]
    if repo_ids:
        lines.extend(
            [
                "## Repositories in scope",
                "",
                *[f"- `{rid}`" for rid in repo_ids],
                "",
            ]
        )

    if response.error:
        lines.extend(
            [
                "## Adapter status",
                "",
                f"Error: {response.error}",
            ]
        )
        if response.hint:
            lines.append(f"Hint: {response.hint}")
        lines.append("")

    lines.extend(
        [
            "## Memory-backed repo notes",
            "",
        ]
    )

    if not response.results:
        lines.extend(["No matching memory hits were returned for this comprehension pass.", ""])
        return "\n".join(lines)

    for index, hit in enumerate(response.results, start=1):
        lines.extend(
            [
                f"### Note {index}",
                f"- Wing: {hit.wing}",
                f"- Room: {hit.room}",
                f"- Source: {hit.source_file}",
                f"- Similarity: {hit.similarity:.3f}",
                "",
                hit.text,
                "",
            ]
        )

    return "\n".join(lines)
