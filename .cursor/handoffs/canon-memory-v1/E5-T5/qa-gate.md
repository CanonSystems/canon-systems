# E5-T5 qa-gate handoff

```text
GATE_RESULTS:
  task_id: E5-T5
  handoff_id: "handoff_20260423T1700Z_E5-T5_synth_show_cli"
  verdict: PASS
  ac_results:
    - id: AC1
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac1_help_exits_zero_and_lists_flags
        - src/canon_systems/synth_cli.py (show subparser declares all 12 flags in _build_parser)
    - id: AC2
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac2_happy_path_streams_plan_and_tasks
        - src/canon_systems/synth_cli.py::_canonical_stream_order + _render_markdown_stream
    - id: AC3
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac3_task_scoping_narrows_to_one_task
        - src/canon_systems/synth_cli.py::_canonical_stream_order (task_filter branch)
    - id: AC4
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac4_streaming_writes_incrementally_per_page
          (stdout spy records 13+ positive-size writes, one per page)
        - src/canon_systems/synth_cli.py::_render_markdown_stream (write+flush per page)
    - id: AC5
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac5_json_mode_deterministic_shape
        - tests/test_cli_synth_show.py::test_ac5_json_mode_back_to_back_byte_identical
          (byte-identical assertion b1==b2 across two back-to-back runs)
        - Manual review: JSON envelope fields are {schema_version, plan_id, task_id,
          cutoff_ts, bucket, prefix, pages, retrieval_breakdown, page_count,
          byte_count}; retrieval_breakdown.payload is deterministic integer counts
          (no event_id/timestamp leakage), pages are sorted by _canonical_stream_order
    - id: AC6
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac6_missing_plan_id_exits_usage
          (rc==SHOW_EXIT_USAGE; stderr JSON {"error":"usage","detail":"...plan_id..."})
        - tests/test_cli_synth_show.py::test_ac6_env_layering_fills_missing_flags
        - tests/test_cli_synth_show.py::test_ac6_flag_overrides_env
        - src/canon_systems/synth_cli.py::_resolve_required_ids (flag>env>error chain)
    - id: AC7
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac7_missing_plan_returns_exit_3_not_found
          (rc==SHOW_EXIT_NOT_FOUND; stderr error=not_found; stdout empty)
    - id: AC8
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac8_access_denied_returns_exit_4_and_emits_denied_event
        - src/canon_systems/synth_cli.py (AccessDenied mapped to SHOW_EXIT_DENIED and
          synth_show event emitted with result="denied")
    - id: AC9
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac9_show_source_has_no_s3_write_calls
          (scans SENTINEL region in src/canon_systems/synth_cli.py; zero matches)
        - tests/test_cli_synth_show.py::test_ac9_source_scan_regex_detects_sample_writes
          (self-check: regex matches each of the 21 forbidden methods)
        - Independent rg scan confirmed: zero forbidden-method call-sites in
          src/canon_systems/synth_cli.py and src/canon_systems/synth_show_reader.py
    - id: AC10
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac10_synth_show_event_written_to_ndjson_on_success
        - tests/test_cli_synth_show.py::test_ac10_synth_show_event_payload_shape
          (asserts payload contains plan_id, task_id, cutoff_ts, bucket, prefix,
          page_count, byte_count, result, format)
        - src/canon_systems/synth_cli.py::_new_show_event + _emit_synth_show_event
    - id: AC11
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac11_retrieval_breakdown_emitted_with_canonical_tokens_out
          (tokens_out on canonical bucket equals totals.tokens_out)
        - tests/test_cli_synth_show.py::test_ac11_retrieval_breakdown_emitted_before_synth_show_in_log
          (added by QA; asserts idx_breakdown < idx_show in the NDJSON log)
        - src/canon_systems/synth_cli.py::_show (retrieval event is emitted before
          synth_show event on every terminal path: usage/not_found/denied/ok)
    - id: AC12
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac12_stream_order_is_canonical_regardless_of_insertion_order
        - tests/test_cli_synth_show.py::test_ac12_cutoff_ts_filters_pages_by_frontmatter_timestamp
        - src/canon_systems/synth_cli.py::_canonical_stream_order sorts tids ASCII-ascending
    - id: AC13
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac13_global_canon_wiring_for_show_verb
          (cli.main(['synth','show','--help']) == 0)
    - id: AC14
      status: PASS
      evidence:
        - tests/test_cli_synth_show.py::test_ac14_reader_shim_source_has_no_s3_write_calls
          (scans entire src/canon_systems/synth_show_reader.py; zero matches)
        - Independent rg confirms zero forbidden-method call sites in the shim
  deviations_reviewed:
    - deviation: "Introduced SHOW_EXIT_* show-scoped exit-code catalog coexisting
        with legacy EXIT_* constants to avoid breaking locked publish tests."
      disposition: accepted
      justification: "legacy EXIT_USAGE=4 and EXIT_TRANSPORT=2 remain importable
        by name; tests/test_cli_synth_publish.py still passes 8/8 with no edits."
    - deviation: "SENTINEL region scoping AC9 inside synth_cli.py; separate
        synth_show_reader.py for AC14."
      disposition: accepted
      justification: "Matches cursor-pilot OUTPUT_FORMAT skeleton D2; preserves
        publish-side put_object call sites outside the scanned region."
    - deviation: "Event seam and retrieval factory reused verbatim from
        stall_watchdog and retrieval_telemetry."
      disposition: accepted
      justification: "Matches cursor-pilot DECISION D3/D4 and avoids reimplementing
        the NDJSON append + dry-run stderr fallback seam."
  tests_added_or_augmented:
    - path: tests/test_cli_synth_show.py
      rationale: "Added test_ac11_retrieval_breakdown_emitted_before_synth_show_in_log
        to explicitly assert retrieval_breakdown event index < synth_show event
        index in the NDJSON log, closing the AC11 ordering sub-requirement that
        the existing test only covered as a presence/totals check."
  suite_result: total=425 passed=425 failed=0 skipped=0
  locked_files_check: PASS
    - backend/synthesis/ untouched
    - backend/synthesis-web/ untouched
    - docs/VAULT-LAYOUT.md untouched
    - backend/shared/canon_backend_shared/events.py untouched
    - .cursor/rules/** untouched
    - .cursor/plans/** untouched
    - tests/test_cli_synth_publish.py untouched (8/8 still pass)
    - tests/test_backend_layout.py untouched
  blocking_issues: []
END_GATE_RESULTS
```
