HANDOFF_TO_QA_SHARD
shard_id: ws4
task_id: readiness-contract
handoff_id: canon-readiness-gates
plan_id: canon_readiness_gates_c389cad8
workstream_id: readiness-contract
branch: feature/canon-run-ledger-readiness

summary: |
  Documented the readiness contract (run-ledger GET boundary, archive-ref-only evaluation, snapshot/`--output`, exit 0/1/2) and explicit deferrals (no QA evidence normalization, shared DoR validator, credential/deploy attestation) across README, SYSTEM-WORKFLOW, MEMORY-PLATFORM-RUNTIME-AND-AGENTS, state-api README, CHANGELOG. Extended `canon readiness check` subparser description with GET /state/run-ledger pointer; added CLI help regression test.

acceptance_criteria:
  - id: AC8
    status: satisfied
    evidence:
      - "docs/SYSTEM-WORKFLOW.md §3 readiness bullet (contract + deferrals + exits)"
      - "docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md (CANON_STATE_API_URL + ledger/readiness boundary)"
      - "README.md commands table row for canon readiness check"
      - "backend/state-api/README.md GET /state/run-ledger read-only contract + canon readiness check"
      - "CHANGELOG.md [Unreleased] readiness entry with deferred work list"
      - "src/canon_systems/readiness_cli.py check description"
      - "tests/test_readiness_cli.py::test_readiness_check_help_documents_flags"

notes: |
  - Graph-first retrieval: `canon graph query` failed (SSL CERTIFICATE_VERIFY_FAILED, exit 5); `canon checkpoint read` failed (transport connection refused to default state-api). Evidence for this shard is file + canonical context.
  - Did not edit `.cursor/plans/canon_readiness_gates_c389cad8.plan.md` per constraints.

tests:
  command: |
    python3 -m pytest tests/test_readiness_cli.py tests/test_readiness.py tests/test_run_ledger_cli.py tests/test_run_ledger.py tests/test_packet_archive.py tests/test_packet_archive_cli.py backend/state-api/tests/test_run_ledger.py -q
    python3 -m pytest tests/ -q
    (cd backend/state-api && python3 -m pytest -q)
  result: "68 passed; 548 passed; 42 passed"

retrieval_breakdown_event: |
  Constructed per `src/canon_systems/retrieval_telemetry.py::build_retrieval_breakdown_event` (not persisted to NDJSON in this subagent turn):
  buckets: graph(degraded, query attempted), state(degraded, checkpoint read attempted), canonical(`.canon/memory/context-latest.md`), file(edited docs + readiness_cli + test_readiness_cli)
END_HANDOFF_TO_QA_SHARD
