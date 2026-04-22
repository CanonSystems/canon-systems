<!-- CURSOR_PILOT_PROMPT: E3-T5 retrieval-source telemetry -->

# E3-T5 Cursor-Pilot Prompt

## ROLE
You are the implementer for Canon Memory Platform v1, Wave 3, Task E3-T5. Work on branch `wave/3/canon-memory-v1` (tip 6594063).

## TASK
Deliver a stdlib-only `retrieval_breakdown` canonical event emitter plus a stub `canon report` CLI, wire them into the existing `canon` CLI, require per-phase emission in the five coder-facing agent templates + `memory-layer-defaults.mdc`, and add 20+ new tests. Additive-only to living specs.

## CONTEXT

### CanonicalEvent invariant (do NOT modify)
- `backend/shared/canon_backend_shared/events.py` defines `CanonicalEvent` (schema_version=1, 16-field dataclass with `payload: Mapping[str, Any]`).
- Import it directly: `from canon_backend_shared.events import CanonicalEvent`.
- Package is already installed as a dev dependency in the repo venv (used by state-api and axon-service).

### Existing `canon` CLI wiring (read-only context)
- `src/canon_systems/cli.py` line ~17 imports `run_graph_cli` from `.graph_indexer`.
- `src/canon_systems/cli.py` line ~309-310 registers `graph` subparser with `nargs=argparse.REMAINDER`.
- `src/canon_systems/cli.py` line ~517-518 dispatches `args.command == "graph"` → `run_graph_cli(list(getattr(args, "args", [])))`.
- MIRROR this pattern exactly for the new `report` subcommand.

### Exit-code catalog (reuse from graph_indexer)
- `EXIT_OK = 0`
- `EXIT_USAGE = 2`
- `EXIT_FILE_NOT_FOUND = 3`
- `EXIT_MALFORMED = 4`

### Fixed bucket order (from E3-T4 Retrieval policy)
`graph → state → canonical → file` — exactly these four keys, in this order.

## REPOSITORY

### New files (2)
1. `src/canon_systems/retrieval_telemetry.py` — emitter module.
2. `src/canon_systems/report_cli.py` — `canon report` subcommand logic.
3. `tests/test_retrieval_telemetry.py` — new test file.

### Modified files (10)
4. `src/canon_systems/cli.py` — additive `report` subparser + dispatch.
5. `src/canon_systems/templates/rules/memory-layer-defaults.mdc` — append `## Retrieval-source telemetry (required)` section.
6. `src/canon_systems/templates/agents/scoper.md` — add `## Retrieval-source telemetry (required)` subsection.
7. `src/canon_systems/templates/agents/cursor-pilot.md` — same.
8. `src/canon_systems/templates/agents/implementer.md` — same.
9. `src/canon_systems/templates/agents/qa-gate.md` — same.
10. `src/canon_systems/templates/agents/release-orchestrator.md` — same.
11. `tests/test_agent_templates.py` — 6 new assertions.
12. `CHANGELOG.md` — prepend E3-T5 bullet.
13. `README.md` — additive `canon report` row in the canon commands table.
14. `docs/SYSTEM-WORKFLOW.md` §6 — additive bullet.

