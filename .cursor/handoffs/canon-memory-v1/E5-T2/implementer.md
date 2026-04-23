```yaml
handoff_id: handoff_20260423_e5t2_synthesis_generator
task_id: E5-T2
branch: wave/5/canon-memory-v1

summary: |
  Implemented deterministic E5-T1 vault projection (redaction, sources, pure generator, S3
  publisher, FastAPI /synth routes), 13 tests under backend/synthesis/synthesis_tests/,
  unwired terraform module infra/terraform/modules/synthesis-vault/, and living-spec/docs.
  Test directory is synthesis_tests/ (not tests/) to avoid Pytest ImportPathMismatch with
  backend/state-api/tests/.../conftest. Full suite: 380 passed. Wikilinks are emitted in
  renderers (citations) rather than a post-pass _wire to avoid double-link corruption.

files_created:
  - backend/synthesis/synthesis/redaction.py
  - backend/synthesis/synthesis/sources.py
  - backend/synthesis/synthesis/generator.py
  - backend/synthesis/synthesis/publisher.py
  - backend/synthesis/synthesis_tests/__init__.py
  - backend/synthesis/synthesis_tests/_fakes.py
  - backend/synthesis/synthesis_tests/conftest.py
  - backend/synthesis/synthesis_tests/test_generator.py
  - backend/synthesis/synthesis_tests/test_endpoints.py
  - backend/synthesis/synthesis_tests/test_publisher_moto.py
  - infra/terraform/modules/synthesis-vault/main.tf
  - infra/terraform/modules/synthesis-vault/variables.tf
  - infra/terraform/modules/synthesis-vault/outputs.tf
  - infra/terraform/modules/synthesis-vault/README.md

files_modified:
  - backend/synthesis/synthesis/__init__.py
  - backend/synthesis/synthesis/main.py
  - backend/synthesis/pyproject.toml
  - backend/synthesis/README.md
  - CHANGELOG.md
  - docs/SYSTEM-WORKFLOW.md

suite_result: total=380 passed=380 skipped=0
verify_command: pytest -q
verify_exit_code: 0

acceptance_criteria:
  - id: AC1
    status: MET
    title: Deterministic output per (plan_id, task_id, cutoff_timestamp)
    evidence: |
      generate_vault sorts by (timestamp, event_id) and filter timestamp<=cutoff; same inputs
      yield identical bytes (test + generator uses stable JSON/YAML, anchor+sorted keys in FM).
    run_result: pytest -q
    covering_tests: |
      backend/synthesis/synthesis_tests/test_generator.py::test_generator_deterministic_byte_identical_output
      backend/synthesis/synthesis_tests/test_generator.py::test_generator_event_ordering_stable_across_permutations

  - id: AC2
    status: MET
    title: Citations link to event_id ([[event:<id>]])
    evidence: |
      Non-_index, non-README .md pages require [[event: in body; event-type pages, task plan
      lines, and indices embed citations.
    run_result: pytest -q
    covering_tests: |
      backend/synthesis/synthesis_tests/test_generator.py::test_citations_present_for_every_rendered_fact
      backend/synthesis/synthesis_tests/test_endpoints.py

  - id: AC3
    status: MET
    title: Idempotent publish; second publish 0 writes
    evidence: |
      SynthesisPublisher compares SHA-256 metadata content-hash; write-once keys skip if
      object exists. Moto: second publish written=0, skipped==len(pages), README head metadata.
    run_result: pytest -q
    covering_tests: |
      backend/synthesis/synthesis_tests/test_publisher_moto.py::test_publish_is_idempotent_no_duplicate_writes
      backend/synthesis/synthesis_tests/test_generator.py

  - id: AC4
    status: MET
    title: GET /synth/vault/changes and /synth/show
    evidence: |
      main.py: since query (422 on bad ISO), show plan/task + format json|markdown, 404 empty.
    run_result: pytest -q
    covering_tests: |
      backend/synthesis/synthesis_tests/test_endpoints.py

  - id: AC5
    status: MET
    title: test_generator 10+ unit tests
    evidence: 10 tests in test_generator.py (all pass)
    run_result: pytest -q
    covering_tests: |
      backend/synthesis/synthesis_tests/test_generator.py

  - id: AC6
    status: MET
    title: Moto idempotent integration
    evidence: test_publish_is_idempotent_no_duplicate_writes with mock_aws
    run_result: pytest -q
    covering_tests: |
      backend/synthesis/synthesis_tests/test_publisher_moto.py::test_publish_is_idempotent_no_duplicate_writes

  - id: AC7
    status: MET
    title: Full suite 367 → 380
    evidence: 380 passed, 0 failed (repo root pytest -q)
    run_result: pytest -q
    covering_tests: |
      (repo-wide suite; synthesis covered by backend/synthesis/synthesis_tests/)

  - id: AC8
    status: MET
    title: Allowlist; no model/raw company/repo; silent payload drop
    evidence: project_safe; project_payload; caplog test; bundle grep for IMC/innermost
    run_result: pytest -q
    covering_tests: |
      backend/synthesis/synthesis_tests/test_generator.py::test_redaction_drops_model_field_from_frontmatter
      backend/synthesis/synthesis_tests/test_generator.py::test_redaction_never_emits_raw_company_id_or_repository_id
      backend/synthesis/synthesis_tests/test_generator.py::test_redaction_silently_drops_unknown_payload_keys

deferred:
  - path: _wire_wikilinks post-pass
    reason: Replaced with explicit wikilinks in renderers to meet citation AC without corrupting
      existing [[...]] (plan/task replacement order issue).
```

