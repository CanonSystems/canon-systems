from __future__ import annotations

import json
from pathlib import Path

import pytest

from canon_backend_shared.events import CanonicalEvent

from canon_systems.cli import main
from canon_systems.report_cli import run as run_report
from canon_systems.retrieval_telemetry import (
    RETRIEVAL_SOURCES,
    RetrievalBreakdown,
    SourceCounts,
    build_comparison_block,
    build_retrieval_breakdown_event,
    build_task_outcome_event,
    comparison_from_payload,
    sum_breakdown,
)


def _sample_event(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "event_id": "evt-1",
        "parent_event_id": "evt-0",
        "event_type": "retrieval_breakdown",
        "company_id": "c",
        "repository_id": "r",
        "plan_id": "p1",
        "task_id": "t1",
        "handoff_id": "h",
        "agent_name": "scoper",
        "agent_run_id": "ar",
        "actor_id": "a",
        "model": "claude",
        "timestamp": "2026-01-01T00:00:00Z",
        "state_version": 1,
        "payload": {
            "sources": {
                "graph": {"tokens_in": 10, "tokens_out": 5},
                "state": {"tokens_in": 2, "tokens_out": 1},
                "canonical": {"tokens_in": 3, "tokens_out": 0},
                "file": {"tokens_in": 0, "tokens_out": 0},
            },
            "totals": {"tokens_in": 15, "tokens_out": 6},
        },
    }
    base.update(overrides)
    return base


def test_source_counts_non_negative() -> None:
    with pytest.raises(ValueError):
        SourceCounts(tokens_in=-1, tokens_out=0)
    with pytest.raises(ValueError):
        SourceCounts(tokens_in=0, tokens_out=-3)


def test_retrieval_breakdown_defaults_zero() -> None:
    b = RetrievalBreakdown()
    for src in RETRIEVAL_SOURCES:
        sc = getattr(b, src)
        assert sc.tokens_in == 0 and sc.tokens_out == 0


def test_build_event_canonical_shape() -> None:
    ev = build_retrieval_breakdown_event(
        event_id="e",
        parent_event_id="p",
        company_id="c",
        repository_id="r",
        plan_id="pl",
        task_id="t",
        handoff_id="h",
        agent_name="scoper",
        agent_run_id="ar",
        actor_id="a",
        model="m",
        timestamp="2026-01-01T00:00:00Z",
        state_version=1,
        breakdown=RetrievalBreakdown(),
    )
    assert ev.event_type == "retrieval_breakdown"
    assert ev.schema_version == 1
    assert isinstance(ev, CanonicalEvent)


def test_canonical_event_envelope_fields_remain_unchanged() -> None:
    expected_keys = [
        "schema_version",
        "event_id",
        "parent_event_id",
        "event_type",
        "company_id",
        "repository_id",
        "plan_id",
        "task_id",
        "handoff_id",
        "agent_name",
        "agent_run_id",
        "actor_id",
        "model",
        "timestamp",
        "state_version",
        "payload",
    ]
    comp = build_comparison_block(
        experiment_id="exp-1",
        memory_mode="Base",
        run_id="run-1",
        task_attempt_id="attempt-1",
    )
    retrieval_event = build_retrieval_breakdown_event(
        event_id="e",
        parent_event_id="p",
        company_id="c",
        repository_id="r",
        plan_id="pl",
        task_id="t",
        handoff_id="h",
        agent_name="scoper",
        agent_run_id="ar",
        actor_id="a",
        model="m",
        timestamp="2026-01-01T00:00:00Z",
        state_version=1,
        breakdown=RetrievalBreakdown(graph=SourceCounts(1, 0)),
        comparison=comp,
    )
    outcome_event = build_task_outcome_event(
        event_id="to-1",
        parent_event_id="p",
        company_id="c",
        repository_id="r",
        plan_id="pl",
        task_id="t",
        handoff_id="h",
        agent_name="release-orchestrator",
        agent_run_id="ar",
        actor_id="a",
        model="m",
        timestamp="2026-01-01T00:00:00Z",
        state_version=1,
        comparison=comp,
        status="completed",
        qa_gate="PASS",
        elapsed_seconds=1,
        retry_count=0,
        reopen_count=0,
        rework_count=0,
    )
    assert list(retrieval_event.to_dict().keys()) == expected_keys
    assert list(outcome_event.to_dict().keys()) == expected_keys
    assert "comparison" not in retrieval_event.to_dict()
    assert "comparison" not in outcome_event.to_dict()


