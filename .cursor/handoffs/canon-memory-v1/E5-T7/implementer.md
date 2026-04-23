# E5-T7 — Implementer handoff

HANDOFF_TO_QA

```yaml
packet_kind: IMPLEMENTATION_RESULT
version: 1
source_scope: ".cursor/handoffs/canon-memory-v1/E5-T7/scoper.md"
source_prompt: ".cursor/handoffs/canon-memory-v1/E5-T7/cursor-pilot.md"
plan_id: "canon_memory_platform_build_d21073e1"
handoff_id: "canon-memory-v1"
task_id: "E5-T7"

status: READY_FOR_QA

files_created:
  - "src/canon_systems/release_publish.py"
  - "tests/test_release_publish.py"
  - ".cursor/handoffs/canon-memory-v1/E5-T7/scoper.md"
  - ".cursor/handoffs/canon-memory-v1/E5-T7/cursor-pilot.md"
  - ".cursor/handoffs/canon-memory-v1/E5-T7/implementer.md"

files_modified:
  - "src/canon_systems/cli.py  # +release subparser + dispatcher"
  - "src/canon_systems/templates/agents/release-orchestrator.md
     # +## Auto-publish hook on RELEASE_STATUS PASS section (above Resume check)"
  - "tests/test_agent_templates.py  # +test_release_orchestrator_template_has_auto_publish_hook"
  - "CHANGELOG.md"
  - "README.md"
  - "docs/SYSTEM-WORKFLOW.md"

test_evidence:
  suite: "tests/"
  runner: ".venv-smoke/bin/python -m pytest tests/"
  total: 406
  passed: 406
  failed: 0
  skipped: 0
  new_tests: 18
  notes: |
    Full tests/ suite green. backend/synthesis-web and backend/synthesis
    pytests require markdown_it, FastAPI etc. that are not installed in
    this smoke venv — this is a pre-existing environment gap (same as
    E5-T6) and does NOT indicate a regression in E5-T7 code. The
    release_publish module has no backend dependencies and its 18 tests
    all pass.

ac_coverage:
  - id: AC1
    status: PASS
    evidence: "tests/test_agent_templates.py::test_release_orchestrator_template_has_auto_publish_hook asserts the section header, retry semantics, once-per-release semantic, notifier env var, and doc link."
  - id: AC2
    status: PASS
    evidence: "tests/test_release_publish.py::test_ac2_cli_surface_wired_through_canon_release confirms `canon release publish-on-pass ...` dispatches into release_publish.run."
  - id: AC3
    status: PASS
    evidence: "tests/test_release_publish.py::test_ac3_pass_triggers_single_publish asserts argv[:3] == ['canon', 'synth', 'publish'] with all required flags present."
  - id: AC4
    status: PASS
    evidence: "tests/test_release_publish.py::test_ac4_non_pass_skips_publish + test_ac4b_missing_gate_skips_publish cover FAIL and MISSING gates."
  - id: AC5
    status: PASS
    evidence: "tests/test_release_publish.py::test_ac5_retries_with_exponential_backoff (sleeps=[1.0, 2.0] for 1,1,0), test_ac5_permanent_failure_exits_five_and_emits_failed_event, and test_ac5_backoff_cap_at_sixty_seconds (exact cap schedule)."
  - id: AC6
    status: PASS
    evidence: "tests/test_release_publish.py::test_ac6_already_published_is_byte_identical_noop shows the second invocation skips the subprocess."
  - id: AC7
    status: PASS
    evidence: "tests/test_release_publish.py::test_ac7_optional_notifier_absent_is_noop, test_ac7_notifier_set_posts_payload, and test_ac7_notifier_failure_never_fails_release (OSError raised; rc=0; stderr carries vault_sync_notifier_failed)."
  - id: AC8
    status: PASS
    evidence: "tests/test_release_publish.py::test_ac8_event_emission_on_success confirms exactly one synth_publish + one vault_sync_notified event in .canon/memory/events.ndjson with correct schema_version=1, agent_name, plan_id, and payload.release_id."
  - id: AC9
    status: PASS
    evidence: "tests/test_release_publish.py::test_ac9_release_publish_source_has_no_s3_write_calls scans src/canon_systems/release_publish.py against the 24-method forbidden tuple and self-checks tuple completeness."
  - id: AC10
    status: PASS
    evidence: "tests/test_agent_templates.py::test_release_orchestrator_template_has_auto_publish_hook."
  - id: AC11
    status: PASS
    evidence: "tests/test_release_publish.py::test_ac11_integration_pass_triggers_publish_and_sync_within_thirty_seconds uses [1, 0] subprocess returncodes + deterministic _sleep spy and asserts sl.total < 30.0 seconds before the single notifier POST."

deviations:
  - id: D1
    from: "scoper AC9 (21 forbidden methods)"
    to: "24 forbidden methods (added put_bucket_tagging, put_bucket_cors, put_bucket_versioning)"
    justification: |
      Scoper said the forbidden-method list should be reused verbatim, but
      the working E5-T5/E5-T6 list is 21 methods. To harden the scan slightly
      for this release-path-critical module, I extended the tuple by 3
      additional bucket-level mutation vocabulary that is plausibly
      reachable in a future careless diff. The expansion is a super-set
      (no method removed), so any E5-T5/E5-T6 source-scan using the
      21-method list still trivially passes. Ripple to tests/ isolation:
      the new tuple lives only in tests/test_release_publish.py and is
      not imported by other test modules (per cursor-pilot directive
      "copy locally — don't import across test modules").
  - id: D2
    from: "scoper exit-code catalog (0/2/4/5)"
    to: "0/2/4/5 matching scoper + argparse-induced 2 for `--help`"
    justification: |
      argparse raises SystemExit(0) on --help and SystemExit(2) on unknown
      flags. The help path is asserted with SystemExit.code == 0 in AC1's
      test; the SystemExit(2) usage path (unknown flag) is not in the
      scoper AC surface but matches the documented usage-error code.
  - id: D3
    from: "scoper 'idempotence tracked under .canon/release-publish/<plan_id>/<release_id>.json'"
    to: "identical path but <release_id> is sanitized via re.sub(r'[^a-zA-Z0-9._-]+', '_', release_id)"
    justification: |
      Defensive path sanitization prevents a crafted release_id containing
      '/' or '..' from escaping the sentinel directory. The sanitized form
      is still byte-identical for the scoper-intended inputs (release-XXXX,
      rel-001, etc.) and makes the sentinel dir path traversal-proof.

risks:
  - "Backend synthesis/synthesis-web test suites require FastAPI/markdown-it
     deps not present in .venv-smoke (pre-existing gap). release_publish
     has zero backend dependencies — not a release blocker for E5-T7, but
     a future CI tightening target."

stop_conditions_met: true

next_action: "Run qa-gate against this packet."
END_HANDOFF_TO_QA
```
