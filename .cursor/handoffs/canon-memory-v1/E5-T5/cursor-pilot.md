<!-- CURSOR_PILOT_PROMPT: E5-T5 synth-show agent CLI -->

```text
CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
Default model: `composer-2-fast`.
</ROLE>

<TASK>
Add a read-only `canon synth show` subverb to `src/canon_systems/synth_cli.py`
that streams the Obsidian-compatible markdown vault for a given
`(plan_id[, task_id])` from the already-published S3 vault (E5-T2 layout) to
stdout — without regenerating the vault, without any S3 write call, and
without a browser. Closes the "agent CLI read path" of E5's three read
paths so the scoper → cursor-pilot → implementer → qa-gate →
release-orchestrator chain can hydrate canonical human-synthesis context
inline, counted as the `canonical` bucket in the E3-T5 `retrieval_breakdown`
token accounting.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: `canon synth show --help` exits 0 and lists the required+optional
  flags: --plan-id, --task-id, --company-id, --repository-id, --cutoff-ts,
  --format, --bucket, --prefix, --aws-region, --aws-profile, --event-log,
  --dry-run.
- AC2: Happy-path markdown streaming given a FakeS3 seeded with a well-formed
  vault; exits 0, writes canonical stream order to stdout.
- AC3: `--task-id T1` narrows to plan index + T1 pages only; phase order
  preserved (index → scoper → cursor-pilot → implementer → qa-gate →
  release-orchestrator).
- AC4: Incremental streaming: one sys.stdout.write+flush per page; a stdout
  spy records >= page_count writes of positive size.
- AC5: Deterministic JSON mode with sorted keys, canonical `pages` order,
  byte-identical across two back-to-back runs on unchanged FakeS3.
- AC6: Env layering flag>env>error; exit 2 with
  `{"error":"usage","detail":"missing required identifier: <name> (set <flag> or <ENV>)"}`
  when any required-5 id is missing.
- AC7: Exit 3 with `{"error":"not_found","detail":"no vault rendered for plan_id=P (prefix=...)"}`
  when plan index key absent; stdout empty.
- AC8: Exit 4 with `{"error":"denied","detail":"s3 access denied: <op>"}`
  on ClientError(AccessDenied,403); synth_show event emitted with result=denied.
- AC9: Source-scan: the SENTINEL-scoped show region in synth_cli.py has zero
  forbidden boto3 write method call sites (21-method set). Self-check test
  proves the regex detects each forbidden name.
- AC10: Canonical `synth_show` event (schema_version=1) appended per
  terminal outcome, with payload
  `{plan_id,task_id,cutoff_ts,bucket,prefix,page_count,byte_count,result,format}`.
  `--dry-run` diverts to stderr.
- AC11: `retrieval_breakdown` event emitted BEFORE the `synth_show` event,
  with `payload.sources.canonical.tokens_out = byte_count`, others zero,
  built via retrieval_telemetry.build_retrieval_breakdown_event.
- AC12: Stream emits [plan index] → for each task_id sorted ASCII-ascending
  [task index, phases in fixed canonical order], regardless of input order.
  `--cutoff-ts` excludes pages whose frontmatter `timestamp > cutoff_ts`.
- AC13: Global `canon synth show --help` wiring via cli.py REMAINDER dispatch
  (no edit needed; test asserts `cli.main(['synth','show','--help'])` = 0).
- AC14: `src/canon_systems/synth_show_reader.py` has zero forbidden write
  call sites (same 21-method regex).
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: handoff_20260423T1700Z_E5-T5_synth_show_cli
- plan_id: canon-memory-v1
- workstream_id: wave-5d
- branch: wave/5/canon-memory-v1
- base_commit: HEAD of wave/5/canon-memory-v1 (tip after E5-T4 commit 23ac5f2).
- Prior work: E5-T3 `canon synth publish` CLI (FakeS3 harness + `_s3_client_factory`
  seam), E5-T4 `S3VaultReader` (read-only pattern + forbidden-method regex),
  E3-T5 retrieval_breakdown contract, E4-T3 `stall_watchdog._emit_event` seam
  (.canon/memory/events.ndjson default; --dry-run stderr fallback).
</CONTEXT>

<REPOSITORY>
- Python 3.11+, stdlib + boto3/botocore only.
- pytest. No new plugins (no moto, no pytest-mock unless already present).
- Files in scope:
  - src/canon_systems/synth_cli.py  (ADD show subparser, dispatcher, helpers,
    events; wrap show region in SENTINEL comments)
  - src/canon_systems/synth_show_reader.py  (CREATE read-only HEAD+GET+LIST shim)
  - tests/test_cli_synth_show.py  (CREATE; 20 node ids)
  - CHANGELOG.md  (prepend bullet)
  - README.md  (append one row to CLI table)
  - docs/SYSTEM-WORKFLOW.md  (§3 append one bullet)
- Locked: backend/synthesis/synthesis/**, backend/synthesis-web/**,
  docs/VAULT-LAYOUT.md, backend/shared/canon_backend_shared/events.py,
  .cursor/rules/**, .cursor/plans/**, tests/test_cli_synth_publish.py,
  tests/test_backend_layout.py.
</REPOSITORY>

<REASONING>
DECISION D1 (exit-code catalog naming). The scoper's literal catalog
(EXIT_OK=0, EXIT_USAGE=2, EXIT_NOT_FOUND=3, EXIT_DENIED=4, EXIT_TRANSPORT=5)
conflicts with module-level constants in synth_cli.py (EXIT_USAGE=4,
EXIT_TRANSPORT=2) which are imported by name in tests/test_cli_synth_publish.py
(LOCKED). RESOLUTION: keep the legacy EXIT_* constants unchanged; introduce
SHOW_EXIT_OK=0, SHOW_EXIT_USAGE=2, SHOW_EXIT_NOT_FOUND=3, SHOW_EXIT_DENIED=4,
SHOW_EXIT_TRANSPORT=5 and use ONLY those in the show code path. Comment in
code explains the two catalogs coexist intentionally.

DECISION D2 (reader shim is a dedicated module). Create
src/canon_systems/synth_show_reader.py so AC14 can target the whole file.
Inside synth_cli.py, wrap the show-reachable region with SENTINEL markers
`# <READ-ONLY-REGION-BEGIN id="synth-show" ...>` and
`# <READ-ONLY-REGION-END id="synth-show">` so AC9 regex scopes to just that
region (publish side is still allowed to call put_object).

