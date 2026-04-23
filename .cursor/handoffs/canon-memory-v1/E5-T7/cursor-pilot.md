# E5-T7 — Cursor-pilot handoff

CURSOR_PILOT_PROMPT

```yaml
packet_kind: IMPLEMENTATION_PROMPT
version: 1
source_scope: ".cursor/handoffs/canon-memory-v1/E5-T7/scoper.md"
plan_id: "canon_memory_platform_build_d21073e1"
handoff_id: "canon-memory-v1"
task_id: "E5-T7"

role: |
  You are the implementer for E5-T7. Take the scope packet as ground
  truth. Deliver production-ready code + tests that satisfy every AC
  without modifying locked files.

task: |
  Build the release auto-publish hook:
    1. Create `src/canon_systems/release_publish.py` with:
       - argparse parser: `--release-status-file`, `--release-id`,
         `--plan-id`, `--company-id`, `--repository-id`, `--bucket`,
         `--prefix`, `--events-file`, `--cutoff-timestamp`,
         `--dry-run`, `--notifier-url`, `--retries`, `--backoff-base`,
         `--backoff-cap`, `--state-dir`.
       - `_sleep` + `_run_subprocess` + `_http_post` module-level
         seams so tests can monkeypatch all I/O.
       - `_parse_release_status(text)` that tolerates both the YAML
         literal block the template emits and a JSON body.
       - `_should_publish(status)` returns True iff all three of
         `qa_gate`, `ci_gate`, `merge_gate` equal `PASS`.
       - `_already_published(state_dir, plan_id, release_id)` checks
         the sentinel under `.canon/release-publish/...` and returns
         True if present.
       - `_invoke_publish(...)` runs the retry loop with the exact
         backoff `min(base * 2**(k-1), cap)` schedule — this matches
         vault-sync's backoff for consistency.
       - `_notify(url, payload, timeout)` optional; catch all
         exceptions and return False; never raise.
       - `_emit_synth_publish_event(...)` + `_emit_vault_sync_notified_event(...)`
         both use `canon_backend_shared.events.CanonicalEvent` with
         `schema_version=1`, `event_type="synth_publish"` /
         `"vault_sync_notified"`, and write to
         `.canon/memory/events.ndjson` (reuse
         `stall_watchdog._emit_event`).
       - `run(argv)` returns one of {0, 2, 4, 5}.

    2. Wire `canon release publish-on-pass` into
       `src/canon_systems/cli.py`:
         - Add a `release` subparser (same `REMAINDER` pattern as
           `vault`/`synth`).
         - Dispatch to `release_publish.run(tail)`.

    3. Amend `src/canon_systems/templates/agents/release-orchestrator.md`
       with a new H2 section `## Auto-publish hook on RELEASE_STATUS PASS`.
       Section MUST include:
         - "**Fires once per release, not per task.**"
         - A fenced shell block showing:
           ```
           canon release publish-on-pass \
             --release-status-file .cursor/handoffs/<handoff_id>/release-status.md \
             --release-id <release_id>
           ```
         - Line:
           `Failure-tolerant retry: bounded exponential backoff
            (min(base*2**(k-1), 60s)), default 3 attempts via
            CANON_PUBLISH_RETRIES.`
         - Line:
           `Optional notifier: set CANON_PUBLISH_NOTIFIER_URL to
            signal vault-sync listeners; absence is a clean no-op.`
         - Link to docs/SYSTEM-WORKFLOW.md.

    4. Tests:
       - `tests/test_agent_templates.py`: add
         `test_release_orchestrator_template_has_auto_publish_hook`
         asserting all the phrases above.
       - `tests/test_release_publish.py`: 14+ tests, one per AC +
         source-scan self-check. Reuse `_FORBIDDEN_METHODS` from
         `tests/test_cli_synth_publish.py` (copy locally — don't
         import across test modules). Use a `_run_subprocess` fake
         that records args and returns a configurable exit code.
         For AC11, drive `_sleep` to track cumulative sleep and
         assert the notifier POST happens within 30 simulated
         seconds.

    5. Additive doc updates:
       - CHANGELOG.md: one E5-T7 bullet under Unreleased.
       - README.md: one-line mention under the release-orchestrator
         section.
       - docs/SYSTEM-WORKFLOW.md: one-paragraph description of the
         auto-publish hook with the notifier knob.

context:
  - "Scope packet: .cursor/handoffs/canon-memory-v1/E5-T7/scoper.md."
  - "Locked files: do not touch synth_cli.py, synth_show_reader.py,
     vault_sync.py, repo_enable.py, backend/synthesis**,
     backend/synthesis-web**, docs/VAULT-LAYOUT.md,
     docs/MEMORY-PLATFORM-BACKLOG.md."
  - "Backoff semantics must match E5-T6 for operator predictability."
  - "Forbidden-method list: identical 21-method tuple that E5-T5
     and E5-T6 use."

reasoning:
  - "Keeping the helper as a thin retry/notifier wrapper around the
     existing `canon synth publish` subprocess means the source-scan
     test can enforce zero direct boto3 writes — all mutation stays
     behind the already-audited publish path."
  - "Once-per-release state lives in `.canon/release-publish/...`
     (not the S3 vault) so retries across machine reboots remain
     idempotent without needing an S3 round-trip."
  - "Notifier is strictly best-effort: a slow or missing endpoint
     must never block the release."

output_format:
  files_created:
    - "src/canon_systems/release_publish.py"
    - "tests/test_release_publish.py"
  files_modified:
    - "src/canon_systems/cli.py  # +release subparser dispatch"
    - "src/canon_systems/templates/agents/release-orchestrator.md
       # +Auto-publish hook section"
    - "tests/test_agent_templates.py  # +1 test"
    - "CHANGELOG.md"
    - "README.md"
    - "docs/SYSTEM-WORKFLOW.md"

  handoff:
    packet: "HANDOFF_TO_QA"
    evidence_path:
      ".cursor/handoffs/canon-memory-v1/E5-T7/implementer.md"

stop_conditions:
  - "All 11 ACs covered with passing tests."
  - "`python -m pytest tests/` green (full suite)."
  - "Locked files unchanged (`git diff --stat` confirms)."
  - "No forbidden boto3 writes in release_publish.py source."

status: READY
END_CURSOR_PILOT_PROMPT
```
