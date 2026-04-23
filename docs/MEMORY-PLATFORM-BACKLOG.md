# Canon Memory Platform — Implementation Backlog

> **v1 status (2026-04-23):** All 23 tasks across Waves 0–7 have a PASS
> `RELEASE_STATUS` under `.cursor/handoffs/canon-memory-v1/<task_id>/`. Full
> `tests/` suite: **440 passing**. The backlog is preserved below as the
> authoritative record of what was built; see `CHANGELOG.md` for the
> per-task summary and `docs/MEMORY-PLATFORM-PLAN.md §9` for the wave-level
> outcomes.

This document turns `docs/MEMORY-PLATFORM-PLAN.md` into a concrete execution
backlog that the Canon agent flow can run task-by-task from `scoper` onwards.

Read order for agents:

1. `docs/MEMORY-PLATFORM-PLAN.md` (why / target architecture)
2. `docs/SYSTEM-WORKFLOW.md` (current runtime + contracts)
3. This file (what to build, in what order, with what shape)
4. `.cursor/plans/canon_memory_platform_build_d21073e1.plan.md` (execution
   discipline: Build Kickoff, agent chain rules, wave boundaries)
5. `.cursor/rules/memory-platform-build-discipline.mdc` (hard-lock rule,
   auto-loaded every turn)

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

Storage: DynamoDB table `canon-state` (per environment), keyed by
`(pk = company_id#repository_id, sk = plan_id#task_id#workstream_id)`.

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

- Writes require expected `state_version` (optimistic, enforced by DynamoDB
  conditional write on `state_version` attribute).
- Lease must be live (`expires_at > now`) and owned by caller for mutating
  writes. Non-owning mutations return structured conflict errors.
- Reads are always allowed.
- TTL on the `lease.expires_at` attribute auto-expires stale leases.
- Write always emits a canonical `checkpoint_write` event to the historical
  plane for auditability.

---

## C) Canonical event envelope (historical plane)

