HANDOFF_NOT_READY
  handoff_id: "handoff_20260424T000000Z_stable_dev_memory_urls"
  missing_fields:
    - "scope_packet.risks_and_assumptions"
    - "scope_packet.risks_and_assumptions.openQuestions"
    - "scope_packet.dor_checklist"
    - "scope_packet.dor_checklist.repo_ref_verification"
    - "scope_packet.dor_checklist.ac_traceability"
    - "scope_packet.ac_traceability"
  quality_failures:
    - "Packet is not execution-ready because `risks_and_assumptions.openQuestions` cannot be verified as empty."
    - "Packet is not execution-ready because DoR status for `repo_ref_verification` and `ac_traceability` is missing."
    - "Packet is not execution-ready because no `ac_traceability` map is present to prove every acceptance criterion has at least one implementation target and one verification test."
  remediation_steps:
    - "Add `scope_packet.risks_and_assumptions` with `openQuestions: []` if none remain."
    - "Add `scope_packet.dor_checklist` and set `repo_ref_verification: pass` and `ac_traceability: pass` only if validated by scoper."
    - "Add `scope_packet.ac_traceability` covering all acceptance criteria with at least one implementation target and one verification test per criterion."
  DOR_FAILURE_LOG:
    stage: "cursor-pilot-preflight"
    root_causes:
      - "missing_required_scoper_fields"
      - "missing_acceptance_traceability_artifact"
      - "missing_dor_verification_metadata"
    evidence:
      - "The provided packet includes `identifiers`, `story`, `repository`, and `constraints`, but no `risks_and_assumptions` block."
      - "The provided packet does not include a `dor_checklist` block."
      - "The provided packet does not include an `ac_traceability` section."
    suggested_agent_improvements:
      - "Update the scoper output template to always emit `risks_and_assumptions`, `dor_checklist`, and `ac_traceability` sections, even when values are empty."
      - "Add a scoper-side validation step that rejects packets unless every acceptance criterion is mapped to implementation targets and verification tests."
      - "Make `openQuestions: []` explicit in Ready packets so cursor-pilot can distinguish 'none remain' from 'field omitted'."
END_HANDOFF_NOT_READY
