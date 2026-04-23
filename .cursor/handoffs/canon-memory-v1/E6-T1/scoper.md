# E6-T1 — Scoper handoff

HANDOFF_TO_CURSOR_PILOT

```yaml
packet_kind: SCOPE_PACKET
version: 1
initiative: "Canon Memory Platform v1"
plan_id: "canon_memory_platform_build_d21073e1"
handoff_id: "canon-memory-v1"
task_id: "E6-T1"
title: "Metrics aggregator over canonical events"

goal: |
  A pure-Python aggregator that reads a stream of canonical events and
  emits a **stable** JSON rollup schema covering: lead/cycle time per
  task, per-phase retries, DoR causes, stalls, and token cost — the
  data model that E6-T2 (`canon report` CLI) and downstream dashboards
  consume.

  The aggregator MUST be:
    - stdlib-only (no pandas, no numpy)
    - deterministic (same input → byte-identical JSON output)
    - scope-filterable (company_id, repository_id, plan_id, time window)
    - schema-versioned (`schema_version: 1`; bump on breaking change)
    - read-only (never emits new events, never touches S3)

non_goals:
  - "Building the E6-T2 operator CLI surface (separate task)."
  - "Publishing dashboards (out of scope for v1)."
  - "Historical rehydration from S3 vault (the aggregator operates
     on locally-available NDJSON event logs)."

acceptance_criteria:
  - id: AC1
    description: |
      `src/canon_systems/metrics_rollup.py` exports `aggregate(events,
      scope, window) -> dict` where:
        - `events: Iterable[dict]` (canonical event envelope shape)
        - `scope: {company_id?, repository_id?, plan_id?}`
        - `window: {since?, until?}` ISO-8601 Z timestamps
      and returns a dict with top-level keys `schema_version`,
      `window`, `scope`, `totals`, `lead_time_by_task`,
      `cycle_time_by_phase`, `retries_by_task_phase`, `dor_causes`,
      `stalls`, `token_cost`, `synth_publish`.
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC2
    description: |
      Scope filters applied in order: company_id → repository_id →
      plan_id → window. Events failing any filter are dropped silently
      (no exception); totals reflect post-filter counts.
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC3
    description: |
      `lead_time_by_task[<task_id>]` contains `first_ts`, `last_ts`,
      and `seconds` (integer). `first_ts` = the earliest event
      timestamp tagged with that task_id; `last_ts` = the latest.
      Tasks with a single event have `seconds == 0`.
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC4
    description: |
      `cycle_time_by_phase[<phase>]` reports `{task_count, total_seconds,
      avg_seconds}` for each of the five canonical phases
      (scoper, cursor-pilot, implementer, qa-gate, release-orchestrator).
      Phase cycle time = max(timestamp) - min(timestamp) across all
      events tagged with `agent_name == <phase>` for a given task_id.
      `avg_seconds` is integer-rounded.
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC5
    description: |
      `retries_by_task_phase[<task_id>][<phase>]` counts repeat
      invocations: the first time a phase appears for a task is
      attempt 1; each subsequent `agent_run_id` for the same
      (task_id, phase) with a distinct event_id adds one to the
      retry count. A task with no retries is omitted.
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC6
    description: |
      `dor_causes[<stage>]` aggregates `dor_failure` event counts by
      the payload `stage` field. Stages that never fail are omitted.
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC7
    description: |
      `stalls.total` = count of `lease_stall_detected` events in scope.
      `stalls.by_task[<task_id>]` breaks that count down by task
      (dropping zero-count tasks).
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC8
    description: |
      `token_cost` aggregates `retrieval_breakdown` events into three
      parallel rollups:
        - `by_phase[<phase>]`: sum of `payload.totals.tokens_in/out`
        - `by_agent[<agent>]`: sum of `payload.totals.tokens_in/out`
        - `by_source[<source>]`: sum of
          `payload.sources.<source>.tokens_in/out` across the four
          canonical buckets (graph, state, canonical, file).
      Missing fields coerce to zero; no exceptions.
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC9
    description: |
      `synth_publish` reports `{ok, failed, notifier_ok}` counts of
      `synth_publish` and `vault_sync_notified` events (from E5-T7).
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC10
    description: |
      `totals` summarizes: `events`, `tasks_seen`, `stalls_detected`,
      `dor_failures`, `retries`, `tokens_in`, `tokens_out`.
      `tasks_seen` = len(lead_time_by_task).
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC11
    description: |
      Determinism: calling aggregate() twice on the same events list
      yields byte-identical JSON when serialized with
      `json.dumps(..., sort_keys=True)`.
    test_hook: "tests/test_metrics_rollup.py"
  - id: AC12
    description: |
      `src/canon_systems/metrics_rollup.py` source MUST NOT import
      pandas, numpy, or boto3; MUST NOT touch the filesystem; MUST
      NOT emit canonical events. Enforced by source-scan + behavior
      test.
    test_hook: "tests/test_metrics_rollup.py"

files_to_create:
  - "src/canon_systems/metrics_rollup.py"
  - "tests/test_metrics_rollup.py"
  - ".cursor/handoffs/canon-memory-v1/E6-T1/scoper.md"
  - ".cursor/handoffs/canon-memory-v1/E6-T1/cursor-pilot.md"
  - ".cursor/handoffs/canon-memory-v1/E6-T1/implementer.md"
  - ".cursor/handoffs/canon-memory-v1/E6-T1/qa-gate.md"
  - ".cursor/handoffs/canon-memory-v1/E6-T1/release-status.md"

files_to_modify:
  - "CHANGELOG.md"
  - "docs/SYSTEM-WORKFLOW.md"

locked_files:
  - "src/canon_systems/report_cli.py  # E3-T5 stub frozen; E6-T2 reworks it."
  - "src/canon_systems/retrieval_telemetry.py  # canonical source of token data."
  - "backend/**  # E6 is CLI-side only."

prior_work_references:
  - "E3-T5 retrieval_telemetry + canon report stub (consumer pattern)"
  - "E5-T7 synth_publish / vault_sync_notified event shapes"
  - "E4-T3 lease_stall_detected event shape"

status: READY
END_HANDOFF_TO_CURSOR_PILOT
```
