HANDOFF_NOT_READY
  handoff_id: "canon-readiness-gates"
  missing_fields:
    - "scope_packet.ac_traceability"
  quality_failures:
    - "Cursor Pilot DoR requires `ac_traceability` to exist and map every acceptance criterion to at least one implementation target and one verification test. The packet only has `dor_checklist.ac_traceability: pass`, but no actual `ac_traceability` section."
  remediation_steps:
    - "Update the persisted scoper packet to include `scope_packet.ac_traceability` entries for AC1 through AC8."
    - "For each AC mapping, include at least one implementation target from `repository.relevantFiles` and at least one verification test from `constraints.requiredTests` or a specific test intent."
    - "Keep the current constraints unchanged: do not edit the plan file, preserve packet archive behavior, and do not implement `canon readiness check`."
  DOR_FAILURE_LOG:
    stage: "cursor-pilot-preflight"
    root_causes:
      - "missing-required-ac-traceability"
    evidence:
      - "Packet defines AC1 through AC8."
      - "Packet marks `dor_checklist.ac_traceability: pass`."
      - "No `scope_packet.ac_traceability` mapping is present before `END_HANDOFF_TO_CURSOR_PILOT`."
    suggested_agent_improvements:
      - "Require scoper to emit a concrete `ac_traceability` block whenever it marks `dor_checklist.ac_traceability` as pass."
      - "Validate packet structure before persistence so checklist pass values cannot be emitted without supporting traceability evidence."
END_HANDOFF_NOT_READY
