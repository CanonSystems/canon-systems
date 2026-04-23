```text
HANDOFF_TO_QA
  handoff_id: "handoff_20260423T1900Z_E5-T6_vault_sync"
  task_id: "E5-T6"
  branch: "wave/5/canon-memory-v1"
  base_head_at_start: "b6c866b2b8f7206e286729213cf331056758641a"

  files_created:
    - "src/canon_systems/vault_sync.py"
    - "src/canon_systems/templates/hooks/vault-sync-preflight.sh"
    - "src/canon_systems/templates/vault-sync/launchd.plist.tmpl"
    - "src/canon_systems/templates/vault-sync/systemd.service.tmpl"
    - "src/canon_systems/templates/vault-sync/schtasks.xml.tmpl"
    - "tests/test_vault_sync.py"
    - ".cursor/handoffs/canon-memory-v1/E5-T6/implementer.md"

  files_modified:
    - "src/canon_systems/cli.py"
    - "src/canon_systems/repo_enable.py"
    - "src/canon_systems/templates/hooks/hooks.json"
    - "pyproject.toml"
    - "CHANGELOG.md"
    - "README.md"
    - "docs/SYSTEM-WORKFLOW.md"
    - "tests/test_repo_enable.py"

  acceptance_criteria:
    - id: AC1
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac1_help_exits_zero_and_lists_flags"]
    - id: AC2
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac2_global_canon_wiring_for_vault_sync"]
    - id: AC3
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac3_once_mirrors_seeded_vault"]
    - id: AC4
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac4_loop_runs_multiple_ticks_then_exits"]
    - id: AC5
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac5_reuses_synth_show_reader_shim"]
    - id: AC6
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac6_incremental_skip_on_unchanged_hash"]
    - id: AC7
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac7_hash_miss_triggers_download"]
    - id: AC8
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac8_deletion_propagation"]
    - id: AC9
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac9_local_edits_silently_overwritten"]
    - id: AC10
      met: true
      covering_tests:
        - "tests/test_vault_sync.py::test_ac10_target_dir_auto_derives_from_git_root"
        - "tests/test_vault_sync.py::test_ac10_outside_git_repo_exits_usage"
    - id: AC11
      met: true
      covering_tests:
        - "tests/test_vault_sync.py::test_ac11_env_layering_fills_missing_flags"
        - "tests/test_vault_sync.py::test_ac11_missing_required_id_exits_usage"
    - id: AC12
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac12_once_mode_transport_error_exits_5"]
    - id: AC13
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac13_loop_mode_tolerates_transport_errors_with_backoff"]
    - id: AC14
      met: true
      covering_tests:
        - "tests/test_vault_sync.py::test_ac14_vault_sync_event_payload_shape"
        - "tests/test_vault_sync.py::test_ac14_dry_run_event_goes_to_stderr"
    - id: AC15
      met: true
      covering_tests:
        - "tests/test_vault_sync.py::test_ac15_launchd_plist_generation_matches_fixture"
        - "tests/test_vault_sync.py::test_ac15_launchd_install_is_idempotent"
    - id: AC16
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac16_systemd_unit_generation_matches_fixture"]
    - id: AC17
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac17_windows_schtasks_invocation_captured"]
    - id: AC18
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac18_install_dispatch_selects_by_platform_system"]
    - id: AC19
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac19_gitignore_block_is_idempotent", "tests/test_repo_enable.py (gitignore block assertion)"]
    - id: AC20
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac20_sync_source_has_no_s3_write_calls"]
    - id: AC21
      met: true
      covering_tests: ["tests/test_vault_sync.py::test_ac21_pre_turn_hook_install_is_idempotent", "tests/test_repo_enable.py (hook files)"]
    - id: AC22
      met: true
      covering_tests: ["tests/test_vault_sync.py (25 tests)"]

  suite_result:
    command: "pytest -q (repo root)"
    total: 450
    passed: 450
    failed: 0
    skipped: 0

  deviations:
    - id: D1
      note: "VAULT_EXIT_* (0,2,3,4,5) defined at module scope; mirrors SHOW_EXIT-style catalog."
    - id: D2
      note: "Module-level _sleep and _run_subprocess seams preserved for tests."
    - id: D3
      note: "Target dir: walk cwd for .git then <root>/vault; override via --target-dir or CANON_VAULT_TARGET_DIR. Tests set CANON_VAULT_SYNC_MAX_TICKS for loop."
    - id: D4
      note: "Content-hash from SynthShowReader head_hash (metadata key content-hash). Empty metadata => treat as miss and pull."
    - id: D5
      note: "Deletion = local files under target not in remote list; prune empty parent dirs up to target root."
    - id: D6
      note: "Pre-turn hook from OUTPUT_FORMAT (set -eu) in templates/hooks/vault-sync-preflight.sh; chmod 0o755 in enable_repo."
    - id: D7
      note: "launchd/systemd: skip write if dest exists with identical text; schtasks: compare against last written XML in ~/.canon (Task Scheduler has no single on-disk 'unit file'); vault_sync_install event either way."
    - id: D8
      note: "install_service dispatches on platform.system(); tests monkeypatch platform + home + subprocess."
    - id: D9
      note: "Gitignore block via _apply_vault_sync_gitignore_block with exact sentinels and body per spec."
    - id: D10
      note: "plan_id on envelope and in vault_sync payload; list_objects_v2 uses full prefix only (no plan_id filter on S3)."
    - id: EXTRA
      note: "When --event-log is unset and not --dry-run, events append to <repo>/.canon/memory/events.ndjson using CANON_SYSTEMS_REPO_ROOT (or cwd) so stall_watchdog._emit_event receives a concrete path (same default pattern as other CLIs)."

END_HANDOFF_TO_QA
```
