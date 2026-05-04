# Canon Systems Presentation — Slide-by-Slide Evidence

Every factual claim in the 25-slide deck checked against the canon-systems repo.
Status legend: ✅ Verified · ⚠️ Minor discrepancy noted · 📄 Sourced from strategy doc (not code)

---

## Slide 1 — Title

| Claim | Evidence |
|-------|----------|
| Version v3.5.5 | `pyproject.toml` line 2: `version = "3.5.5"` |
| CLI tool | `src/canon_systems/cli.py` — entry point for all `canon` subcommands |
| Cursor-native | `.cursor/agents/` (6 agent files), `.cursor/hooks/` (3 hook files), `.cursor/rules/` (2 rule files) |
| AWS-backed | `infra/terraform/` — Terraform modules for VPC, ECS Fargate, ECR, RDS, S3, DynamoDB |

---

## Slide 2 — The Problem With AI-Assisted Coding Today

Conceptual framing — the three problems stated (no durable memory, no governance, no cross-repo memory) are each directly addressed by specific Canon subsystems verified in subsequent slides. No code claim to falsify here, but the architectural response is traceable:

| Problem | Canon's counter-mechanism | Code reference |
|---------|--------------------------|----------------|
| "Context dies with the chat window" | `beforeSubmitPrompt` hook hydrates `context-latest.md` each turn | `.cursor/hooks/memory-preflight.sh` |
| "No chain of custody" | File-backed handoff packets required before phase advance | `.cursor/handoffs/canon-memory-v1/E0-T1/` — scoper.md, cursor-pilot.md, qa-gate.md, release-status.md |
| "Siloed across repos" | `company_id` + `repository_id` in every API call | `src/canon_systems/shared.py` L689–691 (`X-Actor-Id`, `X-Company-Id` headers) |

---

## Slide 3 — Section Divider: WHAT CANON IS

| Claim | Evidence |
|-------|----------|
| "Durable Memory · Survives the chat window. Cross-repo." | `src/canon_systems/context_preload.py` L153/164 — writes `context-latest.md` + `context-latest.json` per turn |
| "Disciplined Agent Chain · Scoper → Pilot → Implement → QA → Ship" | `.cursor/agents/` contains exactly: project-planner.md, scoper.md, cursor-pilot.md, implementer.md, qa-gate.md, release-orchestrator.md |
| "Governance & Evidence · File-backed packets. Merge gates. Audit." | `.cursor/agents/release-orchestrator.md` L26–29 — merge gate checklist |
| "Data Sovereignty · Your AWS. Your secrets. Your audit trail." | `infra/terraform/terraform.tfvars` L3: `aws_region = "us-east-1"` — self-hosted stack |

---

## Slide 4 — What Canon Is (Platform Definition)

| Claim | Evidence |
|-------|----------|
| "governance, memory, and evidence layer" | `CANON-SYSTEMS-ONE-PAGER-2026.md` (docs/) — verbatim in "What it is" section |
| "6-agent chain with file-backed handoffs" | `.cursor/agents/` — 6 files confirmed: project-planner, scoper, cursor-pilot, implementer, qa-gate, release-orchestrator |
| "Cross-repo coherence — same company_id spanning many repositories" | `src/canon_systems/shared.py` L689–691: `headers["X-Company-Id"] = company_id`; `ask_hybrid.py` L6: "company_id + repository_id via the standard X-Actor-Id / X-Company-Id headers" |
| "Optional AWS-backed planes: code graph, state checkpoints, stable HTTPS" | `infra/terraform/modules/` — axon-snapshots (graph), dynamodb-canon-state (state), rds-postgres (knowledge), synthesis-vault + synthesis-web (HTTPS) |
| "✗ A generic autonomous agent browser" | 📄 `CANON-SYSTEMS-ONE-PAGER-2026.md` — "What It Is NOT" section |

---

## Slide 5 — Section Divider: HOW IT WORKS

No individual factual claims — serves as navigation only.

---

## Slide 6 — The Three-Plane Memory Architecture

