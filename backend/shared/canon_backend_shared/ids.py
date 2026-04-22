"""Deterministic identifier helpers (backlog §A)."""

from __future__ import annotations

import hashlib


def deterministic_id(*parts: str, prefix: str | None = None) -> str:
    """
    Return a stable id from ordered string parts using SHA-256 over the
    pipe-joined payload (``company_id|plan_id|task_id|...`` style).
    """
    raw = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    if prefix is not None:
        return f"{prefix}_{raw}"
    return raw
