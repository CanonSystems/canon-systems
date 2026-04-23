# E5-T7 — Scoper handoff

HANDOFF_TO_CURSOR_PILOT

```yaml
packet_kind: SCOPE_PACKET
version: 1
initiative: "Canon Memory Platform v1"
plan_id: "canon_memory_platform_build_d21073e1"
handoff_id: "canon-memory-v1"
task_id: "E5-T7"
title: "Auto-publish hook on RELEASE_STATUS PASS + optional notifier"

goal: |
  When release-orchestrator emits a RELEASE_STATUS with qa_gate=PASS,
  ci_gate=PASS, merge_gate=PASS for a wave/release, the Canon workflow
  MUST fire exactly one `canon synth publish` with failure-tolerant
  retry (once per release — not once per task), and MAY optionally
  ping a notifier URL so downstream `canon vault sync` clients pull
  the fresh vault near-instantly instead of waiting for the next
  10-second tick.

  This task delivers three things:
    1. A small orchestrator helper `release_publish.py` that consumes
       a RELEASE_STATUS packet (file or stdin) and, on PASS, invokes
       `canon synth publish` with retries + optional notifier POST.
    2. A `canon release publish-on-pass` CLI surface (via the global
       `canon` parser) that wraps the helper. This is what the release
       orchestrator template calls.
    3. A templated section in
       `src/canon_systems/templates/agents/release-orchestrator.md`
       that tells the release-orchestrator agent to call the helper
       once RELEASE_STATUS hits PASS, and documents the optional
       notifier knob.

non_goals:
  - "Rewriting `canon synth publish` itself (E5-T3 delivered it)."
  - "Changing `canon vault sync` loop cadence (E5-T6 delivered it)."
  - "Introducing a new transport protocol for the notifier (a simple
     HTTP POST suffices; auth is out of scope v1)."
  - "Deploying the notifier endpoint — it is a pluggable URL."

acceptance_criteria:
  - id: AC1
    description: |
      `src/canon_systems/templates/agents/release-orchestrator.md`
      gains an explicit H2 section titled exactly
      `## Auto-publish hook on RELEASE_STATUS PASS` that:
        - names `canon synth publish` as the publish step
        - documents failure-tolerant retry semantics (exponential
          backoff capped at 60s, default max 3 attempts, knob via
          `CANON_PUBLISH_RETRIES` env)
        - documents that the hook fires once per release/wave, not
          once per task
        - documents the **optional** notifier path via
          `CANON_PUBLISH_NOTIFIER_URL` and states that its absence
          is a clean no-op.
    test_hook: "tests/test_agent_templates.py"
  - id: AC2
    description: |
      `canon release publish-on-pass --release-status-file <path>`
      exists (wired through `src/canon_systems/cli.py`) and accepts
      the same envelope fields that the release-orchestrator writes
      to `.cursor/handoffs/<handoff_id>/release-status.md` (YAML or
      JSON body with `qa_gate`, `ci_gate`, `merge_gate`, `plan_id`,
      `task_id`, `initiative`).
    test_hook: "tests/test_release_publish.py"
  - id: AC3
    description: |
      On RELEASE_STATUS with all three gates=PASS the helper invokes
      `canon synth publish` exactly once (subprocess seam mocked in
      tests) with `--plan-id`, `--company-id`, `--repository-id`,
      `--bucket`, `--prefix`, `--cutoff-timestamp`, `--events-file`
      resolved from env/flags.
    test_hook: "tests/test_release_publish.py"
  - id: AC4
    description: |
      On RELEASE_STATUS where any gate != PASS the helper does NOT
      invoke publish and exits 0 with a clear `skipped: non_pass`
      reason in stdout envelope.
    test_hook: "tests/test_release_publish.py"
  - id: AC5
    description: |
      On transient publish failure (non-zero exit from the subprocess
      seam) the helper retries with exponential backoff
      `min(base * 2**(k-1), 60)` starting at `base=1.0`, up to
      `CANON_PUBLISH_RETRIES` attempts (default 3). On permanent
      failure after retries, it exits with a non-zero code and emits
      one canonical `synth_publish` event with `payload.status="failed"`.
    test_hook: "tests/test_release_publish.py"
  - id: AC6
    description: |
      Once-per-release idempotence: a second invocation for the same
      `(plan_id, release_id)` is a byte-identical no-op (exit 0,
      `skipped: already_published` in stdout; no new subprocess
      invocation). Idempotence is tracked under
      `.canon/release-publish/<plan_id>/<release_id>.json`.
    test_hook: "tests/test_release_publish.py"
  - id: AC7
    description: |
      Optional notifier: when `CANON_PUBLISH_NOTIFIER_URL` is set and
      publish succeeds, the helper POSTs a compact JSON payload
      (`{"plan_id","release_id","publish_cutoff","event_id"}`) to the
      URL with a 5-second connect timeout. Failure to notify must NOT
      fail the hook — it emits a
      `vault_sync_notifier_failed` stderr line and still exits 0.
      When the env is unset, no network call is made.
    test_hook: "tests/test_release_publish.py"
  - id: AC8
    description: |
      Canonical event emission: every successful publish invocation
      emits exactly one `synth_publish` event with
      `payload.status in {"ok","failed"}`, plus optionally a
      `vault_sync_notified` event if the notifier POST returned
      2xx. Events land in `.canon/memory/events.ndjson` unless
      `--dry-run` is passed (then stderr).
    test_hook: "tests/test_release_publish.py"
  - id: AC9
    description: |
      `src/canon_systems/release_publish.py` source MUST NOT reference
      any of the 21 forbidden boto3 write methods (same list the
      synth-show/vault-sync scans enforce). All S3 writes must
      continue to flow through the `canon synth publish` subprocess.
    test_hook: "tests/test_release_publish.py"
  - id: AC10
    description: |
      `tests/test_agent_templates.py` gains a new test
      `test_release_orchestrator_template_has_auto_publish_hook`
      asserting the section header, the `canon release publish-on-pass`
      invocation, `CANON_PUBLISH_RETRIES`,
      `CANON_PUBLISH_NOTIFIER_URL`, and the
      "once per release, not per task" phrasing.
    test_hook: "tests/test_agent_templates.py"
  - id: AC11
    description: |
      Integration test: simulated RELEASE_STATUS=PASS triggers
      exactly one publish subprocess call AND, when notifier URL is
      set, a notifier POST within 30 s (test uses a mocked sleep seam
      to guarantee deterministic measurement).
    test_hook: "tests/test_release_publish.py"