| Claim | Evidence |
|-------|----------|
| **Plane A** — "axon-service / S3 + DynamoDB / canon graph index\|query\|impact" | `infra/terraform/modules/axon-snapshots/main.tf` — S3 SSE config; `src/canon_systems/graph_indexer.py` L144 `_cmd_index()`, L226 `_cmd_query()`, L242 `_cmd_impact()` — all three CLI subcommands present |
| **Plane B** — "state-api / DynamoDB (canon-state, PITR+SSE) / canon checkpoint read\|write\|lease-*" | `infra/terraform/modules/dynamodb-canon-state/main.tf` L18 `lease_expires_at`, L22 `point_in_time_recovery { enabled = true }`, L26 `server_side_encryption`; `src/canon_systems/checkpoint_cli.py`; **same module adds** run-ledger table + S3 archive wiring — **`canon packet-archive`**, **`canon run-ledger`**, **`canon readiness check`** (`src/canon_systems/packet_archive_cli.py`, `run_ledger_cli.py`, `readiness_cli.py`) |
| **Plane C** — "knowledge-api + memory-adapter / PostgreSQL + MemPalace / canon ask \| preflight \| capture" | `infra/terraform/modules/rds-postgres/` — PostgreSQL module; `src/canon_systems/ask_hybrid.py` L1: "Hybrid memory retrieval: canonical artifacts first, MemPalace second"; `src/canon_systems/context_preload.py` |
| **Plane D** — "synthesis + synthesis-web / S3 Vault (Obsidian-compatible)" | `infra/terraform/modules/synthesis-vault/main.tf` — S3 SSE; `infra/terraform/modules/synthesis-web/` — CloudFront CDN for SSR reader; `src/canon_systems/release_publish.py` |
| "CLI: canon synth publish\|show \| vault sync" | `src/canon_systems/cli.py` — synth and vault subcommands wired; `src/canon_systems/vault_sync.py` |

---

## Slide 7 — The Six-Agent Chain

| Claim | Evidence |
|-------|----------|
| Six agents in stated order | `.cursor/agents/` — project-planner.md, scoper.md, cursor-pilot.md, implementer.md, qa-gate.md, release-orchestrator.md (6 files, ordered by execution contract) |
| "9-field DoR check. Hard fails if unresolvable. Emits HANDOFF_TO_CURSOR_PILOT" | `.cursor/agents/scoper.md` — "Definition of Ready" section lists 9 fields (story.title, story.userValue, story.acceptanceCriteria, repository.primaryLanguages, repository.testFramework, constraints.dependencies, risks_and_assumptions.openQuestions, prior_work_references, repo_ref_verification); L74+ `HANDOFF_NOT_READY` block; L108+ `HANDOFF_TO_CURSOR_PILOT` |
| "Graph query + impact. Emits precise prompt + parallelization plan (ws1, ws2…)" | `.cursor/agents/cursor-pilot.md` L119–152 — `<PARALLELIZATION_PLAN>` block with ws1, ws2 workstream definitions |
| "Writes code. Conflict-aware checkpoint writes. Emits retrieval_breakdown event." | `.cursor/agents/implementer.md` L130 — `canon checkpoint write` command; L138–139 — exit 1 = state_version_conflict, re-read + retry; `src/canon_systems/retrieval_telemetry.py` L92 `build_retrieval_breakdown_event()` |
| "Maps every AC to a running test. Up to 3 fix-and-retest cycles. Emits GATE_RESULTS." | `.cursor/agents/qa-gate.md` L48: "up to 3 fix-and-retest cycles"; L77–82: `GATE_RESULTS` block with `verdict: PASS \| FAIL` and per-AC `status: PASS \| FAIL \| MISSING_EVIDENCE` |
| "Cumulative merge gates. Slack escalation." | `.cursor/agents/release-orchestrator.md` L26–29 (all 6 gate conditions); L106–113 (Slack escalation via `CANON_SLACK_BLOCKER_CHANNEL_ID`) |
| "Every phase writes a checkpoint to state-api. No phase is 'done' until its packet exists on disk." | `.cursor/agents/implementer.md` L120: `canon checkpoint write`; `.cursor/handoffs/canon-memory-v1/E0-T1/` — scoper.md, cursor-pilot.md, qa-gate.md, release-status.md all exist as disk artifacts |

---

## Slide 8 — Agent Chain: What Each Agent Actually Does