### Forbidden surfaces
- backend/** (including backend/shared/ — the emitter IMPORTS `CanonicalEvent` but must NOT modify it).
- infra/**
- .cursor/rules/**, .cursor/plans/**
- src/canon_systems/*.py OTHER THAN cli.py (additive only), retrieval_telemetry.py (new), report_cli.py (new).

## IMPLEMENTATION SPECIFICATION

### `src/canon_systems/retrieval_telemetry.py`

```python
"""retrieval_breakdown canonical event emitter (4-bucket: graph/state/canonical/file)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from canon_backend_shared.events import CanonicalEvent

RETRIEVAL_SOURCES: tuple[str, ...] = ("graph", "state", "canonical", "file")


@dataclass(frozen=True)
class SourceCounts:
    tokens_in: int = 0
    tokens_out: int = 0

    def __post_init__(self) -> None:
        if self.tokens_in < 0 or self.tokens_out < 0:
            raise ValueError("tokens_in and tokens_out must be non-negative")


@dataclass
class RetrievalBreakdown:
    graph: SourceCounts = field(default_factory=SourceCounts)
    state: SourceCounts = field(default_factory=SourceCounts)
    canonical: SourceCounts = field(default_factory=SourceCounts)
    file: SourceCounts = field(default_factory=SourceCounts)


def sum_breakdown(breakdown: RetrievalBreakdown) -> SourceCounts:
    total_in = 0
    total_out = 0
    for src in RETRIEVAL_SOURCES:
        sc: SourceCounts = getattr(breakdown, src)
        total_in += sc.tokens_in
        total_out += sc.tokens_out
    return SourceCounts(tokens_in=total_in, tokens_out=total_out)


def build_retrieval_breakdown_event(
    *,
    event_id: str,
    parent_event_id: str,
    company_id: str,
    repository_id: str,
    plan_id: str,
    task_id: str,
    handoff_id: str,
    agent_name: str,
    agent_run_id: str,
    actor_id: str,
    model: str,
    timestamp: str,
    state_version: int,
    breakdown: RetrievalBreakdown,
) -> CanonicalEvent:
    sources_payload: dict[str, dict[str, int]] = {}
    for src in RETRIEVAL_SOURCES:
        sc: SourceCounts = getattr(breakdown, src)
        sources_payload[src] = {"tokens_in": sc.tokens_in, "tokens_out": sc.tokens_out}
    totals = sum_breakdown(breakdown)
    payload: dict[str, Any] = {
        "sources": sources_payload,
        "totals": {"tokens_in": totals.tokens_in, "tokens_out": totals.tokens_out},
    }
    return CanonicalEvent(
        schema_version=1,
        event_id=event_id,
        parent_event_id=parent_event_id,
        event_type="retrieval_breakdown",
        company_id=company_id,
        repository_id=repository_id,
        plan_id=plan_id,
        task_id=task_id,
        handoff_id=handoff_id,
        agent_name=agent_name,
        agent_run_id=agent_run_id,
        actor_id=actor_id,
        model=model,
        timestamp=timestamp,
        state_version=state_version,
        payload=payload,
    )
```

### `src/canon_systems/report_cli.py`

```python
"""canon report CLI (Wave-3 stub per backlog §E3-T5; Wave 6 will polish)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FILE_NOT_FOUND = 3
EXIT_MALFORMED = 4

_GROUPBY_CHOICES = ("phase", "agent", "source")


def _load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise _Malformed(f"line {lineno}: {exc}") from exc
    return events


class _Malformed(Exception):
    pass


def _aggregate(
    events: list[dict[str, Any]],
    *,
    by: str,
    plan_id: str | None,
    task_id: str | None,
) -> dict[str, dict[str, int]]:
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"tokens_in": 0, "tokens_out": 0})
    for ev in events:
        if ev.get("event_type") != "retrieval_breakdown":
            continue
        if plan_id is not None and ev.get("plan_id") != plan_id:
            continue
        if task_id is not None and ev.get("task_id") != task_id:
            continue
        payload = ev.get("payload", {}) or {}
        sources = payload.get("sources", {}) or {}
        if by == "source":
            for src, counts in sources.items():
                buckets[src]["tokens_in"] += int(counts.get("tokens_in", 0))
                buckets[src]["tokens_out"] += int(counts.get("tokens_out", 0))
        elif by in ("phase", "agent"):
            key = str(ev.get("agent_name", "unknown"))
            totals = payload.get("totals", {}) or {}
            buckets[key]["tokens_in"] += int(totals.get("tokens_in", 0))
            buckets[key]["tokens_out"] += int(totals.get("tokens_out", 0))
        else:
            raise ValueError(f"unknown --by: {by}")
    return dict(sorted(buckets.items()))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canon report",
        description="Aggregate retrieval_breakdown canonical events (stub; Wave 6 polishes).",
    )
    p.add_argument("--events", required=True, help="Path to NDJSON file of canonical events.")
    p.add_argument("--by", choices=_GROUPBY_CHOICES, default="source")
    p.add_argument("--plan-id", default=None)
    p.add_argument("--task-id", default=None)
    return p


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    av = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parser.parse_args(av)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return EXIT_OK
        return EXIT_USAGE
    path = Path(args.events)
    if not path.is_file():
        print(f"error: --events file not found: {path}", file=sys.stderr)
        return EXIT_FILE_NOT_FOUND
    try:
        events = _load_events(path)
    except _Malformed as exc:
        print(f"error: malformed NDJSON: {exc}", file=sys.stderr)
        return EXIT_MALFORMED
    agg = _aggregate(events, by=args.by, plan_id=args.plan_id, task_id=args.task_id)
    out = {"by": args.by, "groups": agg}
    print(json.dumps(out, sort_keys=True))
    return EXIT_OK


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
```

### `src/canon_systems/cli.py` additive edits

**Import (add near line 17, alongside `run_graph_cli`):**
```python
from .report_cli import run as run_report_cli
```

**Subparser (add immediately after the existing `graph_parser` block, ~line 311):**
```python
    report_parser = sub.add_parser("report", help="Retrieval-telemetry rollups (stub; Wave 6 polishes)")
    report_parser.add_argument("args", nargs=argparse.REMAINDER)
```

**Dispatch (add immediately after the `graph` dispatch, ~line 519):**
```python
    if args.command == "report":
        return run_report_cli(list(getattr(args, "args", [])))
```

### `tests/test_retrieval_telemetry.py`

Include all 14+ tests enumerated in the scoper packet. Use `tmp_path` for NDJSON fixtures. Use `capsys` to capture stdout. Invoke `run()` directly (no subprocess) for speed.

Example skeleton (flesh out with all assertions from scoper §6-7):
```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from canon_systems.retrieval_telemetry import (
    RETRIEVAL_SOURCES,
    RetrievalBreakdown,
    SourceCounts,
    build_retrieval_breakdown_event,
    sum_breakdown,
)
from canon_systems.report_cli import run as run_report


def _sample_event(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "event_id": "evt-1", "parent_event_id": "evt-0",
        "event_type": "retrieval_breakdown",
        "company_id": "c", "repository_id": "r",
        "plan_id": "p1", "task_id": "t1", "handoff_id": "h",
        "agent_name": "scoper", "agent_run_id": "ar", "actor_id": "a",
        "model": "claude", "timestamp": "2026-01-01T00:00:00Z",
        "state_version": 1,
        "payload": {
            "sources": {
                "graph":     {"tokens_in": 10, "tokens_out": 5},
                "state":     {"tokens_in":  2, "tokens_out": 1},
                "canonical": {"tokens_in":  3, "tokens_out": 0},
                "file":      {"tokens_in":  0, "tokens_out": 0},
            },
            "totals": {"tokens_in": 15, "tokens_out": 6},
        },
    }
    base.update(overrides)
    return base


def test_source_counts_non_negative():
    with pytest.raises(ValueError):
        SourceCounts(tokens_in=-1, tokens_out=0)
    with pytest.raises(ValueError):
        SourceCounts(tokens_in=0, tokens_out=-3)


def test_retrieval_breakdown_defaults_zero():
    b = RetrievalBreakdown()
    for src in RETRIEVAL_SOURCES:
        sc = getattr(b, src)
        assert sc.tokens_in == 0 and sc.tokens_out == 0


def test_build_event_canonical_shape():
    ev = build_retrieval_breakdown_event(
        event_id="e", parent_event_id="p",
        company_id="c", repository_id="r",
        plan_id="pl", task_id="t", handoff_id="h",
        agent_name="scoper", agent_run_id="ar", actor_id="a",
        model="m", timestamp="2026-01-01T00:00:00Z", state_version=1,
        breakdown=RetrievalBreakdown(),
    )
    assert ev.event_type == "retrieval_breakdown"
    assert ev.schema_version == 1


# ...12 more tests per scoper §6-7...
```

### Template + mdc additive sections

Each of the 5 agent templates and `memory-layer-defaults.mdc` gets this exact `## Retrieval-source telemetry (required)` section (adjust prose intro slightly to fit the template's voice; keep the key markers below verbatim):

```
## Retrieval-source telemetry (required)

At the end of each phase, emit one `retrieval_breakdown` canonical event with
`payload.sources` keyed by the four canonical buckets — **graph**, **state**,
**canonical**, **file** — each recording `tokens_in` and `tokens_out`. Use
`src/canon_systems/retrieval_telemetry.py::build_retrieval_breakdown_event`
as the canonical constructor. Zero counts are acceptable when a source was
unused or degraded (e.g., axon unreachable); the event must still be emitted
so `canon report` can render the phase.
```

MARKERS that MUST appear in every affected template + mdc:
- `## Retrieval-source telemetry (required)`
- `retrieval_breakdown`
- The 4 bucket names: `graph`, `state`, `canonical`, `file`
- `build_retrieval_breakdown_event`

### `tests/test_agent_templates.py` additive (6 new tests)

```python
def test_memory_layer_defaults_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.rules").joinpath("memory-layer-defaults.mdc").read_text(encoding="utf-8")
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body
    for src in ("graph", "state", "canonical", "file"):
        assert src in body
    assert "build_retrieval_breakdown_event" in body


def test_scoper_template_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("scoper.md").read_text(encoding="utf-8")
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body
    assert "build_retrieval_breakdown_event" in body


def test_cursor_pilot_template_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("cursor-pilot.md").read_text(encoding="utf-8")
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body


def test_implementer_template_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("implementer.md").read_text(encoding="utf-8")
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body


def test_qa_gate_template_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("qa-gate.md").read_text(encoding="utf-8")
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body


def test_release_orchestrator_template_retrieval_telemetry() -> None:
    body = resources.files("canon_systems.templates.agents").joinpath("release-orchestrator.md").read_text(encoding="utf-8")
    assert "## Retrieval-source telemetry (required)" in body
    assert "retrieval_breakdown" in body
```

### `CHANGELOG.md` prepended (top of `[Unreleased] ### Added`)

```
- **E3-T5** Retrieval-source telemetry: new `src/canon_systems/retrieval_telemetry.py` emits `retrieval_breakdown` canonical events with per-source `tokens_in`/`tokens_out` across the fixed `graph/state/canonical/file` 4-bucket contract, reusing `CanonicalEvent` from `backend/shared`. New `canon report` CLI stub (`src/canon_systems/report_cli.py`) reads NDJSON event files and prints deterministic JSON rollups grouped by `phase`/`agent`/`source` with optional `--plan-id`/`--task-id` filters (Wave 6 will replace the stub with a polished CSV/table renderer). All 5 coder-facing agent templates + `memory-layer-defaults.mdc` now require per-phase emission. Tests: `tests/test_retrieval_telemetry.py` (14 new) + `tests/test_agent_templates.py` (6 new).
```

### `README.md` additive (one row in canon commands table)

```
| `canon report --events <ndjson> [--by phase\|agent\|source] [--plan-id X] [--task-id Y]` | Aggregate retrieval_breakdown canonical events into a JSON rollup (Wave 6 will polish into CSV/table). |
```

### `docs/SYSTEM-WORKFLOW.md` §6 additive bullet

```
- **Retrieval-source telemetry**: Each agent phase emits one `retrieval_breakdown` canonical event with `payload.sources` keyed by the fixed `graph/state/canonical/file` 4-bucket contract (see `src/canon_systems/retrieval_telemetry.py`). `canon report --events <ndjson>` provides a stub rollup grouped by `phase`, `agent`, or `source` (Wave-6 polish). Zero counts are valid when a source is unused or degraded; the event is still emitted.
```

## REASONING

1. Read `backend/shared/canon_backend_shared/events.py` to confirm the `CanonicalEvent` signature is unchanged.
2. Read `src/canon_systems/cli.py` around lines 17 / 309-310 / 517-518 to confirm the `graph` subparser wiring pattern is intact.
3. Read each of the 5 agent templates to find a suitable anchor for the new `## Retrieval-source telemetry (required)` subsection — place it adjacent to the existing `## Graph-first retrieval (required)` section from E3-T4.
4. Implement `retrieval_telemetry.py` and `report_cli.py` exactly per spec.
5. Wire `cli.py` additively (3 edits: import, subparser, dispatch).
6. Author `tests/test_retrieval_telemetry.py` with all 14+ tests.
7. Append 6 new tests to `tests/test_agent_templates.py`.
8. Apply the 5 template edits + mdc edit.
9. Update CHANGELOG / README / SYSTEM-WORKFLOW additively.
10. Run `pytest tests/test_retrieval_telemetry.py -q` and `pytest tests/test_agent_templates.py -q` to confirm new tests pass.
11. Run `pytest -q` at repo root to confirm no regressions.
12. Confirm `canon report --help` exits 0, `canon report --events /tmp/does-not-exist.ndjson` exits 3, and `canon report` (no --events) exits 2.
13. Write `HANDOFF_TO_QA` to `.cursor/handoffs/canon-memory-v1/E3-T5/implementer.md`.

## OUTPUT FORMAT

Emit `HANDOFF_TO_QA` with:
- `handoff_id: handoff_20260422_e3t5_retrieval_telemetry`
- `branch: wave/3/canon-memory-v1`
- `files_modified:` exact list (13 paths: 2 new modules, 1 new test file, 10 modifications).
- `acceptance_criteria:` 18 ACs each with `status: MET`, `evidence`, `run_result`, and `covering_tests:` (YAML block-style list, bare pytest node ids or bare file paths).
- `suite_result:` pytest summary lines for focused + full runs.

## STOP CONDITIONS

Stop and surface a blocker (do not improvise) if:
- `CanonicalEvent` signature has changed (field names, schema_version gate).
- `cli.py` subparser pattern has been refactored away from REMAINDER.
- `canon_backend_shared` is not importable from the CLI test environment.
- Any forbidden-surface edit would be required.