DECISION D3 (reuse event seam). Import
`from .stall_watchdog import _emit_event, _DEFAULT_EVENT_LOG` and reuse it
verbatim. Do NOT reimplement.

DECISION D4 (retrieval factory). Use
`retrieval_telemetry.build_retrieval_breakdown_event(...)` with
`RetrievalBreakdown(canonical=SourceCounts(tokens_in=0, tokens_out=byte_count))`.
Emit BEFORE the synth_show event.

DECISION D5 (streaming cadence). In markdown mode call
`sys.stdout.write(page_bytes); sys.stdout.flush()` once per page. AC4 test
wraps sys.stdout.write to record write sizes.

DECISION D6 (cutoff). Parse frontmatter `timestamp: "<ISO>"`; if present and
`> cutoff_ts`, skip. Missing/unparseable → include.

DECISION D7 (env layering). `_resolve_required_ids(args)` returns a dict
built from flag>env>None for each of (plan_id, company_id, repository_id,
bucket, prefix, task_id, cutoff_ts, event_log). Any required-5 that
resolves to None raises ValueError(detail) mapped to SHOW_EXIT_USAGE.
</REASONING>

<OUTPUT_FORMAT>
Make minimal, additive changes. The following verbatim skeletons MUST be
present in the implementation:

(1) SHOW_EXIT_* constants block in synth_cli.py near the legacy EXIT_*:
```python
# --- E5-T5 show-verb exit-code catalog -------------------------------------
# NOTE: coexists with legacy EXIT_OK / EXIT_USAGE / EXIT_TRANSPORT above
# (publish tests import the legacy names). The `show` subverb MUST use only
# the SHOW_EXIT_* names below.
SHOW_EXIT_OK = 0
SHOW_EXIT_USAGE = 2
SHOW_EXIT_NOT_FOUND = 3
SHOW_EXIT_DENIED = 4
SHOW_EXIT_TRANSPORT = 5
```