```json
{
  "schema_version": 1,
  "event_id": "…",
  "parent_event_id": "…",
  "event_type": "checkpoint_write|dor_failure|qa_result|release_status|graph_query|graph_index|retrieval_breakdown|synth_publish|…",
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
| `canon memory-health` | 1 | Report liveness of canonical + memory-adapter + state-api + axon-service |
| `canon checkpoint read` | 2 | Load checkpoint JSON for `(plan_id, task_id, workstream_id)` |
| `canon checkpoint write` | 2 | Persist checkpoint with lease + version check |
| `canon checkpoint lease` | 2 | Acquire/renew/release lease |
| `canon graph index` | 3 | Push incremental or full index snapshot to axon-service |
| `canon graph query` | 3 | Structural shortlist for a symbol/query |
| `canon graph impact` | 3 | Impact analysis for a file/symbol change |
| `canon resume` | 4 | Resume a plan from durable checkpoints |
| `canon synth publish` | 5 | Regenerate S3 vault from canonical + state (server-side generator entrypoint) |
| `canon synth show` | 5 | Print vault markdown for agent context hydration |
| `canon vault sync` | 5 | One-shot S3 -> `<repo>/vault/` mirror (also runs as background service installed by `canon wire`) |
| `canon report` | 6 | Telemetry rollups (DoR, stalls, tokens, cycle time) |

---

## E) PROJECT_EXECUTION_PLAN (agent-executable)

This block is the handoff to `scoper`. Parent orchestration should pick one
`task_id` at a time and drive the standard per-task chain.

```
PROJECT_EXECUTION_PLAN
  initiative:
    title: "Canon Memory Platform v1"
    objective: "Consolidate in-use backend services into canon-systems/backend/ and deliver a three-plane memory platform (code graph via hosted Axon, operational state via DynamoDB, historical knowledge via canonical API) plus human synthesis (server-rendered Obsidian-compatible S3 vault with three read paths) so multi-agent, multi-machine Canon work is crash-safe, concurrent, and token-efficient."
    assumptions:
      - "Canonical AWS-backed memory (knowledge-api + knowledge-worker + memory-adapter) is live; Wave 0 locates and consolidates the deployment units."
      - "Rejection telemetry contract is already enforced by flow-audit + qa-validate."
      - "Axon (MIT) is an acceptable code-graph engine; it is forked into backend/axon-service and operated multi-tenant."
      - "DynamoDB is the substrate for operational state (checkpoints + leases)."
      - "Sibling repos canon-platform, canon-systems-v2, mempalace, obsidian-mind, temporal, total_recall remain available read-only during Wave 0 audit."
    open_questions:
      - "Final hosting unit for each backend service (ECS Fargate vs Lambda vs Workers) — decided per service inside Wave 0."
      - "Per-company vs per-repo vault scoping default (decided in E5-T1)."
  epic_backlog:

    - epic_id: "E0"
      title: "Inventory and consolidation (blocks everything else)"
      user_value: "One repo (canon-systems) owns every backend service the agents actually use, with a clean monorepo layout and imported IaC; sibling repos are marked deprecated so future work has one home."
      success_criteria:
        - "backend/ monorepo exists with per-service packages: knowledge-api, knowledge-worker, memory-adapter, plus placeholders for state-api, axon-service, synthesis, synthesis-web."
        - "infra/ contains imported IaC for every currently-deployed service (no rewrite, just capture)."
        - "canon capture, canon ask, canon dor-log all pass end-to-end against the consolidated stack."
        - "docs/DEPRECATIONS.md lists every sibling repo with explicit keep/deprecate status."
        - "docs/OBSIDIAN-MIND-CATALOGUE.md enumerates every synthesis/summary/transform capability in obsidian-mind so Wave 5 can absorb the useful logic."
      tasks:
        - task_id: "E0-T1"
          title: "Audit sibling repos and locate backend services"
          goal: "Find which services back KNOWLEDGE_API_URL, KNOWLEDGE_WORKER_URL, MEMORY_ADAPTER_URL and catalogue every asset in canon-platform, canon-systems-v2, mempalace, obsidian-mind, temporal, total_recall."
          acceptance_criteria:
            - "Report names the git repo + path + deployment target for each of the three URLs."
            - "docs/DEPRECATIONS.md drafted with keep|absorb|delete label per sibling."
            - "docs/OBSIDIAN-MIND-CATALOGUE.md drafted listing obsidian-mind capabilities with source file references."
          depends_on: []
          can_run_parallel: false
          parallel_group: "wave-0a"
          done_signal:
            - "docs/DEPRECATIONS.md and docs/OBSIDIAN-MIND-CATALOGUE.md committed."
        - task_id: "E0-T2"
          title: "Create backend/ monorepo skeleton with shared lib"
          goal: "Stand up backend/ with per-service packages and a shared lib for auth + canonical events + IDs."
          acceptance_criteria:
            - "backend/{knowledge-api,knowledge-worker,memory-adapter,state-api,axon-service,synthesis,synthesis-web} directories exist with README placeholders and matching entry-point scaffolding."
            - "backend/shared/ exposes auth, ids, events modules consumable by every service package."
            - "Root pyproject/poetry/turbo (language-appropriate) builds the workspace cleanly."
          depends_on: ["E0-T1"]
          can_run_parallel: false
          parallel_group: "wave-0b"
          done_signal:
            - "Workspace build passes."
            - "tests/test_backend_layout.py asserts the expected directory tree."
        - task_id: "E0-T3"
          title: "Consolidate in-use services into backend/"
          goal: "Move the three in-use services (knowledge-api, knowledge-worker, memory-adapter) into backend/ preserving git history where useful (git subtree / filter-repo)."
          acceptance_criteria:
            - "Each service builds and runs in place from backend/<service>/."
            - "Existing KNOWLEDGE_API_URL/KNOWLEDGE_WORKER_URL/MEMORY_ADAPTER_URL remain serviceable end-to-end."
            - "Git history for moved code is preserved or explicitly waived in the task notes."
          depends_on: ["E0-T2"]
          can_run_parallel: false
          parallel_group: "wave-0c"
          done_signal:
            - "CI builds each service package."
        - task_id: "E0-T4"
          title: "Stand up infra/ by importing existing AWS resources"
          goal: "Capture currently-deployed infra in infra/ (CDK or Terraform) without rewriting or redeploying."
          acceptance_criteria:
            - "infra/ imports existing S3 buckets, IAM roles, Secrets Manager entries, and whatever compute units host the three URLs."
            - "terraform plan / cdk diff shows no changes against production."
          depends_on: ["E0-T3"]
          can_run_parallel: false
          parallel_group: "wave-0d"
          done_signal:
            - "CI runs the import and asserts zero drift."
        - task_id: "E0-T5"
          title: "Smoke-test consolidated stack"
          goal: "canon capture, canon ask, canon dor-log pass end-to-end against backend/ services."
          acceptance_criteria:
            - "Integration harness exercises capture -> ask -> dor-log path."
            - "Run is green against the consolidated stack in dev."
          depends_on: ["E0-T4"]
          can_run_parallel: false
          parallel_group: "wave-0e"
          done_signal:
            - "tests/test_consolidation_smoke.py PASS."

    - epic_id: "E1"
      title: "Stabilize present memory stack"
      user_value: "Agents get honest, fail-closed signals about memory health before acting."
      success_criteria:
        - "canon memory-health reports canonical + memory-adapter + state-api (stub) + axon-service (stub) status as JSON."
        - "Preflight hydrates from working backends only and surfaces degraded state."
        - "CI blocks releases when memory-health is degraded for orchestration-critical backends."
      tasks:
        - task_id: "E1-T1"
          title: "Add canon memory-health CLI"
          goal: "Single command reports structured health of every backend listed in section D."
          acceptance_criteria:
            - "Exit 0 only if all required backends respond within budget."
            - "Emits JSON with per-backend status, latency_ms, version, last_error."
            - "Honors CANON_MEMORY_HEALTH_REQUIRED env (comma list) for fail-closed set."
            - "Stub endpoints (state-api, axon-service) return 'not_deployed' rather than failing the healthy set."
          depends_on: ["E0-T5"]
          can_run_parallel: true
          parallel_group: "wave-1a"
          done_signal:
            - "tests/test_memory_health.py PASS covering healthy/degraded/unreachable/not_deployed."
            - "README command table updated."
        - task_id: "E1-T2"
          title: "Fix memory-adapter endpoint resolution + queue fallback"
          goal: "Eliminate silent 404s by validating MEMORY_ADAPTER_URL and falling back to local queue when unreachable."
          acceptance_criteria:
            - "Preflight records memory_adapter_status explicitly in context-latest.md."
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
        - "backend/state-api service is deployed and backed by DynamoDB."
        - "All five chain phases read a checkpoint before work and write one after."
        - "Optimistic versioning + leases prevent double-writes."
        - "qa-validate + flow-audit enforce checkpoint presence per task."
      tasks:
        - task_id: "E2-T1"
          title: "Provision DynamoDB state table + infra/"
          goal: "Create the canon-state DynamoDB table per environment with the schema in section B."
          acceptance_criteria:
            - "infra/ includes the table with TTL enabled on lease.expires_at."
            - "Dev/staging/prod environments each get an isolated table via workspace var."
          depends_on: ["E0-T4"]
          can_run_parallel: false
          parallel_group: "wave-2a"
          done_signal:
            - "terraform apply / cdk deploy succeeds in dev with no drift."
        - task_id: "E2-T2"
          title: "Implement backend/state-api service"
          goal: "REST endpoints GET/PUT /state/checkpoint and POST /state/lease/{acquire|renew|release}."
          acceptance_criteria:
            - "Conditional DynamoDB writes enforce expected state_version."
            - "Lease endpoints enforce non-expired owner."
            - "Every mutating write emits a checkpoint_write canonical event."
          depends_on: ["E2-T1"]
          can_run_parallel: false
          parallel_group: "wave-2b"
          done_signal:
            - "backend/state-api/tests pass incl. version conflict + lease expiry."
        - task_id: "E2-T3"
          title: "Add canon checkpoint read/write/lease CLI"
          goal: "Expose state-api primitives to agents."
          acceptance_criteria:
            - "JSON in/out; exit codes distinguish conflict (1), lease-denied (2), not-found (3)."
            - "--expected-version and --lease-token flags enforced."
          depends_on: ["E2-T2"]
          can_run_parallel: false
          parallel_group: "wave-2c"
          done_signal:
            - "tests/test_cli_checkpoint.py PASS."
            - "README updated."
        - task_id: "E2-T4"
          title: "Update agent templates to hydrate + checkpoint at phase boundaries"
          goal: "scoper, cursor-pilot, implementer, qa-gate, release-orchestrator read-before/write-after."
          acceptance_criteria:
            - "Each template includes explicit checkpoint read and write steps."
            - "memory-layer-defaults.mdc lists checkpoint contract as required."
          depends_on: ["E2-T3"]
          can_run_parallel: false
          parallel_group: "wave-2d"
          done_signal:
            - "tests/test_agent_templates.py asserts checkpoint clauses per template."
        - task_id: "E2-T5"
          title: "Enforce checkpoint artifacts in flow-audit + qa-validate"
          goal: "Prevent merge when phase checkpoints are missing."
          acceptance_criteria:
            - "flow-audit checks expected checkpoint keys per phase for the task."
            - "qa-validate --require-checkpoints flag added."
          depends_on: ["E2-T4"]
          can_run_parallel: false
          parallel_group: "wave-2e"
          done_signal:
            - "tests/test_flow_audit.py + tests/test_qa_validate.py cover new checks."

    - epic_id: "E3"
      title: "Graph-first code retrieval (code graph plane)"
      user_value: "Agents answer structural questions with ~10x fewer tokens than file-wide search."
      success_criteria:
        - "backend/axon-service (forked Axon) is deployed and multi-tenant."
        - "canon graph query/impact return structural shortlists in <2s p50."
        - "scoper + cursor-pilot hydrate graph context before reading files."
        - "Retrieval source is logged per agent call for token accounting."
      tasks:
        - task_id: "E3-T1"
          title: "Fork and deploy backend/axon-service"
          goal: "Host Axon-style graph index per (company_id, repository_id) with auth + multi-tenant scoping."
          acceptance_criteria:
            - "Service accepts repo index ingestion and exposes query/impact endpoints."
            - "Multi-tenant scoping by company_id + repository_id enforced."
            - "Snapshots versioned by (repository_id, commit_sha) and stored in S3; metadata in DynamoDB."
          depends_on: ["E1-T1"]
          can_run_parallel: true
          parallel_group: "wave-3a"
          done_signal:
            - "Deployed endpoint + health probe integrated into canon memory-health."
        - task_id: "E3-T2"
          title: "Indexer pipeline for repo changes"
          goal: "canon graph index pre-push locally + CI webhook for full reindex on merge."
          acceptance_criteria:
            - "Incremental index job runs under 60s for typical change set."
            - "Reindex status queryable by repository_id + commit_sha."
            - "Agents never index locally at query time — query-time reads are pure RPC."
          depends_on: ["E3-T1"]
          can_run_parallel: false
          parallel_group: "wave-3b"
          done_signal:
            - "Integration test indexes sample repo and queries resolve against the service."
        - task_id: "E3-T3"
          title: "Add canon graph query + canon graph impact CLI"
          goal: "Agent-facing CLI wrappers over backend/axon-service."
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
            - "memory-layer-defaults.mdc encodes retrieval order from plan section 6."
            - "scoper/cursor-pilot/implementer templates cite graph query step."
          depends_on: ["E3-T3", "E2-T4"]
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
          depends_on: ["E2-T5"]
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
          depends_on: ["E2-T3"]
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
      title: "Human synthesis plane (server-rendered vault + three read paths)"
      user_value: "Operators always see current, trustworthy status without manual stitching. Browser users, agents, and Obsidian desktop users all consume the same single source of truth with zero conflicts."
      success_criteria:
        - "backend/synthesis regenerates an Obsidian-compatible S3 vault on RELEASE_STATUS PASS (absorbing useful obsidian-mind logic per E0-T1 catalogue)."
        - "Three read paths work: synthesis-web (browser), canon synth show (agent CLI), automatic in-repo mirror (<repo>/vault/ gitignored, pulled by background service)."
        - "Users never invoke sync manually; canon wire installs the background daemon at login time."
        - "No human source-of-truth drift; vault pages cite event IDs."
      tasks:
        - task_id: "E5-T1"
          title: "Vault layout spec + redaction allowlist"
          goal: "Publish docs/VAULT-LAYOUT.md defining the Obsidian-compatible S3 layout, scoping (per-company|per-repo), and the strict allowlist of event fields rendered into the vault."
          acceptance_criteria:
            - "Layout covers markdown with YAML frontmatter, wikilinks, seeded .obsidian/ config, attachments/."
            - "Allowlist lists every safe event field; everything else is silently dropped by the generator."
            - "Versioned spec (schema_version)."
          depends_on: ["E2-T1"]
          can_run_parallel: true
          parallel_group: "wave-5a"
          done_signal:
            - "docs/VAULT-LAYOUT.md committed and referenced by backend/synthesis README."
        - task_id: "E5-T2"
          title: "backend/synthesis generator service (absorbs obsidian-mind)"
          goal: "Deterministic summary generator reading canonical + state events, applying the allowlist, writing the Obsidian-compatible layout to S3. Absorbs useful summarization/graph-building logic from obsidian-mind per the Wave 0 catalogue."
          acceptance_criteria:
            - "Deterministic output per (plan_id, task_id, cutoff_timestamp)."
            - "Citations link to event_ids."
            - "Idempotent publish; diff-only writes."
            - "Exposes GET /synth/vault/changes?since=<ts> and GET /synth/show?plan_id=... endpoints."
          depends_on: ["E5-T1"]
          can_run_parallel: false
          parallel_group: "wave-5b"
          done_signal:
            - "backend/synthesis/tests/test_generator.py PASS."
            - "Integration test publishes a sample vault to dev S3 and re-publish is a no-op."
        - task_id: "E5-T3"
          title: "canon synth publish CLI (internal driver)"
          goal: "Idempotent diff-only driver used internally by backend/synthesis and by release-orchestrator."
          acceptance_criteria:
            - "JSON output with per-page diff stats."
            - "Safe to invoke repeatedly; no duplicate writes."
          depends_on: ["E5-T2"]
          can_run_parallel: false
          parallel_group: "wave-5c"
          done_signal:
            - "tests/test_cli_synth_publish.py PASS."
        - task_id: "E5-T4"
          title: "Read path 1 — backend/synthesis-web browser renderer"
          goal: "Serve a lightweight web renderer (Quartz-style or our own) over the S3 vault at a hosted URL."
          acceptance_criteria:
            - "Zero install for end users; anyone with access browses pages, backlinks, graph view, search."
            - "Rebuild-on-publish or request-time SSR chosen in a short in-task spike and recorded in the task packet."
          depends_on: ["E5-T2"]
          can_run_parallel: true
          parallel_group: "wave-5d"
          done_signal:
            - "Hosted URL responds with rendered sample vault."
            - "backend/synthesis-web/tests PASS."
        - task_id: "E5-T5"
          title: "Read path 2 — canon synth show for agents"
          goal: "Print vault markdown for a given (plan_id[, task_id]) so agents hydrate human-synthesis context during the chain without browser or sync."
          acceptance_criteria:
            - "CLI streams markdown to stdout."
            - "Honors company_id/repository_id from standard env layering."
          depends_on: ["E5-T2"]
          can_run_parallel: true
          parallel_group: "wave-5d"
          done_signal:
            - "tests/test_cli_synth_show.py PASS."
        - task_id: "E5-T6"
          title: "Read path 3 — automatic in-repo mirror"
          goal: "canon wire installs a user-level background service (launchd/systemd/scheduled task) that one-way pulls S3 -> <repo>/vault/ on a short interval (~10s); canon wire also adds the vault/ entry to .gitignore idempotently."
          acceptance_criteria:
            - "Daemon starts at login and pulls incrementally."
            - "<repo>/vault/ is read-only from client perspective (no push-back); offline laptop silently skips and catches up next tick."
            - "canon vault sync is also invocable manually for one-shot pulls."
            - "Cursor pre-turn hook triggers a refresh before any agent work starts in a session."
          depends_on: ["E5-T2"]
          can_run_parallel: true
          parallel_group: "wave-5d"
          done_signal:
            - "tests/test_vault_sync.py PASS (mocked S3)."
            - "install-script fixtures exercise launchd plist / systemd unit / scheduled task creation."
        - task_id: "E5-T7"
          title: "Auto-publish hook on RELEASE_STATUS PASS + optional notifier"
          goal: "release-orchestrator triggers publish after RELEASE_STATUS: PASS (once per release, not per task). Optional nice-to-have: ping a notifier endpoint so auto-pull fires near-instantly instead of waiting for next tick."
          acceptance_criteria:
            - "Template includes publish step with failure-tolerant retry."
            - "Notifier path is optional and documented."
          depends_on: ["E5-T3", "E5-T6"]
          can_run_parallel: false
          parallel_group: "wave-5e"
          done_signal:
            - "tests/test_agent_templates.py asserts auto-publish step."
            - "Integration test: RELEASE PASS triggers one publish + triggers sync within 30s."

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

    - epic_id: "E7"
      title: "Cleanup and distribution"
      user_value: "Sibling repos are removed, the hard-lock rule is distributed to every wired repo, and the five living-spec files reflect the final state of the platform."
      success_criteria:
        - "Deprecated sibling repos are deleted after a grace period per docs/DEPRECATIONS.md."
        - "canon wire distributes .cursor/rules/memory-platform-build-discipline.mdc to every wired repo via src/canon_systems/templates/rules/."
        - "Final five-file living-spec pass green: docs/SYSTEM-WORKFLOW.md, docs/MEMORY-PLATFORM-PLAN.md, docs/MEMORY-PLATFORM-BACKLOG.md, README.md, CHANGELOG.md."
      tasks:
        - task_id: "E7-T1"
          title: "Template hard-lock rule into canon-systems for canon wire distribution"
          goal: "Copy .cursor/rules/memory-platform-build-discipline.mdc into src/canon_systems/templates/rules/memory-platform-build-discipline.mdc so every repo wired by canon wire gets the rule."
          acceptance_criteria:
            - "Template file content byte-identical to the workspace rule (idempotent distribution)."
            - "canon wire smoke test installs the rule in a fresh repo."
          depends_on: ["E6-T2"]
          can_run_parallel: true
          parallel_group: "wave-7a"
          done_signal:
            - "tests/test_wire_distribution.py asserts rule is installed in a scratch repo."
        - task_id: "E7-T2"
          title: "Delete deprecated sibling repos"
          goal: "Per docs/DEPRECATIONS.md, delete the sibling repos flagged for removal after grace period."
          acceptance_criteria:
            - "Each deletion has a linked canonical event recording decision + grace period end."
            - "Any remaining references in canon-systems are removed or re-pointed."
          depends_on: ["E7-T1"]
          can_run_parallel: false
          parallel_group: "wave-7b"
          done_signal:
            - "docs/DEPRECATIONS.md marked final."
        - task_id: "E7-T3"
          title: "Final five-file living-spec pass"
          goal: "Refresh docs/SYSTEM-WORKFLOW.md, docs/MEMORY-PLATFORM-PLAN.md, docs/MEMORY-PLATFORM-BACKLOG.md, README.md, CHANGELOG.md to reflect the final shipped platform."
          acceptance_criteria:
            - "Each file describes Wave 0-Wave 7 outcomes accurately."
            - "CHANGELOG has entries for every epic."
          depends_on: ["E7-T2"]
          can_run_parallel: false
          parallel_group: "wave-7c"
          done_signal:
            - "Review sign-off recorded in release packet."

  execution_policy:
    mode: "plan-first"
    per_task_workflow: "scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator"
    completion_rule: "all task_ids complete with QA PASS and release gates green; E0 MUST complete before E1; E1 MUST complete before E2; E2 MUST complete before E4; E3 can run in parallel with E2 and E4 (depends only on E1-T1); E5 depends on E2-T1 and can run in parallel with E3/E4 thereafter; E6 depends on E3-T5 and E4-T3; E7 runs last after E6."
