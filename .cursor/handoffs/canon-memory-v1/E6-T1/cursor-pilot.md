# E6-T1 — Cursor-pilot handoff

CURSOR_PILOT_PROMPT

```yaml
packet_kind: IMPLEMENTATION_PROMPT
version: 1
source_scope: ".cursor/handoffs/canon-memory-v1/E6-T1/scoper.md"
plan_id: "canon_memory_platform_build_d21073e1"
handoff_id: "canon-memory-v1"
task_id: "E6-T1"

role: "Implement the metrics aggregator per scoper contract."

task: |
  1. Create `src/canon_systems/metrics_rollup.py`:
     - `SCHEMA_VERSION = 1`
     - `_PHASE_NAMES = ("scoper", "cursor-pilot", "implementer",
       "qa-gate", "release-orchestrator")`
     - Public: `aggregate(events, *, scope=None, window=None) -> dict`
     - Private helpers:
       - `_parse_iso_z(ts) -> datetime | None`
       - `_in_window(ts, since, until) -> bool`
       - `_in_scope(ev, scope) -> bool`
       - `_coerce_int(val) -> int`
     - Use `collections.defaultdict` for bucket accumulation.
     - Sort nested dicts before returning so the top-level dict is
       deterministic under `sort_keys=True` JSON serialization.
     - No I/O, no events emitted, no boto3/pandas/numpy imports.

  2. Create `tests/test_metrics_rollup.py`:
     - A shared `_mk_event(event_type, **overrides)` builder for
       synthetic events (populates all 15 canonical fields).
     - ≥14 tests covering every AC including:
       - empty stream returns zero-filled rollup
       - scope filters drop non-matching events
       - lead time single-event task = 0 seconds
       - phase cycle time avg is integer
       - retry count via distinct agent_run_id per (task_id, phase)
       - dor_causes by stage
       - stall count total + by_task
       - retrieval_breakdown totals + sources split
       - synth_publish ok/failed/notifier_ok
       - totals consistency (sum by_phase tokens == totals.tokens_in/out)
       - determinism: two runs produce byte-identical JSON
       - source scan: no forbidden imports (pandas/numpy/boto3) in module
       - behavior guard: aggregate() with a malformed timestamp string
         silently skips (no raise)

  3. CHANGELOG.md + docs/SYSTEM-WORKFLOW.md: one-paragraph additive
     entry describing the new aggregator and the schema contract.

output_format:
  files_created: ["src/canon_systems/metrics_rollup.py", "tests/test_metrics_rollup.py"]
  files_modified: ["CHANGELOG.md", "docs/SYSTEM-WORKFLOW.md"]

stop_conditions:
  - "All 12 ACs covered with passing tests."
  - "`pytest tests/` green."
  - "No forbidden imports in metrics_rollup.py."

status: READY
END_CURSOR_PILOT_PROMPT
```
