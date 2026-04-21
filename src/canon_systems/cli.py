"""Global CLI for canon-systems (`canon`) in any repository."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .actor_report import run as run_actor_report
from .auth_migration import run as run_auth_migration
from .ask_hybrid import run as run_ask
from .capture_session import run as run_capture
from .dor_log import run as run_dor_log
from .context_preload import run as run_preflight
from .install_wizard import detect_repo_root, run as run_setup
from .repo_enable import enable_repo
from .secrets_submit import run as run_secrets_submit
from .store_pending_user import run as run_store_pending_user
from .version_check import _version_tuple
from .version_check import run as run_version_check


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _pinned_version(root: Path) -> str:
    from .shared import load_env_file

    env = load_env_file(root / ".canon" / "memory-layer.local.env")
    pinned = env.get("CANON_SYSTEMS_VERSION", "").strip()
    if pinned:
        return pinned
    return env.get("CANON_MEMORY_LAYER_VERSION", "").strip()


def _maybe_auto_rewire(root: Path, command: str) -> None:
    """Auto-refresh repo wiring when installed CLI is newer than pin.

    This makes template/rule updates (including agent behavior updates) plug-and-play
    across machines once a newer canon-systems build is installed.
    """
    if command in ("setup", "enable-repo"):
        return
    if _truthy_env("CANON_SYSTEMS_DISABLE_AUTO_REWIRE"):
        return
    pinned = _pinned_version(root)
    if not pinned:
        return
    if _version_tuple(__version__) <= _version_tuple(pinned):
        return
    try:
        enable_repo(root)
        print(
            f"canon-systems: auto-refreshed repo wiring ({pinned} -> {__version__}) in {root}",
            file=sys.stderr,
        )
    except Exception as exc:
        print(
            f"canon-systems: auto-rewire skipped due to error: {exc}",
            file=sys.stderr,
        )


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

    am = sub.add_parser(
        "auth-migration",
        help="Manage phased auth migration (prepare/canary/enforce/rollback).",
    )
    am.add_argument("phase", choices=("status", "prepare", "canary", "enforce", "rollback"))
    am.add_argument("--domain", default="memory.canon-systems.com")
    am.add_argument("--scheme", default="https")
    am.add_argument("--dry-run", action="store_true")

    dl = sub.add_parser(
        "dor-log",
        help="Send structured DoR failure telemetry (with local queue fallback).",
    )
    dl.add_argument("--event-json", default="")
    dl.add_argument("--event-file", default="")
    dl.add_argument("--flush-queue", action="store_true")
    dl.add_argument("--strict", action="store_true")
    dl.add_argument("--quiet", action="store_true")

    sec = sub.add_parser(
        "secrets",
        help="Structured AWS Secrets Manager workflows for Canon runtime credentials.",
    )
    sec_sub = sec.add_subparsers(dest="secrets_command", required=False)

    sec_submit = sec_sub.add_parser("submit", help="Validate and submit repo-scoped secret payload.")
    sec_submit.add_argument("--payload-file", default="")
    sec_submit.add_argument("--set", action="append", default=[])
    sec_submit.add_argument("--secret-id", default="")
    sec_submit.add_argument("--company-id", default="")
    sec_submit.add_argument("--repository-id", default="")
    sec_submit.add_argument("--prefix", default="")
    sec_submit.add_argument("--aws-profile", default="")
    sec_submit.add_argument("--aws-region", default="")
    sec_submit.add_argument("--create-if-missing", action="store_true")
    sec_submit.add_argument("--allow-partial", action="store_true")
    sec_submit.add_argument("--dry-run", action="store_true")

    sec_tmpl = sec_sub.add_parser("template", help="Print canonical secret payload template.")
    sec_tmpl.add_argument("--company-id", default="")
    sec_tmpl.add_argument("--repository-id", default="")
    sec_tmpl.add_argument("--prefix", default="")
    sec_tmpl.add_argument("--aws-region", default="")

    sec_wizard = sec_sub.add_parser("wizard", help="Run interactive secret setup flow.")
    sec_wizard.add_argument("--company-id", default="")
    sec_wizard.add_argument("--repository-id", default="")
    sec_wizard.add_argument("--prefix", default="")
    sec_wizard.add_argument("--aws-profile", default="")
    sec_wizard.add_argument("--aws-region", default="")
    sec_wizard.add_argument("--secret-id", default="")
    sec_wizard.add_argument("--copy-from-secret-id", default="")
    sec_wizard.add_argument("--copy-from-company-id", default="")
    sec_wizard.add_argument("--copy-from-repository-id", default="")
    sec_wizard.add_argument("--copy-from-prefix", default="")
    sec_wizard.add_argument("--allow-partial", action="store_true")
    sec_wizard.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    argv_for_exec = list(sys.argv) if argv is None else [sys.argv[0]] + list(argv)
    root = detect_repo_root(args.repo_root)
    os.environ["CANON_SYSTEMS_REPO_ROOT"] = str(root)
    # Back-compat: legacy env var name still honored downstream.
    os.environ.setdefault("CANON_MEMORY_LAYER_REPO_ROOT", str(root))

    if args.command in ("setup", "enable-repo"):
        from .self_update import try_self_update

        try_self_update(argv_for_exec, force=True)
    else:
        from .self_update import try_self_update

        try_self_update(argv_for_exec)

    _maybe_auto_rewire(root, args.command)

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

    if args.command == "auth-migration":
        am_args: list[str] = [args.phase, "--repo-root", str(root)]
        if args.domain:
            am_args += ["--domain", args.domain]
        if args.scheme:
            am_args += ["--scheme", args.scheme]
        if args.dry_run:
            am_args.append("--dry-run")
        return run_auth_migration(am_args)

    if args.command == "dor-log":
        dl_args: list[str] = []
        if args.event_json:
            dl_args += ["--event-json", args.event_json]
        if args.event_file:
            dl_args += ["--event-file", args.event_file]
        if args.flush_queue:
            dl_args.append("--flush-queue")
        if args.strict:
            dl_args.append("--strict")
        if args.quiet:
            dl_args.append("--quiet")
        return run_dor_log(dl_args)

    if args.command == "secrets":
        sec_cmd = args.secrets_command or "wizard"
        sec_args: list[str] = [sec_cmd]
        if sec_cmd == "submit":
            if args.payload_file:
                sec_args += ["--payload-file", args.payload_file]
            for item in args.set:
                sec_args += ["--set", item]
            if args.secret_id:
                sec_args += ["--secret-id", args.secret_id]
            if args.company_id:
                sec_args += ["--company-id", args.company_id]
            if args.repository_id:
                sec_args += ["--repository-id", args.repository_id]
            if args.prefix:
                sec_args += ["--prefix", args.prefix]
            if args.aws_profile:
                sec_args += ["--aws-profile", args.aws_profile]
            if args.aws_region:
                sec_args += ["--aws-region", args.aws_region]
            if args.create_if_missing:
                sec_args.append("--create-if-missing")
            if args.allow_partial:
                sec_args.append("--allow-partial")
            if args.dry_run:
                sec_args.append("--dry-run")
        if sec_cmd == "template":
            if args.company_id:
                sec_args += ["--company-id", args.company_id]
            if args.repository_id:
                sec_args += ["--repository-id", args.repository_id]
            if args.prefix:
                sec_args += ["--prefix", args.prefix]
            if args.aws_region:
                sec_args += ["--aws-region", args.aws_region]
        if sec_cmd == "wizard":
            if args.company_id:
                sec_args += ["--company-id", args.company_id]
            if args.repository_id:
                sec_args += ["--repository-id", args.repository_id]
            if args.prefix:
                sec_args += ["--prefix", args.prefix]
            if args.aws_profile:
                sec_args += ["--aws-profile", args.aws_profile]
            if args.aws_region:
                sec_args += ["--aws-region", args.aws_region]
            if args.secret_id:
                sec_args += ["--secret-id", args.secret_id]
            if args.copy_from_secret_id:
                sec_args += ["--copy-from-secret-id", args.copy_from_secret_id]
            if args.copy_from_company_id:
                sec_args += ["--copy-from-company-id", args.copy_from_company_id]
            if args.copy_from_repository_id:
                sec_args += ["--copy-from-repository-id", args.copy_from_repository_id]
            if args.copy_from_prefix:
                sec_args += ["--copy-from-prefix", args.copy_from_prefix]
            if args.allow_partial:
                sec_args.append("--allow-partial")
            if args.dry_run:
                sec_args.append("--dry-run")
        return run_secrets_submit(sec_args)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
