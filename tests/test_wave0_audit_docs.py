"""Smoke tests for Wave 0 audit markdown deliverables (E0-T1)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

AUDIT = REPO_ROOT / "docs" / "WAVE-0-AUDIT.md"
DEPRECATIONS = REPO_ROOT / "docs" / "DEPRECATIONS.md"
CATALOGUE = REPO_ROOT / "docs" / "OBSIDIAN-MIND-CATALOGUE.md"

SIBLING_PATHS = (
    "/Users/edwardwalker/localwork/canon-platform",
    "/Users/edwardwalker/localwork/canon-systems-v2",
    "/Users/edwardwalker/localwork/mempalace",
    "/Users/edwardwalker/localwork/obsidian-mind",
    "/Users/edwardwalker/localwork/temporal",
    "/Users/edwardwalker/localwork/total_recall",
)


def test_audit_mentions_all_three_urls() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for key in (
        "KNOWLEDGE_API_URL",
        "KNOWLEDGE_WORKER_URL",
        "MEMORY_ADAPTER_URL",
    ):
        assert key in text, f"audit must mention {key}"


def test_deprecations_covers_all_six_siblings_with_label() -> None:
    text = DEPRECATIONS.read_text(encoding="utf-8")
    label_re = re.compile(r"\b(keep|absorb|delete)\b", re.IGNORECASE)
    for path in SIBLING_PATHS:
        assert path in text, f"deprecations must cite {path}"
        start = text.index(path)
        window = text[start : start + 800]
        assert label_re.search(window), f"label missing near {path}"


def test_obsidian_mind_catalogue_nonempty() -> None:
    text = CATALOGUE.read_text(encoding="utf-8")
    assert len(text.strip()) > 200
    for needle in (
        ".claude/agents/",
        ".claude/commands/",
        ".claude/scripts/",
        ".claude/skills/",
        "vault-manifest.json",
    ):
        assert needle in text
