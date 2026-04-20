"""Version drift guard.

When a repo was enabled with a version of canon-memory-layer, the pinned
version is written to `.canon/memory-layer.local.env` as
`CANON_MEMORY_LAYER_VERSION=<installed_version>`. On every hook invocation we
compare the installed CLI version against the pinned one.

Rules (hard-fail with auto-upgrade offer):
- installed == pinned         -> OK
- installed >  pinned          -> OK (user upgraded; we don't downgrade-warn)
- installed <  pinned          -> FAIL with actionable message; agent is
                                  instructed (via Cursor rule) to offer running
                                  `pipx upgrade canon-memory-layer`.
- pinned missing               -> OK the first time, but write pinned=installed
                                  on first successful run so drift detection
                                  activates from then on.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__ as INSTALLED_VERSION
from .shared import load_env_file, repo_root


def _version_tuple(v: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in v.strip().split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


def _pinned_version(root: Path) -> str:
    env = load_env_file(root / ".canon" / "memory-layer.local.env")
    return env.get("CANON_MEMORY_LAYER_VERSION", "").strip()


def check(root: Path | None = None) -> tuple[bool, str]:
    """Return (ok, message). ok=False means hard-fail."""
    r = root or repo_root()
    pinned = _pinned_version(r)
    if not pinned:
        return True, f"canon-memory-layer: version pin not set yet (installed={INSTALLED_VERSION})"
    if _version_tuple(INSTALLED_VERSION) >= _version_tuple(pinned):
        return True, f"canon-memory-layer: version ok ({INSTALLED_VERSION} >= pinned {pinned})"
    return False, (
        f"canon-memory-layer: installed version {INSTALLED_VERSION} is older than "
        f"pinned {pinned} for this repo. Upgrade with:\n"
        "  pipx upgrade canon-memory-layer\n"
        "  # or: pipx install --force git+ssh://git@github.com/<your-org>/canon-memory-layer.git\n"
        "Then re-run your prompt. (If this is unexpected, inspect "
        ".canon/memory-layer.local.env CANON_MEMORY_LAYER_VERSION.)"
    )


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check canon-memory-layer version drift.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    ok, msg = check()
    if not args.quiet:
        print(msg, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
