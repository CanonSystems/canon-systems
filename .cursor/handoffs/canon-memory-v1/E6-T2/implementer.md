# HANDOFF_TO_QA — E6-T2 `canon report` CLI

## Status
READY_FOR_QA

## Summary
Reworked `src/canon_systems/report_cli.py` (previously an E3-T5 stub) to
be the real `canon report` CLI. It now:
- Reads NDJSON canonical event streams with explicit usage / not-found /
  malformed-line exit codes.
- Supports scope filters `--company-id / --repository-id / --plan-id /
  --task-id` and window filters `--since / --until` (ISO-8601 Z).
- Offers two output modes:
  1. Default groupby (`--by {source,phase,agent}`) — preserves the legacy
     `{by, groups}` envelope consumed by `tests/test_retrieval_telemetry.py`.
  2. `--full` — delegates to `metrics_rollup.aggregate` (E6-T1) and emits
     the complete schema.
- Supports `--format {json,csv}`; CSV renders groupby rollups as
  `source,tokens_in,tokens_out` and `--full` rollups as
  `section,key,tokens_in,tokens_out,count` section rows.

## Files
- modify: `src/canon_systems/report_cli.py`
- add:    `tests/test_cli_report.py`

## Test evidence
- `tests/test_cli_report.py` — 13/13 passed (new)
- `tests/test_retrieval_telemetry.py` — 15/15 passed (legacy behaviour preserved)
- Full `tests/` suite — **435/435 passed**, 0 failed.

## Coverage matrix
- AC1 usage: `test_missing_events_flag_exit_2`
- AC2 not-found: `test_missing_file_exit_3`
- AC3 malformed: `test_malformed_line_exit_4`
- AC4 scope filters: `test_task_id_filter_in_groupby_mode`, `test_full_schema_honors_scope_filters`
- AC5 window filters: `test_since_until_filters_drop_out_of_window`, `test_supports_plan_id_since_until_by_flags`
- AC6 legacy envelope: `test_by_agent_behaves_like_by_phase`, `test_supports_plan_id_since_until_by_flags`
- AC7 full rollup: `test_full_schema_emits_metrics_rollup`
- AC8 csv groupby: `test_format_csv_groupby_source`
- AC9 csv full sections: `test_format_csv_full_emits_section_rows`
- AC10 determinism: `test_determinism_json_output_is_stable`
- AC11 top-level dispatch: `test_canon_cli_dispatches_report`
- AC12 full suite green — see test evidence above.

## Deviations
- D1: `cli.main(["report", "--events", ...])` only forwards remainder args
  when preceded by `--`. This is a pre-existing argparse `REMAINDER`
  limitation; the test asserts dispatch through `cli.main(["report", "--",
  ...])`. No CLI surface change required for operators because the legacy
  `run_report_cli` entrypoint continues to work directly.
