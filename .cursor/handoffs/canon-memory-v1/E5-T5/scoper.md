# E5-T5 scoper handoff

```text
HANDOFF_TO_CURSOR_PILOT
  task_id: E5-T5
  title: "Read path 2 — canon synth show for agents"
  handoff_id: "handoff_20260423T1700Z_E5-T5_synth_show_cli"
  plan_id: "canon-memory-v1"
  workstream_id: "wave-5d"
  branch: "wave/5/canon-memory-v1"
  base_commit: "HEAD of wave/5/canon-memory-v1 (tip after E5-T4 commit 23ac5f2; cursor-pilot MUST `git rev-parse HEAD` and record before branching)"

  SCOPE_SUMMARY:
    - WHAT: Add `canon synth show` subverb to `src/canon_systems/synth_cli.py` that streams Obsidian-vault markdown for `(plan_id[, task_id])` from the already-published S3 vault (E5-T2 layout) to stdout, so agents hydrate human-synthesis context during the chain without a browser or a local mirror.
    - WHY: Closes the "agent CLI read path" of E5's three read paths (browser / CLI / in-repo mirror). Agents running the scoper→cursor-pilot→implementer→qa-gate→release-orchestrator chain gain a zero-dependency, memory-bounded way to pull the canonical human-readable projection inline, counted as `canonical` retrieval in the E3-T5 token-accounting telemetry.
    - IN SCOPE: New `show` subparser alongside existing `publish` subparser in `synth_cli.py`; read-only S3VaultReader reuse (or parallel minimal implementation) with HEAD/GET/LIST only; deterministic stream order (plan index → tasks ASCII-sorted → per-task phase pages in canonical phase order); JSON mode with stable snapshot shape; structured exit-code catalog (0/2/3/4/5); canonical `synth_show` event + `retrieval_breakdown` event emission to local NDJSON event log (same seam `stall_watchdog.py` uses); source-scan test enforcing zero boto3 write-method call sites in the new read-side code path; CLI env layering (flag > CANON_* env > error-with-exit-2); ≥12 tests in `tests/test_cli_synth_show.py` modeled on `tests/test_cli_synth_publish.py` fixtures (FakeS3 DictS3Client).
    - OUT OF SCOPE: Regenerating the vault from raw events at query time (publisher already ran in E5-T3); any S3 write path; modifying `backend/synthesis/synthesis/*.py` (E5-T2 ground truth locked); modifying `docs/VAULT-LAYOUT.md` (E5-T1 stable contract); touching `src/canon_systems/cli.py` beyond the one additive dispatch line if the `synth` top-level subparser already routes remainder argv to `synth_cli.run` (verify at CURSOR_PILOT time); HTTP service work (browser path is E5-T4); daemon/in-repo mirror (E5-T6); auto-publish hook (E5-T7).

  SCOPE_PACKET:
    identifiers:
      handoff_id: "handoff_20260423T1700Z_E5-T5_synth_show_cli"
      company_id: "<resolved at runtime from .canon/memory-layer.local.env via shared.ensure_layered_memory_env; CANON_COMPANY_ID takes precedence>"
      repository_id: "<resolved at runtime from .canon/memory-layer.local.env; CANON_REPOSITORY_ID takes precedence>"

    context:
      repo_paths_in_scope:
        - src/canon_systems/synth_cli.py            # ADD `show` subparser + dispatcher + stream/JSON emitters + event emission
        - tests/test_cli_synth_show.py              # CREATE; ≥12 tests; mirrors tests/test_cli_synth_publish.py style + fixtures
        - CHANGELOG.md                              # ADD bullet at TOP of `[Unreleased] ### Added`
        - README.md                                 # APPEND one row to CLI command table (section D mirror)
        - docs/SYSTEM-WORKFLOW.md                   # §3 ADD one bullet describing `canon synth show` agent hydration path
      repo_paths_readonly_for_context:
        - docs/MEMORY-PLATFORM-BACKLOG.md           # §A canonical IDs, §C event envelope, §D CLI surface, §E E5-T5 entry
        - docs/VAULT-LAYOUT.md                      # Obsidian-compatible layout + allowlist (E5-T1; schema_version: 1)
        - backend/synthesis/synthesis/generator.py  # page-key layout, phase ordering, deterministic sort rules (E5-T2 ground truth)
        - backend/synthesis/synthesis/publisher.py  # x-amz-meta-content-hash metadata (consumed via HEAD)
        - backend/synthesis-web/synthesis_web/reader.py  # E5-T4 S3VaultReader reference implementation (READ-ONLY)
        - backend/synthesis-web/synthesis_web_tests/test_reader_source_scan.py  # forbidden-method source-scan precedent
        - src/canon_systems/synth_cli.py            # existing `publish` shape + _s3_client_factory seam + exit-code catalog
        - tests/test_cli_synth_publish.py           # FakeS3 fixtures, help/happy/idempotent/bad-file test patterns, global-wiring pattern
        - src/canon_systems/stall_watchdog.py       # canonical-event emission seam (`_emit_event`, `_DEFAULT_EVENT_LOG=.canon/memory/events.ndjson`)
        - src/canon_systems/retrieval_telemetry.py  # `build_retrieval_breakdown_event`, `RetrievalBreakdown` dataclass (E3-T5)
        - src/canon_systems/shared.py               # `ensure_layered_memory_env`, CANON_COMPANY_ID / CANON_REPOSITORY_ID resolution
        - src/canon_systems/cli.py                  # confirm `synth` subparser already forwards REMAINDER argv to `run_synth_cli` (E5-T3 verified)
        - backend/shared/canon_backend_shared/events.py  # CanonicalEvent dataclass + `to_dict`

      prior_work_references:
        - artifact_id: ".cursor/handoffs/canon-memory-v1/E5-T3/{scoper,cursor-pilot,implementer,qa-gate}.md"
          source: "local"
          relevance: "Precedent for `canon synth <verb>` CLI — argv parsing, _s3_client_factory seam, structured stderr error envelope (`{error, detail}`), FakeS3 harness, global `canon synth ...` wiring test; E5-T5's `show` verb MUST adopt the same exit-code catalog mapped to THIS task's semantics (see dor_checks)."
        - artifact_id: ".cursor/handoffs/canon-memory-v1/E5-T4/scoper.md"
          source: "local"
          relevance: "Delivered `S3VaultReader` with `list_pages`/`read_page`/`read_hash`/`list_vaults` (read-only) + `test_reader_source_scan.py` forbidden-method regex — directly reusable pattern for E5-T5's source-scan test."
        - artifact_id: ".cursor/handoffs/canon-memory-v1/E3-T5/*"
          source: "local"
          relevance: "E3-T5 retrieval_breakdown contract — `retrieval_telemetry.build_retrieval_breakdown_event` with `RETRIEVAL_SOURCES=(graph,state,canonical,file)`. E5-T5 emits ONE such event per invocation with byte counts aggregated into the `canonical` bucket (tokens_out=byte_count; tokens_in=0)."
        - artifact_id: ".cursor/handoffs/canon-memory-v1/E4-T3/*"
          source: "local"
          relevance: "`stall_watchdog.py::_emit_event` seam — canonical event NDJSON append to `.canon/memory/events.ndjson` with `--event-log` override + `--dry-run` stderr fallback. E5-T5 reuses this exact seam for the `synth_show` event."
        - artifact_id: "docs/VAULT-LAYOUT.md"
          source: "local"
          relevance: "Source of truth for vault key layout. Plan page = `plans/<plan_id>/index.md`; task page = `plans/<plan_id>/tasks/<task_id>/index.md`; phase pages = `plans/<plan_id>/tasks/<task_id>/{scoper,cursor-pilot,implementer,qa-gate,release-orchestrator}.md`. E5-T5 streams exactly these keys in canonical order; attachments / agents / events / _index are OUT OF SCOPE for the stream (reserved for future verbs)."
        - artifact_id: "backend/synthesis/synthesis/main.py::synth_show"
          source: "local"
          relevance: "HTTP analog of this CLI — matches our plan/task page-key selection; E5-T5 must stay byte-compatible in markdown body so the CLI and the endpoint return literally the same bytes for overlapping inputs."

    acceptanceCriteria:
      - "AC1: `canon synth show --help` exits 0 and lists the required+optional flags: --plan-id, --task-id, --company-id, --repository-id, --cutoff-ts, --format, --bucket, --prefix, --aws-region, --aws-profile, --event-log, --dry-run."
      - "AC2: Happy-path markdown streaming. Given a FakeS3 seeded with a well-formed vault (README.md, plans/P/index.md, plans/P/tasks/T1/{index,scoper,cursor-pilot,implementer,qa-gate,release-orchestrator}.md, plans/P/tasks/T2/index.md), `canon synth show --plan-id P --format markdown --bucket b --prefix vault/c/r` writes markdown to stdout in the canonical stream order and exits 0."
      - "AC3: Task scoping. Adding `--task-id T1` narrows the stream to plan index + T1 pages only (T2 pages excluded); ordering within T1 unchanged (index.md → scoper.md → cursor-pilot.md → implementer.md → qa-gate.md → release-orchestrator.md)."
      - "AC4: Streaming semantics. Markdown MUST be written incrementally (one `sys.stdout.write()` + `flush()` per page section) — a test asserts the CLI writes stdout after EACH page read from S3, not one buffered write at the end."
      - "AC5: Deterministic JSON mode. `--format json` emits a single JSON object: `{\"schema_version\":1,\"plan_id\":\"P\",\"task_id\":null_or_string,\"cutoff_ts\":\"...\",\"bucket\":\"...\",\"prefix\":\"...\",\"pages\":[{\"slug\":\"plans/P/index.md\",\"kind\":\"plan\",\"markdown\":\"...\",\"event_ids\":[...]}, ...],\"retrieval_breakdown\":{...},\"page_count\":N,\"byte_count\":M}`, sorted keys, `pages` in canonical stream order, byte-identical across two back-to-back runs on unchanged FakeS3."
      - "AC6: Env layering + exit 2 on missing required IDs. Flag > env (CANON_COMPANY_ID, CANON_REPOSITORY_ID, CANON_PLAN_ID, CANON_TASK_ID, CANON_VAULT_BUCKET, CANON_VAULT_PREFIX, CANON_SYNTH_CUTOFF_TS) > error. When `--plan-id` is absent AND `CANON_PLAN_ID` unset → exit 2 with `{\"error\":\"usage\",\"detail\":\"missing required identifier: plan_id (set --plan-id or CANON_PLAN_ID)\"}` on stderr and empty stdout. Same contract for missing company/repository/bucket/prefix."
      - "AC7: Exit 3 on vault not-found. When the expected `plans/<plan_id>/index.md` key is absent from the S3 vault (FakeS3 returns 404/NoSuchKey) → exit 3 with `{\"error\":\"not_found\",\"detail\":\"no vault rendered for plan_id=P (prefix=vault/c/r)\"}` on stderr; stdout is empty."
      - "AC8: Exit 4 on S3 access-denied. When FakeS3 raises `ClientError(AccessDenied, HTTP 403)` on `get_object`/`head_object`/`list_objects_v2` → exit 4 with `{\"error\":\"denied\",\"detail\":\"s3 access denied: <operation>\"}` on stderr; stdout empty; canonical `synth_show` event emitted with result=denied."
      - "AC9: Read-only enforcement (source-scan). `tests/test_cli_synth_show.py::test_show_source_has_no_s3_write_calls` scans the `show`-code-path region for forbidden boto3 method names — put_object, put_object_acl, delete_object, delete_objects, copy_object, copy, upload_file, upload_fileobj, create_multipart_upload, complete_multipart_upload, abort_multipart_upload, put_bucket_policy, put_bucket_acl, restore_object, write_get_object_response — and asserts zero matches."
      - "AC10: Canonical `synth_show` event emission. On every terminal outcome the CLI appends one `CanonicalEvent` line to the event log with `event_type=\"synth_show\"`, `schema_version=1`, and `payload={\"plan_id\":..., \"task_id\":..., \"cutoff_ts\":..., \"bucket\":..., \"prefix\":..., \"page_count\":N, \"byte_count\":M, \"result\":\"found|not_found|denied|error\", \"format\":\"markdown|json\"}`. `--dry-run` writes to stderr."
      - "AC11: `retrieval_breakdown` event emission. Every invocation ALSO appends one `retrieval_breakdown` canonical event with `payload.sources.canonical.tokens_out = byte_count`, others zeroed. Constructed via `retrieval_telemetry.build_retrieval_breakdown_event`. Emitted BEFORE the `synth_show` event."
      - "AC12: Deterministic canonical stream order. Stream emits pages as [plan index] → for each task_id sorted ASCII-ascending: [task index, then phase pages in fixed canonical phase order (scoper, cursor-pilot, implementer, qa-gate, release-orchestrator), skipping missing phases]. `--cutoff-ts` filters pages whose frontmatter `timestamp > cutoff_ts`."
      - "AC13: Global `canon synth show ...` wiring. `canon_systems.cli.main(['synth','show','--help'])` exits 0."
      - "AC14: Read-only source-scan extends to any new reader shim module."

    deviations_vs_backlog:
      - id: "DEV-1"
        why: "ACs expanded from 2 → 14 so qa-gate can gate merge on testable evidence per E3-T5 and E5-T3 precedent."
      - id: "DEV-2"
        why: "Exit-code catalog 0/2/3/4/5 (adds 3=not_found, 5=transport reserve). Diverges from E5-T3 publish but converges with stall_watchdog catalog."
      - id: "DEV-3"
        why: "New CANON_PLAN_ID / CANON_TASK_ID / CANON_VAULT_BUCKET / CANON_VAULT_PREFIX / CANON_SYNTH_CUTOFF_TS / CANON_EVENT_LOG env vars — first codification for agent-side synthesis reads."
      - id: "DEV-4"
        why: "Source of vault data is S3 (read-only), not events-file. Vault IS the canonical projection once E5-T3 publish ran."
      - id: "DEV-6"
        why: "New `synth_show` event_type — backlog §C explicitly permits additive event types."
      - id: "DEV-7"
        why: "Test location is repo-root `tests/` matching E5-T3 precedent (backlog done_signal: tests/test_cli_synth_show.py)."

    test_plan:
      - "tests/test_cli_synth_show.py::test_ac1_help_exits_zero_and_lists_flags"
      - "tests/test_cli_synth_show.py::test_ac2_happy_path_streams_plan_and_tasks"
      - "tests/test_cli_synth_show.py::test_ac3_task_scoping_narrows_to_one_task"
      - "tests/test_cli_synth_show.py::test_ac4_streaming_writes_incrementally_per_page"
      - "tests/test_cli_synth_show.py::test_ac5_json_mode_deterministic_shape"
      - "tests/test_cli_synth_show.py::test_ac5_json_mode_back_to_back_byte_identical"
      - "tests/test_cli_synth_show.py::test_ac6_missing_plan_id_exits_usage"
      - "tests/test_cli_synth_show.py::test_ac6_env_layering_fills_missing_flags"
      - "tests/test_cli_synth_show.py::test_ac6_flag_overrides_env"
      - "tests/test_cli_synth_show.py::test_ac7_missing_plan_returns_exit_3_not_found"
      - "tests/test_cli_synth_show.py::test_ac8_access_denied_returns_exit_4_and_emits_denied_event"
      - "tests/test_cli_synth_show.py::test_ac9_show_source_has_no_s3_write_calls"
      - "tests/test_cli_synth_show.py::test_ac9_source_scan_regex_detects_sample_writes"
      - "tests/test_cli_synth_show.py::test_ac10_synth_show_event_written_to_ndjson_on_success"
      - "tests/test_cli_synth_show.py::test_ac10_synth_show_event_payload_shape"
      - "tests/test_cli_synth_show.py::test_ac11_retrieval_breakdown_emitted_with_canonical_tokens_out"
      - "tests/test_cli_synth_show.py::test_ac12_stream_order_is_canonical_regardless_of_insertion_order"
      - "tests/test_cli_synth_show.py::test_ac12_cutoff_ts_filters_pages_by_frontmatter_timestamp"
      - "tests/test_cli_synth_show.py::test_ac13_global_canon_wiring_for_show_verb"
      - "tests/test_cli_synth_show.py::test_ac14_reader_shim_source_has_no_s3_write_calls (CONDITIONAL on option-A module split)"

    do_not:
      - "Modify backend/synthesis/synthesis/, backend/synthesis-web/, docs/VAULT-LAYOUT.md, backend/shared/canon_backend_shared/events.py, .cursor/rules/**, .cursor/plans/**."
      - "Add any S3 write call sites in the show code path."
      - "Regenerate the vault at show time — read the already-published S3 vault only."
      - "Edit tests/test_cli_synth_publish.py or tests/test_backend_layout.py."
      - "Add a new top-level `canon` subparser; reuse the existing `synth` REMAINDER forwarder."
      - "Introduce moto or any new pytest plugin; extend the existing FakeS3 DictS3Client pattern."

END_HANDOFF_TO_CURSOR_PILOT
```
