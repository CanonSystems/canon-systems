# E2-T3 Scoper Packet

**Task:** Add canon checkpoint read/write/lease CLI subcommand
**Wave branch:** `wave/2/canon-memory-v1` (tip `e849663`, E2-T2 committed locally)
**DoR verdict:** PASS

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E2-T3 lands a stdlib-only `canon checkpoint` CLI (new module `src/canon_systems/checkpoint_cli.py` wired additively into `src/canon_systems/cli.py`) that exposes the E2-T2 state-api wire protocol to agents over five subsubcommands — `read`, `write`, `lease-acquire`, `lease-renew`, `lease-release`. The CLI speaks JSON-in / JSON-out via `urllib.request`, targets `--base-url` or `$CANON_STATE_API_URL` (default `http://localhost:8080`), requires the five scope-id flags (`--company-id`, `--repository-id`, `--plan-id`, `--task-id`, `--workstream-id`) on every subsubcommand, enforces `--expected-version` + `--lease-token` on write, and maps the state-api error catalog (FastAPI `{\"detail\":{...}}` envelope) to a binding exit-code table: 0 ok, 1 `state_version_conflict`, 2 any `lease_*`/`lease_held` 409, 3 `not_found`, 4 argparse/validation error, 5 transport/network. Tests (`tests/test_cli_checkpoint.py`) inject fake HTTP responses via a monkeypatched `_http_request(method,url,body,timeout_ms)` seam (no live sockets, same discipline as `tests/test_memory_health.py::_probe`); the module delegates to `run(argv)->int` following the `memory_health.py` / `flow_audit.py` precedent. Forbidden-surface zero-diff: `backend/**` (E2-T2 is the consumer, not re-edited), `infra/**`, `.cursor/rules/**`, `.cursor/plans/**`, `.github/workflows/**`, `Dockerfile`, `deploy/**`, every other `src/canon_systems/*.py` except `cli.py` (additive-only) and the new `checkpoint_cli.py`. Additive-only living spec: top-of-[Unreleased]-Added in `CHANGELOG.md` (above the E2-T2 bullet), one additive row in the `canon …` table in root `README.md`, one additive bullet in `docs/SYSTEM-WORKFLOW.md` §6. No terraform, no aws, no live state-api deployment — tests run against the in-process `_http_request` seam. No git commit — parent handles per-task commit on READY_TO_MERGE per rule §9."

  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      plan_id: "canon_memory_platform_build_d21073e1"
      task_id: "E2-T3"
      workstream_id: "wave-2c"
      epic_id: "E2"
      company_id: "IMC"
      repository_id: "innermost"
      repo_ref: "canon-systems @ wave/2/canon-memory-v1 (tip e849663, E2-T2 committed locally)"

    story:
      title: "Add canon checkpoint read/write/lease CLI"
      userValue: "E2-T4 (agent templates hydrate/checkpoint at phase boundaries), E2-T5 (flow-audit + qa-validate enforce checkpoint artifacts), and Wave-4 (canon resume + concurrency) all require a uniform, agent-facing CLI over the state-api wire protocol. E2-T3 lands that surface with a binding exit-code catalog so downstream agents can branch on conflict/lease/not-found without parsing error strings."

      acceptanceCriteria:
        - "AC1: New file `src/canon_systems/checkpoint_cli.py` exists with entry point `def run(argv: list[str] | None = None) -> int:` that returns an `int` exit code. Imports are stdlib-only: `argparse`, `json`, `os`, `sys`, `urllib.request`, `urllib.error`, and `typing` only — verified by a test that reads the file text and asserts `requests`, `httpx`, `aiohttp`, `urllib3` are absent."
        - "AC2: Module exposes a single monkeypatchable network seam `_http_request(method: str, url: str, body: dict|None, timeout_ms: int) -> tuple[int, dict|None, dict[str, str]]` returning `(http_status, parsed_json_or_None, response_headers)`. All subsubcommand dispatchers call this seam and nothing else touches `urllib.request.urlopen`. Tests monkeypatch `checkpoint_cli._http_request` to isolate."
        - "AC3: Top-level CLI registers a new `canon checkpoint` subparser with `add_subparsers(dest='checkpoint_command', required=True)` and exactly five subsubparsers: `read`, `write`, `lease-acquire`, `lease-renew`, `lease-release`. Missing subsubcommand prints argparse usage and exits 4 (usage)."
        - "AC4: Base-URL resolution: `--base-url URL` > `$CANON_STATE_API_URL` > default `http://localhost:8080`. Trailing `/` stripped."
        - "AC5: All five subsubcommands declare the five scope-id flags as required argparse args: `--company-id`, `--repository-id`, `--plan-id`, `--task-id`, `--workstream-id`. Missing any returns exit 4."
        - "AC6: `canon checkpoint read` sends GET `{base}/state/checkpoint?...` with URL-encoded ids. HTTP 200 → pretty-printed JSON body (2-space indent, trailing newline) on stdout; exit 0."
        - "AC7: `canon checkpoint read` HTTP 404: unwrap `body.get('detail', body)`; JSON envelope `{error:'not_found', pk, sk}` on stderr; exit 3."
        - "AC8: `canon checkpoint read` transport failure (URLError / ConnectionError / TimeoutError / socket.gaierror) → JSON envelope `{error:'transport', message, url}` on stderr; exit 5. HTTP 5xx also classified as transport."
        - "AC9: `canon checkpoint write` declares additional required flags: `--handoff-id`, `--phase`, `--phase-status`, `--expected-version` (int), `--lease-token`. Missing any or int-parse failure → exit 4."
        - "AC10: `canon checkpoint write` supports optional body-input via `--body-file PATH` OR `--stdin` (mutually exclusive). Whitelist keys: {inputs, outputs, decisions, open_questions, last_event_id}. Any key outside the whitelist → exit 4 with forbidden-key message. Malformed JSON → exit 4."
        - "AC11: `canon checkpoint write` success: sends PUT `{base}/state/checkpoint` with FLAT body `{...five_ids, handoff_id, phase, phase_status, state_version:<expected>, lease_token, ...whitelisted}`. Note server field is `state_version` — flag `--expected-version` is mapped at wire boundary. HTTP 200 → stdout §B body pretty JSON; stderr exactly one line `canon checkpoint: event_id=<X-Canon-Event-Id>`; exit 0."
        - "AC12: `canon checkpoint write` HTTP 409: unwrap `detail.error`. `state_version_conflict` → stderr envelope with expected/actual, exit 1. `lease_required|lease_expired|lease_token_mismatch|lease_held` → envelope with lease fields, exit 2. Any other 409 → exit 2 (documented default)."
        - "AC13: `canon checkpoint write` HTTP 404 → JSON envelope with pk/sk, exit 3."
        - "AC14: `canon checkpoint write` HTTP 422 → envelope echoing `detail`, exit 4. 5xx/transport → exit 5."
        - "AC15: `canon checkpoint lease-acquire` additional required flags `--owner-agent-run-id`, `--owner-actor-id`, `--ttl-seconds` (int). Sends POST `/state/lease/acquire` with FLAT body {...five_ids, owner_agent_run_id, owner_actor_id, ttl_seconds}. HTTP 200 → pretty-printed LeaseAcquireResponse JSON, exit 0."
        - "AC16: lease-acquire 409 lease_held → envelope {error:'lease_held', owner_agent_run_id, expires_at} (NO lease_token field), exit 2."
        - "AC17: lease-acquire 422 → envelope with detail, exit 4. Non-int ttl → exit 4 client-side."
        - "AC18: `canon checkpoint lease-renew` required flags `--lease-token`, `--ttl-seconds` (int). Sends POST `/state/lease/renew` with NESTED body `{scope_ids:{...five_ids}, lease_token, ttl_seconds}`. HTTP 200 → {lease_token, expires_at}, exit 0."
        - "AC19: lease-renew 409 lease_token_mismatch|lease_expired → envelope, exit 2. 422 → 4. 5xx/transport → 5."
        - "AC20: `canon checkpoint lease-release` required flag `--lease-token`. Sends POST `/state/lease/release` with NESTED body `{scope_ids:{...five_ids}, lease_token}`. HTTP 200 → {released:true}, exit 0."
        - "AC21: lease-release 409 lease_token_mismatch → envelope, exit 2. 422 → 4. 5xx/transport → 5."
        - "AC22: Exit-code catalog is binding and centralized: module defines named constants `EXIT_OK=0`, `EXIT_VERSION_CONFLICT=1`, `EXIT_LEASE_DENIED=2`, `EXIT_NOT_FOUND=3`, `EXIT_USAGE=4`, `EXIT_TRANSPORT=5`; zero integer literals in call sites for return codes (tests assert via `checkpoint_cli.EXIT_LEASE_DENIED == 2`)."
        - "AC23: `run(argv)` never propagates SystemExit to the caller (except `--help`=0, which is caught and converted to `return 0`; mirrors `memory_health.py::run`)."
        - "AC24: `src/canon_systems/cli.py` gains ONE additive import `from .checkpoint_cli import run as run_checkpoint_cli`, ONE additive `sub.add_parser('checkpoint', ...)` block with five nested subsubparsers, and ONE additive dispatcher branch `if args.command == 'checkpoint': return run_checkpoint_cli(<argv>)`. No existing subparser, branch, import, or helper is reordered."
        - "AC25: `canon checkpoint [--help]` and each of the five subsubcommand `--help` invocations exit 0 when invoked via `canon_systems.cli.main([...])`; each help text names the relevant required flags."
        - "AC26: `tests/test_cli_checkpoint.py` exists in root test tree, contains ≥25 pytest test functions, imports `canon_systems.checkpoint_cli as cc` and `from canon_systems.cli import main`."
        - "AC27: Every test exercising network behavior uses `monkeypatch.setattr(cc, '_http_request', fake)`. A dedicated `test_no_live_http_in_suite` asserts the seam is the only network path."
        - "AC28: Tests assert wire-body shape discipline: lease-acquire and write send FLAT bodies (no `scope_ids`); lease-renew and lease-release send NESTED bodies with `scope_ids`; write body `state_version` key equals value passed via `--expected-version`."
        - "AC29: Tests assert FastAPI detail-envelope unwrap on every non-200: a 409 body `{\"detail\":{\"error\":\"state_version_conflict\",\"expected\":7,\"actual\":8}}` causes write to exit 1 AND write a stderr JSON envelope with parsed error/expected/actual preserved. Same for lease_held (acquire) and lease_token_mismatch (renew/release)."
        - "AC30: Root `README.md` gains ONE additive row in the `canon …` command table above the existing `canon secrets` row referencing the five subsubcommands and exit-code catalog. No existing rows reflowed."
        - "AC31: `CHANGELOG.md` [Unreleased] ### Added gets ONE new bullet at the TOP (above E2-T2) starting `E2-T3: canon checkpoint CLI —`."
        - "AC32: `docs/SYSTEM-WORKFLOW.md` §6 gains ONE additive bullet after the existing memory-health bullet mentioning `canon checkpoint` + `state-api`. No reflow."
        - "AC33: Root `pytest -q` exits 0. `bash scripts/smoke-test.sh` exits 0. `python -c 'from canon_systems.checkpoint_cli import run; assert callable(run)'` succeeds."
        - "AC34: Zero diff on forbidden surfaces (see `explicitly_excluded_zero_diff`)."
        - "AC35: No cloud / live-network commands: no `terraform apply|plan|import|destroy|refresh`, no `aws *`, no live HTTP, no live state-api deployment. All tests use the monkeypatch seam."

      done_signal:
        - "`pytest -q tests/test_cli_checkpoint.py` exits 0"
        - "Root `pytest -q` exits 0"
        - "`bash scripts/smoke-test.sh` exits 0"
        - "`python -c 'from canon_systems.checkpoint_cli import run; assert callable(run)'` succeeds"
        - "`canon checkpoint --help` exits 0 via `python -m canon_systems.cli checkpoint --help`"
        - "`git diff --name-only wave/2/canon-memory-v1..HEAD` ∩ forbidden globs empty"
        - "`git grep -nE '^(import|from) (requests|httpx|aiohttp|urllib3)' src/canon_systems/checkpoint_cli.py` zero hits"
        - "README.md shows new `canon checkpoint …` row above `canon secrets`"
        - "CHANGELOG.md [Unreleased] ### Added top bullet begins with `E2-T3: canon checkpoint CLI`"
        - "docs/SYSTEM-WORKFLOW.md §6 bullet names `canon checkpoint` + `state-api`"

    repository:
      primaryLanguages: ["Python 3.10+", "Markdown"]
      testFramework: "pytest 8.x (root suite); stdlib http stubbing via monkeypatch on `_http_request`"
      relevantFiles:
        - "src/canon_systems/cli.py (additive edit)"
        - "src/canon_systems/checkpoint_cli.py (NEW)"
        - "src/canon_systems/memory_health.py (read-only — convention source)"
        - "src/canon_systems/flow_audit.py, qa_validate.py (read-only — convention sources)"
        - "backend/state-api/state_api/{checkpoints,leases,models,api}.py (read-only — wire protocol source of truth)"
        - "backend/state-api/README.md (read-only — curl examples)"
        - "tests/test_memory_health.py (read-only — pattern source)"
        - "tests/test_cli_checkpoint.py (NEW)"
        - "README.md (additive row)"
        - "CHANGELOG.md (additive top bullet)"
        - "docs/SYSTEM-WORKFLOW.md (additive bullet §6)"
        - ".cursor/handoffs/canon-memory-v1/E2-T{1,2}/scoper.md (precedents)"
        - "docs/MEMORY-PLATFORM-BACKLOG.md lines 300-311 (task def)"

    constraints:
      dependencies:
        - "E2-T2 (backend/state-api committed @ e849663) — satisfied"
        - "E2-T1 (infra) — transitively satisfied"
      mustNotBreak:
        - "Root pytest -q"
        - "bash scripts/smoke-test.sh"
        - "Existing canon subcommands still parse"
        - "E2-T2 state-api files — zero diff"
        - "CHANGELOG Keep-a-Changelog newest-first"
        - "Stdlib-only CLI runtime (no new third-party deps)"

    invariants:
      rule_compliance:
        - "§1 agent chain respected"
        - "§2 packets-first"
        - "§4 packet persistence at .cursor/handoffs/canon-memory-v1/E2-T3/"
        - "§5 DoR=PASS"
        - "§6 cumulative merge gates downstream"
        - "§9 per-task commit by parent on READY_TO_MERGE"
        - "§10 wave branch wave/2/canon-memory-v1"
      cloud_waiver_honored: "YES — no terraform/aws/live HTTP"
      additive_only_shared_surfaces:
        - "CHANGELOG.md top-prepend above E2-T2"
        - "README.md additive row in canon table"
        - "docs/SYSTEM-WORKFLOW.md additive bullet §6"
        - "src/canon_systems/cli.py additive import + subparser + dispatcher"
      cli_py_in_scope: "YES — wave-0 cli.py zero-diff waiver dropped per parent guidance"
      stdlib_only_discipline: "YES"
      wire_shape_invariant:
        - "lease-acquire + write: FLAT body"
        - "lease-renew + lease-release: NESTED scope_ids body"
        - "server field `state_version` (not `expected_version`)"
        - "FastAPI HTTPException wraps payload under {detail:{...}} — CLI unwraps"

    non_goals:
      - "Do NOT edit backend/** or infra/**."
      - "Do NOT implement canon resume / phase-boundary hydrate (E2-T4)."
      - "Do NOT add --require-checkpoints flags (E2-T5)."
      - "Do NOT wire auth (OQ-E2-T2-01 deferred)."
      - "Do NOT add third-party deps."
      - "Do NOT resolve --base-url from .canon/memory-layer.local.env."
      - "Do NOT run terraform/aws/live network."
      - "Do NOT reflow existing README/SYSTEM-WORKFLOW/CHANGELOG content."
      - "Do NOT edit .cursor/rules/** or .cursor/plans/**."
      - "Do NOT edit any src/canon_systems/*.py other than cli.py (additive) and the new checkpoint_cli.py."

    target_files:
      to_create:
        - "src/canon_systems/checkpoint_cli.py"
        - "tests/test_cli_checkpoint.py"
      to_modify_additive_only:
        - "src/canon_systems/cli.py"
        - "CHANGELOG.md"
        - "README.md"
        - "docs/SYSTEM-WORKFLOW.md"
      explicitly_excluded_zero_diff:
        - "backend/**"
        - "infra/**"
        - ".cursor/rules/**"
        - ".cursor/plans/**"
        - ".github/workflows/**"
        - "Dockerfile, deploy/**"
        - "src/canon_systems/{__init__,actor_report,ask_hybrid,auth_migration,capture_session,context_preload,dor_log,flow_audit,install_wizard,memory_health,memory_queue,qa_validate,repo_enable,secrets_submit,self_update,shared,store_pending_user,version_check}.py"
        - "src/canon_systems/templates/**"
        - "docs/MEMORY-PLATFORM-BACKLOG.md, docs/MEMORY-PLATFORM-PLAN.md, docs/WAVE-0-*.md, docs/E0-T*.md"
        - "pyproject.toml (root), pytest.ini, requirements-dev.txt"
        - "tests/test_memory_health.py, tests/test_backend_layout.py, tests/test_infra_layout.py (and any other existing tests)"
        - "scripts/**"

    forbidden_surfaces:
      hard_forbidden: "see explicitly_excluded_zero_diff"
      no_cloud_commands:
        - "terraform apply|plan|import|destroy|refresh"
        - "aws *, aws-vault *, boto3 Session against any real account"
        - "live HTTP against any host (including http://localhost:8080 in tests — use _http_request monkeypatch seam)"
      permitted_commands:
        - "python -m canon_systems.cli checkpoint ..."
        - "pytest -q (root and tests/test_cli_checkpoint.py)"
        - "bash scripts/smoke-test.sh"
        - "python -c 'from canon_systems import checkpoint_cli'"
        - "git diff --name-only / git grep"

    dor_checklist:
      overall: "pass"

    ac_traceability: "See full 35-AC mapping in scoper agent transcript; each AC links to specific tests/test_cli_checkpoint.py::test_name. Key mappings: AC1→test_module_exposes_run_entrypoint + test_stdlib_only_imports; AC4→test_base_url_flag_wins/env_used/default/trailing_slash_stripped; AC9→test_write_requires_expected_version_and_lease_token + test_write_expected_version_must_be_int; AC10→test_write_body_file_merges_whitelisted_keys + test_write_body_file_rejects_forbidden_keys_exit_four + test_write_malformed_json_body_exit_four + test_write_body_file_and_stdin_mutually_exclusive; AC12→test_write_409_state_version_conflict_exit_one + test_write_409_lease_{required,expired,token_mismatch,held}_exit_two; AC16→test_lease_acquire_409_lease_held_exit_two + test_lease_acquire_409_does_not_leak_token; AC22→test_exit_code_catalog_values; AC24→test_cli_py_registers_checkpoint_subcommand; AC28→test_write_sends_flat_body + test_lease_renew_sends_nested_scope_ids + test_lease_release_sends_nested_scope_ids; AC29→test_fastapi_detail_unwrap_on_409_conflict/404_not_found/lease_held; AC31→test_changelog_e2t3_bullet_above_e2t2_bullet."

    risks_and_assumptions:
      assumptions:
        - "stdlib urllib sufficient; no streaming/multipart."
        - "FastAPI detail envelope shape verified in state-api source."
        - "X-Canon-Event-Id is the response header name on PUT."
        - "tests/test_cli_checkpoint.py lives at root tests/ (parent guidance + memory_health precedent)."
        - "No .canon/memory-layer.local.env base-url lookup — flag/env/default only."
        - "--expected-version 0 is valid (bootstrap write)."
      openQuestions:
        - id: "OQ-E2-T3-01"
          question: "Read scope-ids from .canon/memory-layer.local.env fallback?"
          proposed_resolution: "NO in v1. Explicit flags only. Revisit in E2-T4."
          blocking_for_this_task: false
        - id: "OQ-E2-T3-02"
          question: "Split --inputs-file / --outputs-file vs one --body-file?"
          proposed_resolution: "NO. One --body-file with whitelist is minimal."
          blocking_for_this_task: false
        - id: "OQ-E2-T3-03"
          question: "Exit code for un-enumerated 409 error codes?"
          proposed_resolution: "Exit 2 (lease-denied) conservative default; documented in comment."
          blocking_for_this_task: false
        - id: "OQ-E2-T3-04"
          question: "Exit code for 422 on missing query param (read)?"
          proposed_resolution: "Exit 4 (usage) — 422 is client-shaped."
          blocking_for_this_task: false
        - id: "OQ-E2-T3-05"
          question: "Print X-Canon-Event-Id to stdout?"
          proposed_resolution: "NO — stdout reserved for §B body; event_id logged to stderr."
          blocking_for_this_task: false
        - id: "OQ-E2-T3-06"
          question: "Need --timeout-ms flag?"
          proposed_resolution: "YES — default 10000, clamped 100..60000 (memory-health precedent)."
          blocking_for_this_task: false

    dor_telemetry:
      next_phase_entry: "cursor-pilot converts 35 ACs into module-by-module checklist: (a) checkpoint_cli.py skeleton with EXIT_* constants, _http_request seam, _resolve_base_url, per-subsubcommand dispatchers; (b) additive cli.py wiring; (c) ≥25 pytest cases covering happy path, every 409 code, wire-body discipline, FastAPI detail unwrap, living-spec greps; (d) additive CHANGELOG/README/SYSTEM-WORKFLOW. Explicit echo required: wire-shape asymmetry (flat vs nested) and FastAPI detail unwrap."

    prior_work_references:
      - ".cursor/handoffs/canon-memory-v1/E2-T{1,2}/*.md (packet precedents; wire protocol source)"
      - "docs/MEMORY-PLATFORM-BACKLOG.md §E E2-T3 lines 300-311"
      - "backend/state-api/state_api/{checkpoints,leases,models,api}.py"
      - "src/canon_systems/{memory_health,flow_audit,qa_validate,cli}.py"
      - "tests/test_memory_health.py"
      - ".cursor/rules/memory-platform-build-discipline.mdc §§1-10"
      - ".cursor/plans/canon_memory_platform_build_d21073e1.plan.md"

END_HANDOFF_TO_CURSOR_PILOT
```
