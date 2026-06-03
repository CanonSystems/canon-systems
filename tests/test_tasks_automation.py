"""Tests for automatic task ↔ session wiring."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from canon_systems import tasks_automation as auto
from canon_systems import tasks_cli


@pytest.fixture()
def task_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo-x"
    repo.mkdir()
    global_home = tmp_path / "global-tasks"
    monkeypatch.setenv("CANON_TASKS_HOME", str(global_home))
    monkeypatch.setenv("CANON_TASKS_NOW", "2026-06-02T09:00:00Z")
    monkeypatch.delenv("CANON_TASKS_API_URL", raising=False)
    monkeypatch.delenv("CANON_STATE_API_URL", raising=False)

    identity = SimpleNamespace(actor_id="usr_me", display_name="Me", company_id="ACME")
    repo_ctx = SimpleNamespace(company_id="ACME", repository_id="repo-x")

    monkeypatch.setattr(tasks_cli, "repo_root", lambda: repo)
    monkeypatch.setattr(tasks_cli, "load_identity_context", lambda: identity)
    monkeypatch.setattr(tasks_cli, "load_repo_context", lambda _id: repo_ctx)
    return SimpleNamespace(repo=repo)


def test_active_refresh_writes_context_and_promotes_open(task_env, capsys) -> None:
    tasks_cli.run(["create", "Do the thing", "--json"])
    capsys.readouterr()
    rc = tasks_cli.run(["active", "--refresh", "--json"])
    assert rc == 0
    ctx_path = task_env.repo / ".canon" / "tasks" / "active-context.json"
    assert ctx_path.exists()
    active = json.loads(ctx_path.read_text(encoding="utf-8"))
    assert active["task_ref"].startswith("tsk_")
    assert active["status"] == "in_progress"


def test_record_session_pins_mentioned_task_ref(task_env, capsys) -> None:
    tasks_cli.run(["create", "Target task", "--task-ref", "tsk_target", "--json"])
    capsys.readouterr()
    ref = "tsk_target"
    hook = task_env.repo / "hook.json"
    hook.write_text(
        json.dumps(
            {
                "user_prompt": f"please finish {ref}",
                "assistant_response": "ok",
            }
        ),
        encoding="utf-8",
    )
    rc = tasks_cli.run(["record-session", "--hook-input", str(hook)])
    assert rc == 0
    active = json.loads(
        (task_env.repo / ".canon" / "tasks" / "active-context.json").read_text(encoding="utf-8")
    )
    assert active["task_ref"] == ref


def test_extract_task_refs() -> None:
    refs = auto.extract_task_refs("see tsk_abc_123 and tsk_abc_123 again")
    assert refs == ["tsk_abc_123"]


def test_distill_progress_note_skips_short_reply() -> None:
    assert auto.distill_progress_note("go", "ok") is None


def test_distill_progress_note_summarizes_substantive_reply() -> None:
    assistant = (
        "## Summary\n\n"
        "- Deployed connect-dev with the new preview button.\n"
        "- Opened partner-hub PR #157 for map studio zones.\n"
    )
    note = auto.distill_progress_note("ship it", assistant)
    assert note is not None
    assert note.startswith("[auto]")
    assert "preview" in note.lower() or "PR" in note


def test_should_record_auto_note_dedupes_same_text(task_env) -> None:
    task = {
        "comments": [{"text": "[auto] Already recorded this exact progress note here."}],
    }
    note = "[auto] Already recorded this exact progress note here."
    assert not auto.should_record_auto_note(
        task, note, turn_fingerprint="abc", active_context={}
    )


def test_record_session_appends_auto_note(task_env, capsys) -> None:
    tasks_cli.run(["create", "Batch item", "--task-ref", "tsk_batch", "--json"])
    capsys.readouterr()
    tasks_cli.run(["active", "--set", "tsk_batch", "--quiet"])
    hook = task_env.repo / "hook.json"
    assistant = (
        "Completed the rollout.\n\n"
        "- Merged feat/map-studio-zones to connect-dev.\n"
        "- Verified live on connect-dev.family.one/mapstudio.\n"
    )
    hook.write_text(
        json.dumps({"user_prompt": "finish tsk_batch", "assistant_response": assistant}),
        encoding="utf-8",
    )
    rc = tasks_cli.run(["record-session", "--hook-input", str(hook)])
    assert rc == 0
    tasks_cli.run(["show", "tsk_batch", "--json"])
    task = capsys.readouterr().out.strip().splitlines()[-1]
    import json as _json

    parsed = _json.loads(task)
    assert parsed["status"] == "in_progress"
    assert parsed["comments"]
    assert parsed["comments"][-1]["text"].startswith("[auto]")
