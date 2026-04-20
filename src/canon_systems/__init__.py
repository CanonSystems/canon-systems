"""Canon Systems — Cursor-native workflow package.

Bundles: tenant-scoped AWS-backed memory client, the Scoper → Cursor
Pilot → QA Gate agent chain, Cursor hooks, per-repo auto-setup, and
version-drift guards. All exposed through the `canon` CLI.

Module internals are implementation details; the public surface is the
`canon` command.
"""

from __future__ import annotations

__version__ = "3.0.0"
