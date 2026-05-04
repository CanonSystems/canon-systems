"""Global CLI for canon-systems (`canon`) in any repository."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .actor_report import run as run_actor_report
from .auth_migration import run as run_auth_migration
from .ask_hybrid import run as run_ask
from .capture_session import run as run_capture
from .checkpoint_cli import run as run_checkpoint_cli
from .packet_archive_cli import run as run_packet_archive_cli
from .run_ledger_cli import run as run_run_ledger_cli
from .readiness_cli import run as run_readiness_cli
from .graph_indexer import run as run_graph_cli
from .report_cli import run as run_report_cli
from .resume_engine import run as run_resume_engine
from .stall_watchdog import run as run_stall_watchdog
from .synth_cli import run as run_synth_cli
from .doctor_cli import run as run_doctor
from .dor_log import run as run_dor_log
from .flow_audit import run as run_flow_audit
from .memory_health import run as run_memory_health
from .context_preload import run as run_preflight
from .install_wizard import detect_repo_root, run as run_setup
from .repo_enable import enable_repo, install_user_scope
from . import vault_sync
from .qa_validate import run as run_qa_validate
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


def _global_rewire_state_path() -> Path:
    return Path.home() / ".canon" / "global-rewire-state.json"


def _global_rewire_roots() -> list[Path]:
    raw = os.environ.get("CANON_SYSTEMS_REWIRE_ROOTS", "").strip()
    if raw:
        items = [p for p in raw.split(os.pathsep) if p.strip()]
        return [Path(p).expanduser().resolve() for p in items]
    return [(Path.home() / "localwork").resolve()]


def _iter_wired_repos_under(root: Path, *, max_depth: int) -> list[Path]:
    repos: list[Path] = []
    if not root.exists() or not root.is_dir():
        return repos
    root_parts = len(root.parts)
    for dirpath, dirnames, _filenames in os.walk(root):
        current = Path(dirpath)
        depth = len(current.parts) - root_parts
        if depth > max_depth:
            dirnames[:] = []
            continue
        if (current / ".git").exists() and (current / ".canon" / "memory-layer.local.env").exists():
            repos.append(current)
            dirnames[:] = []
            continue
        # Skip heavyweight folders during scan.
        dirnames[:] = [d for d in dirnames if d not in (".git", ".venv", "node_modules", ".cursor")]
    return repos


def _should_run_global_rewire() -> bool:
    path = _global_rewire_state_path()
    if not path.exists():
        return True
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return True
    if not isinstance(parsed, dict):
        return True
    return str(parsed.get("version", "")).strip() != __version__


def _mark_global_rewire_done() -> None:
    path = _global_rewire_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": __version__}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _split_canon_resume_cli(user_argv: list[str]) -> tuple[str, list[str]] | None:
    """Recognize [--repo-root PATH]* resume [--] <passthrough-tail> and return passthrough argv.

    Top-level argparse cannot reliably forward resume flags beginning with "-" (REMAINDER
    loses them during sub-parser resolution); this detects ``resume`` at the canon CLI boundary
    and forwards the untouched tail directly to ``resume_engine.run``.
    """
    idx = 0
    repo_root = ""
    while idx < len(user_argv):
        tok = user_argv[idx]
        if tok == "--repo-root" and idx + 1 < len(user_argv):
            repo_root = user_argv[idx + 1]
            idx += 2
            continue
        if tok.startswith("--repo-root="):
            repo_root = tok.split("=", 1)[1]
            idx += 1
            continue
        break
    remainder = user_argv[idx:]
    if not remainder or remainder[0] != "resume":
        return None
    resume_tail = list(remainder[1:])
    if resume_tail and resume_tail[0] == "--":
        resume_tail = resume_tail[1:]
    return (repo_root, resume_tail)


def _maybe_auto_rewire_all(command: str) -> None:
    """Auto-refresh all wired repos once per installed canon-systems version."""
    if command in ("setup", "enable-repo"):
        return
    if _truthy_env("CANON_SYSTEMS_DISABLE_AUTO_REWIRE"):
        return
    if not _should_run_global_rewire():
        return

    # Always refresh user-level scope first so ~/.cursor/agents stays current.
    if not _truthy_env("CANON_SYSTEMS_DISABLE_USER_SCOPE_REWIRE"):
        try:
            install_user_scope()
        except Exception as exc:
            print(
                f"canon-systems: user-scope auto-rewire skipped: {exc}",
                file=sys.stderr,
            )

    if _truthy_env("CANON_SYSTEMS_DISABLE_GLOBAL_REWIRE"):
        _mark_global_rewire_done()
        return
    try:
        max_depth = int(os.environ.get("CANON_SYSTEMS_GLOBAL_REWIRE_MAX_DEPTH", "3"))
    except ValueError:
        max_depth = 3
    max_depth = max(1, max_depth)

    touched = 0
    scanned = 0
    for scan_root in _global_rewire_roots():
        for repo in _iter_wired_repos_under(scan_root, max_depth=max_depth):
            scanned += 1
            pinned = _pinned_version(repo)
            if pinned and _version_tuple(__version__) > _version_tuple(pinned):
                try:
                    enable_repo(repo)
                    touched += 1
                except Exception as exc:
                    print(
                        f"canon-systems: global auto-rewire skipped for {repo}: {exc}",
                        file=sys.stderr,
                    )
    _mark_global_rewire_done()
    if touched:
        print(
            f"canon-systems: auto-refreshed wiring in {touched} repo(s) (scanned {scanned}).",
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

    en = sub.add_parser("enable-repo", help="Install Cursor hooks + subagents + rule in current repo.")
    en.add_argument(
        "--install-vault-sync",
        action="store_true",
        help="Also install the OS-appropriate `canon vault sync` service (requires tenant scope in env/flags).",
    )
    en.add_argument("--company-id", default="")
    en.add_argument("--repository-id", default="")
    en.add_argument("--plan-id", default="")
    en.add_argument("--bucket", default="")
    en.add_argument("--prefix", default="")
    en.add_argument("--vault-target-dir", default="")
    en.add_argument("--interval-seconds", type=int, default=10)

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

    e2e_p = sub.add_parser(
        "e2e-check",
        help="Plug-and-play validation: Cursor wiring + required memory backends (one JSON report).",
    )
    e2e_p.add_argument(
        "--agent",
        action="store_true",
        dest="e2e_agent",
        help="Wrap JSON with <<<CANON_E2E_VERDICT>>> for agent parsing.",
    )

    doc_p = sub.add_parser(
        "doctor",
        help="Diagnose wiring: tenant vs context, AWS secret cache, raw IPv4 URLs in env files.",
    )
    doc_p.add_argument(
        "--fix-cache",
        action="store_true",
        help="Delete the AWS Secrets Manager client cache so the next command refetches JSON.",
    )
    doc_p.add_argument(
        "--json",
        action="store_true",
        dest="doctor_json",
        help="Print JSON report.",
    )
    doc_p.add_argument(
        "--curl-resolve-snippet",
        action="store_true",
        dest="doctor_curl_resolve_snippet",
        help=(
            "Print a curl line with --resolve for KNOWLEDGE_API_URL /healthz (WARP / split DNS)."
        ),
    )

    qv = sub.add_parser(
        "qa-validate",
        help="Validate persisted qa-gate packet artifacts for merge gating.",
    )
    qv.add_argument("--file", required=True)
    qv.add_argument("--require-pass", action="store_true")
    qv.add_argument("--handoff-id", default="")
    qv.add_argument("--task-id", default="")
    qv.add_argument("--require-dor-telemetry", action="store_true")
    qv.add_argument(
        "--require-checkpoints",
        action="store_true",
        help="Require valid per-phase checkpoint JSON (needs --handoff-id and --task-id).",
    )

    fa = sub.add_parser(
        "flow-audit",
        help="Audit per-task agent flow artifacts and plan tracking.",
    )
    fa.add_argument("--handoff-id", required=True)
    fa.add_argument("--task-id", required=True)
    fa.add_argument("--plan-file", default="")
    fa.add_argument("--sample-rate", type=float, default=1.0)
    fa.add_argument("--require-release-status", action="store_true")
    fa.add_argument("--require-memory-health", action="store_true")
    fa.add_argument(
        "--require-checkpoints",
        action="store_true",
        help="Require per-phase checkpoint JSON under checkpoints/ (all five agent phases).",
    )
    fa.add_argument(
        "--require-deploy-attestation",
        action="store_true",
        help="Require deployment-smoke.json (branch/deploy proof) under the task handoff directory.",
    )

    mh = sub.add_parser(
        "memory-health",
        help="Probe memory backend /healthz endpoints and emit a JSON health report.",
    )
    mh.add_argument(
        "--required",
        default=None,
        metavar="CSV",
        help="Comma-separated required backends (overrides CANON_MEMORY_HEALTH_REQUIRED).",
    )
    mh.add_argument(
        "--timeout-ms",
        type=int,
        default=None,
        help="Per-backend probe budget in ms (default 2000; max 60000).",
    )
    mh.add_argument(
        "--json",
        action="store_true",
        help="JSON output (default; idempotent).",
    )
    mh.add_argument("--output", default="", metavar="PATH", help="Also write the JSON report to this path.")
    mh.add_argument("--verbose", action="store_true", help="Log probe details to stderr.")

    ck = sub.add_parser(
        "checkpoint",
        help="Checkpoint + lease CLI over the state-api wire protocol.",
        description=(
            "Subcommands: read, write, lease-acquire, lease-renew, lease-release. "
            "Run `canon checkpoint <subcommand> --help` (arguments re-parsed in checkpoint_cli)."
        ),
    )
    ck.add_argument(
        "checkpoint_tail",
        nargs=argparse.REMAINDER,
        default=[],
        help=argparse.SUPPRESS,
    )

    pa = sub.add_parser(
        "packet-archive",
        help="Archive a packet/evidence file to S3 via state-api (POST /state/archive).",
        description=(
            "Copies an explicit file to the tenant artifact bucket while preserving required "
            "local ``.cursor/handoffs/...`` packets. Use ``--dry-run`` for no-network resolution."
        ),
    )
    pa.add_argument("--file", default="", help="Path to packet or evidence file.")
    pa.add_argument("--body-file", default="")
    pa.add_argument("--company-id", required=True)
    pa.add_argument("--repository-id", required=True)
    pa.add_argument("--plan-id", required=True)
    pa.add_argument("--task-id", required=True)
    pa.add_argument("--workstream-id", required=True)
    pa.add_argument("--handoff-id", required=True)
    pa.add_argument("--phase", required=True)
    pa.add_argument("--artifact-kind", required=True)
    pa.add_argument("--source-label", default="")
    pa.add_argument("--content-type", default="")
    pa.add_argument("--evidence-subtype", default="")
    pa.add_argument("--agent-run-id", default="")
    pa.add_argument("--actor-id", default="")
    pa.add_argument("--outcome", default="")
    pa.add_argument("--status", default="")
    pa.add_argument("--dry-run", action="store_true")
    pa.add_argument("--dry-run-bucket", default="")
    pa.add_argument("--dry-run-prefix", default="")
    pa.add_argument("--state-api-url", default="")
    pa.add_argument("--timeout-seconds", type=float, default=60.0)
    pa.add_argument("--quiet", action="store_true")

    rl = sub.add_parser(
        "run-ledger",
        help="Validate / merge archive refs into a run-ledger record; dry-run or PUT to state-api.",
        description=(
            "Load a ledger record JSON, optionally merge archive metadata snapshots into "
            "``archive_refs`` (by reference only). Use ``--dry-run`` for no network I/O."
        ),
    )
    rlsrc = rl.add_mutually_exclusive_group(required=True)
    rlsrc.add_argument("--record-file", default="", metavar="PATH")
    rlsrc.add_argument("--record-json", default="", metavar="JSON")
    rl.add_argument("--merge-archive-json", default="", metavar="PATH")
    rl.add_argument("--dry-run", action="store_true")
    rl.add_argument("--state-api-url", default="")
    rl.add_argument("--timeout-seconds", type=float, default=60.0)
    rl.add_argument("--quiet", action="store_true")

    rd = sub.add_parser(
        "readiness",
        help="Run-ledger-backed readiness snapshot (GET /state/run-ledger; read-only).",
    )
    rd_sub = rd.add_subparsers(dest="readiness_command", required=True)
    rd_check = rd_sub.add_parser(
        "check",
        help="Emit readiness JSON from scoped run-ledger query.",
    )
    rd_check.add_argument("--company-id", required=True, dest="readiness_company_id")
    rd_check.add_argument("--repository-id", required=True, dest="readiness_repository_id")
    rd_check.add_argument("--plan-id", required=True, dest="readiness_plan_id")
    rd_check.add_argument("--task-id", required=True, dest="readiness_task_id")
    rd_check.add_argument("--workstream-id", required=True, dest="readiness_workstream_id")
    rd_check.add_argument("--handoff-id", required=True, dest="readiness_handoff_id")
    rd_check.add_argument("--ledger-run-id", default="", dest="readiness_ledger_run_id")
    rd_check.add_argument("--state-api-url", default="", dest="readiness_state_api_url")
    rd_check.add_argument("--limit", type=int, default=50, dest="readiness_limit")
    rd_check.add_argument("--output", default="", dest="readiness_output")
    rd_check.add_argument("--timeout-seconds", type=float, default=60.0, dest="readiness_timeout_seconds")
    rd_check.add_argument("--quiet", action="store_true", dest="readiness_quiet")

    graph_parser = sub.add_parser("graph", help="Graph retrieval plane CLI")
    graph_parser.add_argument("args", nargs=argparse.REMAINDER)

    report_parser = sub.add_parser("report", help="Retrieval-telemetry rollups (stub; Wave 6 polishes)")
    report_parser.add_argument("args", nargs=argparse.REMAINDER)

    resume_parser = sub.add_parser("resume", help="Orchestrator resume engine (read-only)")
    resume_parser.add_argument("args", nargs=argparse.REMAINDER)

    stall_watchdog_parser = sub.add_parser(
        "stall-watchdog",
        help="Scan for stalled leases and emit lease_stall_detected events (read-only).",
    )
    stall_watchdog_parser.add_argument("args", nargs=argparse.REMAINDER)

    vault_parser = sub.add_parser("vault", help="Read-only in-repo S3 → vault/ mirror and related helpers.")
    vault_parser.add_argument("args", nargs=argparse.REMAINDER)

    synth_parser = sub.add_parser(
        "synth",
        help="Synthesis vault publishing driver (internal; subcommands: publish).",
    )
    synth_parser.add_argument("args", nargs=argparse.REMAINDER)

    release_parser = sub.add_parser(
        "release",
        help="Release lifecycle helpers (auto-publish on RELEASE_STATUS PASS).",
    )
    release_parser.add_argument("args", nargs=argparse.REMAINDER)

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

    argv_for_exec = list(sys.argv) if argv is None else [sys.argv[0]] + list(argv)
    user_argv = sys.argv[1:] if argv is None else list(argv)

    resume_cli = _split_canon_resume_cli(user_argv)
    if resume_cli is not None:
        rr, resume_argv_tail = resume_cli
        root = detect_repo_root(rr)
        os.environ["CANON_SYSTEMS_REPO_ROOT"] = str(root)
        os.environ.setdefault("CANON_MEMORY_LAYER_REPO_ROOT", str(root))
        from .self_update import try_self_update

        try_self_update(argv_for_exec)
        _maybe_auto_rewire(root, "resume")
        _maybe_auto_rewire_all("resume")
        return run_resume_engine(resume_argv_tail)

    args = parser.parse_args(argv)
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
    _maybe_auto_rewire_all(args.command)

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
        vtd = getattr(args, "vault_target_dir", "") or ""
        enable_repo(
            root,
            install_vault_sync=bool(getattr(args, "install_vault_sync", False)),
            company_id=str(getattr(args, "company_id", "") or "").strip() or None,
            repository_id=str(getattr(args, "repository_id", "") or "").strip() or None,
            plan_id=str(getattr(args, "plan_id", "") or "").strip() or None,
            bucket=str(getattr(args, "bucket", "") or "").strip() or None,
            prefix=str(getattr(args, "prefix", "") or "").strip() or None,
            vault_target_dir=vtd if vtd.strip() else None,
            interval_seconds=int(getattr(args, "interval_seconds", 10) or 10),
        )
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

    if args.command == "qa-validate":
        qv_args: list[str] = ["--file", args.file]
        if args.require_pass:
            qv_args.append("--require-pass")
        if args.handoff_id:
            qv_args += ["--handoff-id", args.handoff_id]
        if args.task_id:
            qv_args += ["--task-id", args.task_id]
        if args.require_dor_telemetry:
            qv_args.append("--require-dor-telemetry")
        if getattr(args, "require_checkpoints", False):
            qv_args.append("--require-checkpoints")
        return run_qa_validate(qv_args)

    if args.command == "flow-audit":
        fa_args: list[str] = [
            "--handoff-id",
            args.handoff_id,
            "--task-id",
            args.task_id,
            "--sample-rate",
            str(args.sample_rate),
        ]
        if args.plan_file:
            fa_args += ["--plan-file", args.plan_file]
        if args.require_release_status:
            fa_args.append("--require-release-status")
        if args.require_memory_health:
            fa_args.append("--require-memory-health")
        if getattr(args, "require_checkpoints", False):
            fa_args.append("--require-checkpoints")
        if args.require_deploy_attestation:
            fa_args.append("--require-deploy-attestation")
        return run_flow_audit(fa_args)

    if args.command == "e2e-check":
        from .e2e_check import run as run_e2e_check

        e2e_argv = ["--agent"] if getattr(args, "e2e_agent", False) else []
        return run_e2e_check(e2e_argv)

    if args.command == "doctor":
        d_args: list[str] = []
        if getattr(args, "fix_cache", False):
            d_args.append("--fix-cache")
        if getattr(args, "doctor_json", False):
            d_args.append("--json")
        if getattr(args, "doctor_curl_resolve_snippet", False):
            d_args.append("--curl-resolve-snippet")
        return run_doctor(d_args)

    if args.command == "memory-health":
        mh_args: list[str] = []
        if args.required is not None:
            mh_args += ["--required", args.required]
        if args.timeout_ms is not None:
            mh_args += ["--timeout-ms", str(args.timeout_ms)]
        if args.json:
            mh_args.append("--json")
        if args.output:
            mh_args += ["--output", args.output]
        if args.verbose:
            mh_args.append("--verbose")
        return run_memory_health(mh_args)

    if args.command == "checkpoint":
        return run_checkpoint_cli(list(getattr(args, "checkpoint_tail", [])))

    if args.command == "packet-archive":
        pa_args: list[str] = []
        if getattr(args, "file", ""):
            pa_args += ["--file", args.file]
        if getattr(args, "body_file", ""):
            pa_args += ["--body-file", args.body_file]
        for fld in (
            "company_id",
            "repository_id",
            "plan_id",
            "task_id",
            "workstream_id",
            "handoff_id",
            "phase",
            "artifact_kind",
            "source_label",
            "content_type",
            "evidence_subtype",
            "agent_run_id",
            "actor_id",
            "outcome",
            "status",
            "dry_run_bucket",
            "dry_run_prefix",
            "state_api_url",
        ):
            v = getattr(args, fld, "") or ""
            if isinstance(v, bool):
                continue
            if v:
                pa_args += [f"--{fld.replace('_', '-')}", str(v)]
        if getattr(args, "dry_run", False):
            pa_args.append("--dry-run")
        if getattr(args, "quiet", False):
            pa_args.append("--quiet")
        ts = getattr(args, "timeout_seconds", None)
        if ts is not None and ts != 60.0:
            pa_args += ["--timeout-seconds", str(ts)]
        return run_packet_archive_cli(pa_args)

    if args.command == "run-ledger":
        rl_args: list[str] = []
        if getattr(args, "record_file", ""):
            rl_args += ["--record-file", args.record_file]
        if getattr(args, "record_json", ""):
            rl_args += ["--record-json", args.record_json]
        maj = getattr(args, "merge_archive_json", "") or ""
        if maj:
            rl_args += ["--merge-archive-json", maj]
        if getattr(args, "dry_run", False):
            rl_args.append("--dry-run")
        surl = getattr(args, "state_api_url", "") or ""
        if surl:
            rl_args += ["--state-api-url", surl]
        ts_rl = getattr(args, "timeout_seconds", None)
        if ts_rl is not None and ts_rl != 60.0:
            rl_args += ["--timeout-seconds", str(ts_rl)]
        if getattr(args, "quiet", False):
            rl_args.append("--quiet")
        return run_run_ledger_cli(rl_args)

    if args.command == "readiness":
        rc: list[str] = ["check"]
        rc += ["--company-id", getattr(args, "readiness_company_id", "")]
        rc += ["--repository-id", getattr(args, "readiness_repository_id", "")]
        rc += ["--plan-id", getattr(args, "readiness_plan_id", "")]
        rc += ["--task-id", getattr(args, "readiness_task_id", "")]
        rc += ["--workstream-id", getattr(args, "readiness_workstream_id", "")]
        rc += ["--handoff-id", getattr(args, "readiness_handoff_id", "")]
        rlr = str(getattr(args, "readiness_ledger_run_id", "") or "").strip()
        if rlr:
            rc += ["--ledger-run-id", rlr]
        rsu = str(getattr(args, "readiness_state_api_url", "") or "").strip()
        if rsu:
            rc += ["--state-api-url", rsu]
        rlim = getattr(args, "readiness_limit", 50)
        if rlim != 50:
            rc += ["--limit", str(rlim)]
        rout = str(getattr(args, "readiness_output", "") or "").strip()
        if rout:
            rc += ["--output", rout]
        rts = getattr(args, "readiness_timeout_seconds", 60.0)
        if rts != 60.0:
            rc += ["--timeout-seconds", str(rts)]
        if getattr(args, "readiness_quiet", False):
            rc.append("--quiet")
        return run_readiness_cli(rc)

    if args.command == "graph":
        return run_graph_cli(list(getattr(args, "args", [])))

    if args.command == "report":
        return run_report_cli(list(getattr(args, "args", [])))

    if args.command == "resume":
        return run_resume_engine(list(getattr(args, "args", [])))

    if args.command == "stall-watchdog":
        return run_stall_watchdog(list(getattr(args, "args", [])))

    if args.command == "vault":
        return vault_sync.run(list(getattr(args, "args", [])))

    if args.command == "synth":
        return run_synth_cli(list(getattr(args, "args", [])))

    if args.command == "release":
        from . import release_publish

        return release_publish.run(list(getattr(args, "args", [])))

    if args.command == "secrets":
        sec_cmd = args.secrets_command or "wizard"
        sec_args: list[str] = [sec_cmd]
        payload_file = getattr(args, "payload_file", "")
        set_items = getattr(args, "set", [])
        secret_id = getattr(args, "secret_id", "")
        company_id = getattr(args, "company_id", "")
        repository_id = getattr(args, "repository_id", "")
        prefix = getattr(args, "prefix", "")
        aws_profile = getattr(args, "aws_profile", "")
        aws_region = getattr(args, "aws_region", "")
        create_if_missing = bool(getattr(args, "create_if_missing", False))
        allow_partial = bool(getattr(args, "allow_partial", False))
        dry_run = bool(getattr(args, "dry_run", False))
        copy_from_secret_id = getattr(args, "copy_from_secret_id", "")
        copy_from_company_id = getattr(args, "copy_from_company_id", "")
        copy_from_repository_id = getattr(args, "copy_from_repository_id", "")
        copy_from_prefix = getattr(args, "copy_from_prefix", "")
        if sec_cmd == "submit":
            if payload_file:
                sec_args += ["--payload-file", payload_file]
            for item in set_items:
                sec_args += ["--set", item]
            if secret_id:
                sec_args += ["--secret-id", secret_id]
            if company_id:
                sec_args += ["--company-id", company_id]
            if repository_id:
                sec_args += ["--repository-id", repository_id]
            if prefix:
                sec_args += ["--prefix", prefix]
            if aws_profile:
                sec_args += ["--aws-profile", aws_profile]
            if aws_region:
                sec_args += ["--aws-region", aws_region]
            if create_if_missing:
                sec_args.append("--create-if-missing")
            if allow_partial:
                sec_args.append("--allow-partial")
            if dry_run:
                sec_args.append("--dry-run")
        if sec_cmd == "template":
            if company_id:
                sec_args += ["--company-id", company_id]
            if repository_id:
                sec_args += ["--repository-id", repository_id]
            if prefix:
                sec_args += ["--prefix", prefix]
            if aws_region:
                sec_args += ["--aws-region", aws_region]
        if sec_cmd == "wizard":
            if company_id:
                sec_args += ["--company-id", company_id]
            if repository_id:
                sec_args += ["--repository-id", repository_id]
            if prefix:
                sec_args += ["--prefix", prefix]
            if aws_profile:
                sec_args += ["--aws-profile", aws_profile]
            if aws_region:
                sec_args += ["--aws-region", aws_region]
            if secret_id:
                sec_args += ["--secret-id", secret_id]
            if copy_from_secret_id:
                sec_args += ["--copy-from-secret-id", copy_from_secret_id]
            if copy_from_company_id:
                sec_args += ["--copy-from-company-id", copy_from_company_id]
            if copy_from_repository_id:
                sec_args += ["--copy-from-repository-id", copy_from_repository_id]
            if copy_from_prefix:
                sec_args += ["--copy-from-prefix", copy_from_prefix]
            if allow_partial:
                sec_args.append("--allow-partial")
            if dry_run:
                sec_args.append("--dry-run")
        return run_secrets_submit(sec_args)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