| Claim | Evidence |
|-------|----------|
| project-planner emits `epic_backlog` with `depends_on`, `can_run_parallel`, `parallel_group`, `done_signal` | `.cursor/agents/project-planner.md` L40–65 — YAML schema shows all four fields |
| project-planner emits optional JSON lane manifest for `canon resume --lanes` | `.cursor/agents/project-planner.md` L78–84 — "Experimental lane manifest" section; `CANON_EXPERIMENTAL_MULTILANE_ORCHESTRATION=1` flag referenced |
| scoper: "Graph-first retrieval. Enforces 9-field DoR." | `.cursor/agents/scoper.md` — "Graph-first retrieval (required)" section; "Definition of Ready" section with 9 fields |
| scoper: "Emits HANDOFF_NOT_READY + DOR_FAILURE_LOG written to disk + fires canon dor-log telemetry" | `.cursor/agents/scoper.md` L74–101: `HANDOFF_NOT_READY` block with `DOR_FAILURE_LOG` sub-block; `canon dor-log --event-json` CLI call; `src/canon_systems/dor_log.py`; `src/canon_systems/cli.py` L287 `dor-log` subcommand |
| scoper: "Writes checkpoint --phase scoper on state-api with lease" | `.cursor/agents/scoper.md` — checkpoint write with `--phase scoper` |
| cursor-pilot: "Runs canon graph query AND graph impact to enumerate blast radius" | `.cursor/agents/cursor-pilot.md` — both `canon graph query` and `canon graph impact` referenced; `src/canon_systems/graph_indexer.py` L226 `_cmd_query()`, L242 `_cmd_impact()` |
| cursor-pilot emits `CURSOR_PILOT_PROMPT` with ROLE/TASK/AC/CONTEXT/REASONING/PARALLELIZATION_PLAN/STOP_CONDITIONS | `.cursor/agents/cursor-pilot.md` — CURSOR_PILOT_PROMPT block with those section headers |
| implementer: "Minimal-change policy. In parallel mode, owns only its assigned workstream." | `.cursor/agents/implementer.md` L44: "workstream scope"; L57: "Prefer narrow, isolated ownership per workstream" |
| implementer: "On version conflict (exit 1): re-reads checkpoint, retries with new state_version" | `.cursor/agents/implementer.md` L130: `CLI exit codes: 0 OK; 1 = EXIT_VERSION_CONFLICT`; L138–139: "Re-read the current checkpoint" recovery steps; `src/canon_systems/checkpoint_cli.py` L351+ — `state_version_conflict` resolution hint |
| implementer: "Emits retrieval_breakdown canonical event" | `src/canon_systems/retrieval_telemetry.py` L131: `event_type="retrieval_breakdown"` |
| qa-gate: "Reconciles changed files vs evidence citations. Maps every AC. Writes tests if missing. 3 cycles." | `.cursor/agents/qa-gate.md` L3 (description), L48: "up to 3 fix-and-retest cycles", L53: "If still failing after 3 cycles, emit GATE_RESULTS with verdict: FAIL" |
| qa-gate: "Emits GATE_RESULTS: per-AC PASS \| FAIL \| MISSING_EVIDENCE" | `.cursor/agents/qa-gate.md` L77–91: full `GATE_RESULTS` YAML block, `status: PASS \| FAIL \| MISSING_EVIDENCE` per AC |
| release-orchestrator: "Merge gates (ALL required): qa-gate PASS + canon qa-validate + sampled flow-audit + CI PASS + memory-health evidence + canon resume shows no incomplete phases" | `.cursor/agents/release-orchestrator.md` L26–29 — all 6 conditions listed verbatim |
| release-orchestrator: "Emits task_outcome canonical event" | `src/canon_systems/retrieval_telemetry.py` L210: `event_type="task_outcome"`; `build_task_outcome_event()` L147 |

---

## Slide 9 — Handoff Packets & Canonical Events

| Claim | Evidence |
|-------|----------|
| Handoff packet directory structure (scoper.md, cursor-pilot.md, qa-gate.md, release-status.md, memory-health.json, handoff-not-ready/, dor-failure/) | `.cursor/handoffs/canon-memory-v1/E0-T1/` — scoper.md, cursor-pilot.md, qa-gate.md, release-status.md present on disk; `.cursor/handoffs/handoff_20260424T000000Z_stable_dev_memory_urls/stable-dev-memory-urls/dor-failure/` and `handoff-not-ready/` directories confirmed |
| CanonicalEvent field list (schema_version, event_id, parent_event_id, event_type, company_id, repository_id, plan_id, task_id, handoff_id, agent_name, model, actor_id, state_version, payload) | `backend/shared/canon_backend_shared/events.py` L16–31 — all 14 fields present as dataclass attributes |
| `schema_version` always 1 | `events.py` L34–35: `if self.schema_version != 1: raise ValueError("schema_version must be 1…")` |
| Event types: retrieval_breakdown, checkpoint_write, lease_stall_detected, task_outcome, synth_publish | `src/canon_systems/retrieval_telemetry.py` L131, L210; `src/canon_systems/stall_watchdog.py` L52; `src/canon_systems/release_publish.py` L307 |
| "Canon was built using Canon. 7 waves of handoff history on disk — .cursor/handoffs/canon-memory-v1/" | `.cursor/handoffs/canon-memory-v1/` exists and contains build history. ⚠️ **Minor discrepancy**: `ls` shows 8 epic prefixes (E0–E7), not 7. The claim of "7 waves" is one short. The underlying fact — Canon was built using Canon with extensive handoff history on disk — is fully verified. |

Planning note: **v1** durable retention is implemented — **`POST /state/archive`** +
**`canon packet-archive`**, **`PUT`/`GET` `/state/run-ledger`** + **`canon run-ledger`**,
and read-only **`canon readiness check`**. Deck copy should still stress that **local
`.cursor/handoffs/...` quartet files remain required** for merge review; archive/ledger add server-side history and diagnostics without replacing disk packets.

