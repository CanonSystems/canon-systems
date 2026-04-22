# E2-T2 Implementer Packet

**Task:** Implement backend/state-api service
**Wave branch:** `wave/2/canon-memory-v1`
**Produced by:** implementer subagent (ID ba9ddb13-0b86-4f09-a6b3-93b2c7d37ae8, composer-2-fast)

---

Implementation delivered:
- `backend/state-api` is a FastAPI service with DynamoDB-backed checkpoints and leases.
- Shared `get_state_store` lives in `leases.py` and is imported by `checkpoints.py` so tests can override one dependency.
- `StateStore.acquire_lease` wraps fresh vs same-owner extend.
- `moto` gated behind `pytest.importorskip` inside the `dynamodb_table` fixture so repo-root / smoke pytest works without optional test deps.
- Docs / CHANGELOG / root README / SYSTEM-WORKFLOW updated per AC.

```
HANDOFF_TO_QA
  handoff_id: canon-memory-v1
  task_id: E2-T2
  workstream_id: wave-2b

  acceptance_criteria_covered:
    - criterion: AC1
      evidence_files:
        - backend/state-api/state_api/__init__.py
        - backend/state-api/state_api/main.py
        - backend/state-api/state_api/config.py
        - backend/state-api/state_api/models.py
        - backend/state-api/state_api/storage.py
        - backend/state-api/state_api/leases.py
        - backend/state-api/state_api/checkpoints.py
        - backend/state-api/state_api/events.py
        - backend/state-api/state_api/api.py
      evidence_tests:
        - backend/state-api/tests/conftest.py
    - criterion: AC2
      evidence_files:
        - backend/state-api/pyproject.toml
      evidence_tests:
        - backend/state-api/tests/conftest.py
    - criterion: AC3
      evidence_files:
        - backend/state-api/state_api/config.py
      evidence_tests:
        - backend/state-api/tests/conftest.py
    - criterion: AC4
      evidence_files:
        - backend/state-api/state_api/main.py
      evidence_tests:
        - backend/state-api/tests/test_healthz.py::test_healthz_ok_when_table_set
        - backend/state-api/tests/test_healthz.py::test_healthz_degraded_when_table_unset
    - criterion: AC5
      evidence_files:
        - backend/state-api/state_api/checkpoints.py
        - backend/state-api/state_api/models.py
      evidence_tests:
        - backend/state-api/tests/test_checkpoint_get.py::test_checkpoint_get_reshapes_lease_no_token
    - criterion: AC6
      evidence_files:
        - backend/state-api/state_api/checkpoints.py
      evidence_tests:
        - backend/state-api/tests/test_checkpoint_get.py::test_checkpoint_get_not_found
    - criterion: AC7
      evidence_files:
        - backend/state-api/state_api/checkpoints.py
      evidence_tests:
        - backend/state-api/tests/test_checkpoint_get.py::test_checkpoint_get_missing_param_422
    - criterion: AC8
      evidence_files:
        - backend/state-api/state_api/checkpoints.py
        - backend/state-api/state_api/storage.py
      evidence_tests:
        - backend/state-api/tests/test_checkpoint_put.py::test_put_success_increments_version_header_and_event
    - criterion: AC9
      evidence_files:
        - backend/state-api/state_api/checkpoints.py
      evidence_tests:
        - backend/state-api/tests/test_checkpoint_put.py::test_put_state_version_conflict
    - criterion: AC10
      evidence_files:
        - backend/state-api/state_api/checkpoints.py
      evidence_tests:
        - backend/state-api/tests/test_checkpoint_put.py::test_put_lease_token_mismatch
        - backend/state-api/tests/test_checkpoint_put.py::test_put_lease_expired
        - backend/state-api/tests/test_checkpoint_put.py::test_put_lease_required
    - criterion: AC11
      evidence_files:
        - backend/state-api/state_api/checkpoints.py
        - backend/state-api/state_api/events.py
      evidence_tests:
        - backend/state-api/tests/test_checkpoint_put.py::test_put_success_increments_version_header_and_event
    - criterion: AC12
      evidence_files:
        - backend/state-api/state_api/events.py
      evidence_tests:
        - backend/state-api/tests/conftest.py
        - backend/state-api/tests/test_checkpoint_put.py::test_default_emitter_logs_json_line
    - criterion: AC13
      evidence_files:
        - backend/state-api/state_api/leases.py
        - backend/state-api/state_api/storage.py
      evidence_tests:
        - backend/state-api/tests/test_lease_acquire.py::test_acquire_mints_uuidv4_and_creates_item
    - criterion: AC14
      evidence_files:
        - backend/state-api/state_api/leases.py
      evidence_tests:
        - backend/state-api/tests/test_lease_acquire.py::test_acquire_foreign_lease_409_no_token_leak
    - criterion: AC15
      evidence_files:
        - backend/state-api/state_api/leases.py
        - backend/state-api/state_api/storage.py
      evidence_tests:
        - backend/state-api/tests/test_lease_acquire.py::test_acquire_same_owner_idempotent_reuses_token
    - criterion: AC16
      evidence_files:
        - backend/state-api/state_api/leases.py
        - backend/state-api/state_api/storage.py
      evidence_tests:
        - backend/state-api/tests/test_lease_renew.py::test_renew_success
        - backend/state-api/tests/test_lease_renew.py::test_renew_token_mismatch
        - backend/state-api/tests/test_lease_renew.py::test_renew_lease_expired
    - criterion: AC17
      evidence_files:
        - backend/state-api/state_api/leases.py
        - backend/state-api/state_api/storage.py
      evidence_tests:
        - backend/state-api/tests/test_lease_release.py::test_release_success
        - backend/state-api/tests/test_lease_release.py::test_release_token_mismatch
        - backend/state-api/tests/test_lease_release.py::test_release_does_not_emit_canonical_event
    - criterion: AC18
      evidence_files:
        - backend/state-api/README.md
      evidence_tests: []
    - criterion: AC19
      evidence_files:
        - backend/state-api/state_api/storage.py
        - backend/state-api/state_api/leases.py
        - backend/state-api/state_api/checkpoints.py
      evidence_tests: []
    - criterion: AC20
      evidence_files:
        - backend/state-api/tests/conftest.py
        - backend/state-api/tests/test_healthz.py
        - backend/state-api/tests/test_checkpoint_get.py
        - backend/state-api/tests/test_checkpoint_put.py
        - backend/state-api/tests/test_lease_acquire.py
        - backend/state-api/tests/test_lease_renew.py
        - backend/state-api/tests/test_lease_release.py
      evidence_tests: []
    - criterion: AC21
      evidence_files:
        - backend/state-api/pyproject.toml
        - backend/state-api/tests/conftest.py
      evidence_tests:
        - "cd backend/state-api && pip install -e ../shared -e .[test] && pytest -q"
    - criterion: AC22
      evidence_files:
        - backend/state-api/state_api/main.py
      evidence_tests:
        - tests/test_backend_layout.py::test_python_services_have_entrypoints[state-api-state_api/main.py]
    - criterion: AC23
      evidence_files: []
      evidence_tests:
        - "bash scripts/smoke-test.sh"
    - criterion: AC24
      evidence_files:
        - CHANGELOG.md
      evidence_tests: []
    - criterion: AC25
      evidence_files:
        - backend/state-api/README.md
      evidence_tests: []
    - criterion: AC26
      evidence_files:
        - README.md
      evidence_tests: []
    - criterion: AC27
      evidence_files:
        - docs/SYSTEM-WORKFLOW.md
      evidence_tests: []
    - criterion: AC28
      evidence_files: []
      evidence_tests: []
    - criterion: AC29
      evidence_files: []
      evidence_tests: []

  summary: |
    Delivered the Wave-2 state-api package: five REST endpoints (GET/PUT checkpoint,
    lease acquire/renew/release), DynamoDB StateStore with conditional writes and
    numeric lease_expires_at for TTL, CanonicalEvent emission on successful
    checkpoint PUT with X-Canon-Event-Id, default JSON-line logger sink, and an
    offline moto test suite. Root/smoke pytest remains green by skipping
    moto-backed tests when moto is not installed; full coverage uses
    `cd backend/state-api && pip install -e ../shared -e .[test] && pytest -q`.

  decisions:
    - Used pydantic-settings for Settings and get_settings() lru_cache; empty
      STATE_TABLE_NAME yields degraded /healthz without crashing imports.
    - Consolidated get_state_store in leases.py and imported it from
      checkpoints.py so app.dependency_overrides[get_state_store] applies to
      both routers.
    - pytest.importorskip("moto") runs inside the dynamodb_table fixture so
      test_healthz runs in minimal envs while other tests skip cleanly if moto
      is absent (avoids editing forbidden root requirements/pytest config).

  next_actions:
    - qa-gate: rerun the reproduction list and confirm no forbidden-path diffs.
    - Parent: pip install -e backend/shared -e backend/state-api before deploy;
      set STATE_TABLE_NAME/AWS_REGION in runtime.

  open_questions:
    - None for v1 scope (auth deferred per OQ-E2-T2-01).

END_HANDOFF_TO_QA
```
