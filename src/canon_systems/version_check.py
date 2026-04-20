"""Version drift guard.

When a repo is enabled with canon-systems, the pinned version is written
to `.canon/memory-layer.local.env` as `CANON_SYSTEMS_VERSION=<installed>`.
On every hook invocation we compare the installed CLI version against the
pinned one.

Rules (hard-fail with auto-upgrade offer):
- installed == pinned         -> OK
- installed >  pinned          -> OK (user upgraded; we don't downgrade-warn)
- installed <  pinned          -> FAIL with actionable message; the
                                  Cursor rule instructs the agent to offer
                                  running `pipx upgrade canon-systems`.
- pinned missing               -> OK the first time. The next `enable-repo`
                                  run will write the pin.

Back-compat: the legacy key `CANON_MEMORY_LAYER_VERSION` is still read as
a fallback so repos wired with the previous package name keep working.
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
    pinned = env.get("CANON_SYSTEMS_VERSION", "").strip()
    if pinned:
        return pinned
    # Legacy pin from the canon-memory-layer era.
    return env.get("CANON_MEMORY_LAYER_VERSION", "").strip()


def check(root: Path | None = None) -> tuple[bool, str]:
    """Return (ok, message). ok=False means hard-fail."""
    r = root or repo_root()
    pinned = _pinned_version(r)
    if not pinned:
        return True, f"canon-systems: version pin not set yet (installed={INSTALLED_VERSION})"
    if _version_tuple(INSTALLED_VERSION) >= _version_tuple(pinned):
        return True, f"canon-systems: version ok ({INSTALLED_VERSION} >= pinned {pinned})"
    return False, (
        f"canon-systems: installed version {INSTALLED_VERSION} is older than "
        f"pinned {pinned} for this repo. Upgrade with:\n"
        "  pipx upgrade canon-systems\n"
        "  # or: pipx install --force git+ssh://git@github.com/<your-org>/canon-systems.git\n"
        "Then re-run your prompt. (If this is unexpected, inspect "
        ".canon/memory-layer.local.env CANON_SYSTEMS_VERSION.)"
    )


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check canon-systems version drift.")
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
