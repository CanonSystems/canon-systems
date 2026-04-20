"""Global CLI for canon-systems (`canon`) in any repository."""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .actor_report import run as run_actor_report
from .ask_hybrid import run as run_ask
from .capture_session import run as run_capture
from .context_preload import run as run_preflight
from .install_wizard import detect_repo_root, run as run_setup
from .repo_enable import enable_repo
from .store_pending_user import run as run_store_pending_user
from .version_check import run as run_version_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="canon",
        description=(
            "Canon Systems — Cursor-native workflow: tenant-scoped AWS-backed "
            "memory, the Scoper → Cursor Pilot → QA Gate agent chain, hooks, "
            "and auto-setup."
        ),
    )
    parser.add_argument("--version", action="version", version=f"canon-systems {__version__}")
    parser.add_argument("--repo-root", default="", help="Target repository root.")
    sub = parser.add_subparsers(dest="command", required=True)

    setup_p = sub.add_parser("setup", help="Configure machine + repo memory-layer access.")
    setup_p.add_argument("--non-interactive", action="store_true")

    sub.add_parser("enable-repo", help="Install Cursor hooks + subagents + rule in current repo.")

    pre = sub.add_parser("preflight", help="Run memory preflight (writes .canon/memory/context-latest.md).")
    pre.add_argument("prompt", nargs="?", default="")
    pre.add_argument("--hook-input", default="")
    pre.add_argument("--quiet", action="store_true")

    cap = sub.add_parser("capture", help="Capture a session turn into AWS-backed memory artifacts.")
    cap.add_argument("--hook-input", default="")
    cap.add_argument("--summary", default="")
    cap.add_argument("--user-text", default="")
    cap.add_argument("--assistant-text", default="")
    cap.add_argument("--conversation-id", default="")
    cap.add_argument("--pending-user-file", default="")
    cap.add_argument("--decisions", default="")
    cap.add_argument("--next-actions", default="")
    cap.add_argument("--open-questions", default="")
    cap.add_argument("--quiet", action="store_true")

    ask_p = sub.add_parser("ask", help="Query memory with a natural-language question.")
    ask_p.add_argument("question")
    ask_p.add_argument("--json", action="store_true", dest="ask_json")

    spu = sub.add_parser(
        "store-pending-user",
        help="Persist pending user prompt for turn-paired capture (used by preflight hook).",
    )
    spu.add_argument("--hook-input", required=True)
    spu.add_argument("--output-file", required=True)

    rep = sub.add_parser("actor-report", help="Show run summaries by actor.")
    rep.add_argument("--actor-id", default="")
    rep.add_argument("--limit", type=int, default=20)
    rep.add_argument("--json", action="store_true", dest="report_json")

    vc = sub.add_parser("version-check", help="Verify installed version >= repo-pinned version.")
    vc.add_argument("--quiet", action="store_true")

    args = parser.parse_args(argv)
    argv_for_exec = list(sys.argv) if argv is None else [sys.argv[0]] + list(argv)
    root = detect_repo_root(args.repo_root)
    os.environ["CANON_SYSTEMS_REPO_ROOT"] = str(root)
    # Back-compat: legacy env var name still honored downstream.
    os.environ.setdefault("CANON_MEMORY_LAYER_REPO_ROOT", str(root))

    if args.command in ("setup", "enable-repo"):
        from .self_update import try_self_update

        try_self_update(argv_for_exec)

    if args.command == "setup":
        setup_args: list[str] = ["--repo-root", str(root)]
        if args.non_interactive:
            setup_args.append("--non-interactive")
        code = run_setup(setup_args)
        if code != 0:
            return code
        enable_repo(root)
        print(f"Enabled canon-systems in {root}")
        return 0

    if args.command == "enable-repo":
        enable_repo(root)
        print(f"Enabled canon-systems in {root}")
        return 0

    if args.command == "preflight":
        pre_args: list[str] = []
        if args.prompt:
            pre_args.append(args.prompt)
        if args.hook_input:
            pre_args += ["--hook-input", args.hook_input]
        if args.quiet:
            pre_args.append("--quiet")
        return run_preflight(pre_args)

    if args.command == "capture":
        cap_args: list[str] = []
        if args.hook_input:
            cap_args += ["--hook-input", args.hook_input]
        if args.summary:
            cap_args += ["--summary", args.summary]
        if args.user_text:
            cap_args += ["--user-text", args.user_text]
        if args.assistant_text:
            cap_args += ["--assistant-text", args.assistant_text]
        if args.conversation_id:
            cap_args += ["--conversation-id", args.conversation_id]
        if args.pending_user_file:
            cap_args += ["--pending-user-file", args.pending_user_file]
        if args.decisions:
            cap_args += ["--decisions", args.decisions]
        if args.next_actions:
            cap_args += ["--next-actions", args.next_actions]
        if args.open_questions:
            cap_args += ["--open-questions", args.open_questions]
        if args.quiet:
            cap_args.append("--quiet")
        return run_capture(cap_args)

    if args.command == "ask":
        ask_args: list[str] = [args.question]
        if args.ask_json:
            ask_args.append("--json")
        return run_ask(ask_args)

    if args.command == "store-pending-user":
        return run_store_pending_user([
            "--hook-input", args.hook_input,
            "--output-file", args.output_file,
        ])

    if args.command == "actor-report":
        rep_args: list[str] = []
        if args.actor_id:
            rep_args += ["--actor-id", args.actor_id]
        rep_args += ["--limit", str(args.limit)]
        if args.report_json:
            rep_args.append("--json")
        return run_actor_report(rep_args)

    if args.command == "version-check":
        vc_args: list[str] = []
        if args.quiet:
            vc_args.append("--quiet")
        return run_version_check(vc_args)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
