<!-- CURSOR_PILOT_PROMPT: E5-T6 vault-sync daemon + canon enable-repo extension -->

```text
CURSOR_PILOT_PROMPT

<ROLE>
Implementer subagent in the Cursor editor. Default model: composer-2-fast.
</ROLE>

<TASK>
Consume the SCOPE_PACKET at `.cursor/handoffs/canon-memory-v1/E5-T6/scoper.md`
verbatim. Deliver `canon vault sync` (CLI + one-shot + loop + service install)
and extend `canon enable-repo` to install the pre-turn hook, gitignore block,
and OS-appropriate background service. All 22 ACs are specified; 25 test node
ids are enumerated in the scope packet's test_plan.
</TASK>

<ACCEPTANCE_CRITERIA>
AC1-AC22 (verbatim from scope packet). See SCOPE_PACKET.acceptanceCriteria.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: handoff_20260423T1900Z_E5-T6_vault_sync
- branch: wave/5/canon-memory-v1 (base: b6c866b, E5-T5 release commit)
- Reuse verbatim: SynthShowReader from E5-T5, FakeS3 DictS3Client + _FORBIDDEN_METHODS from tests/test_cli_synth_show.py, stall_watchdog._emit_event seam.
- Existing canon enable-repo code path: src/canon_systems/repo_enable.py (functions `enable_repo`, `_merge_hooks_json`, `_merge_hook_entries`). Extend; do not rewrite.
</CONTEXT>

<REPOSITORY>
- Python 3.11+ stdlib + boto3/botocore only. No new pytest plugins.
- Files to add: src/canon_systems/vault_sync.py, src/canon_systems/templates/{hooks/vault-sync-preflight.sh, vault-sync/launchd.plist.tmpl, vault-sync/systemd.service.tmpl, vault-sync/schtasks.xml.tmpl}, tests/test_vault_sync.py.
- Files to modify (surgical): src/canon_systems/cli.py, src/canon_systems/repo_enable.py, src/canon_systems/templates/hooks/hooks.json, CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md, pyproject.toml (package-data).
- Locked: backend/synthesis/**, backend/synthesis-web/**, backend/shared/**, docs/VAULT-LAYOUT.md, docs/MEMORY-PLATFORM-BACKLOG.md, .cursor/rules/**, .cursor/plans/**, src/canon_systems/synth_cli.py, src/canon_systems/synth_show_reader.py.
</REPOSITORY>

<REASONING>
DECISION D1: Reuse SHOW_EXIT_* catalog from E5-T5 (or mirror it as VAULT_EXIT_*=0/2/3/4/5). Pick VAULT_EXIT_* to keep module-local and avoid cross-module import.

DECISION D2: Module-level `_sleep = time.sleep` seam for test monkeypatch; module-level `_run_subprocess = subprocess.run` seam for schtasks test capture.

DECISION D3: `_derive_target_dir()` walks upward from Path.cwd() to the first ancestor containing `.git`, returning `<ancestor>/vault`. Cache result in tests via explicit `--target-dir` flag.

DECISION D4: Content-hash diff: compute SHA-256 of local file bytes; compare to HEAD `Metadata['content-hash']` (lowercase metadata key per AWS S3 conventions). Missing metadata on remote → always-download (fail safe).

DECISION D5: Deletion set = (local relative paths under target-dir) \ (remote keys stripped of prefix). Recursive prune of empty dirs up to but NOT including target-dir.

DECISION D6: Pre-turn hook script body: `#!/usr/bin/env bash\nset -e\ncanon vault sync --once --dry-run 2>/dev/null || true\n`. Installed with mode 0o755.

DECISION D7: Install idempotence: read existing installed file (plist/service/xml) if present; compute canonical rendered body; if bytes match, skip write + return no-op status. Emit a `vault_sync_install` event on either branch.

DECISION D8: OS dispatch inside `install_service()` via `platform.system()`. Tests monkeypatch platform.system + the file-system target / subprocess seam independently per OS.

DECISION D9: gitignore block manager in repo_enable.py. Re-use existing `_merge_*` idempotence patterns. Sentinels exactly: `# >>> canon-systems:vault-sync >>>` and `# <<< canon-systems:vault-sync <<<`. Block body = `vault/\n.canon/memory/events.ndjson.lock\n`.

