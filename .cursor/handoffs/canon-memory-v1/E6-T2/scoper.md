# SCOPE_PACKET — E6-T2 `canon report` CLI

## SCOPE_SUMMARY
Wire the existing E6-T1 `metrics_rollup.aggregate` behind the first-class
`canon report` subcommand so operators and CI can produce deterministic
JSON/CSV rollups over a canonical NDJSON event stream, with scope and
window filters, and backwards-compatibility with the legacy `{by, groups}`
envelope consumed by earlier tests.

## Goal
- Operators invoke `canon report --events <path>` to get a stable rollup.
- Two modes: default `--by {source,phase,agent}` groupby envelope, and
  `--full` emitting the complete E6-T1 `metrics_rollup` schema.
- Output `--format {json,csv}`; JSON default; CSV section-rows for `--full`.

## Non-goals
- No network / S3 / boto3; no writes of any kind.
- No new event types; only consumes the canonical event schema.
- No re-implementation of aggregation logic; reuses `metrics_rollup.aggregate`.

## Acceptance Criteria
1. `canon report` with no `--events` returns `EXIT_USAGE=2`.
2. `--events /missing` returns `EXIT_FILE_NOT_FOUND=3`.
3. Malformed NDJSON returns `EXIT_MALFORMED=4`.
4. Supports `--plan-id / --task-id / --company-id / --repository-id` filters.
5. Supports `--since / --until` ISO-8601 Z window filters (inclusive).
6. Default mode emits `{by, groups}` JSON compatible with
   `tests/test_retrieval_telemetry.py` expectations.
7. `--full` mode emits the E6-T1 `metrics_rollup` schema via
   `metrics_rollup.aggregate`.
8. `--format csv` renders groupby rollups as `source,tokens_in,tokens_out`.
9. `--format csv --full` renders section rows
   `section,key,tokens_in,tokens_out,count`.
10. Output is byte-identical on repeat runs (determinism).
11. `canon report` top-level dispatch through `cli.main()` is preserved.
12. `tests/` suite stays green.

## Files
- **modify**: `src/canon_systems/report_cli.py`
- **modify**: `CHANGELOG.md`, `README.md`, `docs/SYSTEM-WORKFLOW.md`
- **add**: `tests/test_cli_report.py`
- **unchanged**: `src/canon_systems/metrics_rollup.py`

## Prior work references
- E6-T1 metrics aggregator — `src/canon_systems/metrics_rollup.py`
- E3-T5 legacy retrieval telemetry CLI — `tests/test_retrieval_telemetry.py`
- Canon CLI dispatch — `src/canon_systems/cli.py`
