# E5-T5 implementer handoff

HANDOFF_TO_QA
  handoff_id: "handoff_20260423T1700Z_E5-T5_synth_show_cli"
  task_id: "E5-T5"
  branch: "wave/5/canon-memory-v1"
  files_created:
    - src/canon_systems/synth_show_reader.py
    - tests/test_cli_synth_show.py
  files_modified:
    - src/canon_systems/synth_cli.py
    - CHANGELOG.md
    - README.md
    - docs/SYSTEM-WORKFLOW.md
  acceptance_criteria:
    - id: AC1
      status: MET
      covering_tests: [tests/test_cli_synth_show.py::test_ac1_help_exits_zero_and_lists_flags]
    - id: AC2
      status: MET
      covering_tests: [tests/test_cli_synth_show.py::test_ac2_happy_path_streams_plan_and_tasks]
    - id: AC3
      status: MET
      covering_tests: [tests/test_cli_synth_show.py::test_ac3_task_scoping_narrows_to_one_task]
    - id: AC4
      status: MET
      covering_tests: [tests/test_cli_synth_show.py::test_ac4_streaming_writes_incrementally_per_page]
    - id: AC5
      status: MET
      covering_tests:
        - tests/test_cli_synth_show.py::test_ac5_json_mode_deterministic_shape
        - tests/test_cli_synth_show.py::test_ac5_json_mode_back_to_back_byte_identical
    - id: AC6
      status: MET
      covering_tests:
        - tests/test_cli_synth_show.py::test_ac6_missing_plan_id_exits_usage
        - tests/test_cli_synth_show.py::test_ac6_env_layering_fills_missing_flags
        - tests/test_cli_synth_show.py::test_ac6_flag_overrides_env
    - id: AC7
      status: MET
      covering_tests: [tests/test_cli_synth_show.py::test_ac7_missing_plan_returns_exit_3_not_found]
    - id: AC8
      status: MET
      covering_tests: [tests/test_cli_synth_show.py::test_ac8_access_denied_returns_exit_4_and_emits_denied_event]
    - id: AC9
      status: MET
      covering_tests:
        - tests/test_cli_synth_show.py::test_ac9_show_source_has_no_s3_write_calls
        - tests/test_cli_synth_show.py::test_ac9_source_scan_regex_detects_sample_writes
    - id: AC10
      status: MET
      covering_tests:
        - tests/test_cli_synth_show.py::test_ac10_synth_show_event_written_to_ndjson_on_success
        - tests/test_cli_synth_show.py::test_ac10_synth_show_event_payload_shape
    - id: AC11
      status: MET
      covering_tests: [tests/test_cli_synth_show.py::test_ac11_retrieval_breakdown_emitted_with_canonical_tokens_out]
    - id: AC12
      status: MET
      covering_tests:
        - tests/test_cli_synth_show.py::test_ac12_stream_order_is_canonical_regardless_of_insertion_order
        - tests/test_cli_synth_show.py::test_ac12_cutoff_ts_filters_pages_by_frontmatter_timestamp
    - id: AC13
      status: MET
      covering_tests: [tests/test_cli_synth_show.py::test_ac13_global_canon_wiring_for_show_verb]
    - id: AC14
      status: MET
      covering_tests: [tests/test_cli_synth_show.py::test_ac14_reader_shim_source_has_no_s3_write_calls]
  suite_result: total=424 passed=424 skipped=0
  deviations:
    - "Introduced SHOW_EXIT_* show-scoped exit-code catalog coexisting with legacy EXIT_* constants to avoid breaking locked publish tests."
    - "SENTINEL region scoping AC9 inside synth_cli.py; separate synth_show_reader.py for AC14."
    - "Event seam and retrieval factory reused verbatim from stall_watchdog and retrieval_telemetry."
END_HANDOFF_TO_QA