files_to_create:
  - "src/canon_systems/release_publish.py"
  - "tests/test_release_publish.py"
  - ".cursor/handoffs/canon-memory-v1/E5-T7/scoper.md"
  - ".cursor/handoffs/canon-memory-v1/E5-T7/cursor-pilot.md"
  - ".cursor/handoffs/canon-memory-v1/E5-T7/implementer.md"
  - ".cursor/handoffs/canon-memory-v1/E5-T7/qa-gate.md"
  - ".cursor/handoffs/canon-memory-v1/E5-T7/release-status.md"

files_to_modify:
  - "src/canon_systems/templates/agents/release-orchestrator.md"
  - "src/canon_systems/cli.py"
  - "tests/test_agent_templates.py"
  - "CHANGELOG.md"
  - "README.md"
  - "docs/SYSTEM-WORKFLOW.md"

locked_files:
  - "src/canon_systems/synth_cli.py  # E5-T3/T5 surface; must not regress."
  - "src/canon_systems/synth_show_reader.py  # E5-T5 reader shim."
  - "src/canon_systems/vault_sync.py  # E5-T6 mirror daemon."
  - "src/canon_systems/repo_enable.py  # gitignore/hooks wiring frozen for E5."
  - "backend/synthesis/**  # E5-T2 boundary."
  - "backend/synthesis-web/**  # E5-T4 boundary."
  - "docs/VAULT-LAYOUT.md"
  - "docs/MEMORY-PLATFORM-BACKLOG.md"

exit_codes:
  - "0 — OK (published, skipped:non_pass, or skipped:already_published)"
  - "2 — usage error"
  - "4 — config error (missing required env/flag resolution)"
  - "5 — publish failed after all retries"

env_layering:
  CANON_PUBLISH_RETRIES: "int, default 3, max 10"
  CANON_PUBLISH_BACKOFF_BASE: "float seconds, default 1.0"
  CANON_PUBLISH_BACKOFF_CAP: "float seconds, default 60.0"
  CANON_PUBLISH_NOTIFIER_URL: "optional; absence disables notifier"
  CANON_PUBLISH_NOTIFIER_TIMEOUT: "float seconds, default 5.0"
  CANON_PLAN_ID: "fallback when --plan-id not passed"
  CANON_COMPANY_ID: "fallback when --company-id not passed"
  CANON_REPOSITORY_ID: "fallback when --repository-id not passed"
  CANON_VAULT_BUCKET: "fallback when --bucket not passed"
  CANON_VAULT_PREFIX: "fallback when --prefix not passed"

prior_work_references:
  - "E5-T3 canon synth publish: src/canon_systems/synth_cli.py + tests/test_cli_synth_publish.py"
  - "E5-T6 canon vault sync: src/canon_systems/vault_sync.py (backoff math + subprocess seam pattern)"
  - "E3-T5 retrieval_breakdown event emission: src/canon_systems/retrieval_telemetry.py"
  - "stall_watchdog._emit_event: the canonical ndjson writer"

dor_checklist:
  - "Locked files identified; no regression to E5-T2/T3/T4/T5/T6 surfaces."
  - "Env layering order fixed: CLI flag > env > default."
  - "Exit-code catalog explicit."
  - "Source-scan forbidden-method list reused verbatim."
  - "Integration-test 30s measurement uses _sleep seam (deterministic)."

status: READY
END_HANDOFF_TO_CURSOR_PILOT
```
