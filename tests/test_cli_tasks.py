"""Integration tests for the `canon task` CLI (canon_systems.tasks_cli)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from canon_systems import tasks_cli


@pytest.fixture()
def task_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Hermetic repo + identity + global-ledger location for the CLI."""
    repo = tmp_path / "repo-x"
    repo.mkdir()
    global_home = tmp_path / "global-tasks"
    monkeypatch.setenv("CANON_TASKS_HOME", str(global_home))
    monkeypatch.setenv("CANON_TASKS_NOW", "2026-06-02T09:00:00Z")

    identity = SimpleNamespace(actor_id="usr_me", display_name="Me", company_id="ACME")
    repo_ctx = SimpleNamespace(company_id="ACME", repository_id="repo-x")

    monkeypatch.setattr(tasks_cli, "repo_root", lambda: repo)
    monkeypatch.setattr(tasks_cli, "load_identity_context", lambda: identity)
    monkeypatch.setattr(tasks_cli, "load_repo_context", lambda _id: repo_ctx)
    return SimpleNamespace(repo=repo, global_home=global_home)


def _run(argv: list[str]) -> int:
    return tasks_cli.run(argv)


def _read_json(capsys) -> object:
    out = capsys.readouterr().out.strip()
    # Some mutating commands print a human status line before JSON output; the
    # JSON payload is always the last non-empty line.
    last = [ln for ln in out.splitlines() if ln.strip()][-1]
    return json.loads(last)


def test_create_repo_task_writes_repo_ledger(task_env, capsys) -> None:
    rc = _run(["create", "Fix the build", "--json"])
    assert rc == 0
    created = _read_json(capsys)
    ref = created["task_ref"]
    ledger = task_env.repo / ".canon" / "tasks" / "ledger.ndjson"
    assert ledger.exists()
    assert ref in ledger.read_text(encoding="utf-8")
    # Canonical mirror event was emitted (best-effort) to memory events log.
    events = task_env.repo / ".canon" / "memory" / "events.ndjson"
    assert events.exists()
    assert "task_activity" in events.read_text(encoding="utf-8")


def test_create_company_task_writes_global_ledger(task_env) -> None:
    rc = _run(["create", "Company wide thing", "--scope", "company"])
    assert rc == 0
    ledger = task_env.global_home / "ACME" / "ledger.ndjson"
    assert ledger.exists()


def test_multi_repo_requires_repos(task_env, capsys) -> None:
    rc = _run(["create", "spans repos", "--scope", "multi-repo"])
    assert rc == tasks_cli.EXIT_USAGE
    assert "requires --repos" in capsys.readouterr().err


def test_list_shows_open_and_filters_mine(task_env, capsys) -> None:
    _run(["create", "Task A", "--json"])
    _run(["create", "Task B", "--assignee", "usr_other", "--json"])
    capsys.readouterr()  # clear
    rc = _run(["list", "--json"])
    assert rc == 0
    listed = _read_json(capsys)
    assert len(listed) == 2

    rc = _run(["list", "--mine", "--json"])
    mine = _read_json(capsys)
    # Both are authored by usr_me, so both are "mine".
    assert len(mine) == 2


def test_status_update_and_show(task_env, capsys) -> None:
    _run(["create", "Track me", "--task-ref", "tsk_track", "--json"])
    capsys.readouterr()
    rc = _run(["status", "tsk_track", "in_progress"])
    assert rc == 0
    rc = _run(["show", "tsk_track", "--json"])
    task = _read_json(capsys)
    assert task["status"] == "in_progress"


def test_assign_adds_and_replaces(task_env, capsys) -> None:
    _run(["create", "Assignable", "--task-ref", "tsk_as", "--json"])
    capsys.readouterr()
    _run(["assign", "tsk_as", "usr_a", "usr_b"])
    _run(["show", "tsk_as", "--json"])
    task = _read_json(capsys)
    assert task["assignees"] == ["usr_a", "usr_b"]
    _run(["assign", "tsk_as", "usr_c", "--replace"])
    _run(["show", "tsk_as", "--json"])
    task = _read_json(capsys)
    assert task["assignees"] == ["usr_c"]


def test_comment_and_close(task_env, capsys) -> None:
    _run(["create", "Closable", "--task-ref", "tsk_close", "--json"])
    capsys.readouterr()
    assert _run(["comment", "tsk_close", "almost done"]) == 0
    assert _run(["close", "tsk_close", "--comment", "shipped"]) == 0
    _run(["show", "tsk_close", "--json"])
    task = _read_json(capsys)
    assert task["status"] == "done"
    assert any(c["text"] == "almost done" for c in task["comments"])
    # Closed tasks are hidden from default list.
    _run(["list", "--json"])
    assert _read_json(capsys) == []
    # ...but visible with --all.
    _run(["list", "--all", "--json"])
    assert len(_read_json(capsys)) == 1


def test_reopen(task_env, capsys) -> None:
    _run(["create", "Reopen me", "--task-ref", "tsk_re", "--json"])
    _run(["close", "tsk_re"])
    capsys.readouterr()
    assert _run(["reopen", "tsk_re"]) == 0
    _run(["show", "tsk_re", "--json"])
    assert _read_json(capsys)["status"] == "open"


def test_update_unknown_task_returns_not_found(task_env, capsys) -> None:
    rc = _run(["status", "tsk_missing", "done"])
    assert rc == tasks_cli.EXIT_NOT_FOUND
    assert "not found" in capsys.readouterr().err


def test_sync_without_bucket_is_noop_ok(task_env, capsys, monkeypatch) -> None:
    monkeypatch.delenv("CANON_TASKS_BUCKET", raising=False)
    rc = _run(["sync"])
    assert rc == 0
    assert "no CANON_TASKS_BUCKET" in capsys.readouterr().err


def test_list_all_repos_includes_other_repo_task(task_env, capsys) -> None:
    _run(["create", "Other repo task", "--scope", "repo", "--repo", "repo-y", "--json"])
    capsys.readouterr()
    # Default (current repo repo-x) hides the repo-y task.
    _run(["list", "--json"])
    assert _read_json(capsys) == []
    # --all-repos surfaces it.
    _run(["list", "--all-repos", "--json"])
    assert len(_read_json(capsys)) == 1
