# E2-T2 Cursor-Pilot Packet

**Task:** Implement backend/state-api service
**Wave branch:** `wave/2/canon-memory-v1`
**Produced by:** cursor-pilot subagent (ID ff7c4073-4e7b-49da-865e-bbe1f6e1f780)

---

CURSOR_PILOT_PROMPT

<ROLE>
You are the `implementer` subagent working inside the Cursor editor.
This prompt must be executed by that subagent (default model:
`composer-2-fast`), not by the parent planner agent.
</ROLE>

<TASK>
Implement the Wave-2 operational-state service `backend/state-api/` so it satisfies Canon Memory Platform Backlog §B: replace the FastAPI scaffold with five REST endpoints — `GET /state/checkpoint` (read-any, no lease), `PUT /state/checkpoint` (optimistic `state_version` conditional write + mandatory live-lease + matching `lease_token` + canonical `checkpoint_write` event emission), and `POST /state/lease/{acquire,renew,release}` using server-minted UUIDv4 lease tokens. Persistence uses boto3 against the DynamoDB table provisioned by E2-T1 (`${project}-${environment}-canon-state`, pk=`company_id#repository_id`, sk=`plan_id#task_id#workstream_id`, TTL attribute `lease_expires_at`). Tests run fully offline via `moto` v5 `@mock_aws` + FastAPI TestClient. This unblocks E2-T3 (CLI), E2-T4 (agent templates), and Wave-4 canon resume.
</TASK>

<ACCEPTANCE_CRITERIA>
- AC1: `backend/state-api/state_api/` contains exactly these Python modules (all new except `main.py` which is rewritten): `__init__.py`, `main.py`, `config.py`, `models.py`, `storage.py`, `leases.py`, `checkpoints.py`, `events.py`, `api.py`.
- AC2: `backend/state-api/pyproject.toml` additive: runtime `dependencies` gains `boto3>=1.35,<2`; new `[project.optional-dependencies]` with `test = [pytest>=8.2,<9, moto[dynamodb]>=5.0,<6, httpx>=0.27,<1]`.
- AC3: `state_api/config.py` exposes `Settings` with `state_table_name: str` (required) and `aws_region: str = 'us-east-1'`. Read via `get_settings()` dependency; overridable in tests.
- AC4: `GET /healthz` returns 200 `{status:'ok', service:'state-api', table:'<name>'}` if `STATE_TABLE_NAME` set; 503 degraded `{status:'degraded', reason:'state_table_name_unset'}` if unset.
- AC5: `GET /state/checkpoint?company_id=&repository_id=&plan_id=&task_id=&workstream_id=` returns 200 with full §B body incl. synthesized `lease` sub-object reshaped from flat DDB attrs (`lease_owner_agent_run_id`, `lease_owner_actor_id`, `lease_acquired_at`, `lease_expires_at`, `lease_token` internal only — never echo token in GET response).
- AC6: GET not-found returns 404 `{error:'not_found', pk, sk}`. GET never checks the lease.
- AC7: GET missing any of the five query params returns 422.
- AC8: `PUT /state/checkpoint` with body containing §B fields + `lease_token` + `state_version` (expected). On success: atomic `UpdateItem` with `ConditionExpression` = `state_version=:expected AND lease_token=:token AND lease_expires_at > :now`; `state_version` increments; response is 200 with post-write §B body plus header `X-Canon-Event-Id: <event_id>`.
- AC9: PUT state_version mismatch → 409 `{error:'state_version_conflict', expected, actual}` (actual via fallback `GetItem`).
- AC10: PUT lease failures → 409 with distinct codes: `lease_required` (no live lease / missing owner), `lease_expired` (token matched stale), `lease_token_mismatch` (live lease, wrong token).
- AC11: On successful PUT, a single `checkpoint_write` CanonicalEvent is emitted: `schema_version=1`, `event_id=UUIDv4`, `parent_event_id=prior last_event_id or ''`; `agent_name='state-api'`; timestamp RFC3339Z; `state_version` = post-increment; `payload={phase, phase_status, updated_at}`.
- AC12: `EventEmitter` is a `Callable[[CanonicalEvent], None]`. Default in `state_api/events.py` logs a single JSON line to `state_api.events` logger. Tests override via `app.dependency_overrides[get_event_emitter]`. Failed PUTs emit zero events.
- AC13: `POST /state/lease/acquire` body `{company_id,...,workstream_id, owner_agent_run_id, owner_actor_id, ttl_seconds}`. `ttl_seconds` int 1..3600 else 422. On success: mint UUIDv4 `lease_token`, set `lease_expires_at=now+ttl`; return 200 `{lease_token, expires_at, acquired_at, owner_agent_run_id, owner_actor_id}`. Item auto-created with `state_version=0` if absent.
- AC14: lease/acquire when live foreign lease held → 409 `{error:'lease_held', owner_agent_run_id, expires_at}` (no token leaked).
- AC15: Idempotent same-owner acquire: if `owner_agent_run_id` matches stored live owner → 200 with existing token + bumped `expires_at` (does NOT rotate token).
- AC16: `POST /state/lease/renew` body `{scope_ids, lease_token, ttl_seconds}`. `ConditionExpression` = `lease_token=:token AND lease_expires_at>:now`. 200 with same token + new `expires_at`. 409 `lease_token_mismatch` or `lease_expired` (distinguish via post-fail `GetItem` probe).
- AC17: `POST /state/lease/release` body `{scope_ids, lease_token}`. Clears lease attrs. 200 `{released:true}` or 409 `lease_token_mismatch`. Release does NOT emit event in v1.
- AC18: `lease_token` scheme documented in state-api README: server-generated UUIDv4; opaque; not reconstructable; losing it = wait TTL expiry.
- AC19: `state_api/storage.py` defines single `StateStore` class (boto3.resource Table); methods `get_item`, `put_checkpoint`, `acquire_lease`, `renew_lease`, `release_lease`. Router layer never imports boto3 directly. Dependency: `get_state_store(settings=Depends(get_settings))`.
- AC20: `backend/state-api/tests/` contains `conftest.py` (dynamodb_table fixture via `moto.mock_aws`, client fixture with TestClient + dependency overrides, captured_events fixture) + `test_healthz.py` + `test_checkpoint_get.py` + `test_checkpoint_put.py` + `test_lease_acquire.py` + `test_lease_renew.py` + `test_lease_release.py`.
- AC21: `cd backend/state-api && pip install -e .[test] && pytest -q` exits 0 with zero network.
- AC22: Root `pytest -q` exits 0 — `tests/test_backend_layout.py::test_python_services_have_entrypoints[state-api-state_api/main.py]` still passes.
- AC23: `bash scripts/smoke-test.sh` exits 0.
- AC24: `CHANGELOG.md` `[Unreleased] ### Added` gets ONE new bullet at the TOP (above the existing E2-T1 bullet) beginning `E2-T2: backend/state-api service — GET/PUT /state/checkpoint + POST /state/lease/{acquire,renew,release} ...`.
- AC25: `backend/state-api/README.md` is substantively rewritten to document endpoints, JSON shapes, lease-token protocol, env vars, event-sink pluggability, and test command. At least one curl example per endpoint.
- AC26: Root `README.md` gains ONE additive mention of `backend/state-api` under services/backends. No existing text rewritten.
- AC27: `docs/SYSTEM-WORKFLOW.md` gains ONE additive bullet naming state-api as operational-state plane endpoint. Additive only.
- AC28: Zero diff under forbidden surfaces (see REPOSITORY.mustNotBreak).
- AC29: No cloud-mutation commands: no `terraform apply|import|plan|destroy|refresh`, no `aws *`, no live boto3 session.
</ACCEPTANCE_CRITERIA>