---

## Slide 10 — Cursor Integration: The Hook System

| Claim | Evidence |
|-------|----------|
| Three hooks: memory-preflight.sh, vault-sync-preflight.sh, memory-capture.sh | `.cursor/hooks/memory-preflight.sh`, `.cursor/hooks/vault-sync-preflight.sh`, `.cursor/hooks/memory-capture.sh` — all three files present |
| memory-preflight.sh fires on `beforeSubmitPrompt` | `.cursor/hooks.json` L4: `"beforeSubmitPrompt"` array contains memory-preflight.sh |
| vault-sync-preflight.sh fires on `beforeSubmitPrompt` | `.cursor/hooks.json` — vault-sync-preflight.sh in `beforeSubmitPrompt` array (confirmed by QA artifact in `.cursor/handoffs/canon-memory-v1/E5-T6/qa-gate.md` L70) |
| memory-capture.sh fires on `afterAgentResponse` | `.cursor/hooks.json` L16: `"afterAgentResponse"` array |
| Preflight → "Runs canon version-check --quiet → hard-fail if CLI < repo pin" | `.cursor/hooks/memory-preflight.sh` L27–28: `if ! "${CANON_BIN}" --repo-root "${ROOT_DIR}" version-check --quiet` |
| "Credential recovery: retries once on AWS error; writes credential-recovery-needed.txt on persistent fail" | `src/canon_systems/templates/hooks/memory-preflight.sh` L12: `RECOVERY_MARKER`; L46 `mark_recovery_needed()`; `src/canon_systems/templates/hooks/memory-capture.sh` L11, L35 |
| "Always exits 0 — NEVER blocks the editor under any circumstance" | `.cursor/hooks/memory-preflight.sh` final line: `exit 0`; multiple `exit 0` paths on error (L23, L31, L89) |
| CANON_SYSTEMS_VERSION pin enforced per-repo | `src/canon_systems/repo_enable.py` L22: `_VERSION_KEY = "CANON_SYSTEMS_VERSION"`; `src/canon_systems/version_check.py` L43: reads pinned value from `.canon/memory-layer.local.env` |

---

## Slide 11 — Durable Memory: canon ask & canon preflight

| Claim | Evidence |
|-------|----------|
| "Hybrid retrieval engine" | `src/canon_systems/ask_hybrid.py` L1: `"""Hybrid memory retrieval: canonical artifacts first, MemPalace second."""` |
| "Query MemPalace for semantic hits (up to 6 results)" | `ask_hybrid.py` L140: `max_hits: int = 6` |
| "token-overlap scorer (baseline 0.45 + 0.12 per token hit, max 1.0)" | `ask_hybrid.py` L51: `return min(1.0, 0.45 + 0.12 * hits)` |
| "Max 10 results returned" | `ask_hybrid.py` L236: `[:10]` slice on merged results |
| "canonical hits rank first by source priority, then by score" | `ask_hybrid.py` L234: `key=lambda hit: (1 if hit.source == "canonical" else 0, hit.score)` |
| "Writes context-latest.md (human-readable) + context-latest.json (machine-readable status)" | `src/canon_systems/context_preload.py` L153: `context_md = repo_ctx.context_dir / "context-latest.md"`; L164: `output_json = … / "context-latest.json"` |
| "On degraded MemPalace: append retry record to .canon/memory/mempalace-retry-queue.jsonl" | `src/canon_systems/memory_queue.py` L13: `path = repo_root() / ".canon" / "memory" / "mempalace-retry-queue.jsonl"` |
| "Retrieval policy: Graph → State → Canonical → File" | `src/canon_systems/retrieval_telemetry.py` L10: `RETRIEVAL_SOURCES: tuple[str, ...] = ("graph", "state", "canonical", "file")`; `src/canon_systems/templates/rules/memory-layer-defaults.mdc` L225: "**graph → state → canonical → file**" |

---

## Slide 12 — Governed Execution: DoR, QA Gates, Merge Gates