END_PROJECT_EXECUTION_PLAN
```

---

## F) Rollout order (human-readable)

1. **Wave 0 (E0):** inventory + consolidation. Blocks everything else.
2. **Wave 1 (E1):** unblock visibility. Nothing is safe to build until we can
   see what is healthy.
3. **Wave 2 (E2):** state-api on DynamoDB. Unlocks resume, concurrency, and
   real multi-agent collaboration.
4. **Wave 3 (E3):** graph-first retrieval via backend/axon-service. Biggest
   single token-efficiency lever; can run in parallel with Wave 2 after E1-T1.
5. **Wave 4 (E4):** resume + concurrency enforcement. Requires E2.
6. **Wave 5 (E5):** human synthesis plane, server-rendered, three read paths,
   automatic in-repo mirror. Requires E2-T1 (canonical is already live).
7. **Wave 6 (E6):** observability. Requires E3 and E4 signal.
8. **Wave 7 (E7):** cleanup + canon-wire distribution of the hard-lock rule.

---

## G) Invariants every task must uphold

- Every CLI touching memory emits a canonical event envelope (section C).
- Every agent phase reads a checkpoint before work and writes one after
  (enforced from Wave 2 onward).
- Every rejection produces the DoR telemetry triple already required by
  `docs/SYSTEM-WORKFLOW.md` Section 4.
- Every new template/rule change is mirrored in:
  - `docs/SYSTEM-WORKFLOW.md`
  - `README.md`
  - relevant test in `tests/`
  - `CHANGELOG.md`
- Parent orchestration MUST use the chain
  `scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator`
  for every task. Direct writes by the parent are a policy violation and are
  rejected by `.cursor/rules/memory-platform-build-discipline.mdc`.

If any invariant is missing, `qa-gate` fails and release is blocked.
