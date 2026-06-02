"""Tests for the event-sourced task core (canon_systems.tasks)."""

from __future__ import annotations

import pytest

from canon_systems import tasks as core


def _created(ref="tsk_1", ts="2026-06-01T10:00:00Z", actor="usr_a", **kw):
    fields = kw.pop("fields", {"title": "Do thing", "status": "open"})
    return core.make_event(
        event_type=core.EVENT_CREATED,
        event_id=kw.pop("event_id", f"evt_{ref}_create"),
        task_ref=ref,
        timestamp=ts,
        actor_id=actor,
        company_id=kw.pop("company_id", "ACME"),
        scope=kw.pop("scope", "repo"),
        repository_id=kw.pop("repository_id", "repo-x"),
        repositories=kw.pop("repositories", None),
        fields=fields,
    )


def test_normalizers() -> None:
    assert core.normalize_scope("multi-repo") == "multi_repo"
    assert core.normalize_scope("REPO") == "repo"
    assert core.normalize_status("todo") == "open"
    assert core.normalize_status("closed") == "done"
    assert core.normalize_priority("") == "normal"
    with pytest.raises(core.TaskError):
        core.normalize_scope("galaxy")
    with pytest.raises(core.TaskError):
        core.normalize_status("frozen")


def test_materialize_basic_create() -> None:
    state = core.materialize([_created()])
    assert "tsk_1" in state
    t = state["tsk_1"]
    assert t["title"] == "Do thing"
    assert t["status"] == "open"
    assert t["scope"] == "repo"
    assert t["repository_id"] == "repo-x"
    assert t["author_id"] == "usr_a"


def test_update_and_status_history() -> None:
    create = _created()
    upd = core.make_event(
        event_type=core.EVENT_UPDATED,
        event_id="evt_2",
        task_ref="tsk_1",
        timestamp="2026-06-01T11:00:00Z",
        actor_id="usr_b",
        fields={"status": "in_progress", "assignees": ["usr_b"]},
    )
    state = core.materialize([create, upd])
    t = state["tsk_1"]
    assert t["status"] == "in_progress"
    assert t["assignees"] == ["usr_b"]
    assert t["updated_at"] == "2026-06-01T11:00:00Z"
    assert any("status: open -> in_progress" in h["change"] for h in t["history"])


def test_comment_appends() -> None:
    create = _created()
    c = core.make_event(
        event_type=core.EVENT_COMMENTED,
        event_id="evt_c",
        task_ref="tsk_1",
        timestamp="2026-06-01T12:00:00Z",
        actor_id="usr_c",
        comment="looking into it",
    )
    state = core.materialize([create, c])
    comments = state["tsk_1"]["comments"]
    assert len(comments) == 1
    assert comments[0]["text"] == "looking into it"
    assert comments[0]["actor"] == "usr_c"


def test_events_fold_deterministically_regardless_of_order() -> None:
    create = _created()
    upd = core.make_event(
        event_type=core.EVENT_UPDATED,
        event_id="evt_2",
        task_ref="tsk_1",
        timestamp="2026-06-01T11:00:00Z",
        actor_id="usr_b",
        fields={"status": "done"},
    )
    forward = core.materialize([create, upd])
    backward = core.materialize([upd, create])
    assert forward == backward
    assert forward["tsk_1"]["status"] == "done"


def test_dedupe_events_is_idempotent_union() -> None:
    create = _created()
    merged = core.dedupe_events([create], [create, _created(ref="tsk_2", event_id="evt_tsk_2_create")])
    ids = sorted(e["event_id"] for e in merged)
    assert ids == ["evt_tsk_1_create", "evt_tsk_2_create"]


def test_filter_hides_terminal_by_default() -> None:
    done = _created(ref="d", event_id="evt_d", fields={"title": "done one", "status": "done"})
    open_t = _created(ref="o", event_id="evt_o", fields={"title": "open one", "status": "open"})
    state = core.materialize([done, open_t])
    visible = core.filter_and_sort(state.values())
    refs = [t["task_ref"] for t in visible]
    assert refs == ["o"]
    with_all = core.filter_and_sort(state.values(), include_terminal=True)
    assert sorted(t["task_ref"] for t in with_all) == ["d", "o"]


def test_filter_mine_matches_author_or_assignee() -> None:
    mine_author = _created(ref="a1", event_id="e1", actor="usr_me")
    assigned = _created(ref="a2", event_id="e2", actor="usr_x", fields={"title": "x", "status": "open", "assignees": ["usr_me"]})
    other = _created(ref="a3", event_id="e3", actor="usr_x")
    state = core.materialize([mine_author, assigned, other])
    mine = core.filter_and_sort(state.values(), mine_actor="usr_me")
    assert sorted(t["task_ref"] for t in mine) == ["a1", "a2"]


def test_company_scope_touches_every_repo() -> None:
    company_task = core.make_event(
        event_type=core.EVENT_CREATED,
        event_id="evt_co",
        task_ref="co1",
        timestamp="2026-06-01T10:00:00Z",
        actor_id="usr_a",
        company_id="ACME",
        scope="company",
        fields={"title": "company-wide", "status": "open"},
    )
    state = core.materialize([company_task])
    assert core.filter_and_sort(state.values(), repository_id="any-repo")


def test_multi_repo_scope_only_matches_listed_repos() -> None:
    mr = core.make_event(
        event_type=core.EVENT_CREATED,
        event_id="evt_mr",
        task_ref="mr1",
        timestamp="2026-06-01T10:00:00Z",
        actor_id="usr_a",
        company_id="ACME",
        scope="multi_repo",
        repositories=["repo-a", "repo-b"],
        fields={"title": "spans two", "status": "open"},
    )
    state = core.materialize([mr])
    assert core.filter_and_sort(state.values(), repository_id="repo-a")
    assert not core.filter_and_sort(state.values(), repository_id="repo-c")


def test_priority_sort_orders_urgent_first() -> None:
    low = _created(ref="low", event_id="el", fields={"title": "l", "status": "open", "priority": "low"})
    urgent = _created(ref="urg", event_id="eu", fields={"title": "u", "status": "open", "priority": "urgent"})
    state = core.materialize([low, urgent])
    ordered = core.filter_and_sort(state.values())
    assert [t["task_ref"] for t in ordered] == ["urg", "low"]


def test_malformed_events_are_skipped() -> None:
    good = _created()
    bad = {"event_type": "task_created"}  # missing required fields
    state = core.materialize([good, bad])
    assert list(state.keys()) == ["tsk_1"]


def test_render_helpers_do_not_crash() -> None:
    state = core.materialize([_created()])
    t = state["tsk_1"]
    assert "tsk_1" in core.render_task_line(t)
    assert "status" in core.render_task_detail(t)
    assert core.render_scope(t) == "repo:repo-x"
