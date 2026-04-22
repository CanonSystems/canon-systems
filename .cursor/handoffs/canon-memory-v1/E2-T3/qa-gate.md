# E2-T3 QA-Gate Packet

**Task:** Add `canon checkpoint` read/write/lease CLI subcommand
**Wave branch:** `wave/2/canon-memory-v1`
**Produced by:** qa-gate subagent (ID 167ec91b-29bb-448b-89db-bb0e544c4cd9)

---

```
GATE_RESULTS
  handoff_id: "canon-memory-v1"
  task_id: "E2-T3"
  wave_branch: "wave/2/canon-memory-v1"
  verdict: PASS
  iterations: 1
  regression_checked: true
  notes: "Added test_write_5xx_is_transport_5 for AC14 write 5xx. Full pytest and smoke re-run. Branch-wide git diff to origin/main still touches backend/** and infra/** from earlier wave commits; E2-T3 file allowlist is clean of forbidden paths."
  acceptance_criteria:
    - criterion: "AC1: src/canon_systems/checkpoint_cli.py exists, stdlib-only imports (argparse/json/os/socket/sys/urllib.request/urllib.error/typing), no third-party HTTP clients."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_stdlib_only_imports_no_banned_third_party"
        - "tests/test_cli_checkpoint.py::test_module_exposes_run_entrypoint"
      run_result: "pass — rg finds zero matches for banned imports; module imports callable run()."
    - criterion: "AC2: single _http_request seam; only urlopen call-site in checkpoint_cli.py; all tests monkeypatch the seam."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_no_live_http_in_suite_monkeypatch_required"
      run_result: "pass — seam asserted; test with unstubbed urlopen raises, confirming no live HTTP."
    - criterion: "AC3: argparse tree dest='checkpoint_command', required=True, five subparsers (read/write/lease-acquire/lease-renew/lease-release)."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_missing_checkpoint_subcommand_exits_usage"
      run_result: "pass — argparse exits 4 (EXIT_USAGE) when subcommand missing; five subparsers present in _build_parser."
    - criterion: "AC4: base URL resolution flag > env CANON_STATE_API_URL > default http://localhost:8080; trailing slash stripped."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_base_url_flag_wins"
        - "tests/test_cli_checkpoint.py::test_base_url_env_used"
        - "tests/test_cli_checkpoint.py::test_base_url_default_localhost"
        - "tests/test_cli_checkpoint.py::test_trailing_slash_stripped_in_url"
      run_result: "pass — four precedence cases green."
    - criterion: "AC5: read requires all five scope-id flags; absence returns EXIT_USAGE (4)."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_read_missing_scope_flag_exits_usage"
      run_result: "pass — argparse rejects missing required scope-id flag."
    - criterion: "AC6: read 200 writes server body to stdout and returns EXIT_OK (0)."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_read_happy_200"
      run_result: "pass — stdout JSON equals monkeypatched body; exit 0."
    - criterion: "AC7: read 404 emits stderr envelope {error:'not_found',pk,sk} and returns EXIT_NOT_FOUND (3)."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_read_404_not_found_stderr"
      run_result: "pass — stderr envelope shape verified; exit 3."
    - criterion: "AC8: read transport/5xx → EXIT_TRANSPORT (5) with stderr envelope."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_read_transport_exits_5"
        - "tests/test_cli_checkpoint.py::test_read_5xx_is_transport_5"
      run_result: "pass — both transport and 5xx cases return 5."
    - criterion: "AC9: write requires --lease-token and --expected-version; missing → EXIT_USAGE."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_write_missing_lease_exits_usage"
      run_result: "pass — argparse rejects; --expected-version typed int."
    - criterion: "AC10: --body-file/--body-stdin mutex; forbidden keys rejected; malformed JSON → EXIT_USAGE."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_write_body_file_rejects_forbidden_key_exit_usage"
        - "tests/test_cli_checkpoint.py::test_write_malformed_json_body_file_exit_4"
        - "tests/test_cli_checkpoint.py::test_write_body_file_and_stdin_mutex"
      run_result: "pass — all three validation paths green."
    - criterion: "AC11: write 200 → stdout body + stderr 'canon checkpoint: event_id=<X-Canon-Event-Id>'; FLAT wire body with state_version key."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_write_happy_200_event_header_stderr_and_flat_body"
      run_result: "pass — flat body asserted (no nested lease), event_id stderr log captured, exit 0."
    - criterion: "AC12: write 409 state_version_conflict → EXIT_VERSION_CONFLICT (1); other 409/lease_* → EXIT_LEASE_DENIED (2)."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_write_409_state_version_conflict_unwraps_detail_exit_1"
        - "tests/test_cli_checkpoint.py::test_write_409_lease_errors_exit_2"
        - "tests/test_cli_checkpoint.py::test_write_409_other_code_exit_2"
      run_result: "pass — detail unwrapping preserves expected/actual; exit codes 1 and 2 correct."
    - criterion: "AC13: write 404 → EXIT_NOT_FOUND."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_write_404_not_found"
      run_result: "pass — exit 3."
    - criterion: "AC14: write 422 → EXIT_USAGE; 5xx/transport → EXIT_TRANSPORT."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_write_422"
        - "tests/test_cli_checkpoint.py::test_write_5xx_is_transport_5"
      run_result: "pass — both branches verified."
    - criterion: "AC15: lease-acquire 200 emits flat body (owner_agent_run_id, owner_actor_id, ttl_seconds, five scope-ids); stdout = server body."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_lease_acquire_flat_body_200"
      run_result: "pass — wire body shape asserted flat; stdout mirrors server response."
    - criterion: "AC16: lease-acquire 409 lease_held → stderr envelope without lease_token leak; EXIT_LEASE_DENIED (2)."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_lease_acquire_409_lease_held_no_token_leak"
      run_result: "pass — envelope has owner_agent_run_id + expires_at, no lease_token key."
    - criterion: "AC17: lease-acquire bad --ttl-seconds → EXIT_USAGE."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_lease_acquire_bad_ttl_exit_usage"
      run_result: "pass."
    - criterion: "AC18: lease-renew 200 emits NESTED body {scope_ids:{...5}, lease_token, ttl_seconds}; stdout = {lease_token,expires_at}."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_lease_renew_nested_scope_ids_200"
      run_result: "pass — nested scope_ids asserted; response passthrough verified."
    - criterion: "AC19: lease-renew 409 mismatch → EXIT_LEASE_DENIED; 422 → EXIT_USAGE; 5xx → EXIT_TRANSPORT."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_lease_renew_409_mismatch"
        - "tests/test_cli_checkpoint.py::test_lease_renew_422"
        - "tests/test_cli_checkpoint.py::test_lease_renew_5xx_transport"
      run_result: "pass."
    - criterion: "AC20: lease-release 200 emits NESTED body {scope_ids:{...5}, lease_token}; stdout = {released:true}."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_lease_release_nested_and_200"
      run_result: "pass."
    - criterion: "AC21: lease-release 409 mismatch → EXIT_LEASE_DENIED; 422 → EXIT_USAGE."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_lease_release_409_mismatch"
        - "tests/test_cli_checkpoint.py::test_lease_release_422"
      run_result: "pass."
    - criterion: "AC22: Exit-code catalog EXIT_OK=0, EXIT_VERSION_CONFLICT=1, EXIT_LEASE_DENIED=2, EXIT_NOT_FOUND=3, EXIT_USAGE=4, EXIT_TRANSPORT=5 exposed as module constants."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_exit_code_catalog_values"
      run_result: "pass — six constants match."
    - criterion: "AC23: run() catches argparse SystemExit; --help → 0, usage errors → 4."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_run_help_exits_0"
        - "tests/test_cli_checkpoint.py::test_read_missing_scope_flag_exits_usage"
      run_result: "pass."
    - criterion: "AC24: src/canon_systems/cli.py registers checkpoint subparser and dispatches to run_checkpoint_cli."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_cli_py_registers_checkpoint_subcommand"
        - "tests/test_cli_checkpoint.py::test_main_delegates_to_checkpoint_cli"
      run_result: "pass — REMAINDER delegation verified."
    - criterion: "AC25: canon checkpoint --help works via both direct run() and cli main()."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_run_help_exits_0"
        - "tests/test_cli_checkpoint.py::test_main_checkpoint_help_exits_0"
        - "tests/test_cli_checkpoint.py::test_main_checkpoint_subcommand_help_exits_0"
      run_result: "pass."
    - criterion: "AC26: tests/test_cli_checkpoint.py exists, ≥25 test functions, imports checkpoint_cli + cli.main."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_stdlib_only_imports_no_banned_third_party"
      run_result: "pass — 45 test functions; imports as specified."
    - criterion: "AC27: tests do not perform live HTTP."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_no_live_http_in_suite_monkeypatch_required"
      run_result: "pass."
    - criterion: "AC28: happy-path tests assert flat vs nested wire shapes per endpoint."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_write_happy_200_event_header_stderr_and_flat_body"
        - "tests/test_cli_checkpoint.py::test_lease_acquire_flat_body_200"
        - "tests/test_cli_checkpoint.py::test_lease_renew_nested_scope_ids_200"
        - "tests/test_cli_checkpoint.py::test_lease_release_nested_and_200"
      run_result: "pass."
    - criterion: "AC29: FastAPI detail unwrap on error branches (404/409/lease_held)."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_write_409_state_version_conflict_unwraps_detail_exit_1"
        - "tests/test_cli_checkpoint.py::test_lease_acquire_409_lease_held_no_token_leak"
        - "tests/test_cli_checkpoint.py::test_lease_renew_409_mismatch"
        - "tests/test_cli_checkpoint.py::test_unwrap_fastapi_404_uses_detail_dict"
      run_result: "pass."
    - criterion: "AC30: README.md canon commands table gains a new checkpoint row positioned ABOVE the canon secrets row."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_readme_table_row_mentions_checkpoint_above_secrets"
      run_result: "pass — row precedes secrets row."
    - criterion: "AC31: CHANGELOG.md [Unreleased] ### Added has E2-T3 bullet at top, above the E2-T2 bullet."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_changelog_e2t3_bullet_above_e2t2_bullet"
      run_result: "pass."
    - criterion: "AC32: docs/SYSTEM-WORKFLOW.md §6 gains additive bullet referencing `canon checkpoint` + `state-api`, after memory-health bullet."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_system_workflow_section_6_mentions_checkpoint_and_state_api"
      run_result: "pass."
    - criterion: "AC33: pytest -q, smoke-test.sh, import check, and canon checkpoint --help all exit 0."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_exit_code_catalog_values"
      run_result: "pass — pytest -q exit 0 (221 passed); SMOKE_SKIP_TERRAFORM=1 bash scripts/smoke-test.sh exit 0; python3 -c 'from canon_systems.checkpoint_cli import run; assert callable(run)' exit 0; python3 -m canon_systems.cli checkpoint --help exit 0."
    - criterion: "AC34: E2-T3 touches only src/canon_systems/checkpoint_cli.py, src/canon_systems/cli.py, tests/test_cli_checkpoint.py, CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_changelog_e2t3_bullet_above_e2t2_bullet"
      run_result: "pass — E2-T3 file allowlist ∩ forbidden globs = ∅. (git diff --name-only origin/main shows 26 forbidden paths from earlier E2 wave commits, not this task.)"
    - criterion: "AC35: No live network in the new test file."
      status: PASS
      covering_tests:
        - "tests/test_cli_checkpoint.py::test_no_live_http_in_suite_monkeypatch_required"
      run_result: "pass."
END_GATE_RESULTS
```