## HANDOFF_TO_QA (machine-readable)

```
HANDOFF_TO_QA
  handoff_id: handoff_20260423_e5t2_synthesis_generator
  task_id: E5-T2
  branch: wave/5/canon-memory-v1
  files_created:
    - backend/synthesis/synthesis/redaction.py
    - backend/synthesis/synthesis/sources.py
    - backend/synthesis/synthesis/generator.py
    - backend/synthesis/synthesis/publisher.py
    - backend/synthesis/synthesis_tests/__init__.py
    - backend/synthesis/synthesis_tests/_fakes.py
    - backend/synthesis/synthesis_tests/conftest.py
    - backend/synthesis/synthesis_tests/test_generator.py
    - backend/synthesis/synthesis_tests/test_endpoints.py
    - backend/synthesis/synthesis_tests/test_publisher_moto.py
    - infra/terraform/modules/synthesis-vault/main.tf
    - infra/terraform/modules/synthesis-vault/variables.tf
    - infra/terraform/modules/synthesis-vault/outputs.tf
    - infra/terraform/modules/synthesis-vault/README.md
  files_modified:
    - backend/synthesis/synthesis/__init__.py
    - backend/synthesis/synthesis/main.py
    - backend/synthesis/pyproject.toml
    - backend/synthesis/README.md
    - CHANGELOG.md
    - docs/SYSTEM-WORKFLOW.md
  suite_result: total=380 passed=380 skipped=0
  acceptance_criteria:
    - id: AC1
      status: MET
      evidence: "Determinism: sorted events, stable dict keys, test_generator.*"
      run_result: pytest -q
      covering_tests: |
        backend/synthesis/synthesis_tests/test_generator.py::test_generator_deterministic_byte_identical_output
        backend/synthesis/synthesis_tests/test_generator.py::test_generator_event_ordering_stable_across_permutations
    - id: AC2
      status: MET
      evidence: "[[event:]] in non-index md pages + endpoints"
      run_result: pytest -q
      covering_tests: |
        backend/synthesis/synthesis_tests/test_generator.py::test_citations_present_for_every_rendered_fact
        backend/synthesis/synthesis_tests/test_endpoints.py
    - id: AC3
      status: MET
      evidence: "Moto re-publish 0 writes, content-hash metadata"
      run_result: pytest -q
      covering_tests: |
        backend/synthesis/synthesis_tests/test_publisher_moto.py::test_publish_is_idempotent_no_duplicate_writes
    - id: AC4
      status: MET
      evidence: "synthesis/main.py routes + 422/404"
      run_result: pytest -q
      covering_tests: |
        backend/synthesis/synthesis_tests/test_endpoints.py
    - id: AC5
      status: MET
      evidence: 10 tests in test_generator.py
      run_result: pytest -q
      covering_tests: |
        backend/synthesis/synthesis_tests/test_generator.py
    - id: AC6
      status: MET
      evidence: "moto idempotence"
      run_result: pytest -q
      covering_tests: |
        backend/synthesis/synthesis_tests/test_publisher_moto.py::test_publish_is_idempotent_no_duplicate_writes
    - id: AC7
      status: MET
      evidence: "full suite 380"
      run_result: pytest -q
      covering_tests: |
        (repository pytest -q)
    - id: AC8
      status: MET
      evidence: "redaction + caplog + raw id grep"
      run_result: pytest -q
      covering_tests: |
        backend/synthesis/synthesis_tests/test_generator.py::test_redaction_drops_model_field_from_frontmatter
        backend/synthesis/synthesis_tests/test_generator.py::test_redaction_never_emits_raw_company_id_or_repository_id
        backend/synthesis/synthesis_tests/test_generator.py::test_redaction_silently_drops_unknown_payload_keys
        backend/synthesis/synthesis_tests/test_generator.py::test_redaction_unknown_event_type_routes_to_opaque_with_dropped_payload_marker
END_HANDOFF_TO_QA
```
