```
HANDOFF_TO_QA
  task_id: E2-T3
  handoff_id: canon-memory-v1
  branch: wave/2/canon-memory-v1

  summary: |
    Shipped stdlib-only `canon checkpoint` (checkpoint_cli + cli REMAINDER delegation) with five
    subsubcommands, single _http_request seam, wire-shaped flat/nested bodies, exit catalog 0–5,
    living-spec updates, and 45 pytest cases with no live HTTP.

  decisions:
    - "canon" layer uses REMAINDER on `checkpoint` so `run_checkpoint_cli` owns full nested argparse;
      five named subparsers live in `checkpoint_cli._build_parser` (satisfies AC3 intent for
      `checkpoint_command` + five commands).
    - Transport metadata carried via negative HTTP status and synthetic header keys in the third
      tuple element for _http_request when status is -1.
    - 5xx and connection-level failures on read/write/lease return EXIT_TRANSPORT (5).

  open_questions: []

  next_actions:
    - Run qa-gate; parent may persist this block to .cursor/handoffs/canon-memory-v1/E2-T3/implementer.md
    - Parent per-task commit on READY_TO_MERGE (no commit from implementer)

  acceptance_criteria_covered:
    AC1: "src/canon_systems/checkpoint_cli.py" + "tests/test_cli_checkpoint::test_stdlib_only_imports_no_banned_third_party"
    AC2: "checkpoint_cli.py::_http_request" + "tests/...::test_no_live_http_in_suite_monkeypatch_required" (seam + urlopen only here)
    AC3: "checkpoint_cli.py::_build_parser" (dest checkpoint_command, five subparsers) + "tests/...::test_module_exposes_run_entrypoint" (missing sub -> usage)
    AC4: "checkpoint_cli.py::_resolve_base_url" + "tests/...::test_base_url_flag_wins|test_base_url_env_used|test_base_url_default_localhost|test_trailing_slash_stripped_in_url"
    AC5: "tests/...::test_read_missing_scope_flag_exits_usage"
    AC6: "checkpoint_cli.py::_cmd_read" + "tests/...::test_read_happy_200"
    AC7: "checkpoint_cli.py::_cmd_read" + "tests/...::test_read_404_not_found_stderr"
    AC8: "checkpoint_cli.py::_cmd_read" + "tests/...::test_read_transport_exits_5|test_read_5xx_is_transport_5"
    AC9: "tests/...::test_write_missing_lease_exits_usage"
    AC10: "tests/...::test_write_body_file_rejects_forbidden_key|test_write_malformed_json|test_write_body_file_and_stdin_mutex"
    AC11: "checkpoint_cli.py::_cmd_write" + "tests/...::test_write_happy_200_event_header_stderr_and_flat_body"
    AC12: "tests/...::test_write_409_state_version|test_write_409_lease_errors_exit_2|test_write_409_other_code_exit_2"
    AC13: "tests/...::test_write_404_not_found"
    AC14: "tests/...::test_write_422 + transport cases under write/lease 5xx"
    AC15: "tests/...::test_lease_acquire_flat_body_200"
    AC16: "tests/...::test_lease_acquire_409_lease_held_no_token_leak"
    AC17: "tests/...::test_lease_acquire_bad_ttl|write 422"
    AC18: "tests/...::test_lease_renew_nested_scope_ids_200"
    AC19: "tests/...::test_lease_renew_409_mismatch|test_lease_renew_422|test_lease_renew_5xx_transport"
    AC20: "tests/...::test_lease_release_nested_and_200"
    AC21: "tests/...::test_lease_release_409_mismatch|test_lease_release_422"
    AC22: "checkpoint_cli.py EXIT_*" + "tests/...::test_exit_code_catalog_values"
    AC23: "checkpoint_cli.py::run (SystemExit handler)" + "tests/...::test_run_help_exits_0|test_read_missing"
    AC24: "src/canon_systems/cli.py" + "tests/...::test_main_delegates|test_main_checkpoint_help"
    AC25: "cli REMAINDER + run_checkpoint" + "tests/...::test_run_help|test_main_checkpoint_help|implicit read --help path"
    AC26: "tests/test_cli_checkpoint.py" (import pattern + 45 tests)
    AC27: "tests/...::test_no_live_http" + all network tests use monkeypatch
    AC28: "tests/...::test_write_happy_200|test_lease_acquire_flat|test_lease_renew_nested|test_lease_release_nested"
    AC29: "tests/...::test_write_409_state_version|test_lease_acquire_409_lease_held|test_lease_renew_409; test_unwrap_fastapi_404"
    AC30: "tests/...::test_readme_table_row_mentions_checkpoint_above_secrets"
    AC31: "tests/...::test_changelog_e2t3_bullet_above_e2t2_bullet"
    AC32: "tests/...::test_system_workflow_section_6_mentions_checkpoint_and_state_api"
    AC33: "pytest -q, smoke script, python -c" (executed in reproduce gate)
    AC34: "Only allowed paths touched" (forbidden surfaces zero)
    AC35: "No live network in tests" (monkeypatch + seam only)

  files_changed:
    - src/canon_systems/checkpoint_cli.py
    - src/canon_systems/cli.py
    - tests/test_cli_checkpoint.py
    - CHANGELOG.md
    - README.md
    - docs/SYSTEM-WORKFLOW.md

  tests_run:
    - pytest -q (214 passed)
    - SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh (passed)
    - python3 -c "from canon_systems.checkpoint_cli import run; assert callable(run)"
    - python3 -m canon_systems.cli checkpoint --help
    - rg banned imports: zero matches
END_HANDOFF_TO_QA
```
