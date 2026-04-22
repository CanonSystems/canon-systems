"""Workspace path bootstrap for local development."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_workspace_paths() -> None:
    """Add the service and shared local library paths to ``sys.path``.

    This keeps the service runnable from the monorepo root without requiring
    the sibling libraries to be installed into the active environment first.
    """

    service_root = Path(__file__).resolve().parents[1]
    repo_root = service_root.parent.parent

    candidate_paths = [
        service_root,
        repo_root / "backend" / "knowledge-schema" / "src",
        repo_root / "backend" / "knowledge-policy" / "src",
        repo_root / "libs" / "knowledge-schema" / "src",
        repo_root / "libs" / "knowledge-policy" / "src",
    ]

    for path in reversed(candidate_paths):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
