HANDOFF_NOT_READY
  handoff_id: "canon-readiness-gates"
  missing_fields:
    - "scope_packet.repository"
    - "scope_packet.repository.primaryLanguages"
    - "scope_packet.repository.testFramework"
    - "scope_packet.constraints.mustNotBreak"
  quality_failures:
    - "Scoper packet is not execution-ready for cursor-pilot because the required repository metadata block is absent."
    - "Scoper packet does not define constraints.mustNotBreak, so implementer cannot be given explicit protected behavior/surfaces."
  remediation_steps:
    - "Update the scoper packet to include repository.primaryLanguages and repository.testFramework."
    - "Update the scoper packet to include constraints.mustNotBreak with protected behavior/surfaces for readiness-contract."
    - "Rerun cursor-pilot after the packet includes all required DoR fields."
  DOR_FAILURE_LOG:
    stage: "cursor-pilot-preflight"
    root_causes:
      - "missing_repository_metadata"
      - "missing_must_not_break_constraints"
    evidence:
      - "Packet includes identifiers, story acceptance criteria, dor_checklist pass values, and ac_traceability, but no scope_packet.repository block."
      - "Packet includes scope_packet.constraints.dependencies and requiredTests, but no scope_packet.constraints.mustNotBreak field."
END_HANDOFF_NOT_READY
