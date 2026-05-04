"""CLI packet-archive dry-run (no live AWS / state-api required)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from canon_systems.cli import main as canon_main
from canon_systems.packet_archive_cli import run as run_packet_archive_cli


def test_packet_archive_cli_dry_run_resolves_record(tmp_path: Path) -> None:
    p = tmp_path / "scoper.md"
    p.write_text("# hello\n", encoding="utf-8")
    argv = [
        "--file",
        str(p),
        "--company-id",
        "CSC",
        "--repository-id",
        "canon-systems",
        "--plan-id",
        "plan",
        "--task-id",
        "task",
        "--workstream-id",
        "ws",
        "--handoff-id",
        "hof",
        "--phase",
        "scoper",
        "--artifact-kind",
        "packet_scoper",
        "--dry-run",
        "--dry-run-bucket",
        "unit-test-bucket",
        "--quiet",
    ]
    # argparse prints JSON to stdout; capture via redirect would need subprocess;
    # invoke run() and patch print — simpler: run produces JSON lines to stdout via print;
    # use capsys
    import io
    import sys

    buf = io.StringIO()
    old_out = sys.stdout
    sys.stdout = buf
    try:
        code = run_packet_archive_cli(argv)
    finally:
        sys.stdout = old_out
    assert code == 0
    rec = json.loads(buf.getvalue())
    assert rec["s3_bucket"] == "unit-test-bucket"
    assert rec["artifact_kind"] == "packet_scoper"
    assert rec["byte_length"] == p.stat().st_size


def test_top_level_packet_archive_help_lists_scope_and_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC2: public ``canon packet-archive --help`` matches packet_archive_cli."""
    with pytest.raises(SystemExit) as ei:
        canon_main(["--repo-root", str(tmp_path), "packet-archive", "--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "--artifact-kind" in out
    assert "--dry-run" in out
    assert "--workstream-id" in out
