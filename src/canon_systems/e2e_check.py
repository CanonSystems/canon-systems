"""Single-command plug-and-play validation for operator workstations."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

from . import __version__
from .shared import apply_layered_canon_env_for_repo, load_env_file, repo_root
from .version_check import _version_tuple

EXIT_OK = 0
EXIT_FAIL = 1


def _pinned_version(root: Path) -> str:
    env = load_env_file(root / ".canon" / "memory-layer.local.env")
    return (env.get("CANON_SYSTEMS_VERSION") or "").strip()


def run(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="canon e2e-check",
        description=(
            "Validate this repo is ready for day-to-day Canon use: Cursor hooks/rules, "
            "version pin vs installed CLI, and required memory backends (canonical + mempalace) "
            "via the same env layering as hooks."
        ),
    )
    p.add_argument(
        "--agent",
        action="store_true",
        help="Wrap stdout JSON with <<<CANON_E2E_VERDICT>>> lines for agent parsing.",
    )
    args = p.parse_args(argv)

    checks: list[dict[str, str]] = []
    root_s = os.environ.get("CANON_SYSTEMS_REPO_ROOT", "").strip()
    root = Path(root_s).expanduser().resolve() if root_s else repo_root()
    os.environ["CANON_SYSTEMS_REPO_ROOT"] = str(root)

    def add(cid: str, ok: bool, detail: str) -> None:
        checks.append({"id": cid, "status": "PASS" if ok else "FAIL", "detail": detail})

    pre = root / ".cursor" / "hooks" / "memory-preflight.sh"
    cap = root / ".cursor" / "hooks" / "memory-capture.sh"
    hooks_ok = (
        pre.is_file()
        and os.access(pre, os.X_OK)
        and cap.is_file()
        and os.access(cap, os.X_OK)
    )
    add("hooks_executable", hooks_ok, "memory-preflight.sh + memory-capture.sh +x")

    disc = root / ".cursor" / "rules" / "memory-platform-build-discipline.mdc"
    defaults = root / ".cursor" / "rules" / "memory-layer-defaults.mdc"
    add("cursor_rules", disc.is_file() and defaults.is_file(), "hard-lock + memory-layer-defaults .mdc")

    env_path = root / ".canon" / "memory-layer.local.env"
    add("memory_layer_local_env", env_path.is_file(), str(env_path))
    pin = _pinned_version(root) if env_path.is_file() else ""
    pin_line_ok = bool(pin) or not env_path.is_file()
    if env_path.is_file():
        body = env_path.read_text(encoding="utf-8")
        pin_line_ok = "CANON_SYSTEMS_VERSION=" in body
    add("version_pin_key", pin_line_ok, pin or "(empty)")

    drift_ok = True
    drift_detail = "no pin"
    if pin:
        if _version_tuple(pin) > _version_tuple(__version__):
            drift_ok = False
            drift_detail = f"pin {pin} > installed {__version__} — run: pipx upgrade canon-systems"
        else:
            drift_detail = f"pin {pin}; installed {__version__}"
    add("version_pin_vs_cli", drift_ok, drift_detail)

    apply_layered_canon_env_for_repo(root)

    from . import memory_health as mh

    buf = io.StringIO()
    with redirect_stdout(buf):
        mh_code = mh.run([])
    raw_mh = buf.getvalue()
    mh_payload: dict[str, object] = {}
    try:
        parsed = json.loads(raw_mh)
        if isinstance(parsed, dict):
            mh_payload = parsed
    except json.JSONDecodeError as exc:
        add("memory_health", False, f"invalid JSON from memory-health: {exc}")
    else:
        if not mh_payload:
            add("memory_health", False, "memory-health stdout was not a JSON object")
        else:
            overall = str(mh_payload.get("overall_status", ""))
            mh_ok = mh_code == 0 and overall != "unhealthy"
            add(
                "memory_health",
                mh_ok,
                f"exit={mh_code} overall_status={overall!r}",
            )

    all_pass = all(c["status"] == "PASS" for c in checks)
    verdict = "PASS" if all_pass else "FAIL"
    out_obj: dict[str, object] = {
        "verdict": verdict,
        "canon_version": __version__,
        "repo_root": str(root),
        "checks": checks,
        "memory_health_report": mh_payload or None,
        "summary": (
            "Plug-and-play OK: wiring + required memory backends healthy."
            if all_pass
            else "Fix failing checks above, then re-run canon e2e-check."
        ),
    }
    text = json.dumps(out_obj, indent=2, ensure_ascii=True) + "\n"

    if args.agent:
        sys.stdout.write("<<<CANON_E2E_VERDICT_START>>>\n")
    sys.stdout.write(text)
    if args.agent:
        sys.stdout.write("<<<CANON_E2E_VERDICT_END>>>\n")

    return EXIT_OK if all_pass else EXIT_FAIL


__all__ = ["run", "EXIT_OK", "EXIT_FAIL"]
