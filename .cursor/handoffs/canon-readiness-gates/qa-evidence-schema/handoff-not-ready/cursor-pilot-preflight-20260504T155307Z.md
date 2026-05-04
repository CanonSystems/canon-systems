HANDOFF_NOT_READY
  handoff_id: "canon-readiness-gates"
  missing_fields:
    - "scope_packet.risks_and_assumptions.openQuestions"
  quality_failures:
    - "Scoper packet does not include `risks_and_assumptions.openQuestions` as an empty array, so cursor-pilot cannot verify there are no unresolved open questions before implementation."
  remediation_steps:
    - "Update the scoper packet to include `scope_packet.risks_and_assumptions.openQuestions: []`."
    - "Rerun cursor-pilot after the scoper packet includes the required readiness field."
  DOR_FAILURE_LOG:
    stage: "cursor-pilot-preflight"
    root_causes:
      - "missing_required_readiness_field"
END_HANDOFF_NOT_READY
