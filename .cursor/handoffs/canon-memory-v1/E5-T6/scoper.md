# E5-T6 scoper handoff

```text
HANDOFF_TO_CURSOR_PILOT
  scope_summary: |
    E5-T6 adds Read Path 3 (automatic in-repo mirror) of the E5 human-synthesis plane.
    A new `canon vault sync` subverb performs a read-only S3 → `<repo>/vault/` mirror
    (one-shot or loop), reusing the `SynthShowReader` shim (HEAD/GET/LIST only) and
    `x-amz-meta-content-hash` diff semantics from E5-T5. `canon enable-repo` (the
    actual `canon wire` code path in this repo) is extended to (1) install a
    per-tenant background service (launchd plist on macOS, systemd user unit on
    Linux, schtasks fixture on Windows) that runs `canon vault sync`, (2) register
    a new pre-turn hook `.cursor/hooks/vault-sync-preflight.sh` (idempotently
    merged into `.cursor/hooks.json` beforeSubmitPrompt array), and (3) add an
    idempotent `vault/` gitignore block with sentinel markers. All ticks emit
    canonical `vault_sync` events; failures are tolerated (exponential backoff,
    60 s cap) in loop mode and non-zero only in `--once`. No S3 writes anywhere
    in the sync code path (enforced by source-scan test).

  SCOPE_PACKET:

    identifiers:
      handoff_id: "handoff_20260423T1900Z_E5-T6_vault_sync"
      plan_id: "canon-memory-v1"
      task_id: "E5-T6"
      workstream_id: "wave-5d"
      branch: "wave/5/canon-memory-v1"
      base_commit: "b6c866b (tip after E5-T5 release commit; implementer MUST `git rev-parse HEAD` before branching)"

    story:
      title: "Read path 3 — automatic in-repo S3→vault/ mirror + service install"
      userValue: |
        Operators and agents always have the latest canonical human-synthesis
        vault on disk (<repo>/vault/) without manual invocation. Cursor sessions
        refresh vault/ before any agent turn. Laptops offline? Silent skip,
        catches up next tick. No push-back: vault/ is a one-way projection of
        S3, gitignored, never a user-edit surface.
      acceptanceCriteria:
        - "AC1: `canon vault sync --help` exits 0 and lists flags: --once, --interval-seconds, --company-id, --repository-id, --plan-id, --bucket, --prefix, --target-dir, --aws-region, --aws-profile, --event-log, --dry-run, --install."
        - "AC2: `canon_systems.cli.main(['vault','sync','--help'])` exits 0 (new `vault` top-level subparser with REMAINDER forwarder mirroring the `synth`/`graph` pattern)."
        - "AC3: `canon vault sync --once --plan-id P --company-id c --repository-id r --bucket b --prefix vault/c/r --target-dir <tmp>` mirrors all seeded keys with byte-identical content to S3 bodies and exits 0."
        - "AC4: With `--interval-seconds 0.01` and a fake `_sleep` seam + max-ticks ceiling, the CLI exits 0 after N ticks; each tick performs a full list+diff pass; test asserts ≥2 distinct tick canonical events in the NDJSON log."
        - "AC5: Sync code path imports `canon_systems.synth_show_reader.SynthShowReader` (no re-implementation); only HEAD, GET, and list_objects_v2 paginator calls are issued."
        - "AC6: When every local file's SHA-256 equals the remote `x-amz-meta-content-hash`, a fresh `--once` tick writes zero files; payload reports `pulled_count=0, skipped_count=13, pulled_bytes=0`."
        - "AC7: Hash miss (or missing local file) triggers GET and overwrite; payload reports `pulled_count>=1, pulled_bytes>=len(body)`."
        - "AC8: Deletion propagation: keys present locally but not listed remotely are removed; empty directories pruned up to target-dir root (never prunes target-dir itself)."
        - "AC9: Local edits overwritten silently on hash mismatch vs remote; no warning emitted."
        - "AC10: Without `--target-dir`, walk upward from Path.cwd() to nearest `.git` dir and use `<git-root>/vault/`. If no git root found, exit 2 `{\"error\":\"usage\",\"detail\":\"unable to derive target-dir: not inside a git repo; pass --target-dir\"}`."
        - "AC11: Env layering: CANON_COMPANY_ID, CANON_REPOSITORY_ID, CANON_PLAN_ID, CANON_VAULT_BUCKET, CANON_VAULT_PREFIX, CANON_VAULT_TARGET_DIR, CANON_VAULT_SYNC_INTERVAL_SECONDS, CANON_EVENT_LOG. Flag > env > error. Missing required → exit 2."
        - "AC12: --once mode: EndpointConnectionError → exit 5 (transport) with stderr {\"error\":\"transport\",...} and one vault_sync event with payload.result='error'."
        - "AC13: Loop mode: failed ticks emit vault_sync result='error' events, never crash, sleep per exponential backoff `min(base * 2**(k-1), 60)`, reset to base on success."
        - "AC14: vault_sync event payload shape `{result, pulled_bytes, pulled_count, deleted_count, skipped_count, error_message?}`. --dry-run → stderr via stall_watchdog._emit_event."
        - "AC15: macOS launchd install writes ~/Library/LaunchAgents/systems.canon.vault-sync.<ch>-<rh>.plist (ProgramArguments = canon vault sync ..., RunAtLoad=true, KeepAlive=true); rendered from templates/vault-sync/launchd.plist.tmpl. Idempotent (content-hash check)."
        - "AC16: Linux systemd install writes ~/.config/systemd/user/canon-vault-sync-<ch>-<rh>.service (ExecStart=canon vault sync ..., Restart=always, [Install] WantedBy=default.target); rendered from templates/vault-sync/systemd.service.tmpl."
        - "AC17: Windows schtasks install invokes schtasks.exe /Create via injectable _run_subprocess seam; fake subprocess captures argv + XML body; XML matches templates/vault-sync/schtasks.xml.tmpl."
        - "AC18: Install function dispatches on platform.system() ('Darwin'|'Linux'|'Windows'); each branch unit-testable via monkeypatch."
        - "AC19: `canon enable-repo` appends sentinel-framed idempotent block to <repo>/.gitignore (sentinels: `# >>> canon-systems:vault-sync >>>` / `# <<< canon-systems:vault-sync <<<`) containing `vault/` + `.canon/memory/events.ndjson.lock`. Re-running keeps block byte-identical."
        - "AC20: tests/test_vault_sync.py::test_ac20_sync_source_has_no_s3_write_calls scans src/canon_systems/vault_sync.py for the 20 forbidden boto3 method names (reuse _FORBIDDEN_METHODS from tests/test_cli_synth_show.py); match count = 0."
        - "AC21: `canon enable-repo` installs templates/hooks/vault-sync-preflight.sh (chmod 755) into <repo>/.cursor/hooks/ and merges its entry into .cursor/hooks.json beforeSubmitPrompt via the existing _merge_hook_entries dedupe-by-command logic. Script invokes `canon vault sync --once --dry-run 2>/dev/null || true`. Idempotent."
        - "AC22: tests/test_vault_sync.py PASS with mocked S3; ≥20 tests green under pytest tests/test_vault_sync.py -q."

    repository:
      primaryLanguages: ["python"]
      testFramework: "pytest"
      relevantFiles:
        # ADD
        - "src/canon_systems/vault_sync.py  # NEW CLI + sync loop + install dispatch"
        - "src/canon_systems/templates/hooks/vault-sync-preflight.sh  # NEW Cursor pre-turn hook"
        - "src/canon_systems/templates/vault-sync/launchd.plist.tmpl"
        - "src/canon_systems/templates/vault-sync/systemd.service.tmpl"
        - "src/canon_systems/templates/vault-sync/schtasks.xml.tmpl"
        - "tests/test_vault_sync.py  # NEW ≥20 tests"
        # MODIFY
        - "src/canon_systems/cli.py  # ADD `vault` subparser with REMAINDER forwarder"
        - "src/canon_systems/repo_enable.py  # ADD vault-sync hook install, gitignore block, service install invocation"
        - "src/canon_systems/templates/hooks/hooks.json  # ADD beforeSubmitPrompt entry"
        - "CHANGELOG.md  # prepend bullet"
        - "README.md  # append row to CLI table"
        - "docs/SYSTEM-WORKFLOW.md  # §3 append bullet"
        - "pyproject.toml  # ADD templates/vault-sync to package-data"

    constraints:
      dependencies: ["E5-T2"]
      mustNotBreak:
        - "tests/test_cli_synth_show.py, tests/test_cli_synth_publish.py"
        - "backend/synthesis/synthesis_tests/, backend/synthesis-web/synthesis_web_tests/"
        - "tests/test_backend_layout.py, tests/test_agent_templates.py, tests/test_flow_audit.py, tests/test_qa_validate.py"
        - "tests/test_repo_enable.py"
        - "Existing .cursor/hooks.json beforeSubmitPrompt entries remain unchanged post-merge"
      locked_files:
        - "backend/synthesis/synthesis/**"
        - "backend/synthesis-web/synthesis_web/**"
        - "backend/shared/canon_backend_shared/**"
        - "docs/VAULT-LAYOUT.md, docs/MEMORY-PLATFORM-BACKLOG.md"
        - ".cursor/rules/**, .cursor/plans/**"
        - "src/canon_systems/synth_cli.py, src/canon_systems/synth_show_reader.py (reuse only)"

    deviations_vs_backlog:
      - id: "DEV-A"
        why: "`canon wire` does not exist as a top-level command in this repo; `canon enable-repo` is the established install entrypoint. E5-T6 extends enable_repo() to install vault-sync service + pre-turn hook + gitignore block. `canon vault sync --install` is a convenience that delegates to the same platform-install helper."
      - id: "DEV-B"
        why: "Gitignore block is sentinel-framed so enable-repo can rewrite deterministically without duplicating."
      - id: "DEV-C"
        why: "Pre-turn hook uses --dry-run to keep per-turn latency bounded; background daemon (launchd/systemd/schtasks) is the hot path for actual pulls."
      - id: "DEV-D"
        why: "Default --interval-seconds=10 with module-level _sleep seam for test monkeypatch; backoff min(base * 2**(k-1), 60)."
      - id: "DEV-E"
        why: "New event_type=vault_sync; NOT retrieval_breakdown (this is a service tick, not an agent phase hydration)."

    test_plan:
      - "tests/test_vault_sync.py::test_ac1_help_exits_zero_and_lists_flags"
      - "tests/test_vault_sync.py::test_ac2_global_canon_wiring_for_vault_sync"
      - "tests/test_vault_sync.py::test_ac3_once_mirrors_seeded_vault"
      - "tests/test_vault_sync.py::test_ac4_loop_runs_multiple_ticks_then_exits"
      - "tests/test_vault_sync.py::test_ac5_reuses_synth_show_reader_shim"
      - "tests/test_vault_sync.py::test_ac6_incremental_skip_on_unchanged_hash"
      - "tests/test_vault_sync.py::test_ac7_hash_miss_triggers_download"
      - "tests/test_vault_sync.py::test_ac8_deletion_propagation"
      - "tests/test_vault_sync.py::test_ac9_local_edits_silently_overwritten"
      - "tests/test_vault_sync.py::test_ac10_target_dir_auto_derives_from_git_root"
      - "tests/test_vault_sync.py::test_ac10_outside_git_repo_exits_usage"
      - "tests/test_vault_sync.py::test_ac11_env_layering_fills_missing_flags"
      - "tests/test_vault_sync.py::test_ac11_missing_required_id_exits_usage"
      - "tests/test_vault_sync.py::test_ac12_once_mode_transport_error_exits_5"
      - "tests/test_vault_sync.py::test_ac13_loop_mode_tolerates_transport_errors_with_backoff"
      - "tests/test_vault_sync.py::test_ac14_vault_sync_event_payload_shape"
      - "tests/test_vault_sync.py::test_ac14_dry_run_event_goes_to_stderr"
      - "tests/test_vault_sync.py::test_ac15_launchd_plist_generation_matches_fixture"
      - "tests/test_vault_sync.py::test_ac15_launchd_install_is_idempotent"
      - "tests/test_vault_sync.py::test_ac16_systemd_unit_generation_matches_fixture"
      - "tests/test_vault_sync.py::test_ac17_windows_schtasks_invocation_captured"
      - "tests/test_vault_sync.py::test_ac18_install_dispatch_selects_by_platform_system"
      - "tests/test_vault_sync.py::test_ac19_gitignore_block_is_idempotent"
      - "tests/test_vault_sync.py::test_ac20_sync_source_has_no_s3_write_calls"
      - "tests/test_vault_sync.py::test_ac21_pre_turn_hook_install_is_idempotent"

    do_not:
      - "Do not modify backend/synthesis/**, backend/synthesis-web/**, backend/shared/**, docs/VAULT-LAYOUT.md, docs/MEMORY-PLATFORM-BACKLOG.md, .cursor/rules/**, .cursor/plans/**, src/canon_systems/synth_cli.py, src/canon_systems/synth_show_reader.py."
      - "Do not introduce moto or any new pytest plugin — use the FakeS3 DictS3Client pattern from tests/test_cli_synth_show.py."
      - "Do not issue any boto3 write method call anywhere in src/canon_systems/vault_sync.py or templates."
      - "Do not call real time.sleep inside tests; always monkeypatch the module-level _sleep seam."
      - "Do not actually register launchd/systemd/schtasks daemons from a test — mock filesystem target and subprocess seam."
      - "Do not filter the S3 prefix by plan_id — daemon mirrors the whole tenant prefix; plan_id appears only on canonical-event payload."

END_HANDOFF_TO_CURSOR_PILOT
```
