# Canon Memory Platform — Implementation Backlog

This document turns `docs/MEMORY-PLATFORM-PLAN.md` into a concrete execution
backlog that the Canon agent flow can run task-by-task from `scoper` onwards.

Read order for agents:

1. `docs/MEMORY-PLATFORM-PLAN.md` (why / target architecture)
2. `docs/SYSTEM-WORKFLOW.md` (current runtime + contracts)
3. This file (what to build, in what order, with what shape)

Every task below is sized to be directly consumable by `scoper` — it has
explicit acceptance criteria, a done signal, and a dependency edge. Parent
orchestration is expected to drive these through:

`scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator`

with the standard packet persistence, DoR telemetry, and merge gates already
enforced by `canon qa-validate` and `canon flow-audit`.

---

## A) Canonical identifiers (used across all tasks)

Every record/event/artifact produced by these tasks must carry:

- `company_id`, `repository_id`, `plan_id`, `task_id`, `workstream_id`
- `handoff_id`, `agent_name`, `agent_run_id`, `actor_id`, `model`
- `event_id`, `parent_event_id`, `timestamp`, `state_version`

IDs are deterministic where possible (`sha256(company_id|plan_id|task_id|...)`)
so writes are idempotent and safe to retry.

---

## B) Checkpoint schema (introduced in Wave 2, reused after)

Storage key: `checkpoint/<company_id>/<repository_id>/<plan_id>/<task_id>/<workstream_id>.json`

```json
{
  "schema_version": 1,
  "company_id": "…",
  "repository_id": "…",
  "plan_id": "…",
  "task_id": "…",
  "workstream_id": "…",
  "handoff_id": "…",
  "phase": "scoper|cursor-pilot|implementer|qa-gate|release-orchestrator",
  "phase_status": "in_progress|pass|fail|stalled|deferred",
  "state_version": 7,
  "lease": {
    "owner_agent_run_id": "…",
    "owner_actor_id": "…",
    "acquired_at": "…",
    "expires_at": "…"
  },
  "inputs": { "packet_paths": ["…"], "evidence_refs": ["…"] },
  "outputs": { "packet_paths": ["…"], "artifact_refs": ["…"] },
  "decisions": [ { "id": "…", "summary": "…", "rationale": "…" } ],
  "open_questions": ["…"],
  "last_event_id": "…",
  "updated_at": "…"
}
```

Rules:

- Writes require expected `state_version` (optimistic).
- Lease must be live (non-expired) and owned by caller for mutating writes.
- Reads are always allowed.
- Write always emits a canonical event (`checkpoint_write`) to the historical
  plane for auditability.

---

## C) Canonical event envelope (historical plane)

```json
{
  "schema_version": 1,
  "event_id": "…",
  "parent_event_id": "…",
  "event_type": "checkpoint_write|dor_failure|qa_result|release_status|graph_query|…",
  "company_id": "…",
  "repository_id": "…",
  "plan_id": "…",
  "task_id": "…",
  "handoff_id": "…",
  "agent_name": "…",
  "agent_run_id": "…",
  "actor_id": "…",
  "model": "…",
  "timestamp": "…",
  "state_version": 7,
  "payload": { "…": "…" }
}
```

All CLI commands introduced below must emit this envelope on terminal outcomes.

---

## D) CLI surface added by this backlog

| Command | Wave | Purpose |
|---|---|---|
| `canon memory-health` | 1 | Report liveness of canonical + mempalace + graph backends |
| `canon checkpoint read` | 2 | Load checkpoint JSON for `(plan_id, task_id, workstream_id)` |
| `canon checkpoint write` | 2 | Persist checkpoint with lease + version check |
| `canon checkpoint lease` | 2 | Acquire/renew/release lease |
| `canon graph query` | 3 | Structural shortlist for a symbol/query |
| `canon graph impact` | 3 | Impact analysis for a file/symbol change |
| `canon resume` | 4 | Resume a plan from durable checkpoints |
| `canon synth publish` | 5 | Publish human-readable synthesis to vault |
| `canon report` | 6 | Telemetry rollups (DoR, stalls, tokens, cycle time) |

