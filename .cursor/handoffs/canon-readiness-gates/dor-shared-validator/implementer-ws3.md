HANDOFF_TO_QA_SHARD
shard_id: ws3
task_id: dor-shared-validator
workstream_id: dor-shared-validator
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8

summary: |
  flow-audit already called collect_dor_telemetry_errors_for_task with flow_audit labels (ws1).
  ws3 adds tests: AC1 monkeypatch proves single delegation with correct kwargs; AC4 focused
  exit_code marker test; AC5 proves sample-rate skip never invokes DoR helper. pytest
  tests/test_flow_audit.py: 24 passed.

acceptance_criteria:
  - id: AC1
    status: satisfied
    evidence:
      - "src/canon_systems/flow_audit.py (collect_dor_telemetry_errors_for_task + DorTelemetryLabels.flow_audit)"
      - "tests/test_flow_audit.py::test_flow_audit_ac1_invokes_collect_dor_telemetry_errors_for_task"
  - id: AC4
    status: satisfied
    evidence:
      - "tests/test_flow_audit.py::test_flow_audit_ac4_telemetry_status_requires_exit_code_marker"
      - "tests/test_flow_audit.py::test_flow_audit_dor_telemetry_identity_and_exit_code_marker"
  - id: AC5
    status: satisfied
    evidence:
      - "tests/test_flow_audit.py::test_flow_audit_ac5_sample_rate_skip_does_not_call_dor_helper"
      - "existing non-DoR tests unchanged (memory-health, checkpoints, plan, artifact tokens)"

artifacts:
  - tests/test_flow_audit.py

verification:
  command: "python3 -m pytest tests/test_flow_audit.py -q"
  result: "24 passed"

notes: |
  Graph: canon graph query failed (missing AXON_SERVICE_URL / AWS credentials).
  State: canon checkpoint read transport refused localhost:8080 — skipped checkpoint write.

retrieval_breakdown:
  Constructed via build_retrieval_breakdown_event (implementer phase, illustrative counts):
    graph: tokens_in=80, tokens_out=0 (degraded)
    state: tokens_in=60, tokens_out=120 (checkpoint stderr)
    canonical: tokens_in=400, tokens_out=0 (context-latest)
    file: tokens_in=12000, tokens_out=2200 (flow_audit.py, dor_telemetry.py, test_flow_audit edits)

END_HANDOFF_TO_QA_SHARD
