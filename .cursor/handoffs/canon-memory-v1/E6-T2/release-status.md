# RELEASE_STATUS — E6-T2 `canon report` CLI

plan_id: canon-memory-v1
task_id: E6-T2
status: PASS
qa_gate: PASS
suite: 435/435 passed
branch: wave/6/canon-memory-v1
notes: |
  Canon report CLI now emits either the legacy `{by, groups}` envelope or
  the full E6-T1 `metrics_rollup` schema, in JSON or CSV, with full scope
  and time-window filtering. Backwards compatible with the E3-T5 retrieval
  telemetry tests.
