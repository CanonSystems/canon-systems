# Canon Memory Platform Plan (Living Draft)

This document defines the target architecture for perpetual, crash-safe,
multi-agent collaboration across users and machines. Update this file each time
we evolve memory architecture, retrieval strategy, or orchestration contracts.

## 1) North Star

Build a three-plane memory system where agents can always:

- resume after crashes without losing task state,
- coordinate concurrently without stepping on each other,
- query code structure efficiently (low token/context cost),
- and prove who did what, when, and why.

## 2) Memory Planes

### A. Code Graph Plane (structural code intelligence)

Purpose: answer "what exists and what depends on what?" with minimal token cost.

- Primary candidate: Axon-style graph retrieval (query/context/impact).
- Optional interoperability layer: SCIP indexes as normalized exchange format.
- Core requirement: graph-first retrieval before broad file reads.

### B. Operational State Plane (shared working memory)

Purpose: answer "what is happening right now?" for all active agents.

- Shared cloud state (task/workstream scoped) for checkpoints and handoffs.
- Mandatory pre-step hydration + post-step checkpoint writes.
- Concurrency controls: lease/lock, optimistic versioning, conflict handling.

### C. Historical Knowledge Plane (durable canonical memory)

Purpose: answer "what happened and why?" with auditability.

- Canonical artifact captures for decisions, QA results, releases, failures.
- Immutable event trail keyed by company/repo/plan/task/handoff/agent.
- Telemetry for DoR failures, stalls, retries, and gate outcomes.

### D. Human Synthesis Plane (operator visibility)

Purpose: answer "what matters now?" for humans.

- Obsidian-Mind style summaries, status pages, decision journals, blocker views.
- Synced from canonical + operational layers (not source of truth itself).

## 3) Canonical IDs and Event Model

Required identifiers on all major records:

- `company_id`, `repository_id`, `plan_id`, `task_id`, `workstream_id`,
  `handoff_id`
- `actor_id`, `agent_name`, `agent_run_id`, `model`
- `event_id`, `parent_event_id`, `timestamp`, `state_version`

Required event payload dimensions:

- transition (`from_state` -> `to_state`)
- evidence artifacts (paths + IDs)
- decisions and open questions
- blocker classification and unblock ask

## 4) Crash Recovery and Resume Contract

Every chain phase (`scoper`, `cursor-pilot`, `implementer`, `qa-gate`,
`release-orchestrator`) must:

1. Read latest checkpoint before doing work.
2. Verify lease/version ownership for its workstream.
3. Write checkpoint at phase boundary.
4. Write terminal status (`PASS`, `FAIL`, `STALLED`, `DEFERRED`) before exit.

On restart, orchestrator must resume from first incomplete phase based on
durable checkpoint state, not chat history.

## 5) Concurrency Contract

- Lease-based ownership per `(plan_id, task_id, workstream_id)`.
- Optimistic updates require expected `state_version`.
- On conflict:
  - merge non-overlapping updates,
  - reject stale writes,
  - escalate semantic collisions.
- Watchdog marks stale runs as `STALLED` after timeout and emits unblock path.

## 6) Retrieval Strategy (Efficiency)

For coding tasks, retrieval order:

1. Code graph query (structural shortlist).
2. Operational checkpoint context (what changed this run).
3. Canonical memory summary (historical decisions/constraints).
4. Minimal direct file reads for implementation/testing.

Success metric: reduce exploratory read/search calls per task while preserving
quality and regression safety.

## 7) Observability and Accountability

Track per-task and per-wave:

- lead time, cycle time, retry count
- DoR reject causes and remediation latency
- stall frequency and unblock time
- token usage by phase and retrieval source
- model usage by agent role

Every terminal event must answer:

- who acted,
- what changed,
- what evidence proves it,
- why the decision was made.

## 8) Reliability Posture

- Fail closed for orchestration-critical state writes.
- Queue + retry for non-critical telemetry transport.
- Idempotent event writes (deterministic IDs).
- Health gates for memory backends before major execution waves.

## 9) Implementation Waves

**Status:** Waves 0–7 **shipped** under Canon Memory Platform v1
(see `docs/MEMORY-PLATFORM-BACKLOG.md` and `CHANGELOG.md` for the
per-task record). Summary:

### Wave 0 — Inventory + consolidation (E0) — SHIPPED

- Sibling-repo audit (`docs/WAVE-0-AUDIT.md`, `docs/DEPRECATIONS.md`);
  consolidated backend monorepo under `backend/`; Terraform root
  mirrored into `infra/terraform/`.

### Wave 1 — Stabilize present stack (E1) — SHIPPED

- `canon memory-health` probes canonical/mempalace/state/graph.
- MemPalace retry queue + `canon flow-audit --require-memory-health`
  release-gate flag; release-orchestrator enforces memory-health.

### Wave 2 — Shared checkpoint API (E2) — SHIPPED

- `backend/state-api` REST plane on DynamoDB; `canon checkpoint`
  lease + versioning CLI; per-phase checkpoint artifacts enforced in
  `canon flow-audit` / `canon qa-validate`.

### Wave 3 — Graph-first integration (E3) — SHIPPED

- `backend/axon-service` FastAPI multi-tenant graph plane
  (`/index`, `/query`, `/impact`, `/healthz`); `canon graph` CLI
  subcommands; `retrieval_breakdown` canonical events.

### Wave 4 — Resume automation (E4) — SHIPPED

- `canon resume` orchestrator resume engine; lease enforcement in
  CLI + templates; `canon stall-watchdog scan` with
  `lease_stall_detected` events; resume runbook wired into the
  release-gate checklist.

### Wave 5 — Human synthesis (E5) — SHIPPED

- `docs/VAULT-LAYOUT.md` v1; deterministic `backend/synthesis`
  generator + publisher; `backend/synthesis-web` read-only SSR
  browser; `canon synth show` streaming CLI; `canon vault sync`
  + background mirror daemon; `canon release publish-on-pass`
  auto-publish hook.

### Wave 6 — Observability (E6) — SHIPPED

- `metrics_rollup.aggregate` pure-Python aggregator; `canon report`
  CLI with scope/window filters and JSON/CSV output.

### Wave 7 — Cleanup + distribution (E7) — SHIPPED

- Hard-lock discipline rule distributed via `canon wire` to every
  enabled repo (`tests/test_wire_distribution.py`); sibling-repo
  disposition finalized in `docs/DEPRECATIONS.md`; five-file
  living-spec refresh.

## 9a) Executable backlog

The concrete, agent-executable version of this plan lives in
[`docs/MEMORY-PLATFORM-BACKLOG.md`](MEMORY-PLATFORM-BACKLOG.md). It contains a
`PROJECT_EXECUTION_PLAN` block sized for `scoper -> cursor-pilot -> implementer
-> qa-gate -> release-orchestrator`, plus the schemas/CLI surface each task
targets.

## 10) Definition of Done (Platform Level)

The platform is "complete enough" when:

- concurrent agents can safely collaborate without hidden state loss,
- crash recovery resumes deterministically from checkpoints,
- code comprehension is graph-assisted and token-efficient,
- full auditability exists for actor/agent/task transitions,
- human operators have current, trustworthy synthesis without manual stitching.