(2) `show` subparser in `_build_parser` with the 12 flags from AC1.

(3) SENTINEL-wrapped show region:
```python
# <READ-ONLY-REGION-BEGIN id="synth-show" reason="AC9 forbidden-method scan target">
#   Must not reference: put_object, put_object_acl, put_object_tagging,
#   put_object_retention, put_object_legal_hold, put_bucket_policy,
#   put_bucket_acl, delete_object, delete_objects, delete_object_tagging,
#   copy_object, copy, upload_file, upload_fileobj, upload_part,
#   upload_part_copy, create_multipart_upload, complete_multipart_upload,
#   abort_multipart_upload, restore_object, write_get_object_response.
def _show(args): ...
def _canonical_stream_order(...): ...
def _apply_cutoff_filter(...): ...
def _render_markdown_stream(...): ...
def _render_json_envelope(...): ...
def _resolve_required_ids(...): ...
def _emit_synth_show_event(...): ...
def _emit_retrieval_event(...): ...
# <READ-ONLY-REGION-END id="synth-show">
```

(4) New module `src/canon_systems/synth_show_reader.py` exposing
`SynthShowReader` (`list_pages`, `read_page`, `head_hash`), `NotFound`,
`AccessDenied`. HEAD/GET/LIST only.

(5) Test file `tests/test_cli_synth_show.py` with all 20 node ids from the
scoper test_plan. Extend the FakeS3 DictS3Client pattern from
tests/test_cli_synth_publish.py (no new plugins).

(6) Additive-only doc diffs:
  - CHANGELOG.md — prepend one bullet at the top of `[Unreleased] ### Added`:
    "`canon synth show` read-only CLI subverb streams Obsidian vault markdown
    (plan + tasks) for `(plan_id[, task_id])` from the published S3 vault,
    with markdown/JSON modes, canonical stream order, ISO-Z `--cutoff-ts`
    filter, `--dry-run` event-log fallback, and a 21-method boto3 source-scan
    enforcing zero S3 write call sites. (E5-T5)"
  - README.md — append one row to the CLI command table:
    "| `canon synth show` | Stream Obsidian vault markdown for
    `(plan_id[, task_id])` from S3 (read-only; markdown or JSON). Honors
    `CANON_PLAN_ID` / `CANON_TASK_ID` / `CANON_VAULT_BUCKET` /
    `CANON_VAULT_PREFIX` / `CANON_SYNTH_CUTOFF_TS`. |"
  - docs/SYSTEM-WORKFLOW.md — §3 append one bullet describing the agent
    hydration path.
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
Emit the following block (filled in with real values) verbatim before exit:

HANDOFF_TO_QA
  handoff_id: "handoff_20260423T1700Z_E5-T5_synth_show_cli"
  task_id: "E5-T5"
  branch: "wave/5/canon-memory-v1"
  files_created:
    - src/canon_systems/synth_show_reader.py
    - tests/test_cli_synth_show.py
  files_modified:
    - src/canon_systems/synth_cli.py
    - CHANGELOG.md
    - README.md
    - docs/SYSTEM-WORKFLOW.md
  acceptance_criteria:
    - id: AC1 .. AC14
      status: MET
      covering_tests: [tests/test_cli_synth_show.py::<node_id>, ...]
  suite_result: total=<n> passed=<n> skipped=<n>
  deviations:
    - "Introduced SHOW_EXIT_* show-scoped exit-code catalog coexisting with
       legacy EXIT_* constants to avoid breaking locked publish tests."
    - "SENTINEL region scoping AC9 inside synth_cli.py; separate
       synth_show_reader.py for AC14."
    - "Event seam and retrieval factory reused verbatim from stall_watchdog
       and retrieval_telemetry."
END_HANDOFF_TO_QA

Do not declare the task complete without this block.
</STOP_CONDITIONS>
```
