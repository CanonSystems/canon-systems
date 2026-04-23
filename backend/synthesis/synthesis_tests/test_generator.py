from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from canon_backend_shared.events import CanonicalEvent
from synthesis.generator import generate_vault, render_frontmatter
from synthesis.redaction import shorthash
from synthesis.redaction import project_safe, project_payload


def _e(**kw) -> CanonicalEvent:
    d = {
        "schema_version": 1,
        "event_id": "01JBASEV",
        "parent_event_id": "01J0000",
        "event_type": "retrieval_breakdown",
        "company_id": "IMC",
        "repository_id": "innermost",
        "plan_id": "plan-a",
        "task_id": "E5-T2",
        "handoff_id": "h1",
        "agent_name": "implementer",
        "agent_run_id": "run-1",
        "actor_id": "actor-1",
        "model": "m1",
        "timestamp": "2026-04-23T10:00:00Z",
        "state_version": 1,
        "payload": {"phase": "implementer", "agent": "a", "sources": {}},
    }
    d.update(kw)
    return CanonicalEvent.from_dict(d)


def test_generator_deterministic_byte_identical_output() -> None:
    ev1 = _e(
        event_id="01JAAA",
        timestamp="2026-04-23T10:00:01Z",
    )
    ev2 = _e(
        event_id="01JBBB",
        timestamp="2026-04-23T10:00:02Z",
    )
    a = generate_vault(
        [ev1, ev2],
        company_id="IMC",
        repository_id="innermost",
        cutoff_timestamp="2026-04-23T10:00:10Z",
    )
    b = generate_vault(
        [ev1, ev2],
        company_id="IMC",
        repository_id="innermost",
        cutoff_timestamp="2026-04-23T10:00:10Z",
    )
    assert a.pages == b.pages


def test_generator_event_ordering_stable_across_permutations() -> None:
    ev1 = _e(
        event_id="01JAAA",
        timestamp="2026-04-23T10:00:01Z",
    )
    ev2 = _e(
        event_id="01JBBB",
        timestamp="2026-04-23T10:00:02Z",
    )
    a = generate_vault(
        [ev1, ev2],
        company_id="IMC",
        repository_id="innermost",
        cutoff_timestamp="2026-12-31T00:00:00Z",
    )
    b = generate_vault(
        [ev2, ev1],
        company_id="IMC",
        repository_id="innermost",
        cutoff_timestamp="2026-12-31T00:00:00Z",
    )
    assert a.pages == b.pages


def test_redaction_drops_model_field_from_frontmatter() -> None:
    ev = _e(model="secret-model-xyz", event_id="01JMODL")
    s = project_safe(ev)
    assert "model" not in s.frontmatter
    bundle = generate_vault(
        [ev],
        company_id="IMC",
        repository_id="innermost",
        cutoff_timestamp="2026-12-31T00:00:00Z",
    )
    for body in bundle.pages.values():
        assert b"secret-model" not in body
        assert b"model:" not in body


def test_redaction_never_emits_raw_company_id_or_repository_id() -> None:
    ev = _e(
        event_id="01JRAW0",
    )
    bundle = generate_vault(
        [ev],
        company_id="IMC",
        repository_id="innermost",
        cutoff_timestamp="2026-12-31T00:00:00Z",
    )
    for body in bundle.pages.values():
        s = body.decode("utf-8", errors="replace")
        assert "IMC" not in s
        assert "innermost" not in s


def test_redaction_silently_drops_unknown_payload_keys(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    caplog.set_level(logging.DEBUG)
    ev = _e(
        event_id="01JUNKN",
        payload={"phase": "scoper", "agent": "x", "ninja_key": 123, "sources": {}},
    )
    _ = project_payload(ev.event_type, ev.payload)
    _ = project_safe(ev)
    assert not caplog.records


def test_redaction_unknown_event_type_routes_to_opaque_with_dropped_payload_marker() -> (
    None
):
    ev = _e(
        event_id="01JUNKT",
        event_type="ninja_event_type_404",
        payload={"secret": 1},
    )
    b = generate_vault(
        [ev],
        company_id="IMC",
        repository_id="innermost",
        cutoff_timestamp="2026-12-31T00:00:00Z",
    )
    key = "events/opaque/01JUNKT.md"
    assert key in b.pages
    t = b.pages[key].decode("utf-8")
    assert "dropped_payload" in t


def test_citations_present_for_every_rendered_fact() -> None:
    ev = _e(
        event_id="01JCITE",
    )
    bundle = generate_vault(
        [ev],
        company_id="IMC",
        repository_id="innermost",
        cutoff_timestamp="2026-12-31T00:00:00Z",
    )
    for name, data in sorted(bundle.pages.items()):
        if not name.endswith(".md"):
            continue
        if name == "README.md" or name.startswith("_index/"):
            continue
        assert b"[[event:" in data, name


def test_shorthashes_are_deterministic_sha256_prefix() -> None:
    assert shorthash("IMC") == hashlib.sha256(b"IMC").hexdigest()[:8]


def test_frontmatter_key_order_anchors_first_then_alphabetical() -> None:
    ev = _e(event_id="01JFM01", timestamp="2026-01-01T00:00:00Z")
    s = project_safe(ev)
    fm = render_frontmatter(s)
    m = re.match(
        r"^---\n(.*?)\n---\n",
        fm,
        re.DOTALL,
    )
    assert m
    lines = m.group(1).strip().split("\n")
    keys = [x.split(":", 1)[0] for x in lines]
    assert keys[0] == "schema_version"
    assert keys[1] == "event_id"
    assert keys[2:] == sorted(keys[2:])


def test_no_wallclock_reads_in_generator_module() -> None:
    base = Path(__file__).resolve().parent.parent / "synthesis"
    for name in ("generator.py", "redaction.py", "sources.py"):
        text = (base / name).read_text(encoding="utf-8")
        assert "datetime.now" not in text
        assert "import time" not in text
        assert "import datetime" not in text


def test_obsidian_seed_present_and_write_once() -> None:
    ev = _e(event_id="01JOBS01")
    bundle = generate_vault(
        [ev],
        company_id="IMC",
        repository_id="innermost",
        cutoff_timestamp="2026-12-31T00:00:00Z",
    )
    assert ".obsidian/app.json" in bundle.pages
    assert ".obsidian/graph.json" in bundle.pages
    assert ".obsidian/workspace.json" in bundle.pages
    assert ".obsidian/app.json" in bundle.write_once_keys
    assert ".obsidian/graph.json" in bundle.write_once_keys
    assert ".obsidian/workspace.json" in bundle.write_once_keys


def test_cross_links_emit_plan_task_event_wikilinks() -> None:
    ev = _e(
        event_id="01JXLINK",
        plan_id="plan-xlink",
        task_id="T-xlink",
    )
    bundle = generate_vault(
        [ev],
        company_id="IMC",
        repository_id="innermost",
        cutoff_timestamp="2026-12-31T00:00:00Z",
    )
    task_key = "plans/plan-xlink/tasks/T-xlink/index.md"
    plan_key = "plans/plan-xlink/index.md"
    assert task_key in bundle.pages
    assert plan_key in bundle.pages
    task_body = bundle.pages[task_key].decode("utf-8")
    plan_body = bundle.pages[plan_key].decode("utf-8")
    assert "[[plan:plan-xlink]]" in task_body
    assert "[[task:T-xlink]]" in task_body
    assert "[[event:01JXLINK]]" in task_body
    assert "[[plan:plan-xlink]]" in plan_body
    assert "[[task:T-xlink]]" in plan_body