<CONTEXT>
- handoff_id: canon-memory-v1
- plan_id: canon_memory_platform_build_d21073e1
- task_id: E2-T2
- workstream_id: wave-2b
- epic_id: E2
- company_id: IMC
- repository_id: innermost
- repo_ref: canon-systems @ wave/2/canon-memory-v1 (tip 2f6ceb4, E2-T1 merged locally)
- Authoritative invariants:
  - TTL attribute `lease_expires_at` MUST be written as DynamoDB Number (epoch seconds).
  - REST `lease.expires_at` is epoch-seconds int; §B JSON example is semantic.
  - DynamoDB item layout is FLAT; REST reshapes to nested §B `lease {...}` sub-object.
  - Five structured 409 codes: `state_version_conflict`, `lease_required`, `lease_expired`, `lease_token_mismatch`, `lease_held`.
  - `boto3` imported ONLY in `state_api/storage.py`.
  - Consume `CanonicalEvent` from `backend/shared/canon_backend_shared/events.py`; do NOT redefine.
  - `EventEmitter = Callable[[CanonicalEvent], None]`; default v1 sink = one JSON line per event to `state_api.events` logger. Tests override via `app.dependency_overrides[get_event_emitter]`.
  - Auth NOT wired in v1 (OQ-E2-T2-01 non-blocking).
  - `src/canon_systems/cli.py` FORBIDDEN (E2-T3 owns).
  - Per-task commit handled by PARENT — implementer must NOT `git commit`.
</CONTEXT>

<REPOSITORY>
- primaryLanguages: ["Python 3.10+", "Markdown"]
- testFramework: "pytest 8.x + moto 5.x (`@mock_aws`) + FastAPI TestClient"
- relevantFiles:
  - backend/state-api/state_api/main.py (scaffold — rewrite; keep `app` module-level)
  - backend/state-api/state_api/__init__.py
  - backend/state-api/pyproject.toml (additive only)
  - backend/state-api/README.md (substantive rewrite permitted)
  - backend/state-api/tests/ (new dir + 7 test files + __init__.py + conftest.py)
  - backend/shared/canon_backend_shared/events.py (READ-ONLY)
  - backend/shared/canon_backend_shared/ids.py (READ-ONLY)
  - backend/knowledge-api/app/ (READ-ONLY — convention reference)
  - infra/terraform/modules/dynamodb-canon-state/main.tf (READ-ONLY)
  - docs/MEMORY-PLATFORM-BACKLOG.md §B, §C (READ-ONLY)
  - tests/test_backend_layout.py (READ-ONLY — do NOT edit)
  - CHANGELOG.md (additive top-of-Unreleased-Added, ABOVE existing E2-T1 bullet)
  - README.md (additive mention)
  - docs/SYSTEM-WORKFLOW.md (additive bullet)
