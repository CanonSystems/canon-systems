# E2-T3 Cursor-Pilot Packet

**Task:** Add canon checkpoint read/write/lease CLI
**Wave branch:** `wave/2/canon-memory-v1`
**Produced by:** cursor-pilot subagent (ID 8ea3ba52-7598-41ed-bbae-9a3456b26746)

---

```
CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent (pin model: `composer-2-fast`) operating inside Cursor in ASK-disabled / Agent mode with write access to `/Users/edwardwalker/localwork/canon-systems` on branch `wave/2/canon-memory-v1` (tip `e849663`, E2-T2 committed). You write code + tests only. You DO NOT run `git commit`, `git push`, `terraform *`, `aws *`, or any live HTTP. Parent commits per-task on READY_TO_MERGE.
</ROLE>

<TASK>
Land E2-T3: ship a stdlib-only `canon checkpoint` CLI that exposes the E2-T2 state-api wire protocol to agents via five subsubcommands (`read`, `write`, `lease-acquire`, `lease-renew`, `lease-release`) with a binding exit-code catalog (0 ok / 1 state_version_conflict / 2 lease-denied / 3 not_found / 4 usage / 5 transport). New module `src/canon_systems/checkpoint_cli.py` wired additively into `src/canon_systems/cli.py`. Tests at `tests/test_cli_checkpoint.py` (ROOT tests/ — NOT backend/) using a monkeypatched `_http_request` seam (zero live sockets). Additive-only living-spec touches to CHANGELOG / README / docs/SYSTEM-WORKFLOW.md.
</TASK>

<ACCEPTANCE_CRITERIA>
AC1..AC35 as enumerated in scoper.md (35 ACs). Key explicit invariants:
- Stdlib-only imports (argparse/json/os/sys/urllib.request/urllib.error/typing; socket only if needed for gaierror).
- Single `_http_request(method,url,body,timeout_ms) -> (status,json|None,headers)` seam — THE only urlopen call site.
- Exit-code catalog named constants EXIT_OK=0, EXIT_VERSION_CONFLICT=1, EXIT_LEASE_DENIED=2, EXIT_NOT_FOUND=3, EXIT_USAGE=4, EXIT_TRANSPORT=5.
- Wire-shape asymmetry: write + lease-acquire FLAT; lease-renew + lease-release NESTED under `scope_ids`.
- Server field `state_version` (flag `--expected-version` translated at wire boundary).
- FastAPI detail unwrap: `body.get('detail', body)` on every non-200.
- Pre-authorized --timeout-ms (default 10000, clamped 100..60000).
- run(argv) never propagates SystemExit except --help→0.
- src/canon_systems/cli.py IS in-scope (additive-only).
- tests at ROOT tests/test_cli_checkpoint.py (≥25 functions).
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-memory-v1
- task_id: E2-T3
- plan_id: canon_memory_platform_build_d21073e1
- wave_branch: wave/2/canon-memory-v1 (tip e849663)
- prior_work: E2-T1, E2-T2 packet quartets; docs/MEMORY-PLATFORM-BACKLOG.md §E lines 300-311; backend/state-api/state_api/{checkpoints,leases,models,api}.py (wire truth); src/canon_systems/{memory_health,flow_audit,qa_validate,cli}.py; tests/test_memory_health.py.

EXPLICIT WIRE-SHAPE ASYMMETRY:
- write (PUT /state/checkpoint): FLAT body {...five_ids, handoff_id, phase, phase_status, state_version, lease_token, ...whitelisted}
- lease-acquire (POST /state/lease/acquire): FLAT {...five_ids, owner_agent_run_id, owner_actor_id, ttl_seconds}
- lease-renew (POST /state/lease/renew): NESTED {scope_ids:{...five_ids}, lease_token, ttl_seconds}
- lease-release (POST /state/lease/release): NESTED {scope_ids:{...five_ids}, lease_token}

EXIT-CODE CATALOG: 0 ok; 1 state_version_conflict; 2 any lease_* / lease_held 409 (and un-enumerated 409); 3 not_found; 4 usage/argparse/422; 5 transport (URLError/ConnectionError/TimeoutError/OSError/5xx).
</CONTEXT>

<REPOSITORY>
- primaryLanguages: Python 3.10+, Markdown
- testFramework: pytest 8.x (root)
- relevantFiles:
  - src/canon_systems/checkpoint_cli.py (NEW)
  - src/canon_systems/cli.py (additive)
  - tests/test_cli_checkpoint.py (NEW, ROOT tests/)
  - README.md (additive row above `canon secrets`)
  - CHANGELOG.md (additive top bullet in [Unreleased] ### Added above E2-T2)
  - docs/SYSTEM-WORKFLOW.md (additive bullet §6)
  - src/canon_systems/memory_health.py (read-only — convention)
  - backend/state-api/state_api/{checkpoints,leases,models}.py (read-only — wire truth)
  - tests/test_memory_health.py (read-only — pattern)
- mustNotBreak:
  - Root pytest -q
  - bash scripts/smoke-test.sh
  - Existing canon subcommands
  - E2-T2 state-api files (zero diff)
  - CHANGELOG newest-first
  - Stdlib-only CLI runtime
- explicitly_excluded_zero_diff:
  - backend/**, infra/**, .cursor/rules/**, .cursor/plans/**, .github/workflows/**, Dockerfile, deploy/**
  - src/canon_systems/*.py except cli.py (additive) and new checkpoint_cli.py
  - src/canon_systems/templates/**
  - docs/MEMORY-PLATFORM-BACKLOG.md, docs/MEMORY-PLATFORM-PLAN.md, docs/WAVE-0-*.md, docs/E0-T*.md
  - pyproject.toml, pytest.ini, requirements-dev.txt
  - tests/test_memory_health.py, tests/test_backend_layout.py, tests/test_infra_layout.py, pre-existing tests
  - scripts/**
</REPOSITORY>

<REASONING>
1. checkpoint_cli.py: EXIT_* constants, _http_request (urlopen classification + timeout), _resolve_base_url (flag>env>default, strip trailing /), _unwrap_detail, _emit_stdout_json + _emit_stderr_json (2-space indent, trailing newline), --timeout-ms clamped. Five _cmd_* dispatchers enforce wire-shape asymmetry. run(argv) catches argparse SystemExit to convert to EXIT_USAGE or EXIT_OK (--help).

2. cli.py: one additive import `from .checkpoint_cli import run as run_checkpoint_cli`; one additive sub.add_parser('checkpoint', ...) block with 5 subsubparsers (cleanest: stub parser that delegates to run_checkpoint_cli with relative argv, matching memory_health precedent); one additive dispatcher branch. No reordering.

3. tests/test_cli_checkpoint.py (≥25): stdlib-import scan, run-entrypoint probe, base-url resolution matrix, argparse-required flag matrix (exit 4), happy paths for all 5 endpoints, every 409 code (state_version_conflict→1, lease_required/expired/token_mismatch/held→2, unknown→2), 404 → 3, 422 → 4, transport/5xx → 5, wire-body shape assertions (flat vs nested, state_version key translation), FastAPI detail unwrap on 404/409/422, exit-code catalog constants, --help exits 0, no-live-http guarantee, living-spec greps for README/CHANGELOG/SYSTEM-WORKFLOW.

4. Living spec: README row above `canon secrets`; CHANGELOG top bullet above E2-T2 starting "E2-T3: canon checkpoint CLI —"; SYSTEM-WORKFLOW §6 bullet after memory-health.
</REASONING>

<PARALLELIZATION_PLAN>
Single-stream execution acceptable for context efficiency. Parent-pilot recommended layout: ws1 checkpoint_cli.py → ws2 cli.py wire-in → ws3 tests/test_cli_checkpoint.py → ws4 living-spec → ws5 reproduction. Implementer may consolidate into one pass.
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Stdlib-only. No refactors. No cloud/live-HTTP commands. DO NOT `git commit`. Reproduction gate (all exit 0 before HANDOFF_TO_QA):
1. pytest -q (repo root)
2. bash scripts/smoke-test.sh
3. python3 -c 'from canon_systems.checkpoint_cli import run; assert callable(run)'
4. python3 -m canon_systems.cli checkpoint --help
5. git diff --name-only ∩ forbidden globs = empty
6. rg '^(import|from) (requests|httpx|aiohttp|urllib3)' src/canon_systems/checkpoint_cli.py → 0 hits
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
Emit HANDOFF_TO_QA with acceptance_criteria_covered (AC1..AC35), summary, decisions, next_actions, open_questions. Parent persists to `.cursor/handoffs/canon-memory-v1/E2-T3/implementer.md` and runs qa-gate. Parent commits on READY_TO_MERGE.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
```