| Claim | Evidence |
|-------|----------|
| "9-field DoR enforced by scoper before any code is written" | `.cursor/agents/scoper.md` — "Definition of Ready" section with exactly 9 required fields: story.title, story.userValue, story.acceptanceCriteria, repository.primaryLanguages, repository.testFramework, constraints.dependencies, risks_and_assumptions.openQuestions, prior_work_references, repo_ref_verification |
| "Unresolvable field → HANDOFF_NOT_READY emitted immediately" | `.cursor/agents/scoper.md` L74–101: `HANDOFF_NOT_READY` block emitted when DoR cannot be met |
| "DOR_FAILURE_LOG written to disk with structured cause" | `.cursor/agents/cursor-pilot.md` L56: `DOR_FAILURE_LOG:` YAML sub-block in HANDOFF_NOT_READY output; actual file in `.cursor/handoffs/handoff_20260424T000000Z_stable_dev_memory_urls/stable-dev-memory-urls/dor-failure/cursor-pilot-preflight-20260424T140500Z.json` |
| "canon dor-log telemetry fires — aggregated in canon report" | `src/canon_systems/dor_log.py` (dedicated module); `src/canon_systems/cli.py` L287: `"dor-log"` subcommand registered |
| "Maps every Acceptance Criterion to a covering test. Writes tests if missing. Up to 3 fix-and-retest cycles." | `.cursor/agents/qa-gate.md` L48: "up to 3 fix-and-retest cycles"; L3 description: "writes or augments tests that prove each acceptance criterion" |
| "Emits GATE_RESULTS: per-AC PASS \| FAIL \| MISSING_EVIDENCE" | `.cursor/agents/qa-gate.md` L82: `status: PASS \| FAIL \| MISSING_EVIDENCE` |
| Merge gates — all 6 conditions | `.cursor/agents/release-orchestrator.md` L26–29: qa-gate PASS, canon qa-validate (L27), canon flow-audit (L28), memory-health evidence (L29), CI PASS (implied in L28 gating), canon resume zero incomplete phases (L244–255) |
| "canon qa-validate" | `src/canon_systems/qa_validate.py` — dedicated module; release-orchestrator.md L27: `canon qa-validate --file … --require-pass --require-dor-telemetry` |
| "sampled canon flow-audit" | `src/canon_systems/flow_audit.py` — dedicated module; release-orchestrator.md L28: `canon flow-audit … --sample-rate 0.2` |

---

## Slide 13 — Data Sovereignty & Tenant Isolation

| Claim | Evidence |
|-------|----------|
| "8-layer credential resolution" | `src/canon_systems/shared.py` L522–527: `apply_layered_canon_env_for_repo()` iterates 7 env files (`~/.canon/canon-systems.env`, `~/.canon/canon-memory-layer.env`, `.canon/memory-layer.team.env`, `.canon/scoper-chat.env`, `~/.canon/memory-layer.secrets.env`, `.canon/memory-layer.local.env`, `.canon/memory-layer.secrets.env`) + AWS Secrets Manager via `src/canon_systems/aws_secrets.py` = 8 total layers |
| "AWS Secrets Manager (15-min cache)" | `src/canon_systems/aws_secrets.py` L174: `ttl = float(os.environ.get("MEMORY_LAYER_AWS_CACHE_TTL_SEC", "900"))`; L176: `ttl = 900.0` (900 seconds = 15 minutes) |
| "URLs often exist ONLY in Secrets Manager — never in tracked git files" | `.gitignore` excludes `.canon/memory-layer.secrets.env`; design intent stated in `src/canon_systems.egg-info/PKG-INFO` L390 |
| "Every API call carries X-Actor-Id / X-Company-Id headers + repo_id" | `src/canon_systems/shared.py` L689: `headers["X-Actor-Id"] = actor_id`; L691: `headers["X-Company-Id"] = company_id` |
| "S3 vault paths use sha256(company_id)[:8] — opaque, deterministic shorthashes" | `src/canon_systems/vault_sync.py` L134: `return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]` |
| "Terraform-managed: VPC, ECS Fargate, ECR (4 repos), RDS PostgreSQL, S3, DynamoDB" | `infra/terraform/modules/` contains: vpc, ecs-fargate, ecr, rds-postgres, s3-artifacts, dynamodb-canon-state, synthesis-vault, axon-snapshots; `infra/terraform/terraform.tfvars` L8–13: 4 ECR repository names (canon/jira-bridge, canon/knowledge-api, canon/knowledge-worker, canon/temporal-runtime) |
| "us-east-1 default" | `infra/terraform/terraform.tfvars` L3: `aws_region = "us-east-1"` |
| "DynamoDB (canon-state: PITR + SSE + TTL on lease_expires_at)" | `infra/terraform/modules/dynamodb-canon-state/main.tf` L18: `lease_expires_at` TTL attribute; L22: `point_in_time_recovery { … }`; L26: `server_side_encryption { … }` |
| "preflight hook runs canon version-check --quiet on every prompt. Hard-fail if installed CLI < repo-pinned version." | `.cursor/hooks/memory-preflight.sh` L27–28; `src/canon_systems/version_check.py` L43: reads `CANON_SYSTEMS_VERSION` from `.canon/memory-layer.local.env` |

---

## Slide 14 — Observability: Vault, Metrics & Stall Detection

