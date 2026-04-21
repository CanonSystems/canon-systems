"""Self-update when running `canon setup` or `canon enable-repo`.

If this process is running from a **pipx** venv for `canon-systems`, we run
`pipx upgrade canon-systems` and compare the installed distribution version
before vs after. When the version **increases**, we **re-exec** the `canon`
binary so the rest of the command runs on the upgraded code (including the
correct `__version__` for `enable-repo` pins).

Disabled when:

- `CANON_SYSTEMS_SKIP_SELF_UPDATE` is set to `1`, `true`, or `yes`
- `CI` is set to `1`, `true`, or `yes`

Set `CANON_SYSTEMS_SKIP_SELF_UPDATE=1` in CI or if you must pin an exact
build without surprise upgrades.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .version_check import _version_tuple


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def should_skip_self_update() -> bool:
    if _truthy_env("CANON_SYSTEMS_SKIP_SELF_UPDATE"):
        return True
    if _truthy_env("CI"):
        return True
    return False


def _is_pipx_canon_systems() -> bool:
    """True when this interpreter lives under pipx's canon-systems venv.

    Real installs look like ``.../pipx/venvs/canon-systems/bin/python``.
    We match ``venvs`` + ``canon-systems`` so tests can use a temp tree
    without copying the user's home directory layout.
    """
    try:
        exe = Path(sys.executable).resolve()
    except OSError:
        return False
    parts = exe.parts
    return "venvs" in parts and "canon-systems" in parts


def _installed_dist_version(venv_python: Path) -> str:
    """Read canon-systems version from disk via the venv interpreter (subprocess)."""
    code = "import importlib.metadata as m; print(m.version('canon-systems'))"
    proc = subprocess.run(
        [str(venv_python), "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _run_pipx_upgrade() -> tuple[int, str]:
    proc = subprocess.run(
        ["pipx", "upgrade", "canon-systems"],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode, out


def _self_update_state_path() -> Path:
    return Path.home() / ".canon" / "self-update-state.json"


def _should_throttle_self_update() -> bool:
    """True when a recent self-update check already happened.

    Controlled by CANON_SYSTEMS_SELF_UPDATE_INTERVAL_SEC (default 6h).
    Set 0 to disable throttling.
    """
    try:
        interval = int(os.environ.get("CANON_SYSTEMS_SELF_UPDATE_INTERVAL_SEC", "21600"))
    except ValueError:
        interval = 21600
    interval = max(0, interval)
    if interval == 0:
        return False
    path = _self_update_state_path()
    if not path.exists():
        return False
    try:
        last = float(path.read_text(encoding="utf-8").strip() or "0")
    except Exception:
        return False
    return (time.time() - last) < interval


def _mark_self_update_check() -> None:
    path = _self_update_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(time.time()), encoding="utf-8")


def try_self_update(argv: list[str], *, force: bool = False) -> None:
    """Maybe upgrade via pipx and re-exec `canon` with the same args tail.

    `argv` should be the full argv list (including program name at index 0).
    """
    if should_skip_self_update():
        return
    if not _is_pipx_canon_systems():
        return
    if not shutil.which("pipx"):
        return
    if not force and _should_throttle_self_update():
        return

    venv_python = Path(sys.executable).resolve()
    before = _installed_dist_version(venv_python)
    if not before:
        return

    _mark_self_update_check()
    print("canon-systems: checking for updates (pipx upgrade canon-systems)...", flush=True)
    code, combined = _run_pipx_upgrade()
    if code != 0:
        print(
            f"canon-systems: pipx upgrade exited {code}; continuing with {before}.\n{combined.strip()}",
            file=sys.stderr,
            flush=True,
        )
        return

    after = _installed_dist_version(venv_python)
    if not after:
        return

    if _version_tuple(after) <= _version_tuple(before):
        print(f"canon-systems: already up to date ({after}).", flush=True)
        return

    canon_path = shutil.which("canon")
    if not canon_path:
        print(
            f"canon-systems: upgraded {before} → {after} but 'canon' not on PATH; "
            "open a new shell and re-run your command.",
            file=sys.stderr,
            flush=True,
        )
        return

    rest = argv[1:] if len(argv) > 1 else []
    new_argv = [canon_path, *rest]
    print(f"canon-systems: upgraded {before} → {after}; restarting: {' '.join(new_argv)}", flush=True)
    os.execv(canon_path, new_argv)
