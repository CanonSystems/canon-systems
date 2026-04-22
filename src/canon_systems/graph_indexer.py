"""Graph indexer CLI: POST snapshots to axon-service /index and GET /reindex-status (stdlib HTTP)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from urllib.parse import quote
from typing import Any

ENV_BASE = "AXON_SERVICE_URL"
ENV_TOKEN = "AXON_SERVICE_TOKEN"

EXIT_OK = 0
EXIT_SERVER = 1
EXIT_USAGE = 2
EXIT_HTTP_4XX = 3
EXIT_HTTP_5XX = 4
EXIT_TRANSPORT = 5

SOFT_TIME_BUDGET_SECONDS = 60.0


class TransportError(Exception):
    """Low-level HTTP client failure (wrapped URLError)."""


def _http_request(
    url: str,
    *,
    method: str,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 30.0,
) -> tuple[int, bytes, dict[str, str]]:
    hdrs: dict[str, str] = dict(headers or {})
    req = urllib.request.Request(url=url, data=body, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read()
            status = int(resp.getcode() or 0)
            head = {k: v for k, v in resp.headers.items()}
            return (status, raw, head)
    except urllib.error.HTTPError as exc:
        raw_err = exc.read()
        head = {k: v for k, v in exc.headers.items()} if exc.headers else {}
        return (int(exc.code or 0), raw_err, head)
    except urllib.error.URLError as exc:
        raise TransportError(str(exc)) from exc


def _resolve_base_url(args: argparse.Namespace) -> str:
    if getattr(args, "base_url", None):
        u = str(args.base_url).strip()
    else:
        u = os.environ.get(ENV_BASE, "").strip()
    return u.rstrip("/")


def _resolve_token(args: argparse.Namespace) -> str:
    if getattr(args, "service_token", None):
        return str(args.service_token).strip()
    return os.environ.get(ENV_TOKEN, "").strip()


def _unwrap_detail(body_bytes: bytes) -> str:
    if not body_bytes.strip():
        return ""
    try:
        text = body_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""
    try:
        body: Any = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(body, dict) and "detail" in body:
        d = body.get("detail")
        if isinstance(d, str):
            return d
    if isinstance(body, (dict, list)):
        return json.dumps(body, ensure_ascii=True)
    return text


def _list_all_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    return lines


def _sibling_edges(paths: list[str]) -> list[dict[str, str]]:
    by_dir: dict[str, list[str]] = defaultdict(list)
    for p in paths:
        if not p:
            continue
        d = os.path.dirname(p) or "."
        by_dir[d].append(p)
    edges: list[dict[str, str]] = []
    for _dirn in sorted(by_dir.keys()):
        files = sorted(set(by_dir[_dirn]))
        if len(files) >= 2:
            a, b = files[0], files[1]
            edges.append({"from": a, "to": b, "type": "sibling"})
    return edges


def _build_payload(*, changed_files: list[str] | None, full: bool) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if full:
        paths = _list_all_files()
    else:
        paths = list(changed_files or [])
    nodes = [{"id": p, "type": "file", "path": p} for p in sorted(set(paths))]
    edges = _sibling_edges([p for p in paths if p])
    return nodes, edges


def _print_stdout_raw(body: bytes) -> None:
    if not body:
        print("", end="")
        return
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        text = ""
    sys.stdout.write(text)
    if text and not text.endswith("\n"):
        sys.stdout.write("\n")


def _cmd_index(args: argparse.Namespace) -> int:
    base_url = _resolve_base_url(args)
    token = _resolve_token(args)
    if not base_url or not token:
        print("error: AXON_SERVICE_URL/--base-url and AXON_SERVICE_TOKEN/--service-token required", file=sys.stderr)
        return EXIT_USAGE
    if args.full and args.changed_files is not None:
        print("error: --full and --changed-files are mutually exclusive", file=sys.stderr)
        return EXIT_USAGE

    changed: list[str] | None = None if args.full else (args.changed_files if args.changed_files is not None else [])
    nodes, edges = _build_payload(changed_files=changed, full=bool(args.full))
    body_obj: dict[str, Any] = {
        "commit_sha": args.commit_sha,
        "nodes": nodes,
        "edges": edges,
        "metadata": {"mode": "full" if args.full else "incremental"},
    }
    body_bytes = json.dumps(body_obj, ensure_ascii=True).encode("utf-8")
    url = f"{base_url}/axon/{args.company_id}/{args.repository_id}/index"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    t0 = time.monotonic()
    try:
        status, resp_body, _h = _http_request(
            url, method="POST", headers=headers, body=body_bytes, timeout=30.0
        )
    except TransportError as exc:
        print(f"error: transport: {exc}", file=sys.stderr)
        return EXIT_TRANSPORT
    elapsed = time.monotonic() - t0
    if elapsed > SOFT_TIME_BUDGET_SECONDS:
        print(
            f"warning: index took {elapsed:.1f}s (soft budget {SOFT_TIME_BUDGET_SECONDS}s)",
            file=sys.stderr,
        )
    if status in (200, 201):
        _print_stdout_raw(resp_body)
        return EXIT_OK
    if 400 <= status <= 499:
        print(_unwrap_detail(resp_body), file=sys.stderr)
        return EXIT_HTTP_4XX
    if 500 <= status <= 599:
        return EXIT_HTTP_5XX
    print(f"error: unexpected HTTP {status}", file=sys.stderr)
    return EXIT_SERVER


def _cmd_reindex_status(args: argparse.Namespace) -> int:
    base_url = _resolve_base_url(args)
    token = _resolve_token(args)
    if not base_url or not token:
        print("error: AXON_SERVICE_URL/--base-url and AXON_SERVICE_TOKEN/--service-token required", file=sys.stderr)
        return EXIT_USAGE
    sha_q = quote(args.commit_sha, safe="")
    url = f"{base_url}/axon/{args.company_id}/{args.repository_id}/reindex-status?commit_sha={sha_q}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        status, resp_body, _h = _http_request(url, method="GET", headers=headers, timeout=30.0)
    except TransportError as exc:
        print(f"error: transport: {exc}", file=sys.stderr)
        return EXIT_TRANSPORT
    if status == 200:
        _print_stdout_raw(resp_body)
        return EXIT_OK
    if 400 <= status <= 499:
        print(_unwrap_detail(resp_body), file=sys.stderr)
        return EXIT_HTTP_4XX
    if 500 <= status <= 599:
        return EXIT_HTTP_5XX
    print(f"error: unexpected HTTP {status}", file=sys.stderr)
    return EXIT_SERVER


def _cmd_query(_args: argparse.Namespace) -> int:
    print("canon graph query: deferred to E3-T3; use canon graph index for writes", file=sys.stderr)
    return EXIT_USAGE


def _cmd_impact(_args: argparse.Namespace) -> int:
    print("canon graph query: deferred to E3-T3; use canon graph index for writes", file=sys.stderr)
    return EXIT_USAGE


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon graph",
        description="Graph retrieval plane: index snapshots and reindex status (axon-service).",
    )
    sp = p.add_subparsers(dest="graph_command", required=True)

    pi = sp.add_parser("index", help="POST /axon/.../index (graph snapshot).")
    pi.add_argument("--commit-sha", required=True)
    pi.add_argument("--company-id", required=True)
    pi.add_argument("--repository-id", required=True)
    pi.add_argument("--full", action="store_true")
    pi.add_argument("--changed-files", nargs="*", default=None)
    pi.add_argument("--base-url", default=None)
    pi.add_argument("--service-token", default=None)

    pr = sp.add_parser("reindex-status", help="GET /axon/.../reindex-status.")
    pr.add_argument("--commit-sha", required=True)
    pr.add_argument("--company-id", required=True)
    pr.add_argument("--repository-id", required=True)
    pr.add_argument("--base-url", default=None)
    pr.add_argument("--service-token", default=None)

    sp.add_parser("query", help="Deferred (E3-T3).")
    sp.add_parser("impact", help="Deferred (E3-T3).")
    return p


def run(argv: list[str] | None = None) -> int:
    p = build_parser()
    av = list(sys.argv[1:] if argv is None else argv)
    try:
        args = p.parse_args(av)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return EXIT_OK
        return EXIT_USAGE
    if args.graph_command == "index":
        return _cmd_index(args)
    if args.graph_command == "reindex-status":
        return _cmd_reindex_status(args)
    if args.graph_command == "query":
        return _cmd_query(args)
    if args.graph_command == "impact":
        return _cmd_impact(args)
    return EXIT_USAGE


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