---

## E) PROJECT_EXECUTION_PLAN (agent-executable)

This block is the handoff to `scoper`. Parent orchestration should pick one
`task_id` at a time and drive the standard per-task chain.

```
PROJECT_EXECUTION_PLAN
  initiative:
    title: "Canon Memory Platform v1"
    objective: "Deliver a three-plane memory platform (code graph, operational state, historical knowledge) plus human synthesis so multi-agent, multi-machine Canon work is crash-safe, concurrent, and token-efficient."
    assumptions:
      - "Canonical AWS-backed memory is live and healthy."
      - "Rejection telemetry contract is already enforced by flow-audit + qa-validate."
      - "Axon-style graph retrieval is acceptable as the code graph implementation."
    open_questions:
      - "Final hosting target for the graph service (Workers + D1/R2 vs ECS)."
      - "Obsidian-Mind vault ownership model (per-company vs per-repo)."
  epic_backlog:

    - epic_id: "E1"
      title: "Stabilize present memory stack"
      user_value: "Agents get honest, fail-closed signals about memory health before acting."
      success_criteria:
        - "canon memory-health reports canonical + mempalace + graph status as JSON."
        - "Preflight hydrates from working backends only and surfaces degraded state."
        - "CI blocks releases when memory-health is degraded for orchestration-critical backends."
      tasks:
        - task_id: "E1-T1"
          title: "Add canon memory-health CLI"
          goal: "Single command reports structured health of canonical, mempalace, graph."
          acceptance_criteria:
            - "Exit 0 only if all required backends respond within budget."
            - "Emits JSON with per-backend status, latency_ms, version, last_error."
            - "Honors CANON_MEMORY_HEALTH_REQUIRED env (comma list) for fail-closed set."
          depends_on: []
          can_run_parallel: true
          parallel_group: "wave-1"
          done_signal:
            - "tests/test_memory_health.py PASS covering healthy/degraded/unreachable."
            - "README command table updated."
        - task_id: "E1-T2"
          title: "Fix mempalace endpoint resolution + queue fallback"
          goal: "Eliminate silent 404s by validating MEMORY_ADAPTER_URL and falling back to local queue when unreachable."
          acceptance_criteria:
            - "Preflight records mempalace_status explicitly in context-latest.md."
            - "Failed searches enqueue retry and do not surface as empty success."
          depends_on: ["E1-T1"]
          can_run_parallel: false
          parallel_group: "wave-1b"
          done_signal:
            - "Integration test simulates 404 and asserts degraded mode + queue write."
        - task_id: "E1-T3"
          title: "Release gate: require memory-health PASS for critical backends"
          goal: "Wire memory-health into release-orchestrator merge gates."
          acceptance_criteria:
            - "release-orchestrator template lists memory-health as required gate."
            - "flow-audit verifies memory-health evidence artifact per handoff."
          depends_on: ["E1-T1"]
          can_run_parallel: true
          parallel_group: "wave-1b"
          done_signal:
            - "tests/test_agent_templates.py asserts new gate text."
            - "tests/test_flow_audit.py covers missing memory-health evidence."

    - epic_id: "E2"
      title: "Shared checkpoint API (operational state plane)"
      user_value: "Agents can resume from durable state instead of chat history."
      success_criteria:
        - "All five chain phases read a checkpoint before work and write one after."
        - "Optimistic versioning + leases prevent double-writes."
        - "qa-validate + flow-audit enforce checkpoint presence per task."
      tasks:
        - task_id: "E2-T1"
          title: "Define checkpoint schema + storage adapter"
          goal: "Implement AWS-backed checkpoint store with the schema in section B."
          acceptance_criteria:
            - "Read/write/compare-and-set primitives exist in canon_systems/checkpoint.py."
            - "Deterministic IDs + idempotent writes verified by tests."
          depends_on: ["E1-T1"]
          can_run_parallel: false
          parallel_group: "wave-2a"
          done_signal:
            - "tests/test_checkpoint_store.py PASS incl. version conflict + lease expiry."
        - task_id: "E2-T2"
          title: "Add canon checkpoint read/write/lease CLI"
          goal: "Expose checkpoint primitives to agents."
          acceptance_criteria:
            - "JSON in/out; exit codes distinguish conflict, lease-denied, not-found."
            - "--expected-version and --lease-token flags enforced."
          depends_on: ["E2-T1"]
          can_run_parallel: false
          parallel_group: "wave-2b"
          done_signal:
            - "tests/test_cli_checkpoint.py PASS."
            - "README updated."
        - task_id: "E2-T3"
          title: "Update agent templates to hydrate + checkpoint at phase boundaries"
          goal: "scoper, cursor-pilot, implementer, qa-gate, release-orchestrator read-before/write-after."
          acceptance_criteria:
            - "Each template includes explicit checkpoint read and write steps."
            - "memory-layer-defaults.mdc lists checkpoint contract as required."
          depends_on: ["E2-T2"]
          can_run_parallel: false
          parallel_group: "wave-2c"
          done_signal:
            - "tests/test_agent_templates.py asserts checkpoint clauses per template."
        - task_id: "E2-T4"
          title: "Enforce checkpoint artifacts in flow-audit + qa-validate"
          goal: "Prevent merge when phase checkpoints are missing."
          acceptance_criteria:
            - "flow-audit checks expected checkpoint keys per phase for the task."
            - "qa-validate --require-checkpoints flag added."
          depends_on: ["E2-T3"]
          can_run_parallel: false
          parallel_group: "wave-2d"
          done_signal:
            - "tests/test_flow_audit.py + tests/test_qa_validate.py cover new checks."

    - epic_id: "E3"
      title: "Graph-first code retrieval (code graph plane)"
      user_value: "Agents answer structural questions with ~10x fewer tokens than file-wide search."
      success_criteria:
        - "canon graph query/impact return structural shortlists in <2s p50."
        - "scoper + cursor-pilot hydrate graph context before reading files."
        - "Retrieval source is logged per agent call for token accounting."
      tasks:
        - task_id: "E3-T1"
          title: "Stand up graph backend service"
          goal: "Host Axon-style graph index per (company_id, repository_id) with auth."
          acceptance_criteria:
            - "Service accepts repo index ingestion and exposes query/impact endpoints."
            - "Multi-tenant scoping by company_id + repository_id enforced."
          depends_on: ["E1-T1"]
          can_run_parallel: true
          parallel_group: "wave-3a"
          done_signal:
            - "Deployed endpoint + health probe integrated into canon memory-health."
        - task_id: "E3-T2"
          title: "Indexer pipeline for repo changes"
          goal: "Incrementally reindex on commit/push + support full reindex."
          acceptance_criteria:
            - "Incremental index job runs under 60s for typical change set."
            - "Reindex status queryable by repository_id + commit_sha."
          depends_on: ["E3-T1"]
          can_run_parallel: false
          parallel_group: "wave-3b"
          done_signal:
            - "Integration test indexes sample repo and queries resolve."
        - task_id: "E3-T3"
          title: "Add canon graph query + canon graph impact CLI"
          goal: "Agent-facing CLI wrappers over the graph service."
          acceptance_criteria:
            - "JSON output includes nodes, edges, scores, and source spans."
            - "Honors company_id/repository_id from standard env layering."
          depends_on: ["E3-T1"]
          can_run_parallel: false
          parallel_group: "wave-3c"
          done_signal:
            - "tests/test_graph_cli.py PASS with recorded fixtures."
        - task_id: "E3-T4"
          title: "Retrieval policy: graph-first in templates + rules"
          goal: "Require graph hydration before broad file reads for coding work."
          acceptance_criteria:
            - "memory-layer-defaults.mdc encodes retrieval order from plan §6."
            - "scoper/cursor-pilot/implementer templates cite graph query step."
          depends_on: ["E3-T3", "E2-T3"]
          can_run_parallel: false
          parallel_group: "wave-3d"
          done_signal:
            - "tests/test_agent_templates.py asserts graph-first clauses."
        - task_id: "E3-T5"
          title: "Retrieval-source telemetry"
          goal: "Record tokens_in/out per retrieval source (graph, checkpoint, canonical, file)."
          acceptance_criteria:
            - "Every agent phase emits a retrieval_breakdown canonical event."
            - "canon report surfaces per-phase token cost by source (stub accepted if Wave 6 not yet delivered)."
          depends_on: ["E3-T4"]
          can_run_parallel: true
          parallel_group: "wave-3e"
          done_signal:
            - "tests/test_retrieval_telemetry.py PASS."

    - epic_id: "E4"
      title: "Crash-safe resume + concurrency"
      user_value: "No lost work across crashes, restarts, or concurrent agents."
      success_criteria:
        - "canon resume restarts from first incomplete phase using checkpoints only."
        - "Lease conflicts return structured errors that orchestration handles."
        - "Stalled runs auto-escalate with unblock instructions."
      tasks:
        - task_id: "E4-T1"
          title: "Orchestrator resume engine"
          goal: "Detect incomplete phases per task and re-enter at the correct agent."
          acceptance_criteria:
            - "canon resume --plan-id <id> replays from checkpoint, not chat."
            - "Idempotent re-entry; no duplicate canonical events."
          depends_on: ["E2-T4"]
          can_run_parallel: false
          parallel_group: "wave-4a"
          done_signal:
            - "Crash/restart integration test PASS."
        - task_id: "E4-T2"
          title: "Lease + versioning enforcement in CLI + templates"
          goal: "All mutating checkpoint writes require live lease + expected version."
          acceptance_criteria:
            - "Conflict paths produce actionable errors with resolution steps."
            - "Templates document acquire/renew/release flow."
          depends_on: ["E2-T2"]
          can_run_parallel: true
          parallel_group: "wave-4a"
          done_signal:
            - "tests/test_checkpoint_concurrency.py PASS."
        - task_id: "E4-T3"
          title: "Stall watchdog + unblock event"
          goal: "Mark expired leases STALLED and emit unblock canonical event."
          acceptance_criteria:
            - "Scheduled job scans active leases and transitions stuck ones."
            - "Unblock event includes diagnostic evidence + suggested next step."
          depends_on: ["E4-T2"]
          can_run_parallel: false
          parallel_group: "wave-4b"
          done_signal:
            - "Simulated stall test PASS."
        - task_id: "E4-T4"
          title: "Resume runbook + release gate"
          goal: "Operators have a one-page path for resume + release checks it."
          acceptance_criteria:
            - "docs/runbooks/RESUME.md exists with canon resume examples."
            - "release-orchestrator template references resume check."
          depends_on: ["E4-T1"]
          can_run_parallel: true
          parallel_group: "wave-4c"
          done_signal:
            - "Template test asserts resume-aware wording."

    - epic_id: "E5"
      title: "Human synthesis plane"
      user_value: "Operators always see current, trustworthy status without manual stitching."
      success_criteria:
        - "Per plan/task synthesis is auto-published from canonical + operational data."
        - "No human source-of-truth drift; vault pages cite event IDs."
      tasks:
        - task_id: "E5-T1"
          title: "Synthesis generator service"
          goal: "Materialize plan/task/decision/blocker summaries from canonical events."
          acceptance_criteria:
            - "Deterministic output per (plan_id, task_id, cutoff_timestamp)."
            - "Citations link to event_ids."
          depends_on: ["E2-T1"]
          can_run_parallel: true
          parallel_group: "wave-5a"
          done_signal:
            - "tests/test_synth_generator.py PASS."
        - task_id: "E5-T2"
          title: "canon synth publish CLI"
          goal: "Push synthesis into Obsidian-Mind-compatible vault structure."
          acceptance_criteria:
            - "Idempotent publish; diff-only writes."
            - "Vault target configurable per company/repo."
          depends_on: ["E5-T1"]
          can_run_parallel: false
          parallel_group: "wave-5b"
          done_signal:
            - "tests/test_synth_publish.py PASS."
        - task_id: "E5-T3"
          title: "Auto-publish hook on phase completion"
          goal: "release-orchestrator triggers publish after RELEASE_STATUS."
          acceptance_criteria:
            - "Template includes publish step with failure-tolerant retry."
          depends_on: ["E5-T2"]
          can_run_parallel: false
          parallel_group: "wave-5c"
          done_signal:
            - "Template test asserts publish step."

    - epic_id: "E6"
      title: "Observability + accountability"
      user_value: "We can see lead time, DoR causes, stalls, and token cost per task/wave."
      success_criteria:
        - "canon report returns per-phase metrics with drilldowns."
        - "Dashboards driven by canonical events only."
      tasks:
        - task_id: "E6-T1"
          title: "Metrics aggregator over canonical events"
          goal: "Rollups for lead/cycle time, retries, DoR causes, stalls, token cost."
          acceptance_criteria:
            - "Aggregator reads events by company_id/plan_id/time window."
            - "Outputs stable JSON schema usable by dashboards."
          depends_on: ["E3-T5", "E4-T3"]
          can_run_parallel: true
          parallel_group: "wave-6a"
          done_signal:
            - "tests/test_metrics_rollup.py PASS."
        - task_id: "E6-T2"
          title: "canon report CLI"
          goal: "Operator-facing rollups + CSV export."
          acceptance_criteria:
            - "Supports --plan-id, --since, --until, --by (phase|agent|source)."
          depends_on: ["E6-T1"]
          can_run_parallel: false
          parallel_group: "wave-6b"
          done_signal:
            - "tests/test_cli_report.py PASS."
            - "README updated."

  execution_policy:
    mode: "plan-first"
    per_task_workflow: "scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator"
    completion_rule: "all task_ids complete with QA PASS and release gates green; E1 must complete before E2; E2 must complete before E4; E3 can run in parallel with E2/E4; E5 depends on E2; E6 depends on E3 and E4."
END_PROJECT_EXECUTION_PLAN
```

---

## F) Rollout order (human-readable)

1. **Wave 1 (E1):** unblock visibility. Nothing else is safe to build until we
   can see what is healthy.
2. **Wave 2 (E2):** checkpoint API. Unlocks resume, concurrency, and real
   multi-agent collaboration.
3. **Wave 3 (E3):** graph-first retrieval. Biggest single token-efficiency
   lever; can run in parallel with Wave 2.
4. **Wave 4 (E4):** resume + concurrency enforcement. Requires E2.
5. **Wave 5 (E5):** human synthesis. Requires E2 (plus canonical, already live).
6. **Wave 6 (E6):** observability. Requires E3 and E4 to produce the source
   signal.

---

## G) Invariants every task must uphold

- Every CLI touching memory emits a canonical event envelope (section C).
- Every agent phase reads a checkpoint before work and writes one after.
- Every rejection produces the DoR telemetry triple already required by
  `docs/SYSTEM-WORKFLOW.md` §4.
- Every new template/rule change is mirrored in:
  - `docs/SYSTEM-WORKFLOW.md`
  - `README.md`
  - relevant test in `tests/`
  - `CHANGELOG.md`

If any invariant is missing, `qa-gate` fails and release is blocked.