def test_build_event_payload_sources_keys() -> None:
    ev = build_retrieval_breakdown_event(
        event_id="e",
        parent_event_id="p",
        company_id="c",
        repository_id="r",
        plan_id="pl",
        task_id="t",
        handoff_id="h",
        agent_name="scoper",
        agent_run_id="ar",
        actor_id="a",
        model="m",
        timestamp="2026-01-01T00:00:00Z",
        state_version=1,
        breakdown=RetrievalBreakdown(
            graph=SourceCounts(1, 0),
            state=SourceCounts(0, 1),
        ),
    )
    p = ev.payload
    assert "sources" in p
    srcs = p["sources"]
    assert list(srcs.keys()) == list(RETRIEVAL_SOURCES)
    for src in RETRIEVAL_SOURCES:
        assert "tokens_in" in srcs[src] and "tokens_out" in srcs[src]


def test_build_event_payload_totals_sum() -> None:
    b = RetrievalBreakdown(
        graph=SourceCounts(10, 2),
        state=SourceCounts(3, 1),
        canonical=SourceCounts(0, 4),
        file=SourceCounts(2, 0),
    )
    ev = build_retrieval_breakdown_event(
        event_id="e",
        parent_event_id="p",
        company_id="c",
        repository_id="r",
        plan_id="pl",
        task_id="t",
        handoff_id="h",
        agent_name="x",
        agent_run_id="ar",
        actor_id="a",
        model="m",
        timestamp="2026-01-01T00:00:00Z",
        state_version=1,
        breakdown=b,
    )
    t = ev.payload["totals"]
    assert t["tokens_in"] == 10 + 3 + 0 + 2
    assert t["tokens_out"] == 2 + 1 + 4 + 0


def test_sum_breakdown_zero_for_default() -> None:
    s = sum_breakdown(RetrievalBreakdown())
    assert s.tokens_in == 0 and s.tokens_out == 0


def test_sum_breakdown_sums_all_sources() -> None:
    s = sum_breakdown(
        RetrievalBreakdown(
            graph=SourceCounts(1, 2),
            state=SourceCounts(3, 4),
            canonical=SourceCounts(5, 6),
            file=SourceCounts(7, 8),
        )
    )
    assert s.tokens_in == 1 + 3 + 5 + 7
    assert s.tokens_out == 2 + 4 + 6 + 8


def test_event_roundtrip_via_to_dict_from_dict() -> None:
    b = RetrievalBreakdown(
        graph=SourceCounts(1, 0),
        canonical=SourceCounts(0, 2),
    )
    ev = build_retrieval_breakdown_event(
        event_id="e1",
        parent_event_id="p0",
        company_id="c",
        repository_id="r",
        plan_id="pl",
        task_id="t",
        handoff_id="h",
        agent_name="scoper",
        agent_run_id="ar",
        actor_id="a",
        model="m",
        timestamp="2026-01-01T00:00:00Z",
        state_version=1,
        breakdown=b,
    )
    d = ev.to_dict()
    ev2 = CanonicalEvent.from_dict(d)
    assert ev2.payload == ev.payload
    assert ev2.event_type == "retrieval_breakdown"