DECISION D10: plan_id does NOT filter list_objects_v2; it only appears on canonical-event payload for attribution. Daemon syncs the full tenant prefix (vault/<ch>/<rh>/).
</REASONING>

<OUTPUT_FORMAT>
Minimal, additive changes. Source-scan (AC20) MUST find zero of the 20 forbidden boto3 method names in src/canon_systems/vault_sync.py; reuse the _FORBIDDEN_METHODS tuple from tests/test_cli_synth_show.py.

Launchd plist template MUST include exactly:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>systems.canon.vault-sync.{COMPANY_SHORTHASH}-{REPO_SHORTHASH}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{CANON_BIN}</string>
    <string>vault</string>
    <string>sync</string>
    <string>--interval-seconds</string>
    <string>{INTERVAL_SECONDS}</string>
    <string>--company-id</string>
    <string>{COMPANY_ID}</string>
    <string>--repository-id</string>
    <string>{REPOSITORY_ID}</string>
    <string>--plan-id</string>
    <string>{PLAN_ID}</string>
    <string>--bucket</string>
    <string>{BUCKET}</string>
    <string>--prefix</string>
    <string>{PREFIX}</string>
    <string>--target-dir</string>
    <string>{TARGET_DIR}</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{LOG_OUT}</string>
  <key>StandardErrorPath</key><string>{LOG_ERR}</string>
</dict>
</plist>
```

Systemd unit template MUST include:
```ini
[Unit]
Description=Canon vault sync daemon ({COMPANY_SHORTHASH}-{REPO_SHORTHASH})
After=network-online.target

[Service]
Type=simple
ExecStart={CANON_BIN} vault sync --interval-seconds {INTERVAL_SECONDS} --company-id {COMPANY_ID} --repository-id {REPOSITORY_ID} --plan-id {PLAN_ID} --bucket {BUCKET} --prefix {PREFIX} --target-dir {TARGET_DIR}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

Windows schtasks XML template MUST include the Exec command line identical in spirit to the systemd ExecStart (canon.exe vault sync ...), wrapped in the standard Task Scheduler 1.4 XML envelope.

Pre-turn hook script (src/canon_systems/templates/hooks/vault-sync-preflight.sh):
```bash
#!/usr/bin/env bash
set -eu
canon vault sync --once --dry-run 2>/dev/null || true
```

CHANGELOG.md — prepend bullet:
"- `canon vault sync` read-only S3→<repo>/vault/ mirror (one-shot + loop) with
  exponential backoff, content-hash diff, deletion propagation, and
  `canon enable-repo` integration installing the OS-appropriate background
  daemon (launchd/systemd/schtasks), the sentinel-framed `vault/` gitignore
  block, and the `.cursor/hooks/vault-sync-preflight.sh` pre-turn refresh
  hook. No S3 writes anywhere in the sync code path (20-method source-scan
  gate). (E5-T6)"

README.md — append row to the CLI table (section D mirror):
"| `canon vault sync` | Mirror S3 vault into `<repo>/vault/` (read-only, content-hash diff, offline-tolerant). `--once` for single pull; default loop interval 10s. `--install` registers a per-tenant launchd/systemd/schtasks daemon. |"

docs/SYSTEM-WORKFLOW.md — §3 append bullet:
"- **In-repo vault mirror (E5-T6).** `canon enable-repo` installs a per-tenant
  background daemon (launchd/systemd/schtasks) that runs `canon vault sync
  --interval-seconds 10` and maintains `<repo>/vault/` as a one-way read-only
  projection of the canonical S3 vault. The Cursor `beforeSubmitPrompt` hook
  `.cursor/hooks/vault-sync-preflight.sh` smoke-refreshes before agent work;
  `vault/` is added to `.gitignore` via a sentinel-framed idempotent block."
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
Emit HANDOFF_TO_QA block in .cursor/handoffs/canon-memory-v1/E5-T6/implementer.md with:
- handoff_id, task_id, branch, files_created, files_modified
- acceptance_criteria (AC1..AC22 each MET with covering_tests)
- suite_result (full repo pytest count)
- deviations (D1..D10 as justified above, plus any surprises)
END_HANDOFF_TO_QA
</STOP_CONDITIONS>
```
