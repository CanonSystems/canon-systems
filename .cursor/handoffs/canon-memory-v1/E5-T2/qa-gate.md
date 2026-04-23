# E5-T2 QA Gate Results

```
GATE_RESULTS
  handoff_id: handoff_20260423_e5t2_synthesis_generator
  task_id: E5-T2
  branch: wave/5/canon-memory-v1
  verdict: PASS
  regression_checked: true
  iterations: 1
  suite_result: total=382 passed=382 skipped=0
  focused_result: backend/synthesis/synthesis_tests -q → 15 passed
  verify_commands:
    - pytest backend/synthesis/synthesis_tests -q
    - pytest -q
    - rg -n "^(import|from)\s+(datetime|time)(\s|$)" backend/synthesis/synthesis/generator.py backend/synthesis/synthesis/redaction.py backend/synthesis/synthesis/sources.py
    - rg -n "synthesis-vault" infra/terraform/

  acceptance_criteria:
    - id: AC1
      status: MET
      evidence: |
        generate_vault sorts events by (timestamp, event_id) and filters on
        timestamp<=cutoff_timestamp; bytes are identical across two runs and
        across permuted input order. Frontmatter uses anchor keys
        (schema_version, event_id) first then alphabetical via
        render_frontmatter, and JSON attachments use
        json.dumps(..., sort_keys=True, separators=(",", ":")).
      covering_tests:
        - backend/synthesis/synthesis_tests/test_generator.py::test_generator_deterministic_byte_identical_output
        - backend/synthesis/synthesis_tests/test_generator.py::test_generator_event_ordering_stable_across_permutations
        - backend/synthesis/synthesis_tests/test_generator.py::test_frontmatter_key_order_anchors_first_then_alphabetical

    - id: AC2
      status: MET
      evidence: |
        project_safe restricts frontmatter to SAFE_ENVELOPE_FIELDS (10 fields:
        schema_version, event_id, parent_event_id, event_type, plan_id,
        task_id, handoff_id, agent_name, timestamp, state_version) and
        path_shorthashes to SCOPE_SAFE_ALIASED (company_id, repository_id,
        agent_run_id, actor_id) via shorthash(sha256[:8]). The model field is
        DROPPED (never serialized). project_payload dispatches to per-type
        projections for retrieval_breakdown / lease_stall_detected /
        checkpoint_write and returns {} for unknown types; renderer emits
        events/opaque/<event_id>.md with a visible dropped_payload marker.
        caplog records zero log lines during redaction. Bundle bytes do not
        contain raw "IMC" / "innermost" — only shorthashes. Verified
        SAFE/SCOPE_SAFE frozensets line up with docs/VAULT-LAYOUT.md §5.
      covering_tests:
        - backend/synthesis/synthesis_tests/test_generator.py::test_redaction_drops_model_field_from_frontmatter
        - backend/synthesis/synthesis_tests/test_generator.py::test_redaction_never_emits_raw_company_id_or_repository_id
        - backend/synthesis/synthesis_tests/test_generator.py::test_redaction_silently_drops_unknown_payload_keys
        - backend/synthesis/synthesis_tests/test_generator.py::test_redaction_unknown_event_type_routes_to_opaque_with_dropped_payload_marker
        - backend/synthesis/synthesis_tests/test_generator.py::test_shorthashes_are_deterministic_sha256_prefix
        - backend/synthesis/synthesis/redaction.py
        - docs/VAULT-LAYOUT.md

    - id: AC3
      status: MET
      evidence: |
        generator.py::_obsidian_seeds() emits .obsidian/app.json,
        .obsidian/workspace.json, and .obsidian/graph.json as JSON bytes with
        deterministic key ordering. VaultBundle.write_once_keys defaults to
        frozenset({".obsidian/app.json", ".obsidian/workspace.json",
        ".obsidian/graph.json"}), and SynthesisPublisher.publish honors the
        write_once set by skipping objects that already exist (verified in
        moto integration alongside AC5). Dedicated QA-added assertion
        confirms both presence and write-once membership.
      covering_tests:
        - backend/synthesis/synthesis_tests/test_generator.py::test_obsidian_seed_present_and_write_once
        - backend/synthesis/synthesis/generator.py

    - id: AC4
      status: MET
      evidence: |
        Cross-links are emitted directly in renderers (not via a post-pass
        _wire_wikilinks, which the implementer removed after discovering it
        produced doubled [[plan:[[plan:...]]]]). _task_index_for_task emits
        [[plan:<plan_id>]], [[task:<task_id>]], and [[event:<event_id>]];
        _plan_index_for_plan emits [[plan:<plan_id>]] and [[task:<task_id>]];
        per-event rendered pages (retrieval / stall / opaque / agent-run /
        checkpoint) embed [[event:<event_id>]]. QA-added assertion
        test_cross_links_emit_plan_task_event_wikilinks exercises all three
        forms directly against the generated bundle. The existing citation
        test confirms every non-index / non-README page carries at least one
        [[event:<id>]] wikilink.
      covering_tests:
        - backend/synthesis/synthesis_tests/test_generator.py::test_cross_links_emit_plan_task_event_wikilinks
        - backend/synthesis/synthesis_tests/test_generator.py::test_citations_present_for_every_rendered_fact

    - id: AC5
      status: MET
      evidence: |
        SynthesisPublisher writes with Metadata['content-hash'] = sha256(body)
        via put_page (text/markdown; charset=utf-8) and put_attachment
        (application/json). On second publish, list_remote_hashes +
        head_object metadata match per-key, so publish returns written=0 /
        skipped=N. Moto-backed integration test asserts a second publish of
        the same bundle yields zero writes and the README.md head_object
        carries a 64-char lowercase-hex content-hash sidecar.
      covering_tests:
        - backend/synthesis/synthesis_tests/test_publisher_moto.py::test_publish_is_idempotent_no_duplicate_writes
        - backend/synthesis/synthesis/publisher.py

    - id: AC6
      status: MET
      evidence: |
        GET /synth/vault/changes?since=<iso8601> parses the since query via
        datetime.fromisoformat (422 on junk), invokes
        EventSource.iter_events, and returns a JSON envelope with
        schema_version=1, count, since, and a changes[] list sorted
        deterministically by (timestamp, event_id). Verified order across two
        events with non-monotonic insertion order.
      covering_tests:
        - backend/synthesis/synthesis_tests/test_endpoints.py::test_synth_vault_changes_returns_deterministic_change_list

    - id: AC7
      status: MET
      evidence: |
        GET /synth/show?plan_id=...&task_id=...[&format=json|markdown]
        returns a JSON envelope {vault_key, schema_version:1, markdown:...}
        by default and raw markdown (Content-Type: text/markdown;
        charset=utf-8) when format=markdown. The envelope's markdown body
        matches the raw markdown body byte-for-byte. Empty-after-redaction
        returns 404. vault_key resolves to
        plans/<plan_id>/tasks/<task_id>/index.md.
      covering_tests:
        - backend/synthesis/synthesis_tests/test_endpoints.py::test_synth_show_returns_json_envelope_and_markdown_alt_format

    - id: AC8
      status: MET
      evidence: |
        Static import scan confirms no `import datetime`, no
        `from datetime ...`, no `import time`, and no `datetime.now` in
        generator.py, redaction.py, or sources.py. Verified independently by
        a repo-level rg invocation that returned zero matches. datetime is
        only imported in synthesis/main.py (allowed per scope; used solely
        for parsing the since query), not in the pure core modules.
      covering_tests:
        - backend/synthesis/synthesis_tests/test_generator.py::test_no_wallclock_reads_in_generator_module
        - backend/synthesis/synthesis/generator.py
        - backend/synthesis/synthesis/redaction.py
        - backend/synthesis/synthesis/sources.py

  deviations:
    - id: DEV-1
      area: test_directory_name
      summary: |
        Tests live in backend/synthesis/synthesis_tests/ rather than
        backend/synthesis/tests/. Implementer renamed the package to avoid
        pytest ImportPathMismatchError from the duplicate `tests.conftest`
        module name collision with backend/state-api/tests/conftest.py.
        Same pattern is already used by backend/axon-service/axon_service_tests/.
        Documented in backend/synthesis/README.md and docs/SYSTEM-WORKFLOW.md.
      ratified: true

    - id: DEV-2
      area: wikilink_emission_strategy
      summary: |
        The _wire_wikilinks post-pass described in SCOPE_PACKET §2 and
        cursor-pilot §3 was removed. The post-pass produced doubled tokens
        (e.g. [[plan:[[plan:...]]]]) due to ordering collisions between
        raw_id → wikilink substitution and pre-existing wikilinks emitted by
        renderers. Cross-links are now produced directly in each renderer
        (_task_index_for_task, _plan_index_for_plan, per-event renderers).
        AC2 (citations) and the QA-added AC4 (plan/task/event wikilinks)
        verify the final surface; byte determinism is unaffected.
      ratified: true

    - id: DEV-3
      area: files_modified_count
      summary: |
        Cursor-pilot §REPOSITORY declared 14 files created / 5 files
        modified. Implementer packet lists 14 files created / 6 files
        modified (adds docs/SYSTEM-WORKFLOW.md). The additive
        SYSTEM-WORKFLOW.md edit is explicitly permitted by scoper §8
        ("Allowed ... docs/SYSTEM-WORKFLOW.md ... additive Wave-5 entry
        only"). Counted as bookkeeping discrepancy, not a scope violation.
      ratified: true

    - id: DEV-4
      area: suite_total_delta
      summary: |
        Scoper / cursor-pilot committed to 367 → 380 (+13). QA gate added
        two additional tests to make AC3 (.obsidian seed + write_once) and
        AC4 (plan/task wikilinks, in addition to event wikilinks)
        behaviorally explicit — total now 367 → 382 (+15 net, +2 from QA
        augmentation). Both new tests live in
        backend/synthesis/synthesis_tests/test_generator.py and pass
        deterministically with no changes to production code.
      ratified: true

  remaining_gaps: []
  notes: |
    Full suite green (382 passed / 0 skipped / 0 failed). Focused synthesis
    suite green (15 passed). Every AC has ≥1 covering pytest node; AC3 and
    AC4 strengthened with two QA-added tests after observing coverage
    deficits relative to the gate-level AC wording. Redaction allowlist
    cross-checked against docs/VAULT-LAYOUT.md §5 — SAFE_ENVELOPE_FIELDS
    matches the 10 SAFE rows; SCOPE_SAFE_ALIASED matches the 4 SCOPE-SAFE
    rows; `model` is DROPPED from both. Wallclock scan returns zero hits on
    generator.py / redaction.py / sources.py. Terraform module
    infra/terraform/modules/synthesis-vault/ is confirmed unwired (only its
    own files reference the bucket name; infra/terraform/main.tf is
    untouched). Four implementer deviations ratified above. No
    regressions; baseline honored.
END_GATE_RESULTS
```
