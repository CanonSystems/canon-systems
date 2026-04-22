# E2-T2 Scoper Packet

**Task:** Implement backend/state-api service (REST + DynamoDB + lease + canonical event emission)
**Wave branch:** `wave/2/canon-memory-v1` (tip `2f6ceb4`, E2-T1 committed locally)
**DoR verdict:** PASS

```
HANDOFF_TO_CURSOR_PILOT
  scope_summary: "E2-T2 implements the Wave-2 operational-state service `backend/state-api/` by replacing the FastAPI scaffold (currently only `/healthz`) with the five REST endpoints the Canon Memory Platform Backlog §B requires: GET /state/checkpoint (read-any, no lease), PUT /state/checkpoint (optimistic conditional write on `state_version` + mandatory live-lease + matching `lease_token` + canonical `checkpoint_write` event emission), and POST /state/lease/{acquire,renew,release} with UUIDv4 lease tokens. Persistence uses boto3 against the DynamoDB table provisioned by E2-T1 (`${project}-${environment}-canon-state`, pk=`company_id#repository_id`, sk=`plan_id#task_id#workstream_id`, TTL on top-level attribute `lease_expires_at`). The item is stored with a flat attribute layout (top-level `state_version` for conditional writes, top-level `lease_expires_at` so E2-T1's TTL fires, top-level `lease_owner_agent_run_id|owner_actor_id|acquired_at|token`); REST request/response bodies shape these back into the nested `lease {...}` §B sub-object on serialization. The `checkpoint_write` canonical event is produced through a pluggable `EventEmitter` callable whose v1 default writes one JSON line to a `state_api.events` logger (sink is deferred to Wave 6 per Backlog); tests inject a capturing stub via FastAPI `app.dependency_overrides`. Auth is not required for v1 — `canon_backend_shared.auth.verify_caller` stays `NotImplementedError` and is not wired into the routers (captured as OQ-E2-T2-01 non-blocking). Tests use `moto` (new dev-dep in `backend/state-api/pyproject.toml` under `[project.optional-dependencies].test`) via `@mock_aws`; no live AWS is called; `STATE_TABLE_NAME` and `AWS_REGION` come from env. Shared-surface discipline: CHANGELOG top-of-Unreleased-Added new bullet above the existing E2-T1 bullet; README.md + docs/SYSTEM-WORKFLOW.md gain one additive mention each; backend/state-api/README.md is substantively rewritten (it's a scaffold note). Forbidden-surface zero-diff: `infra/**`, `src/canon_systems/**` (specifically `src/canon_systems/cli.py` — E2-T3 owns), `.cursor/rules/**`, `.cursor/plans/**`, all other `backend/<service>/**` (knowledge-api, memory-adapter, knowledge-worker, etc.), and `backend/shared/canon_backend_shared/**` (event/ids/auth stubs are already correct). No `terraform`, no `aws` CLI, no network in tests. No git commit — parent handles per-task commit on READY_TO_MERGE per rule §9."

  scope_packet:
    identifiers:
      handoff_id: "canon-memory-v1"
      plan_id: "canon_memory_platform_build_d21073e1"
      task_id: "E2-T2"
      workstream_id: "wave-2b"
      epic_id: "E2"
      company_id: "IMC"
      repository_id: "innermost"
      repo_ref: "canon-systems @ wave/2/canon-memory-v1 (tip 2f6ceb4, E2-T1 merged locally)"

    story:
      title: "Implement backend/state-api service (REST + DynamoDB + lease + canonical event emission)"
      userValue: "E2-T3 (checkpoint CLI), E2-T4 (phase-boundary hydrate/checkpoint in agent templates), and Wave-4 (canon resume) all require a durable, lease-protected, optimistically-versioned REST API for the operational state plane."

      acceptanceCriteria:
        - "AC1: `backend/state-api/state_api/` contains exactly these Python modules (all new except main.py which is rewritten): `__init__.py`, `main.py`, `config.py`, `models.py`, `storage.py`, `leases.py`, `checkpoints.py`, `events.py`, `api.py`."
        - "AC2: `backend/state-api/pyproject.toml` additive: runtime `dependencies` gains `boto3>=1.35,<2`; new `[project.optional-dependencies]` with `test = [pytest>=8.2,<9, moto[dynamodb]>=5.0,<6, httpx>=0.27,<1]`."
        - "AC3: `state_api/config.py` exposes `Settings` with `state_table_name: str` (required) and `aws_region: str = 'us-east-1'`. Read via `get_settings()` dependency; overridable in tests."
        - "AC4: `GET /healthz` returns 200 `{status:'ok', service:'state-api', table:'<name>'}` if STATE_TABLE_NAME set; 503 degraded `{status:'degraded', reason:'state_table_name_unset'}` if unset."
        - "AC5: `GET /state/checkpoint?company_id=&repository_id=&plan_id=&task_id=&workstream_id=` returns 200 with full §B body incl. synthesized `lease` sub-object from flat DDB attrs (`lease_owner_agent_run_id`, `lease_owner_actor_id`, `lease_acquired_at`, `lease_expires_at`)."
        - "AC6: GET not-found returns 404 `{error:'not_found', pk, sk}`. GET never checks the lease."
        - "AC7: GET missing any of the five query params returns 422."
        - "AC8: `PUT /state/checkpoint` with body containing §B fields + `lease_token` + `state_version` (expected). On success: atomic UpdateItem with ConditionExpression `state_version=:expected AND lease_token=:token AND lease_expires_at > :now`; state_version increments; response is 200 with post-write §B body plus header `X-Canon-Event-Id: <event_id>`."
        - "AC9: PUT state_version mismatch → 409 `{error:'state_version_conflict', expected, actual}` (actual via fallback GetItem)."
        - "AC10: PUT lease failures → 409 with distinct codes: `lease_required` (no live lease / missing owner), `lease_expired` (token matched stale), `lease_token_mismatch` (live lease, wrong token)."
        - "AC11: On successful PUT, a single `checkpoint_write` CanonicalEvent is emitted: schema_version=1, event_id=UUIDv4, parent_event_id=prior last_event_id or ''; agent_name='state-api'; timestamp RFC3339Z; state_version=post-increment; payload={phase, phase_status, updated_at}."
        - "AC12: `EventEmitter` is a `Callable[[CanonicalEvent], None]`. Default in `state_api/events.py` logs a single JSON line to `state_api.events` logger. Tests override via `app.dependency_overrides[get_event_emitter]`. Failed PUTs emit zero events."
        - "AC13: `POST /state/lease/acquire` body `{company_id,...,workstream_id, owner_agent_run_id, owner_actor_id, ttl_seconds}`. ttl_seconds int 1..3600 else 422. On success: mint UUIDv4 lease_token, set lease_expires_at=now+ttl; return 200 `{lease_token, expires_at, acquired_at, owner_agent_run_id, owner_actor_id}`. Item auto-created with state_version=0 if absent."
        - "AC14: lease/acquire when live foreign lease held → 409 `{error:'lease_held', owner_agent_run_id, expires_at}` (no token leaked)."
        - "AC15: Idempotent same-owner acquire: if `owner_agent_run_id` matches stored live owner → 200 with existing token + bumped expires_at (does NOT rotate token)."
        - "AC16: `POST /state/lease/renew` body `{scope_ids, lease_token, ttl_seconds}`. ConditionExpression `lease_token=:token AND lease_expires_at>:now`. 200 with same token + new expires_at. 409 `lease_token_mismatch` or `lease_expired` (distinguish via post-fail GetItem probe)."
        - "AC17: `POST /state/lease/release` body `{scope_ids, lease_token}`. Clears lease attrs. 200 `{released:true}` or 409 `lease_token_mismatch`. Release does NOT emit event in v1."
        - "AC18: lease_token scheme documented in state-api README: server-generated UUIDv4; opaque; not reconstructable; losing it = wait TTL expiry."
        - "AC19: `state_api/storage.py` defines single `StateStore` class (boto3.resource Table); methods `get_item`, `put_checkpoint`, `acquire_lease`, `renew_lease`, `release_lease`. Router layer never imports boto3 directly. Dependency: `get_state_store(settings=Depends(get_settings))`."
        - "AC20: `backend/state-api/tests/` contains conftest.py (dynamodb_table fixture via `moto.mock_aws`, client fixture with TestClient + dependency overrides, captured_events fixture) + test_healthz.py + test_checkpoint_get.py + test_checkpoint_put.py + test_lease_acquire.py + test_lease_renew.py + test_lease_release.py."
        - "AC21: `cd backend/state-api && pip install -e .[test] && pytest -q` exits 0 with zero network (moto mocks boto3)."
        - "AC22: Root `pytest -q` exits 0 — `tests/test_backend_layout.py::test_python_services_have_entrypoints[state-api-state_api/main.py]` still passes."
        - "AC23: `bash scripts/smoke-test.sh` exits 0."
        - "AC24: `CHANGELOG.md` [Unreleased] ### Added gets ONE NEW bullet at the TOP (above the existing E2-T1 bullet) beginning `E2-T2: backend/state-api service — GET/PUT /state/checkpoint + POST /state/lease/{acquire,renew,release} ...`."
        - "AC25: `backend/state-api/README.md` is substantively rewritten to document endpoints, JSON shapes, lease-token protocol, env vars, event-sink pluggability, and test command. At least one curl example per endpoint."
        - "AC26: `README.md` (root) gains ONE additive mention of `backend/state-api` under services/backends. No existing text rewritten."
        - "AC27: `docs/SYSTEM-WORKFLOW.md` gains ONE additive bullet naming state-api as operational-state plane endpoint. Additive only."
        - "AC28: Zero diff under forbidden surfaces: `infra/**`, `src/canon_systems/**`, `.cursor/rules/**`, `.cursor/plans/**`, `backend/shared/**`, `backend/{knowledge-api,knowledge-worker,memory-adapter,axon-service,synthesis,synthesis-web,knowledge-client,knowledge-policy,knowledge-schema}/**`, `.github/workflows/**`, root `pyproject.toml`/`pytest.ini`/`requirements-dev.txt`, `Dockerfile`, `deploy/**`."
        - "AC29: No cloud-mutation commands: no `terraform apply|import|plan|destroy|refresh`, no `aws *`, no live boto3 session against a real account."

      done_signal:
        - "`cd backend/state-api && pip install -e .[test] && pytest -q` exits 0"
        - "Root `pytest -q` exits 0"
        - "`bash scripts/smoke-test.sh` exits 0"
        - "`python -c 'import state_api.main as m; assert hasattr(m, \"app\")'` succeeds"
        - "`git diff --name-only` intersected with forbidden-surface globs is empty"
        - "`git grep -nE 'import boto3' backend/state-api/state_api/` returns hits ONLY in `storage.py`"

    repository:
      primaryLanguages: ["Python 3.10+", "Markdown"]
      testFramework: "pytest 8.x + moto 5.x + FastAPI TestClient"
      relevantFiles:
        - "backend/state-api/state_api/main.py (current scaffold — rewrite)"
        - "backend/state-api/state_api/__init__.py"
        - "backend/state-api/pyproject.toml (additive)"
        - "backend/state-api/README.md (substantive rewrite permitted)"
        - "backend/state-api/tests/ (new dir + 7 files)"
        - "backend/shared/canon_backend_shared/events.py (read-only — consume CanonicalEvent)"
        - "backend/shared/canon_backend_shared/ids.py (read-only — optional helpers)"
        - "backend/knowledge-api/app/ (read-only — convention reference)"
        - "infra/terraform/modules/dynamodb-canon-state/main.tf (read-only — TTL attr confirms `lease_expires_at`)"
        - "docs/MEMORY-PLATFORM-BACKLOG.md §B, §C (authoritative schemas)"
        - "tests/test_backend_layout.py (read-only — do NOT edit)"
        - "CHANGELOG.md (additive top-of-Unreleased-Added)"
        - "README.md (additive mention)"
        - "docs/SYSTEM-WORKFLOW.md (additive bullet)"
        - ".cursor/handoffs/canon-memory-v1/E2-T1/ (precedent packets)"

    constraints:
      dependencies: ["E2-T1 (DynamoDB table module) — committed on wave/2/canon-memory-v1 @ 2f6ceb4"]
      mustNotBreak:
        - "Terraform validate (zero diff on infra/)"
        - "Root pytest -q incl. tests/test_backend_layout.py"
        - "bash scripts/smoke-test.sh"
        - "backend/shared CanonicalEvent shape (consume-only)"
        - "E2-T1 TTL attribute name `lease_expires_at` (must be DynamoDB Number on write)"
        - "CHANGELOG Keep-a-Changelog newest-first"

    invariants:
      rule_compliance:
        - "§1 agent chain respected"
        - "§2 packets-first (parent persists scoper + cursor-pilot markdown before non-markdown writes)"
        - "§4 packet persistence at `.cursor/handoffs/canon-memory-v1/E2-T2/`"
        - "§5 DoR=PASS (no rejection telemetry needed)"
        - "§6 cumulative merge gates downstream"
        - "§9 per-task commit handled by parent"
        - "§10 wave branch wave/2/canon-memory-v1 (continuing)"
      cloud_waiver_honored: "YES — no terraform/aws CLI; tests via moto"
      additive_only_shared_surfaces:
        - "CHANGELOG.md: top-prepend above E2-T1 bullet"
        - "README.md: additive"
        - "docs/SYSTEM-WORKFLOW.md: additive"
        - "backend/state-api/README.md: substantive rewrite permitted (scaffold)"
        - "backend/state-api/pyproject.toml: additive"
      cli_py_excluded_for_this_task: "YES — src/canon_systems/cli.py zero diff"
      no_duplicate_shared_types: "YES — consume CanonicalEvent from backend/shared; no redefinition"
      ttl_contract: "lease_expires_at written as DynamoDB Number (epoch seconds) — String breaks TTL"

    non_goals:
      - "Do NOT implement canon checkpoint CLI (E2-T3 owns)."
      - "Do NOT update agent templates (E2-T4 owns)."
      - "Do NOT deploy to ECS/Fargate (cloud waiver)."
      - "Do NOT implement real event sink (Kinesis/EventBridge) — default logger is sufficient for v1."
      - "Do NOT add non-DynamoDB persistence."
      - "Do NOT wire auth — verify_caller stays NotImplementedError."
      - "Do NOT modify DynamoDB table schema (no GSI/LSI/Streams)."
      - "Do NOT edit src/canon_systems/**, infra/**, .cursor/rules/**, .cursor/plans/**."
      - "Do NOT edit backend/shared/** or any other backend/<service>/**."
      - "Do NOT run terraform or aws CLI."

    target_files:
      to_create:
        - "backend/state-api/state_api/config.py"
        - "backend/state-api/state_api/models.py"
        - "backend/state-api/state_api/storage.py"
        - "backend/state-api/state_api/leases.py"
        - "backend/state-api/state_api/checkpoints.py"
        - "backend/state-api/state_api/events.py"
        - "backend/state-api/state_api/api.py"
        - "backend/state-api/tests/__init__.py"
        - "backend/state-api/tests/conftest.py"
        - "backend/state-api/tests/test_healthz.py"
        - "backend/state-api/tests/test_checkpoint_get.py"
        - "backend/state-api/tests/test_checkpoint_put.py"
        - "backend/state-api/tests/test_lease_acquire.py"
        - "backend/state-api/tests/test_lease_renew.py"
        - "backend/state-api/tests/test_lease_release.py"
      to_rewrite_substantively_allowed:
        - "backend/state-api/state_api/main.py"
        - "backend/state-api/README.md"
      to_modify_additive_only:
        - "backend/state-api/pyproject.toml"
        - "CHANGELOG.md"
        - "README.md"
        - "docs/SYSTEM-WORKFLOW.md"
      explicitly_excluded_zero_diff:
        - "src/canon_systems/cli.py"
        - "src/canon_systems/** (entire tree)"
        - "infra/**"
        - ".cursor/rules/**, .cursor/plans/**"
        - "backend/shared/**"
        - "backend/{knowledge-api,knowledge-worker,memory-adapter,axon-service,synthesis,synthesis-web,knowledge-client,knowledge-policy,knowledge-schema}/**"
        - "tests/** (root)"
        - "scripts/**"
        - "pyproject.toml (root), pytest.ini, requirements-dev.txt"
        - ".github/workflows/**"
        - "Dockerfile, deploy/**"

    forbidden_surfaces:
      hard_forbidden: "see explicitly_excluded_zero_diff list above"
      no_cloud_commands: ["terraform apply|destroy|import|plan|refresh", "aws *", "live boto3 Session against real account"]
      permitted_commands:
        - "pip install -e .[test] inside backend/state-api"
        - "pytest (root and backend/state-api)"
        - "bash scripts/smoke-test.sh"
        - "python -c 'import state_api.main as m'"

    dor_checklist:
      overall: "pass"

    ac_traceability:
      - criterion: "AC1: module layout"
        verification_tests: ["import-all-modules probe in conftest + tests/test_backend_layout.py root assertion"]
      - criterion: "AC2: pyproject additive"
        verification_tests: ["tomllib parse + assert boto3 + moto in test group"]
      - criterion: "AC3-AC4: Settings + /healthz"
        verification_tests: ["tests/test_healthz.py::{test_healthz_ok_when_table_set,test_healthz_degraded_when_table_unset}"]
      - criterion: "AC5-AC7: GET behaviors"
        verification_tests: ["tests/test_checkpoint_get.py::{test_get_returns_full_section_b_shape,test_get_not_found,test_get_missing_query_param_422}"]
      - criterion: "AC8-AC12: PUT + event emission"
        verification_tests: ["tests/test_checkpoint_put.py::{test_put_happy_path_increments_state_version,test_put_response_exposes_event_id_header,test_put_wrong_expected_version_409,test_put_without_live_lease_409_lease_required,test_put_with_expired_lease_409_lease_expired,test_put_with_wrong_token_409_lease_token_mismatch,test_put_emits_canonical_event,test_put_event_state_version_is_post_increment,test_put_event_parent_id_threads_across_writes,test_put_failed_writes_emit_zero_events,test_emitter_is_overridable_via_dependency,test_default_emitter_writes_single_json_line_to_state_api_events_logger}"]
      - criterion: "AC13-AC15: lease/acquire"
        verification_tests: ["tests/test_lease_acquire.py::{test_acquire_when_none,test_acquire_creates_item_with_state_version_zero,test_acquire_validates_ttl_seconds_bounds,test_acquire_when_foreign_lease_live_409_lease_held,test_acquire_response_does_not_leak_token_on_409,test_same_owner_reacquire_reuses_token_bumps_expiry}"]
      - criterion: "AC16: lease/renew"
        verification_tests: ["tests/test_lease_renew.py::{test_renew_valid,test_renew_wrong_token_409,test_renew_expired_409}"]
      - criterion: "AC17: lease/release"
        verification_tests: ["tests/test_lease_release.py::{test_release_valid_clears_attrs,test_release_wrong_token_409}"]
      - criterion: "AC18: token scheme doc"
        verification_tests: ["grep 'uuid.uuid4' + 'not reconstructable' in backend/state-api/README.md"]
      - criterion: "AC19: StateStore single DDB surface"
        verification_tests: ["git grep -nE 'import boto3' backend/state-api/state_api/ returns only storage.py"]
      - criterion: "AC20-AC21: test suite green under moto"
        verification_tests: ["cd backend/state-api && pytest -q"]
      - criterion: "AC22-AC23: root pytest + smoke green"
        verification_tests: ["pytest -q root, bash scripts/smoke-test.sh"]
      - criterion: "AC24: CHANGELOG top-bullet above E2-T1"
        verification_tests: ["awk-based line-number check"]
      - criterion: "AC25: state-api README rewrite"
        verification_tests: ["grep endpoints + env + pytest -q mentions"]
      - criterion: "AC26-AC27: additive living-spec"
        verification_tests: ["grep state-api README.md + SYSTEM-WORKFLOW.md; diff -c '^-' ≤ 2"]
      - criterion: "AC28: zero diff forbidden"
        verification_tests: ["git diff --name-only ∩ forbidden globs == empty"]
      - criterion: "AC29: no cloud commands"
        verification_tests: ["transcript grep returns zero hits"]

    risks_and_assumptions:
      assumptions:
        - "boto3>=1.35,<2 acceptable (matches knowledge-api pin range)."
        - "moto v5 mock_aws is the right mocking layer."
        - "FastAPI TestClient sufficient (no async tests)."
        - "TTL attribute MUST be Number type (String silently disables TTL)."
        - "REST lease.expires_at serialized as epoch-seconds int (NOT ISO) — §B JSON example is normative for semantics, not byte-literal."
        - "agent_name on events = 'state-api'; caller agent info rides in body and echoes through."
      openQuestions:
        - id: "OQ-E2-T2-01"
          question: "Caller authentication in v1?"
          proposed_resolution: "None. verify_caller stays NotImplementedError. Deferred to Wave 6/7."
          blocking_for_this_task: false
        - id: "OQ-E2-T2-02"
          question: "Deterministic lease_token?"
          proposed_resolution: "No — opaque UUIDv4. Recovery via TTL expiry."
          blocking_for_this_task: false
        - id: "OQ-E2-T2-03"
          question: "lease.expires_at serialization (epoch vs ISO)?"
          proposed_resolution: "Epoch-seconds int. §B ISO example normative for semantics only."
          blocking_for_this_task: false
        - id: "OQ-E2-T2-04"
          question: "Emit events on lease acquire/renew/release?"
          proposed_resolution: "No. Only checkpoint_write. Deferred to Wave 6 audit-trail decision."
          blocking_for_this_task: false
        - id: "OQ-E2-T2-05"
          question: "Structured error code catalog?"
          proposed_resolution: "Five codes: state_version_conflict, lease_required, lease_expired, lease_token_mismatch, lease_held. E2-T3 maps to CLI exit codes."
          blocking_for_this_task: false
        - id: "OQ-E2-T2-06"
          question: "ttl_seconds upper bound?"
          proposed_resolution: "3600 (1h) in v1."
          blocking_for_this_task: false

    dor_telemetry:
      next_phase_entry: "cursor-pilot converts 29 ACs into implementation checklist grouped by module and test file; explicitly echoes the TTL attribute type invariant (Number) and the five 409 error codes."

    prior_work_references:
      - ".cursor/handoffs/canon-memory-v1/E2-T1/{scoper,cursor-pilot,implementer,qa-gate,release-status}.md (packet shape precedent)"
      - "docs/MEMORY-PLATFORM-BACKLOG.md §B (checkpoint schema), §C (event envelope), §E E2-T2 task def"
      - "infra/terraform/modules/dynamodb-canon-state/main.tf (TTL attribute source of truth)"
      - "backend/shared/canon_backend_shared/events.py (CanonicalEvent — single source)"
      - "backend/knowledge-api/app/ (convention reference)"
      - "tests/test_backend_layout.py (must keep passing)"
      - ".cursor/rules/memory-platform-build-discipline.mdc §§1-10"
      - ".cursor/plans/canon_memory_platform_build_d21073e1.plan.md"

END_HANDOFF_TO_CURSOR_PILOT
```