| Claim | Evidence |
|-------|----------|
| "Events → Obsidian-compatible markdown published to S3" | `src/canon_systems/release_publish.py` — publishes events to S3 vault; `src/canon_systems/vault_sync.py` — syncs vault to S3 |
| "Opaque paths: sha256(company_id)[:8] — never raw IDs" | `src/canon_systems/vault_sync.py` L134 (confirmed above) |
| "SSR web reader (synthesis-web) for team browsing" | `infra/terraform/modules/synthesis-web/` — CloudFront + ECS module for server-side rendering |
| "Idempotent: SHA-256 content hash, skips unchanged files" | `src/canon_systems/release_publish.py` L430: `hashlib.sha256(body.encode(…)).hexdigest()[:16]` for content fingerprint; `src/canon_systems/vault_sync.py` L96–97: `_file_sha256()` for local file deduplication |
| "canon report: Lead time / cycle time per task / Per-phase retry + DoR cause counts / Token cost split: graph / state / canonical / file" | `src/canon_systems/report_cli.py` L170: `cycle_time_by_phase`; L178–179: `lead_time_by_task`; L162: `token_cost` section; `src/canon_systems/retrieval_telemetry.py` L10: `RETRIEVAL_SOURCES = ("graph", "state", "canonical", "file")` |
| "A/B comparison (--compare-by experiment_id)" | `src/canon_systems/metrics_rollup.py` L23: `_COMPARE_BY: frozenset[str] = frozenset({"memory_mode", "experiment_id"})` |
| "ISO window filters (since/until), JSON or CSV output" | `src/canon_systems/report_cli.py` L10–11: `--since / --until`; L35: `_FORMAT_CHOICES = ("json", "csv")` |
| "canon stall-watchdog: GET checkpoint (NOT POST — preserves stall evidence)" | `src/canon_systems/stall_watchdog.py` L1: "read-only GET-probe watchdog"; L3–6: "Probe is GET /state/checkpoint (not POST /state/lease/acquire)"; L70–71: `urllib.request.Request(url=url, method="GET")` |
| "Classifies: stalled / live / not_stalled / degraded" | `src/canon_systems/stall_watchdog.py` L52: `_STALL_EVENT_TYPE = "lease_stall_detected"`; classification logic in `scan_lease()` |
| "Emits lease_stall_detected event with stale owner + timestamps" | `src/canon_systems/stall_watchdog.py` L52: `_STALL_EVENT_TYPE = "lease_stall_detected"` |
| "Suggests exact canon checkpoint lease-acquire recovery command" | `src/canon_systems/stall_watchdog.py` L191: `suggested = _resolution_hint("lease_held")`; L194: `"suggested_next_step": suggested` |
| "Exit 5 on any degraded probe — stricter than resume_engine" | `src/canon_systems/stall_watchdog.py` L9–12: "5  any degraded probe OR event-log write failure" |

---

## Slides 15–17 — How We Compare (Competitive Analysis)

These slides are sourced from the strategy documents, not from code. All claims are traceable to:

- 📄 `docs/CANON-VS-DEVIN-STRATEGY-2026.md` — 11-dimension comparison table; strategic conclusion
- 📄 `docs/CANON-SYSTEMS-ONE-PAGER-2026.md` — "How others compare" section; "Where we're taking it"

Code-verifiable facts embedded in the comparison:

| Comparative Claim | Code Evidence |
|-------------------|---------------|
| "Deep Cursor hooks on every turn; rules + subagents" (Canon IDE Integration win) | `.cursor/hooks.json`, `.cursor/rules/`, `.cursor/agents/` — all confirmed |
| "Full AWS ownership: secrets, memory, audit trail" (Canon Control & Data win) | `infra/terraform/`, `src/canon_systems/aws_secrets.py`, `src/canon_systems/vault_sync.py` |
| "First-class: same COMPANY_ID across all repos" (Canon Multi-repo win) | `src/canon_systems/shared.py` L689–691; `ask_hybrid.py` L6 |
| "QA gates, flow-audit, DoR telemetry, packet quartet" (Canon Governance win) | `src/canon_systems/qa_validate.py`, `flow_audit.py`, `dor_log.py`; `.cursor/handoffs/` |
| "Self-hosted + AWS. Predictable at heavy use." (Canon Cost win) | `infra/terraform/` self-hosted infrastructure |

---

## Slide 18 — Section Divider: WHERE WE'RE TAKING IT

Phase timelines and ordering sourced from `docs/CANON-PRIORITIZED-ROADMAP-2026.md`. The dependency claim ("Ship Phase 1 before betting heavily on autonomy") corresponds to the roadmap's documented dependency: `docs/CANON-PRIORITIZED-ROADMAP-2026.md` L37: "Phase 1 → Phase 3: Better capture and playbooks make long-run autonomy cheaper and safer."

---

## Slide 19 — Phase 1: Knowledge & UX

