GATE_RESULTS
  handoff_id: "handoff_20260424T1545Z_memory_ablation_telemetry_compare"
  verdict: PASS
  acceptance_criteria:
    - criterion: "Experiment metadata is an additive shared block at `payload.comparison` on experiment-bearing canonical events, with required string keys `experiment_id`, `memory_mode`, `run_id`, and `task_attempt_id`; `CanonicalEvent` stays `schema_version=1` and no envelope fields are added or renamed."
      status: PASS
      covering_tests:
        - "tests/test_retrieval_telemetry.py::test_comparison_from_payload_requires_all_keys"
        - "tests/test_retrieval_telemetry.py::test_build_retrieval_breakdown_with_comparison_adds_block"
        - "tests/test_retrieval_telemetry.py::test_canonical_event_envelope_fields_remain_unchanged"
      run_result: "pass: comparison validation, payload insertion, and unchanged envelope-key checks all succeeded"
    - criterion: "A new canonical event type `task_outcome` is defined and wired into the release-orchestrator contract so one event is emitted per task attempt with `payload.comparison` plus final task-result fields sufficient for reporting: outcome/status, `qa_gate`, `elapsed_seconds`, `retry_count`, `reopen_count`, and `rework_count`."
      status: PASS
      covering_tests:
        - "tests/test_retrieval_telemetry.py::test_build_task_outcome_event_shape"
        - "tests/test_agent_templates.py::test_release_orchestrator_template_has_merge_and_deploy_gates"
        - "tests/test_agent_templates.py::test_workspace_release_orchestrator_template_stays_in_sync"
      run_result: "pass: task_outcome payload shape and both release-orchestrator template contracts validated"
    - criterion: "`metrics_rollup` remains deterministic and backwards-compatible for legacy callers, but also supports experiment-aware filtering/comparison so runs can be compared by `memory_mode` or `experiment_id`; compare output includes token totals plus outcome summaries (tasks seen, completed/ready, QA pass/fail, average elapsed seconds, retry/reopen/rework totals), and events missing comparison metadata are retained under an `unlabeled` bucket instead of being dropped."
      status: PASS
      covering_tests:
        - "tests/test_metrics_rollup.py::test_experiment_filter_requires_comparison"
        - "tests/test_metrics_rollup.py::test_compare_by_memory_mode_buckets_unlabeled"
        - "tests/test_metrics_rollup.py::test_compare_rollup_includes_all_outcome_summary_fields"
        - "tests/test_metrics_rollup.py::test_compare_by_experiment_id"
        - "tests/test_metrics_rollup.py::test_aggregate_without_compare_has_no_compare_key"
        - "tests/test_metrics_rollup.py::test_ac11_determinism_byte_identical_json"
      run_result: "pass: experiment filters, unlabeled retention, compare summaries, legacy no-compare shape, and deterministic serialization all succeeded"
    - criterion: "`canon report` adds additive compare/filter UX for this slice: `--experiment-id`, `--memory-mode`, and JSON `--compare-by {memory_mode,experiment_id}` on top of the existing CLI. Existing `--by phase|agent|source`, `--full`, and CSV behavior stay unchanged when compare flags are absent."
      status: PASS
      covering_tests:
        - "tests/test_cli_report.py::test_full_compare_by_adds_section"
        - "tests/test_cli_report.py::test_full_compare_by_experiment_id_groups_output"
        - "tests/test_cli_report.py::test_compare_by_without_full_exits_2"
        - "tests/test_cli_report.py::test_experiment_id_filter_narrowing"
        - "tests/test_cli_report.py::test_memory_mode_filter_narrowing"
        - "tests/test_cli_report.py::test_format_csv_groupby_source"
        - "tests/test_cli_report.py::test_format_csv_full_emits_section_rows"
      run_result: "pass: compare-by, experiment filters, memory-mode filters, and legacy JSON/CSV paths all succeeded"
  iterations: 0
  regression_checked: true
  remaining_gaps:
    - "None."
  notes: "QA added focused coverage for unchanged envelope keys, full compare outcome summaries, CLI memory-mode filtering, compare-by experiment grouping, and release-orchestrator template sync. Graph retrieval degraded with an SSL certificate validation error, and checkpoint hydration was skipped because `CANON_STATE_API_URL` is unset, but repo-based verification and the relevant pytest sweep completed successfully."
END_GATE_RESULTS
