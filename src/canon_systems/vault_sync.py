"""`canon vault sync`: read-only S3 → <repo>/vault/ mirror (one-shot or loop) + service install."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError

from canon_backend_shared.events import CanonicalEvent

from .stall_watchdog import _emit_event
from .synth_show_reader import AccessDenied, NotFound, SynthShowReader

VAULT_EXIT_OK = 0
VAULT_EXIT_USAGE = 2
VAULT_EXIT_SYNC = 3
VAULT_EXIT_CONFIG = 4
VAULT_EXIT_TRANSPORT = 5

_sleep: Callable[[float], None] = time.sleep
_run_subprocess: Callable[..., Any] = subprocess.run


def _s3_client_factory(aws_region: str, aws_profile: str) -> Any:
    import boto3  # lazy; tests may monkeypatch this

    session = boto3.Session(
        profile_name=aws_profile or None,
        region_name=aws_region or None,
    )
    return session.client("s3")


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _find_git_root(start: Path) -> Path | None:
    cur = start.resolve()
    for p in (cur, *list(cur.parents)):
        if (p / ".git").exists():
            return p
    return None


def _derive_target_dir(s: str | None) -> Path | None:
    if s and str(s).strip():
        return Path(str(s).strip()).expanduser().resolve()
    gr = _find_git_root(Path.cwd())
    if not gr:
        return None
    return (gr / "vault").resolve()


def _env_first(flag: str | None, env: str) -> str | None:
    raw = (flag or "").strip() if flag is not None else ""
    if raw:
        return raw
    v = os.environ.get(env, "").strip()
    return v or None


def _resolve_required(args: argparse.Namespace) -> dict[str, str]:
    out = {
        "plan_id": _env_first(getattr(args, "plan_id", None), "CANON_PLAN_ID") or "",
        "company_id": _env_first(getattr(args, "company_id", None), "CANON_COMPANY_ID") or "",
        "repository_id": _env_first(getattr(args, "repository_id", None), "CANON_REPOSITORY_ID") or "",
        "bucket": _env_first(getattr(args, "bucket", None), "CANON_VAULT_BUCKET") or "",
        "prefix": _env_first(getattr(args, "prefix", None), "CANON_VAULT_PREFIX") or "",
    }
    for key, fl, ev in (
        ("plan_id", "--plan-id", "CANON_PLAN_ID"),
        ("company_id", "--company-id", "CANON_COMPANY_ID"),
        ("repository_id", "--repository-id", "CANON_REPOSITORY_ID"),
        ("bucket", "--bucket", "CANON_VAULT_BUCKET"),
        ("prefix", "--prefix", "CANON_VAULT_PREFIX"),
    ):
        if not out[key]:
            raise ValueError(f"missing required: {key} (set {fl} or {ev})")
    return {k: str(out[k]) for k in out}


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _iter_local_files(root: Path) -> Iterator[Path]:
    if not root.exists():
        return
    for p in root.rglob("*"):
        if p.is_file():
            yield p


def _rel_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _prune_empty_after_delete(deleted_file: Path, troot: Path) -> None:
    t2 = troot.resolve()
    d = deleted_file.parent
    while d != t2 and t2 in d.parents:
        if not d.is_dir() or not d.exists():
            break
        try:
            if any(d.iterdir()):
                break
        except OSError:
            break
        parent = d.parent
        try:
            d.rmdir()
        except OSError:
            break
        d = parent


def _short_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def _load_template(name: str) -> str:
    mod = importlib.import_module("canon_systems")
    base = Path(mod.__file__).resolve().parent / "templates" / "vault-sync" / name
    return base.read_text(encoding="utf-8")


def _sync_once(reader: SynthShowReader, target_dir: Path, *, dry_run: bool) -> dict[str, int]:
    """HEAD content-hash (lowercase) vs local SHA-256; missing metadata always pulls."""
    try:
        remote_rels = reader.list_pages()
    except EndpointConnectionError:
        raise
    except BotoCoreError as e:
        if type(e) is EndpointConnectionError:
            raise
        raise
    rset = {r for r in remote_rels if r and not r.endswith("/")}

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    local_rels: set[str] = set()
    if target_dir.exists():
        for f in _iter_local_files(target_dir):
            local_rels.add(_rel_posix(f, target_dir))

    deleted_count = 0
    troot = target_dir.resolve()
    for rel in sorted(local_rels - rset):
        lp = (target_dir / rel).resolve()
        if not str(lp).startswith(str(troot)):
            continue
        if dry_run:
            deleted_count += 1
            continue
        if lp.is_file():
            lp.unlink()
            deleted_count += 1
            _prune_empty_after_delete(lp, troot)

    pulled_count = 0
    skipped_count = 0
    pulled_bytes = 0

    for rel in sorted(rset):
        loc = target_dir / rel
        try:
            h_remote = reader.head_hash(rel)
        except EndpointConnectionError:
            raise
        except (AccessDenied, BotoCoreError) as e:
            if isinstance(e, EndpointConnectionError):
                raise
            raise
        on_disk = loc.is_file()
        h_local = _file_sha256(loc) if on_disk else ""
        if h_remote and on_disk and h_local == h_remote:
            skipped_count += 1
            continue
        if dry_run:
            try:
                b = reader.read_page(rel)
            except NotFound:
                continue
            except EndpointConnectionError:
                raise
            except (AccessDenied, BotoCoreError) as e:
                if isinstance(e, EndpointConnectionError):
                    raise
                raise
            pulled_count += 1
            pulled_bytes += len(b)
            continue
        b = reader.read_page(rel)
        loc.parent.mkdir(parents=True, exist_ok=True)
        loc.write_bytes(b)
        pulled_count += 1
        pulled_bytes += len(b)

    return {
        "pulled_count": pulled_count,
        "deleted_count": deleted_count,
        "skipped_count": skipped_count,
        "pulled_bytes": pulled_bytes,
    }


def _build_vault_event(
    *, company_id: str, repository_id: str, plan_id: str, payload: dict[str, Any]
) -> CanonicalEvent:
    return CanonicalEvent(
        schema_version=1,
        event_id="ev-vault-" + uuid.uuid4().hex,
        parent_event_id="",
        event_type="vault_sync",
        company_id=company_id,
        repository_id=repository_id,
        plan_id=plan_id,
        task_id="",
        handoff_id="",
        agent_name="canon-vault-sync",
        agent_run_id="run-vault-" + uuid.uuid4().hex[:16],
        actor_id="",
        model="",
        timestamp=_utc_ts(),
        state_version=0,
        payload=payload,
    )


def _default_event_log() -> Path:
    root = Path(os.environ.get("CANON_SYSTEMS_REPO_ROOT", str(Path.cwd()))).resolve()
    return (root / ".canon" / "memory" / "events.ndjson").resolve()


def _emit_vault_sync_event(
    event: CanonicalEvent, *, event_log: Path | None, dry_run: bool
) -> None:
    el: Path | None = event_log
    if not dry_run and el is None:
        el = _default_event_log()
    _emit_event(event, event_log=el, dry_run=dry_run)


def _err_usage(detail: str) -> int:
    sys.stderr.write(
        json.dumps({"error": "usage", "detail": detail}, sort_keys=True) + "\n"
    )
    return VAULT_EXIT_USAGE


def _err_transport(detail: str) -> int:
    sys.stderr.write(
        json.dumps({"error": "transport", "detail": detail}, sort_keys=True) + "\n"
    )
    return VAULT_EXIT_TRANSPORT


def _build_install_event(
    *, company_id: str, repository_id: str, plan_id: str, status: str
) -> CanonicalEvent:
    return CanonicalEvent(
        schema_version=1,
        event_id="ev-vault-install-" + uuid.uuid4().hex,
        parent_event_id="",
        event_type="vault_sync_install",
        company_id=company_id,
        repository_id=repository_id,
        plan_id=plan_id,
        task_id="",
        handoff_id="",
        agent_name="canon-vault-sync-install",
        agent_run_id="run-" + uuid.uuid4().hex[:16],
        actor_id="",
        model="",
        timestamp=_utc_ts(),
        state_version=0,
        payload={"status": status},
    )


def _render_launchd_plist(
    *,
    ch: str,
    rh: str,
    canon_bin: str,
    interval_seconds: int,
    company_id: str,
    repository_id: str,
    plan_id: str,
    bucket: str,
    prefix: str,
    target_dir: Path,
    log_out: str,
    log_err: str,
) -> str:
    raw = _load_template("launchd.plist.tmpl")
    rep: dict[str, str] = {
        "COMPANY_SHORTHASH": ch,
        "REPO_SHORTHASH": rh,
        "CANON_BIN": canon_bin,
        "INTERVAL_SECONDS": str(int(interval_seconds)),
        "COMPANY_ID": company_id,
        "REPOSITORY_ID": repository_id,
        "PLAN_ID": plan_id,
        "BUCKET": bucket,
        "PREFIX": prefix,
        "TARGET_DIR": str(target_dir),
        "LOG_OUT": log_out,
        "LOG_ERR": log_err,
    }
    for k, v in rep.items():
        raw = raw.replace("{" + k + "}", v)
    return raw


def _render_systemd_unit(
    *,
    ch: str,
    rh: str,
    canon_bin: str,
    interval_seconds: int,
    company_id: str,
    repository_id: str,
    plan_id: str,
    bucket: str,
    prefix: str,
    target_dir: Path,
) -> str:
    raw = _load_template("systemd.service.tmpl")
    rep: dict[str, str] = {
        "COMPANY_SHORTHASH": ch,
        "REPO_SHORTHASH": rh,
        "CANON_BIN": canon_bin,
        "INTERVAL_SECONDS": str(int(interval_seconds)),
        "COMPANY_ID": company_id,
        "REPOSITORY_ID": repository_id,
        "PLAN_ID": plan_id,
        "BUCKET": bucket,
        "PREFIX": prefix,
        "TARGET_DIR": str(target_dir),
    }
    for k, v in rep.items():
        raw = raw.replace("{" + k + "}", v)
    return raw


def _render_schtasks_xml(
    *,
    ch: str,
    rh: str,
    canon_bin: str,
    interval_seconds: int,
    company_id: str,
    repository_id: str,
    plan_id: str,
    bucket: str,
    prefix: str,
    target_dir: Path,
) -> str:
    raw = _load_template("schtasks.xml.tmpl")
    tdir = str(target_dir)
    rep: dict[str, str] = {
        "COMPANY_SHORTHASH": ch,
        "REPO_SHORTHASH": rh,
        "CANON_BIN": canon_bin,
        "INTERVAL_SECONDS": str(int(interval_seconds)),
        "COMPANY_ID": company_id,
        "REPOSITORY_ID": repository_id,
        "PLAN_ID": plan_id,
        "BUCKET": bucket,
        "PREFIX": prefix,
        "TARGET_DIR": tdir,
    }
    for k, v in rep.items():
        raw = raw.replace("{" + k + "}", v)
    return raw


def _resolve_canon_bin() -> str:
    c = os.environ.get("CANON_VAULT_CANON_BIN", "").strip()
    if c:
        return c
    w = shutil.which("canon")
    if w:
        return w
    return sys.executable


def _install_launchd(
    *,
    plist_body: str,
    ch: str,
    rh: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    event_log: Path | None,
    dry_run: bool,
) -> None:
    name = f"systems.canon.vault-sync.{ch}-{rh}.plist"
    dest = Path.home() / "Library" / "LaunchAgents" / name
    need_write = (not dest.exists()) or dest.read_text(encoding="utf-8") != plist_body
    if need_write:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(plist_body, encoding="utf-8")
    st = "written" if need_write else "unchanged"
    _emit_vault_sync_event(
        _build_install_event(
            company_id=company_id, repository_id=repository_id, plan_id=plan_id, status=st
        ),
        event_log=event_log,
        dry_run=dry_run,
    )


def _install_systemd(
    *,
    unit_body: str,
    name: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    event_log: Path | None,
    dry_run: bool,
) -> None:
    dest = Path.home() / ".config" / "systemd" / "user" / name
    need_write = (not dest.exists()) or dest.read_text(encoding="utf-8") != unit_body
    if need_write:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(unit_body, encoding="utf-8")
    st = "written" if need_write else "unchanged"
    _emit_vault_sync_event(
        _build_install_event(
            company_id=company_id, repository_id=repository_id, plan_id=plan_id, status=st
        ),
        event_log=event_log,
        dry_run=dry_run,
    )


def _install_schtasks(
    *,
    xml_body: str,
    task_name: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    event_log: Path | None,
    dry_run: bool,
) -> None:
    side = Path.home() / ".canon" / f"vault-schtasks-{task_name}.last.xml"
    same = side.exists() and side.read_text(encoding="utf-8") == xml_body
    st = "unchanged" if same else "written"
    if not same:
        side.parent.mkdir(parents=True, exist_ok=True)
        tmp = side.with_suffix(".new.xml")
        tmp.write_text(xml_body, encoding="utf-8")
        tmp.replace(side)
        _run_subprocess(
            [
                "schtasks",
                "/Create",
                "/TN",
                f"canon\\vault-sync\\{task_name}",
                "/XML",
                str(side),
                "/F",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    _emit_vault_sync_event(
        _build_install_event(
            company_id=company_id, repository_id=repository_id, plan_id=plan_id, status=st
        ),
        event_log=event_log,
        dry_run=dry_run,
    )


def install_service(
    *,
    company_id: str,
    repository_id: str,
    plan_id: str,
    bucket: str,
    prefix: str,
    target_dir: Path,
    interval_seconds: int = 10,
    aws_region: str = "",
    aws_profile: str = "",
    event_log: Path | None = None,
    dry_run: bool = False,
) -> None:
    ch = _short_hash(company_id)
    rh = _short_hash(repository_id)
    _ = aws_region, aws_profile
    canon = _resolve_canon_bin()
    tdir = target_dir.expanduser().resolve()
    sysname = platform.system()
    if sysname == "Darwin":
        logd = str(Path.home() / "Library" / "Logs" / f"canon-vault-sync-{ch}-{rh}.out.log")
        loge = str(Path.home() / "Library" / "Logs" / f"canon-vault-sync-{ch}-{rh}.err.log")
        pl = _render_launchd_plist(
            ch=ch,
            rh=rh,
            canon_bin=canon,
            interval_seconds=interval_seconds,
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            bucket=bucket,
            prefix=prefix,
            target_dir=tdir,
            log_out=logd,
            log_err=loge,
        )
        _install_launchd(
            plist_body=pl,
            ch=ch,
            rh=rh,
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            event_log=event_log,
            dry_run=dry_run,
        )
    elif sysname == "Linux":
        un = f"canon-vault-sync-{ch}-{rh}.service"
        unit = _render_systemd_unit(
            ch=ch,
            rh=rh,
            canon_bin=canon,
            interval_seconds=interval_seconds,
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            bucket=bucket,
            prefix=prefix,
            target_dir=tdir,
        )
        _install_systemd(
            unit_body=unit,
            name=un,
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            event_log=event_log,
            dry_run=dry_run,
        )
    elif sysname == "Windows":
        xml = _render_schtasks_xml(
            ch=ch,
            rh=rh,
            canon_bin=canon,
            interval_seconds=interval_seconds,
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            bucket=bucket,
            prefix=prefix,
            target_dir=tdir,
        )
        _install_schtasks(
            xml_body=xml,
            task_name=f"{ch}-{rh}",
            company_id=company_id,
            repository_id=repository_id,
            plan_id=plan_id,
            event_log=event_log,
            dry_run=dry_run,
        )
    else:
        raise OSError("unsupported platform for install_service")


def _tick(
    s3: Any,
    bucket: str,
    pfx: str,
    target_dir: Path,
    req: dict[str, str],
    event_log: Path | None,
    dry_run: bool,
) -> dict[str, Any]:
    reader = SynthShowReader(bucket=bucket, prefix=pfx, s3_client=s3)
    err_kind: str | None = None
    em: str | None = None
    try:
        st = _sync_once(reader, target_dir, dry_run=dry_run)
    except EndpointConnectionError as e:
        em = str(e)
        err_kind = "transport"
    except BotoCoreError as e:  # noqa: B904
        em = str(e)
        err_kind = "boto"
    except AccessDenied as e:
        em = str(e)
        err_kind = "other"
    except NotFound as e:
        em = str(e)
        err_kind = "other"
    except ClientError as e:
        em = str(e)
        err_kind = "other"
    else:
        pld0 = {
            "result": "ok",
            "pulled_bytes": st["pulled_bytes"],
            "pulled_count": st["pulled_count"],
            "deleted_count": st["deleted_count"],
            "skipped_count": st["skipped_count"],
            "plan_id": req["plan_id"],
        }
        ev = _build_vault_event(
            company_id=req["company_id"],
            repository_id=req["repository_id"],
            plan_id=req["plan_id"],
            payload=pld0,
        )
        _emit_vault_sync_event(ev, event_log=event_log, dry_run=dry_run)
        return pld0

    pld1 = {
        "result": "error",
        "pulled_bytes": 0,
        "pulled_count": 0,
        "deleted_count": 0,
        "skipped_count": 0,
        "error_message": em or "error",
        "plan_id": req["plan_id"],
    }
    if err_kind:
        pld1["error_kind"] = err_kind
    ev2 = _build_vault_event(
        company_id=req["company_id"],
        repository_id=req["repository_id"],
        plan_id=req["plan_id"],
        payload=pld1,
    )
    _emit_vault_sync_event(ev2, event_log=event_log, dry_run=dry_run)
    return pld1


def _run_loop(
    s3: Any,
    target_dir: Path,
    req: dict[str, str],
    bucket: str,
    pfx: str,
    elog: Path | None,
    dry_run: bool,
    interval: float,
) -> int:
    base_backoff = 1.0
    fail = 0
    ticks = 0
    while True:
        ticks += 1
        p = _tick(s3, bucket, pfx, target_dir, req, elog, dry_run)
        mx = os.environ.get("CANON_VAULT_SYNC_MAX_TICKS", "").strip()
        if mx.isdigit() and ticks >= int(mx):
            return VAULT_EXIT_OK
        if p.get("result") == "ok":
            fail = 0
            _sleep(float(interval))
        else:
            fail += 1
            _sleep(min(base_backoff * (2 ** (fail - 1)), 60.0))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon vault sync",
        description="Read-only S3 → local vault/ mirror (tenant prefix; no S3 writes).",
    )
    p.add_argument(
        "--once", action="store_true", help="Run a single sync then exit."
    )
    p.add_argument(
        "--interval-seconds",
        type=float,
        default=10.0,
        help="Loop interval (default: 10).",
    )
    p.add_argument("--company-id", default=None)
    p.add_argument("--repository-id", default=None)
    p.add_argument("--plan-id", default=None)
    p.add_argument("--bucket", default=None)
    p.add_argument("--prefix", default=None)
    p.add_argument("--target-dir", default=None, dest="target_dir")
    p.add_argument("--aws-region", default="")
    p.add_argument("--aws-profile", default="")
    p.add_argument("--event-log", default=None)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; log canonical events to stderr.",
    )
    p.add_argument(
        "--install",
        action="store_true",
        help="Install the OS-appropriate background service for this scope.",
    )
    return p


def _event_log_path(raw: str | None) -> Path | None:
    v = _env_first(raw, "CANON_EVENT_LOG")
    return Path(v).expanduser() if v else None


def run(argv: list[str] | None = None) -> int:
    av0 = list(sys.argv[1:] if argv is None else argv)
    if av0 and av0[0] == "sync":
        av0 = av0[1:]
    p = _build_parser()
    try:
        args = p.parse_args(av0)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return VAULT_EXIT_OK
        return VAULT_EXIT_USAGE
    for k, e in (
        ("plan_id", "CANON_PLAN_ID"),
        ("company_id", "CANON_COMPANY_ID"),
        ("repository_id", "CANON_REPOSITORY_ID"),
    ):
        v = _env_first(getattr(args, k, None), e)
        setattr(args, k, v)
    for k, e in (("bucket", "CANON_VAULT_BUCKET"), ("prefix", "CANON_VAULT_PREFIX")):
        v = _env_first(getattr(args, k, None), e)
        setattr(args, k, v)
    env_iv = _env_first(None, "CANON_VAULT_SYNC_INTERVAL_SECONDS")
    if env_iv and not any(x == "--interval-seconds" for x in av0):
        try:
            args.interval_seconds = float(env_iv)
        except ValueError:
            pass
    tdir = _derive_target_dir(
        _env_first(getattr(args, "target_dir", None), "CANON_VAULT_TARGET_DIR")
    )
    if tdir is None:
        return _err_usage("unable to derive target-dir: not inside a git repo; pass --target-dir")
    try:
        req = _resolve_required(args)
    except ValueError as e:
        return _err_usage(str(e))
    elog = _event_log_path(getattr(args, "event_log", None))
    dry = bool(getattr(args, "dry_run", False))
    if bool(getattr(args, "install", False)):
        try:
            install_service(
                company_id=req["company_id"],
                repository_id=req["repository_id"],
                plan_id=req["plan_id"],
                bucket=req["bucket"],
                prefix=req["prefix"],
                target_dir=tdir,
                interval_seconds=int(float(args.interval_seconds or 10)),
                aws_region=str(getattr(args, "aws_region", "") or ""),
                aws_profile=str(getattr(args, "aws_profile", "") or ""),
                event_log=elog,
                dry_run=dry,
            )
        except OSError as e:
            return _err_usage(str(e))
        return VAULT_EXIT_OK
    try:
        s3 = _s3_client_factory(
            str(getattr(args, "aws_region", "") or ""),
            str(getattr(args, "aws_profile", "") or ""),
        )
    except (EndpointConnectionError, BotoCoreError) as e:
        pld0 = {
            "result": "error",
            "pulled_bytes": 0,
            "pulled_count": 0,
            "deleted_count": 0,
            "skipped_count": 0,
            "error_message": str(e),
            "plan_id": req["plan_id"],
        }
        if bool(getattr(args, "once", False)):
            _emit_vault_sync_event(
                _build_vault_event(
                    company_id=req["company_id"],
                    repository_id=req["repository_id"],
                    plan_id=req["plan_id"],
                    payload=pld0,
                ),
                event_log=elog,
                dry_run=dry,
            )
        if isinstance(e, EndpointConnectionError):
            return _err_transport(str(e))
        return VAULT_EXIT_SYNC
    except OSError:
        return VAULT_EXIT_SYNC
    if bool(getattr(args, "once", False)):
        pld = _tick(s3, req["bucket"], req["prefix"], tdir, req, elog, dry)
        if pld.get("result") != "ok":
            emsg = str(pld.get("error_message", ""))
            if pld.get("error_kind") == "transport":
                return _err_transport(emsg)
            return VAULT_EXIT_SYNC
        return VAULT_EXIT_OK
    _run_loop(
        s3,
        tdir,
        req,
        req["bucket"],
        req["prefix"],
        elog,
        dry,
        float(args.interval_seconds or 10.0),
    )
    return VAULT_EXIT_OK
