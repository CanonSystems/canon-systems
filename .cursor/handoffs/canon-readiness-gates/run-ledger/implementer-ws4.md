HANDOFF_TO_QA_SHARD
shard_id: ws4
task_id: run-ledger
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
branch: feature/canon-run-ledger-readiness

implementation_summary: |
  Documented archive vs run-ledger vs checkpoint/lease vs future readiness
  (no canon readiness check). Extended state-api README with
  STATE_RUN_LEDGER_TABLE_NAME, PUT/GET contract, and test pointers. Synced
  SYSTEM-WORKFLOW persistence bullet and MEMORY-PLATFORM-RUNTIME env table +
  boundary subsection. Root README command table + backend blurb; CHANGELOG
  Unreleased run-ledger entry. Fixed CLI HTTP verb: POST -> PUT to match
  FastAPI run_ledger router (ws2/ws3 integration).

artifacts:
  - backend/state-api/README.md
  - docs/SYSTEM-WORKFLOW.md
  - docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md
  - README.md
  - CHANGELOG.md
  - src/canon_systems/run_ledger.py
  - src/canon_systems/run_ledger_cli.py
  - src/canon_systems/cli.py
  - tests/test_run_ledger_cli.py

acceptance_criteria:
  - id: AC7
    status: SATISFIED
    evidence:
      - "SYSTEM-WORKFLOW §3 run-ledger bullet: separate table, keys, archive_refs by reference, CANON_STATE_API_URL, later readiness explicit deferral."
      - "MEMORY-PLATFORM-RUNTIME §1.3: STATE_RUN_LEDGER_TABLE_NAME + three-way boundary (archive / ledger / checkpoint)."
      - "backend/state-api/README.md: configuration table + PUT/GET sections + CLI pointer."
      - "README.md: canon run-ledger row in Commands."
  - id: AC8
    status: SATISFIED
    evidence:
      - "pytest tests/ : 519 passed"
      - "pytest backend/state-api/tests/ : 39 passed"
  - id: integration_ws2_ws3
    status: SATISFIED
    evidence:
      - "post_run_ledger_to_state_api uses urllib Request method PUT; test asserts req.get_method() == PUT"

pytest: |
  repo-root tests/: 519 passed
  backend/state-api/tests/: 39 passed
END_HANDOFF_TO_QA_SHARD