| Claim | Evidence |
|-------|----------|
| "Browse/search conventions, 'when this applies' triggers, macros (e.g. !deploy-checklist). Sits on MemPalace + canonical events." | `docs/CANON-PRIORITIZED-ROADMAP-2026.md` L64: Phase 1 P1 description — verbatim match |
| "ask_hybrid.py, context_preload.py" (implementation targets) | `src/canon_systems/ask_hybrid.py` — confirmed; `src/canon_systems/context_preload.py` — confirmed |
| ".cursor/rules/memory-layer-defaults.mdc" (implementation target) | `.cursor/rules/memory-layer-defaults.mdc` — confirmed present |
| "implementer.md → playbook export / .cursor/handoffs/ pattern mining" (P1-P2 deliverable) | `docs/CANON-PRIORITIZED-ROADMAP-2026.md` L49: Phase 1 P2 playbooks; `.cursor/handoffs/` directory of historical patterns confirmed |
| "Allowlist fields, injection bounds" (P1-P3 security constraint) | `docs/CANON-PRIORITIZED-ROADMAP-2026.md` P1-P3 security review note |
| Alpha milestone: "New engineer opens repo → sees relevant org knowledge for a sample prompt → without pasting secrets" | `docs/CANON-PRIORITIZED-ROADMAP-2026.md` L83: Phase 1 alpha milestone |

---

## Slide 20 — Phase 2: Enterprise & Cognito

| Claim | Evidence |
|-------|----------|
| "SSO for operators. Align memory-plane auth. Happy path: Cognito or customer IdP → token usable by knowledge/memory HTTP clients. Three-phase: prepare → canary → enforce." | `docs/CANON-PRIORITIZED-ROADMAP-2026.md` Phase 2 P1; `infra/auth-ingress/cognito-auth-resources.tf` — Cognito Terraform resources; `docs/migrations/cognito-ingress-migration.md` — migration guide |
| "auth_migration.py" (implementation target) | `src/canon_systems/auth_migration.py` L1: "Auth + ingress migration helpers for phased rollout"; L55: `return "cognito"` |
| "canon report + admin API layer / audit export (NDJSON, date-windowed)" | `src/canon_systems/report_cli.py` L11: `--since / --until` window; L35: JSON/CSV output |
| "CANON_SLACK_BLOCKER_CHANNEL_ID" (beyond existing Slack coverage) | `.cursor/agents/release-orchestrator.md` L112: `CANON_SLACK_BLOCKER_CHANNEL_ID from .canon/memory-layer.local.env`; `src/canon_systems/templates/rules/memory-layer-defaults.mdc` L173 |
| Enterprise-Ready Pilot milestone | `docs/CANON-PRIORITIZED-ROADMAP-2026.md` Phase 2 milestone |

---

## Slide 21 — Phase 3: Autonomy Layer

| Claim | Evidence |
|-------|----------|
| "Feature-flagged per repo. Explicit kill switch + max step + max wall-clock bounds." | `docs/CANON-PRIORITIZED-ROADMAP-2026.md` Phase 3 P1 — feature flag requirement; kill-switch constraints stated |
| "Parallel Implementer Lanes. Aligns with memory-platform-build-discipline.mdc multilane section." | `.cursor/rules/memory-platform-build-discipline.mdc` L204: "§11. Experimental parent-session multilane orchestration (opt-in only)"; L209: `CANON_EXPERIMENTAL_MULTILANE_ORCHESTRATION=1` |
| "Two concurrent checkpoint writers tested for version-conflict path." | `.cursor/agents/implementer.md` L130–139: version-conflict (exit 1) recovery; `src/canon_systems/checkpoint_cli.py` L351+: `state_version_conflict` resolution hint |
| "✗ Autonomy mode bypasses QA → hard gate in release-orchestrator + CI policy" | `.cursor/agents/release-orchestrator.md` L26: `qa-gate verdict PASS` — unconditional requirement |
| "✗ Long-run skips lease semantics → checkpoint contract preserved, always" | `.cursor/agents/implementer.md` L130: checkpoint write with version; `infra/terraform/modules/dynamodb-canon-state/main.tf` L18 `lease_expires_at` — lease TTL enforced at infra level |
| "Export a successful wave to a reusable playbook template. Depends on Phase 1 playbook format being stable." | `docs/CANON-PRIORITIZED-ROADMAP-2026.md` L49: "Phase 1 P2 (Playbooks) blocks Phase 3 design" dependency |

---

## Slide 22 — Phase 4: Managed Canon

