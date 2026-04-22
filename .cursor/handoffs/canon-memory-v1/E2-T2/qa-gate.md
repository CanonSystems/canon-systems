# E2-T2 QA-Gate Packet

**Task:** Implement backend/state-api service
**Wave branch:** `wave/2/canon-memory-v1`
**Produced by:** qa-gate subagent (ID 6d00614f-b571-48b7-b6d2-3e519b06c3a6)

---

```
GATE_RESULTS
  handoff_id: "canon-memory-v1"
  task_id: "E2-T2"
  wave_branch: "wave/2/canon-memory-v1"
  verdict: PASS
  acceptance_criteria:
    - criterion: "AC1: backend/state-api/state_api/ contains exactly __init__.py, main.py, config.py, models.py, storage.py, leases.py, checkpoints.py, events.py, api.py"
      status: PASS
      covering_tests:
        - "tests/test_backend_layout.py::test_python_services_have_entrypoints[state-api-state_api/main.py]"
        - "backend/state-api/tests/test_healthz.py::test_healthz_ok_when_table_set"
      run_result: "pass — `ls backend/state-api/state_api/` returns exactly the nine required modules (plus __pycache__); test_healthz.py import of state_api.main succeeds, conftest.py imports state_api.{config,events,leases,main,storage} without error"
    - criterion: "AC2: pyproject additive with boto3>=1.35,<2 and [project.optional-dependencies].test = [pytest>=8.2,<9, moto[dynamodb]>=5.0,<6, httpx>=0.27,<1]"
      status: PASS
      covering_tests:
        - "backend/state-api/pyproject.toml"
        - "backend/state-api/tests/test_checkpoint_put.py::test_put_success_increments_version_header_and_event"
      run_result: "pass — pyproject.toml lines 12-26 declare boto3>=1.35,<2 runtime dep and the test extra with the three pins; `pip install -e ../shared -e '.[test]'` succeeded; moto + httpx + pytest consumed by the suite"
    - criterion: "AC3: Settings exposes state_table_name (required/env) and aws_region (default us-east-1); get_settings dependency overridable"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_healthz.py::test_healthz_ok_when_table_set"
        - "backend/state-api/tests/test_healthz.py::test_healthz_degraded_when_table_unset"
        - "backend/state-api/tests/conftest.py"
      run_result: "pass — Settings reads STATE_TABLE_NAME via env alias; conftest overrides get_settings via app.dependency_overrides; healthz tests monkeypatch env successfully"
    - criterion: "AC4: GET /healthz 200 {status:'ok', service:'state-api', table:<name>} when STATE_TABLE_NAME set; 503 {status:'degraded', reason:'state_table_name_unset'} when unset"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_healthz.py::test_healthz_ok_when_table_set"
        - "backend/state-api/tests/test_healthz.py::test_healthz_degraded_when_table_unset"
      run_result: "pass — both tests green"
    - criterion: "AC5: GET /state/checkpoint returns §B body with nested lease synthesized from flat DDB attrs; lease_token never echoed"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_checkpoint_get.py::test_checkpoint_get_reshapes_lease_no_token"
      run_result: "pass — asserts body.lease.owner_agent_run_id + expires_at reshaped from lease_owner_agent_run_id/lease_expires_at; asserts 'lease_token' not in body and not in body.lease"
    - criterion: "AC6: GET not-found returns 404 {error:'not_found', pk, sk}; GET never checks lease"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_checkpoint_get.py::test_checkpoint_get_not_found"
      run_result: "pass — 404 with {error:'not_found', pk:'IMC#innermost', sk:'p1#E2-T2#ws1'}; checkpoints.get_checkpoint code path calls store.get_item only (no lease probe)"
    - criterion: "AC7: GET missing any of the five query params returns 422"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_checkpoint_get.py::test_checkpoint_get_missing_param_422"
      run_result: "pass — FastAPI rejects missing workstream_id with 422"
    - criterion: "AC8: PUT /state/checkpoint atomic UpdateItem with state_version=:expected AND lease_token=:token AND lease_expires_at>:now; state_version increments; 200 with §B body and X-Canon-Event-Id header"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_checkpoint_put.py::test_put_success_increments_version_header_and_event"
      run_result: "pass — body.state_version == 1 after write (from initial 0); X-Canon-Event-Id present and matches body.last_event_id; storage.put_checkpoint ConditionExpression '#sv = :esv AND #lt = :ltok AND #le > :now' verified at backend/state-api/state_api/storage.py:86"
    - criterion: "AC9: PUT state_version mismatch → 409 {error:'state_version_conflict', expected, actual} (actual via fallback GetItem)"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_checkpoint_put.py::test_put_state_version_conflict"
      run_result: "pass — second PUT with stale state_version=0 returns 409 with {error:'state_version_conflict', expected:0, actual:1}"
    - criterion: "AC10: PUT lease failures → 409 with distinct codes lease_required, lease_expired, lease_token_mismatch"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_checkpoint_put.py::test_put_lease_required"
        - "backend/state-api/tests/test_checkpoint_put.py::test_put_lease_expired"
        - "backend/state-api/tests/test_checkpoint_put.py::test_put_lease_token_mismatch"
      run_result: "pass — three independent 409s with distinct error codes; _classify_put_failure disambiguates via fallback GetItem (checkpoints.py:38-66)"
    - criterion: "AC11: Successful PUT emits single checkpoint_write CanonicalEvent (schema_version=1, event_id UUIDv4, parent_event_id=prior last_event_id or '', agent_name='state-api', RFC3339Z timestamp, state_version post-increment, payload={phase, phase_status, updated_at})"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_checkpoint_put.py::test_put_success_increments_version_header_and_event"
      run_result: "pass — captured event asserts event_type='checkpoint_write', schema_version=1, agent_name='state-api', state_version=1 (post-increment), parent_event_id='' (no prior), payload={phase, phase_status, updated_at}; timestamp built via datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')"
    - criterion: "AC12: EventEmitter = Callable[[CanonicalEvent], None]; default logs single JSON line to state_api.events logger; overridable via app.dependency_overrides[get_event_emitter]; failed PUTs emit zero events"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_checkpoint_put.py::test_put_failed_emits_zero_events"
        - "backend/state-api/tests/test_checkpoint_put.py::test_default_emitter_logs_json_line"
        - "backend/state-api/tests/conftest.py"
      run_result: "pass — conftest overrides get_event_emitter to append to captured_events; failed PUT leaves captured_events empty; default emitter writes JSON with event_type='checkpoint_write' to the state_api.events logger (asserted via caplog + json.loads)"
    - criterion: "AC13: POST /state/lease/acquire mints UUIDv4 lease_token, sets lease_expires_at=now+ttl; ttl_seconds 1..3600 else 422; item auto-created with state_version=0 when absent"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_lease_acquire.py::test_acquire_mints_uuidv4_and_creates_item"
        - "backend/state-api/tests/test_lease_acquire.py::test_acquire_ttl_bounds_422"
      run_result: "pass — UUID(body['lease_token']).version == 4; DynamoDB item state_version == 0 on first acquire; ttl_seconds=0 and 3601 both reject with 422 via pydantic validator"
    - criterion: "AC14: lease/acquire when live foreign lease held → 409 {error:'lease_held', owner_agent_run_id, expires_at} (no token leaked)"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_lease_acquire.py::test_acquire_foreign_lease_409_no_token_leak"
      run_result: "pass — second acquire by owner-b returns 409 lease_held with owner_agent_run_id='owner-a'; asserts r1 token not present anywhere in r2.text and 'lease_token' not in error detail"
    - criterion: "AC15: Same-owner idempotent acquire: matching owner_agent_run_id → 200 with existing token + bumped expires_at (no token rotation)"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_lease_acquire.py::test_acquire_same_owner_idempotent_reuses_token"
      run_result: "pass — second acquire reuses same lease_token, bumps expires_at, preserves acquired_at; storage._acquire_lease_extend_same_owner updates only #le"
    - criterion: "AC16: POST /state/lease/renew with ConditionExpression lease_token=:token AND lease_expires_at>:now; 200 same token + new expires_at; 409 lease_token_mismatch or lease_expired via post-fail GetItem probe"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_lease_renew.py::test_renew_success"
        - "backend/state-api/tests/test_lease_renew.py::test_renew_token_mismatch"
        - "backend/state-api/tests/test_lease_renew.py::test_renew_lease_expired"
      run_result: "pass — renew success returns same token + expires_at≥before+ttl; mismatched token returns 409 lease_token_mismatch; expired lease (backdated via direct DDB update_item) returns 409 lease_expired; probe in leases.py:165-192 disambiguates"
    - criterion: "AC17: POST /state/lease/release clears lease attrs; 200 {released:true} or 409 lease_token_mismatch; no event emission"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/test_lease_release.py::test_release_success"
        - "backend/state-api/tests/test_lease_release.py::test_release_token_mismatch"
        - "backend/state-api/tests/test_lease_release.py::test_release_does_not_emit_canonical_event"
      run_result: "pass — release with correct token returns {released:true}; wrong token returns 409 lease_token_mismatch; captured_events remains empty after release (storage.release_lease REMOVEs five lease attrs via conditional update)"
    - criterion: "AC18: lease_token scheme documented in state-api README: server-generated UUIDv4; opaque; not reconstructable; losing it = wait TTL expiry"
      status: PASS
      covering_tests:
        - "backend/state-api/README.md"
      run_result: "pass — README explicitly states 'server-generated UUIDv4', 'opaque', 'not reconstructable', and 'Losing a token means waiting until TTL expiry'; `rg -n 'UUIDv4|not reconstructable' backend/state-api/README.md` matches"
    - criterion: "AC19: StateStore is single boto3 import site; router layer never imports boto3; methods get_item/put_checkpoint/acquire_lease/renew_lease/release_lease; get_state_store dependency"
      status: PASS
      covering_tests:
        - "backend/state-api/state_api/storage.py"
        - "backend/state-api/tests/test_lease_acquire.py::test_acquire_mints_uuidv4_and_creates_item"
        - "backend/state-api/tests/test_checkpoint_put.py::test_put_success_increments_version_header_and_event"
      run_result: "pass — `rg 'import boto3' backend/state-api/state_api/` returns only storage.py:7; storage.py exposes all five StateStore methods; get_state_store(settings=Depends(get_settings)) lives in leases.py and is re-imported by checkpoints.py"
    - criterion: "AC20: backend/state-api/tests/ contains __init__.py, conftest.py, test_healthz.py, test_checkpoint_get.py, test_checkpoint_put.py, test_lease_acquire.py, test_lease_renew.py, test_lease_release.py"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/__init__.py"
        - "backend/state-api/tests/conftest.py"
        - "backend/state-api/tests/test_healthz.py"
        - "backend/state-api/tests/test_checkpoint_get.py"
        - "backend/state-api/tests/test_checkpoint_put.py"
        - "backend/state-api/tests/test_lease_acquire.py"
        - "backend/state-api/tests/test_lease_renew.py"
        - "backend/state-api/tests/test_lease_release.py"
      run_result: "pass — all eight required files present; conftest provides dynamodb_table (moto.mock_aws), client (TestClient + dependency overrides), and captured_events fixtures"
    - criterion: "AC21: cd backend/state-api && pip install -e .[test] && pytest -q exits 0 with zero network (moto mocks boto3)"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/conftest.py"
        - "backend/state-api/tests/test_checkpoint_put.py::test_put_success_increments_version_header_and_event"
      run_result: "pass — `cd backend/state-api && pip install -e ../shared -e '.[test]' && STATE_TABLE_NAME=test pytest -q` → 23 passed in 1.56s (exit 0); conftest uses moto.mock_aws context; no real AWS endpoints hit"
    - criterion: "AC22: Root pytest -q exits 0; tests/test_backend_layout.py::test_python_services_have_entrypoints[state-api-state_api/main.py] still passes"
      status: PASS
      covering_tests:
        - "tests/test_backend_layout.py::test_python_services_have_entrypoints[state-api-state_api/main.py]"
      run_result: "pass — repo-root `pytest -q` → 169 passed in 2.47s (exit 0); state-api parametrized layout assertion included"
    - criterion: "AC23: bash scripts/smoke-test.sh exits 0"
      status: PASS
      covering_tests:
        - "tests/test_consolidation_smoke.py"
        - "scripts/smoke-test.sh"
      run_result: "pass — `bash scripts/smoke-test.sh` → build ok, pytest 148 passed + 21 skipped ok (moto-gated tests skip under smoke's minimal env), terraform validate ok; ALL STAGES PASSED (exit 0)"
    - criterion: "AC24: CHANGELOG.md [Unreleased] ### Added gets ONE new bullet at top (above E2-T1 bullet) beginning 'E2-T2: backend/state-api service ...'"
      status: PASS
      covering_tests:
        - "CHANGELOG.md"
      run_result: "pass — CHANGELOG.md:12 holds the E2-T2 bullet; line 13 is the E2-T1 bullet; ordering preserved; no rewrite of prior bullets"
    - criterion: "AC25: backend/state-api/README.md substantively rewritten — endpoints, JSON shapes, lease-token protocol, env vars, event-sink pluggability, test command, one curl example per endpoint"
      status: PASS
      covering_tests:
        - "backend/state-api/README.md"
      run_result: "pass — README documents Configuration table, lease token protocol (UUIDv4, opaque, not reconstructable), canonical events with default logger sink + pluggability, all five endpoints with JSON shapes, 409 codes, one curl example each, plus the pytest command"
    - criterion: "AC26: Root README.md gains ONE additive mention of backend/state-api under services/backends; no existing text rewritten"
      status: PASS
      covering_tests:
        - "README.md"
      run_result: "pass — additive mention of backend/state-api; git diff shows additive only"
    - criterion: "AC27: docs/SYSTEM-WORKFLOW.md gains ONE additive bullet naming state-api as operational-state plane endpoint; additive only"
      status: PASS
      covering_tests:
        - "docs/SYSTEM-WORKFLOW.md"
      run_result: "pass — single bullet describing state-api as the operational-state plane for checkpoint/lease endpoints; surrounding content unchanged"
    - criterion: "AC28: Zero diff under forbidden surfaces"
      status: PASS
      covering_tests:
        - "tests/test_backend_layout.py::test_python_services_have_entrypoints[state-api-state_api/main.py]"
      run_result: "pass — `git status --porcelain` shows modified only: CHANGELOG.md, README.md, docs/SYSTEM-WORKFLOW.md, backend/state-api/{README.md,pyproject.toml,state_api/main.py}; untracked only under backend/state-api/state_api/**, backend/state-api/tests/**, .cursor/handoffs/canon-memory-v1/E2-T2/**; intersection with forbidden-surface globs is empty"
    - criterion: "AC29: No cloud-mutation commands (no terraform apply|import|plan|destroy|refresh, no aws *, no live boto3 session)"
      status: PASS
      covering_tests:
        - "backend/state-api/tests/conftest.py"
        - "scripts/smoke-test.sh"
      run_result: "pass — only pip install -e, pytest -q, bash scripts/smoke-test.sh (terraform init -backend=false + terraform validate, both read-only), and python3 import probe; no apply/import/plan/destroy/refresh; no aws CLI; all boto3 traffic routed through moto.mock_aws"
  iterations: 0
  regression_checked: true
  regression_evidence:
    - "backend/state-api pytest: 23 passed in 1.56s"
    - "repo-root pytest -q: 169 passed in 2.47s (up from 146 at E2-T1 close; +23 additive, 0 regressions)"
    - "bash scripts/smoke-test.sh: ALL STAGES PASSED"
    - "import state_api.main succeeds with STATE_TABLE_NAME set"
    - "rg 'import boto3' backend/state-api/state_api/ → only storage.py:7"
    - "Forbidden-surface intersection: empty"
  fixes_applied: []
  rule_compliance:
    "§1_agent_chain": "respected"
    "§2_packets_first": "respected"
    "§4_packet_persistence": "ok"
    "§6_cumulative_merge_gates": "qa-gate PASS"
    "§9_per_task_commit": "deferred to parent"
    "§10_wave_branch": "wave/2/canon-memory-v1"
  cloud_waiver_honored: true
  merge_gate_checklist:
    qa_gate: PASS
    canon_qa_validate: TBD_release_orchestrator
    canon_flow_audit: TBD_release_orchestrator
    canon_memory_health: TBD_release_orchestrator
  remaining_gaps: []
  notes: "All 29 ACs PASS in 0 iterations. E2-T2 delivers Wave-2 operational-state service backend/state-api with offline moto suite. Ready for parent commit and release-orchestrator to run the three canon gates at wave/2 close."
END_GATE_RESULTS
```