- mustNotBreak (forbidden surfaces — zero diff required):
  - infra/** (entire tree)
  - src/canon_systems/** (entire tree, incl. cli.py — E2-T3 owns)
  - .cursor/rules/**, .cursor/plans/**
  - backend/shared/**
  - backend/{knowledge-api,knowledge-worker,memory-adapter,axon-service,synthesis,synthesis-web,knowledge-client,knowledge-policy,knowledge-schema}/**
  - tests/** (root test tree)
  - scripts/**
  - Root pyproject.toml, pytest.ini, requirements-dev.txt
  - .github/workflows/**
  - Dockerfile, deploy/**
</REPOSITORY>

<REASONING>
1. Foundation: pyproject (additive), config.Settings + get_settings, models (§B + request/response), storage.StateStore (ONLY boto3 import site, uses UpdateItem + ConditionExpression on state_version/lease_token/lease_expires_at), events (CanonicalEvent consumed, EventEmitter Callable, default JSON-line logger sink, get_event_emitter dependency), main.app wired with routers, /healthz ok/degraded per Settings.
2. Checkpoint router: GET reshapes flat DDB → nested §B `lease`, never echoes `lease_token`, 404 on miss, 422 on missing param. PUT atomic UpdateItem w/ compound ConditionExpression; on ConditionalCheckFailedException, fallback GetItem probe classifies into the five 409 codes; on success emit one CanonicalEvent and set X-Canon-Event-Id header.
3. Lease router: acquire (UUIDv4 mint, same-owner idempotency with expiry bump, foreign lease → 409 lease_held no-leak, ttl bounds 422); renew (post-fail GetItem probe distinguishes expired vs mismatch); release (conditional clear, no event emission).
4. Tests: conftest fixtures (mock_aws table matching E2-T1 schema, TestClient with get_settings/get_state_store/get_event_emitter overrides, captured_events list); per-endpoint tests enumerated in ac_traceability.
5. Docs: state-api README substantive rewrite (endpoints + curl + lease-token scheme per AC18); CHANGELOG top-prepend above E2-T1; root README + SYSTEM-WORKFLOW additive mentions.
6. Risks: TTL must be Number type; moto v5 `@mock_aws`; REST expires_at epoch-seconds int.
</REASONING>

<PARALLELIZATION_PLAN>
- strategy: "parallel-first"
- workstreams:
  - ws1 (foundation, no deps): pyproject, config, models, storage, events, main, api, tests/__init__, tests/conftest, tests/test_healthz.
  - ws2 (depends ws1): leases.py + test_lease_acquire/renew/release.
  - ws3 (depends ws1): checkpoints.py + test_checkpoint_get/put.
  - ws4 (depends ws1): state-api README rewrite, CHANGELOG top-prepend, root README, SYSTEM-WORKFLOW bullet.
- execution_waves:
  - wave 1: ws1 alone.
  - wave 2: ws2, ws3, ws4 in parallel.
- Parent orchestration: aggregates shard HANDOFF_TO_QA_SHARD blocks into one HANDOFF_TO_QA, runs the full reproduction suite, persists QA packet, commits on READY_TO_MERGE.
</PARALLELIZATION_PLAN>

<OUTPUT_FORMAT>
Produce only the code changes needed to satisfy the 29 ACs plus the seven test files. Honor the zero-diff forbidden-surface list exactly. Do NOT import boto3 outside `state_api/storage.py`. Do NOT redefine `CanonicalEvent`. Do NOT wire auth. Do NOT run terraform/aws/live boto3. Do NOT `git commit`.

Reproduction commands (must pass before emitting handoff):
1. `cd backend/state-api && pip install -e .[test] && pytest -q`
2. `pytest -q` from repo root
3. `bash scripts/smoke-test.sh`
4. `python -c 'import state_api.main as m; assert hasattr(m, "app")'`
5. `git diff --name-only` ∩ forbidden globs = empty
6. `git grep -nE 'import boto3' backend/state-api/state_api/` returns only `storage.py`
</OUTPUT_FORMAT>

<STOP_CONDITIONS>
Single-stream: emit HANDOFF_TO_QA block with acceptance_criteria_covered (criterion, evidence_files, evidence_tests), summary, decisions, next_actions, open_questions.

Parallel-stream: each shard emits HANDOFF_TO_QA_SHARD with shard_id; parent aggregates into one HANDOFF_TO_QA for qa-gate.

Do NOT `git commit` — parent orchestrator owns the per-task commit on READY_TO_MERGE.
</STOP_CONDITIONS>

END_CURSOR_PILOT_PROMPT