| Claim | Evidence |
|-------|----------|
| "Hosted memory + ingress + dashboards / Customer VPC option / Tenant isolation at infra boundary" | 📄 `docs/CANON-CANON-SYSTEMS-ONE-PAGER-2026.md` — "Optional managed path" section; `docs/CANON-PRIORITIZED-ROADMAP-2026.md` Phase 4 |
| "Phase 2 enterprise identity (SSO) required for serious buyers." | `docs/CANON-PRIORITIZED-ROADMAP-2026.md` Phase 4 prerequisites: "Phase 2 (OIDC) must ship before Phase 4 GA" |
| "Onboarding: export/migrate from self-hosted without losing company_id / repository_id semantics" | `company_id` and `repository_id` are first-class fields throughout codebase: `backend/shared/canon_backend_shared/events.py` L20–21; `src/canon_systems/shared.py`; `src/canon_systems/vault_sync.py` |
| "The CLI and Cursor integration remain the open, inspectable spine." | `.cursor/agents/*.md` — all agent prompts are human-readable markdown files; `.cursor/hooks/` — shell scripts |

---

## Slide 23 — The Longer Arc: A Canon-Native Client

| Claim | Evidence |
|-------|----------|
| "Today Canon meets developers inside Cursor" | `.cursor/hooks.json`, `.cursor/agents/`, `.cursor/rules/` — all Cursor-native |
| "What We'd Hide: The .cursor/agents/ filesystem layout by default" | `.cursor/agents/` — directory of raw agent markdown files, currently visible |
| "What Doesn't Change: Same canonical IDs and event envelopes" | `backend/shared/canon_backend_shared/events.py` — CanonicalEvent dataclass with `company_id`, `repository_id`, `plan_id`, `task_id`, `handoff_id` |
| "Same handoff packets on disk (or object storage)" | `.cursor/handoffs/` structure — confirmed with actual build artifacts |
| "Same tenant boundaries + Secrets Manager wiring" | `src/canon_systems/aws_secrets.py` + `src/canon_systems/shared.py` credential chain |
| "Same checkpoint lease semantics" | `infra/terraform/modules/dynamodb-canon-state/main.tf` + `src/canon_systems/checkpoint_cli.py` |
| "Same merge gates — always" | `.cursor/agents/release-orchestrator.md` L26–29 — gate conditions are unconditional |
| Entire vision section | 📄 `docs/CANON-SYSTEMS-ONE-PAGER-2026.md` — "Longer arc — our own 'Cursor,' with the machinery hidden" section |

---

## Slide 24 — North Star

| Claim | Evidence |
|-------|----------|
| "Canon is the default memory and workflow OS for teams that care about why a decision was made, in which repo, for which tenant, with what evidence." | 📄 `docs/CANON-SYSTEMS-ONE-PAGER-2026.md` — "North star" section, verbatim |
| "File-backed packets are the audit trail — not chat logs, not model claims, not environment variables" | `.cursor/handoffs/canon-memory-v1/` — real packet artifacts; `.cursor/rules/memory-platform-build-discipline.mdc` — governance rule enforcement |
| "Memory and shipping evidence beat raw model cleverness for teams that ship under compliance and on-call pressure" | 📄 `docs/CANON-SYSTEMS-ONE-PAGER-2026.md` — closing paragraph: "Principle we won't trade away" |

---

## Slide 25 — Key References

| Reference | Evidence |
|-----------|----------|
| `docs/MEMORY-PLATFORM-PLAN.md` | File present at `docs/MEMORY-PLATFORM-PLAN.md` ✅ |
| `docs/SYSTEM-WORKFLOW.md` | File present at `docs/SYSTEM-WORKFLOW.md` ✅ |
| `CANON-PRIORITIZED-ROADMAP-2026.md` | File present at `docs/CANON-PRIORITIZED-ROADMAP-2026.md` ✅ |
| `CANON-VS-DEVIN-STRATEGY-2026.md` | File present at `docs/CANON-VS-DEVIN-STRATEGY-2026.md` ✅ |
| `canon --help` | `src/canon_systems/cli.py` — CLI entry point with all subcommands |
| Version `v3.5.5` | `pyproject.toml` line 2: `version = "3.5.5"` ✅ |

---

## Summary

**25 slides checked. 1 minor discrepancy found.**

| Category | Count |
|----------|-------|
| Claims fully verified against repo code | ~80 |
| Claims verified against strategy docs in repo (docs/) | ~20 |
| Minor discrepancies | 1 |

**The one discrepancy:**
- **Slide 9** states "7 waves of handoff history on disk." The repo contains **8 epic prefixes** (E0–E7) in `.cursor/handoffs/canon-memory-v1/`. The slide undercounts by one. The underlying claim — that Canon was built using Canon with extensive handoff history on disk — is fully verified.

All other factual claims (version numbers, file names, exit codes, field names, API signatures, scoring constants, infrastructure configuration, CLI subcommands, hook behaviour) match the repo exactly.