def test_report_cli_aggregates_by_source(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a = _sample_event(event_id="a", event_type="retrieval_breakdown", plan_id="p1", task_id="t1")
    b = _sample_event(
        event_id="b",
        event_type="retrieval_breakdown",
        plan_id="p1",
        task_id="t1",
        payload={
            "sources": {
                "graph": {"tokens_in": 1, "tokens_out": 0},
                "state": {"tokens_in": 0, "tokens_out": 0},
                "canonical": {"tokens_in": 0, "tokens_out": 0},
                "file": {"tokens_in": 0, "tokens_out": 0},
            },
            "totals": {"tokens_in": 1, "tokens_out": 0},
        },
    )
    p = tmp_path / "e.ndjson"
    p.write_text("\n".join(json.dumps(x) for x in (a, b)) + "\n", encoding="utf-8")
    assert run_report(["--events", str(p), "--by", "source"]) == 0
    out = capsys.readouterr().out.strip()
    assert out == json.dumps(json.loads(out), sort_keys=True)
    data = json.loads(out)
    assert data["by"] == "source"
    g = data["groups"]["graph"]
    assert g == {"tokens_in": 10 + 1, "tokens_out": 5 + 0}
    # stable key order
    assert list(data.keys()) == ["by", "groups"]


def test_report_cli_aggregates_by_phase(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    z = {"graph": 0, "state": 0, "canonical": 0, "file": 0}
    sc = {k: {"tokens_in": z[k], "tokens_out": 0} for k in z}
    sc["graph"] = {"tokens_in": 1, "tokens_out": 0}
    qg = {k: {"tokens_in": z[k], "tokens_out": 0} for k in z}
    qg["state"] = {"tokens_in": 2, "tokens_out": 0}
    p = tmp_path / "e.ndjson"
    p.write_text(
        "\n".join(
            [
                json.dumps({**_sample_event(event_id="1"), "agent_name": "scoper", "payload": {"sources": sc, "totals": {"tokens_in": 1, "tokens_out": 0}}}),
                json.dumps(
                    {**_sample_event(event_id="2"), "agent_name": "qa-gate", "payload": {"sources": qg, "totals": {"tokens_in": 2, "tokens_out": 0}}}
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert run_report(["--events", str(p), "--by", "phase"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["by"] == "phase"
    assert data["groups"]["scoper"] == {"tokens_in": 1, "tokens_out": 0}
    assert data["groups"]["qa-gate"] == {"tokens_in": 2, "tokens_out": 0}
    # sorted bucket keys
    assert list(data["groups"].keys()) == ["qa-gate", "scoper"]


def test_report_cli_filters_by_plan_id(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a = _sample_event(event_id="a", plan_id="keep", task_id="t1")
    b = _sample_event(
        event_id="b", plan_id="other", task_id="t1", agent_name="x", event_type="retrieval_breakdown"
    )
    p = tmp_path / "e.ndjson"
    p.write_text("\n".join((json.dumps(a), json.dumps(b))) + "\n", encoding="utf-8")
    assert run_report(["--events", str(p), "--by", "source", "--plan-id", "keep"]) == 0
    data = json.loads(capsys.readouterr().out)
    # only first event: graph 10+5+...
    g = data["groups"]["graph"]
    assert g == {"tokens_in": 10, "tokens_out": 5}


def test_report_cli_missing_file_exit_3() -> None:
    assert run_report(["--events", "/nonexistent/path/ndjson-xyz-abc.ndjson"]) == 3


def test_report_cli_malformed_line_exit_4(tmp_path: Path) -> None:
    p = tmp_path / "b.ndjson"
    p.write_text("not json\n", encoding="utf-8")
    assert run_report(["--events", str(p)]) == 4


def test_report_cli_missing_events_flag_exit_2() -> None:
    assert run_report([]) == 2


def test_comparison_from_payload_requires_all_keys() -> None:
    assert comparison_from_payload({}) is None
    assert comparison_from_payload({"comparison": {"experiment_id": "e"}}) is None
    c = comparison_from_payload(
        {
            "comparison": {
                "experiment_id": "exp1",
                "memory_mode": "BASELINE",
                "run_id": "r1",
                "task_attempt_id": "t1",
            }
        }
    )
    assert c is not None
    assert c["memory_mode"] == "baseline"


def test_build_retrieval_breakdown_with_comparison_adds_block() -> None:
    comp = build_comparison_block(
        experiment_id="e1", memory_mode="Mode_A", run_id="run-x", task_attempt_id="ta-1"
    )
    ev = build_retrieval_breakdown_event(
        event_id="e",
        parent_event_id="p",
        company_id="c",
        repository_id="r",
        plan_id="pl",
        task_id="t",
        handoff_id="h",
        agent_name="scoper",
        agent_run_id="agent-proc",
        actor_id="a",
        model="m",
        timestamp="2026-01-01T00:00:00Z",
        state_version=1,
        breakdown=RetrievalBreakdown(graph=SourceCounts(1, 1)),
        comparison=comp,
    )
    assert ev.payload["comparison"]["run_id"] == "run-x"
    assert ev.payload["comparison"]["memory_mode"] == "mode_a"
    assert ev.agent_run_id == "agent-proc"


def test_build_task_outcome_event_shape() -> None:
    comp = build_comparison_block(
        experiment_id="e1", memory_mode="ab", run_id="run-1", task_attempt_id="ta-1"
    )
    ev = build_task_outcome_event(
        event_id="to-1",
        parent_event_id="p",
        company_id="c",
        repository_id="r",
        plan_id="pl",
        task_id="t",
        handoff_id="h",
        agent_name="release-orchestrator",
        agent_run_id="ar-proc",
        actor_id="a",
        model="m",
        timestamp="2026-01-01T00:00:00Z",
        state_version=1,
        comparison=comp,
        status="completed",
        qa_gate="pass",
        elapsed_seconds=120,
        retry_count=1,
        reopen_count=0,
        rework_count=2,
    )
    assert ev.event_type == "task_outcome"
    assert ev.schema_version == 1
    p = ev.payload
    assert p["qa_gate"] == "PASS"
    assert p["elapsed_seconds"] == 120
    assert p["retry_count"] == 1
    assert p["comparison"]["task_attempt_id"] == "ta-1"
    assert p["comparison"]["run_id"] == "run-1"


def test_cli_graph_and_report_help() -> None:
    with pytest.raises(SystemExit) as eg:
        main(["graph", "--help"])
    assert eg.value.code == 0
    with pytest.raises(SystemExit) as er:
        main(["report", "--help"])
    assert er.value.code == 0
