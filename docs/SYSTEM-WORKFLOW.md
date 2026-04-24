# Canon System Workflow (Living Spec)

This document is the current source of truth for how Canon works end-to-end.
Update it on every meaningful Canon iteration (new command, gate, agent
contract, hook behavior, memory behavior, or rollout policy).

> **Canon Memory Platform v1 — SHIPPED (2026-04-23).** Waves 0–7 are
> complete. See `docs/MEMORY-PLATFORM-PLAN.md §9` for wave-level
> outcomes, `docs/MEMORY-PLATFORM-BACKLOG.md` for the per-task record,
> and `CHANGELOG.md` for the detailed per-epic entries. Everything
> described below reflects the v1 final state.

## 1) Runtime model

- Canon ships as one CLI package: `canon-systems` (binary: `canon`).
- Scope is tenant-bound by `company_id` + `repository_id`.
- Memory is AWS-backed and loaded from layered env + Secrets Manager.
- Cursor hooks run per turn:
  - preflight context hydration
  - post-response memory capture
- Failed or unreachable MemPalace `/memory/search` calls are classified (`mempalace_status` in preflight + `canon ask --json`); non-ok outcomes are logged to a local JSONL queue (`.canon/memory/mempalace-retry-queue.jsonl`) for later replay — exit codes stay healthy unless another failure applies.

## 2) Core execution chain

For non-trivial work, expected chain:

`project-planner -> scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator`

Key contracts:

- `project-planner` emits `PROJECT_EXECUTION_PLAN` with task graph.
- `scoper` emits `HANDOFF_TO_CURSOR_PILOT` (or `HANDOFF_NOT_READY`).
- `cursor-pilot` emits `CURSOR_PILOT_PROMPT` (or `HANDOFF_NOT_READY`).
- `implementer` emits `HANDOFF_TO_QA` / `HANDOFF_TO_QA_SHARD`.
- `qa-gate` emits `GATE_RESULTS`.
- `release-orchestrator` emits `RELEASE_STATUS`.

## 3) Persistence contract (required)

Packets must be file-backed, not chat-only:

- `.cursor/handoffs/<handoff_id>/<task_id>/scoper.md`
- `.cursor/handoffs/<handoff_id>/<task_id>/cursor-pilot.md`
- `.cursor/handoffs/<handoff_id>/<task_id>/qa-gate.md`
- `.cursor/handoffs/<handoff_id>/<task_id>/release-status.md`

Plan state file:

- `.cursor/plans/<plan-id>.plan.md` updated on every task status transition.

- **Resume engine (`canon resume`)**: Read-only, idempotent scanner over state-api checkpoints. Given a `--plan-id` + tenant scope and a task list (via `--tasks-file` or `--handoffs-dir`), it returns a JSON envelope identifying the first incomplete `(task_id, phase)` pair per the canonical 5-phase order (`scoper → cursor-pilot → implementer → qa-gate → release-orchestrator`). The engine emits zero canonical events — operators (or the parent agent) use the output to decide which agent to re-invoke; the re-invocation itself happens elsewhere. Running `canon resume` twice on unchanged plan state yields byte-identical stdout. **Experimental:** with **`CANON_EXPERIMENTAL_MULTILANE_ORCHESTRATION=1`** and **`canon resume --tasks-file ... --lanes`**, the same checkpoints plus optional manifest metadata (`depends_on`, `parallel_group`, `can_run_parallel`) add `runnable_targets` / `active_targets` / `blocked_targets` / `task_threads` for parent scheduling visibility only; merge-gate serial checks remain artifact-backed per task (see `docs/runbooks/RESUME.md` and `memory-platform-build-discipline.mdc` §11).
- **E4-T2 lease + versioning enforcement (CLI):** every `canon checkpoint` mutating command (`write`, `lease-acquire`, `lease-renew`, `lease-release`) now emits an additive `resolution: {message, command}` object on 409 stderr envelopes, carrying the exact `canon checkpoint ...` recovery invocation. Exit codes remain `1` (version conflict) and `2` (lease denied). Operators (and orchestrator agents) can parse `resolution.command` to drive automated recovery. See `src/canon_systems/templates/agents/implementer.md § Conflict recovery (E4-T2)`.
- **E4-T3 stall watchdog (`canon stall-watchdog scan`):** Read-only GET-probe scanner that detects stalled leases (`lease.expires_at <= now_epoch`) and emits one `lease_stall_detected` canonical event per stall (default target `.canon/memory/events.ndjson`; `--dry-run` routes to stderr). Event payload embeds a `suggested_next_step` copy-pasteable `canon checkpoint lease-acquire` command imported verbatim from `checkpoint_cli._resolution_hint("lease_held")`. Deliberately uses GET (not `POST /state/lease/acquire`) because the state-api silently steals expired leases on acquire, destroying stall evidence. Exit 5 on any degraded probe.
- **E5-T2 synthesis generator + publisher:** `backend/synthesis` renders `CanonicalEvent` rows deterministically into the E5-T1 S3 vault layout via `redaction.py` (15-field allowlist + per-event-type payload catalogue), `sources.py` (`InMemoryEventSource` for tests/E5-T3 CLI; `StateApiEventSource` Wave-5-waived stub), `generator.py` (pure `events → VaultBundle`; no wallclock, no S3, no network), `publisher.py` (SHA-256 content-hash diff-only writes via injectable `boto3.client("s3")`, `.obsidian/` write-once), and two new FastAPI routes (`GET /synth/vault/changes`, `GET /synth/show`). Suite +13 (367 → 380). Unwired terraform module `infra/terraform/modules/synthesis-vault/` under Precedent §1 `cloud_execution_deferred` waiver. Tests live in `backend/synthesis/synthesis_tests/` (pytest import-path: avoids `tests.conftest` collision with `backend/state-api/tests`).
- E5-T3 (canon synth publish CLI): operators and release-orchestrator may invoke `canon synth publish --events-file <jsonl> --plan-id ... --bucket ... --prefix ...` to converge an S3 vault to the current canonical-event set. The command is idempotent: repeat invocations with unchanged inputs + bucket state report `written=0, skipped=<all>`. `--dry-run` renders the bundle in-memory and prints the JSON envelope without any S3 I/O.
- **E5-T5 (canon synth show CLI):** agent-side read path — `canon synth show` streams the already-published S3 Obsidian vault (plan index + per-task pages in canonical phase order, or JSON snapshot) to stdout for inline hydration in the scoper → cursor-pilot → implementer → qa-gate → release-orchestrator chain, without regenerating the vault, write I/O, or a browser. Emits `retrieval_breakdown` + `synth_show` events to the same NDJSON seam as other canon CLIs.
- **E5-T4 `backend/synthesis-web`:** read-only FastAPI service SSRs HTML + JSON (`/_graph`, `/_search`) from the live S3 vault at request time (ETag from `content-hash` metadata; no S3 writes). URLs are scoped by 8-char hex `company_shorthash`/`repo_shorthash` under `/v/{c}/{r}/...`. Templates use inline CSS only (zero CDN). Tests: `backend/synthesis-web/synthesis_web_tests/`. Terraform module `infra/terraform/modules/synthesis-web/` is unwired (Precedent §1 deferred apply).
- **E5-T1 vault layout spec (schema_version 1):** new `docs/VAULT-LAYOUT.md` is the Wave-5 projection contract. Defines the Obsidian-compatible S3 vault layout, `company_shorthash`/`repo_shorthash` path scoping, the 15-field `CanonicalEvent` redaction allowlist (with `model` dropped + unknown payload keys silently dropped), the per-event-type payload catalogue, citation/idempotence rules, and the `schema_version` bump policy. E5-T2..E5-T7 implement against this contract; `backend/synthesis/README.md` links it.
- **In-repo vault mirror (E5-T6).** `canon enable-repo` installs a per-tenant
  background daemon (launchd/systemd/schtasks) that runs `canon vault sync
  --interval-seconds 10` and maintains `<repo>/vault/` as a one-way read-only
  projection of the canonical S3 vault. The Cursor `beforeSubmitPrompt` hook
  `.cursor/hooks/vault-sync-preflight.sh` smoke-refreshes before agent work;
  `vault/` is added to `.gitignore` via a sentinel-framed idempotent block.
- **Metrics aggregator (E6-T1).** `src/canon_systems/metrics_rollup.py`
  exports `aggregate(events, *, scope=None, window=None)` — a stdlib-only
  pure function that consumes any iterable of canonical events (NDJSON
  rows loaded by callers) and produces a stable `schema_version=1`
  JSON rollup describing lead/cycle time per task, per-phase retries,
  DoR cause counts, stall counts, token cost split by phase/agent/source
  (graph/state/canonical/file), and `synth_publish` health. Scope
  filters (`company_id`, `repository_id`, `plan_id`) and ISO-Z window
  filters (`since`/`until`) apply before aggregation.   Deterministic
  under `json.dumps(..., sort_keys=True)`. This is the data model the
  E6-T2 operator CLI and downstream dashboards consume.
- **Operator rollups (E6-T2).** `canon report --events <ndjson>` is the
  first-class surface over `metrics_rollup.aggregate`. Default mode
  preserves the legacy `{by, groups}` envelope (`--by
  {source,phase,agent}`) for back-compat with E3-T5 callers; `--full`
  emits the complete E6-T1 schema. Scope (`--company-id /
  --repository-id / --plan-id / --task-id`) and window (`--since /
  --until`) filters narrow the event stream before aggregation.
  `--format {json,csv}` controls output shape; CSV under `--full` emits
  `section,key,tokens_in,tokens_out,count` rows for direct spreadsheet
  import. Byte-identical deterministic output.
- **Auto-publish on RELEASE PASS (E5-T7).** When the release-orchestrator
  emits a `RELEASE_STATUS` packet with all three gates (qa/ci/merge) equal
  to `PASS`, it calls `canon release publish-on-pass --release-status-file
  .cursor/handoffs/<handoff_id>/release-status.md --release-id <release_id>`.
  The hook fires exactly once per release (not per task) and invokes
  `canon synth publish` with bounded exponential-backoff retries
  (`min(base*2**(k-1), 60 s)`; default 3 attempts via
  `CANON_PUBLISH_RETRIES`). Idempotent via the per-release sentinel at
  `.canon/release-publish/<plan_id>/<release_id>.json`. Set
  `CANON_PUBLISH_NOTIFIER_URL` to an HTTP endpoint to signal downstream
  `canon vault sync` listeners within ~30 s — absence is a clean no-op and
  notifier failures never fail the release. Emits one `synth_publish`
  canonical event per attempt outcome, plus an optional
  `vault_sync_notified` event on successful POST.
- **Hard-lock rule distribution (E7-T1).** The Canon Memory Platform v1 build
  discipline rule lives at `.cursor/rules/memory-platform-build-discipline.mdc`
  and is packaged byte-identically at
  `src/canon_systems/templates/rules/memory-platform-build-discipline.mdc`.
  Every repo wired by `canon setup` / `canon enable-repo` (and the
  user-scope `~/.cursor/rules/` tree) gets the rule installed automatically;
  `tests/test_wire_distribution.py` regression-locks byte-identity and
  idempotence so the rule cannot drift between wire and workspace.
- **E4-T4 resume runbook + release-gate integration:** new `docs/runbooks/RESUME.md` gives operators a one-page path for `canon resume`. The `release-orchestrator` template now requires a `canon resume` check before advancing the merge gate (`resume_target == null` AND empty `degraded_tasks`). Cross-references the E4-T3 stall watchdog for the combined "scan-then-resume" operator workflow.

## 4) DoR rejection telemetry contract

When `scoper` or `cursor-pilot` returns `HANDOFF_NOT_READY`, parent orchestration
must persist and send telemetry artifacts:

- Rejection packet:
  - `.cursor/handoffs/<handoff_id>/<task_id>/handoff-not-ready/<stage>-<timestamp>.md`
- Telemetry event payload:
  - `.cursor/handoffs/<handoff_id>/<task_id>/dor-failure/<stage>-<timestamp>.json`
- Telemetry send status:
  - `.cursor/handoffs/<handoff_id>/<task_id>/dor-failure/<stage>-<timestamp>.status`
  - Must include `exit_code:`
- Send command:
  - `canon dor-log --event-file <payload-json> --quiet`

## 5) Merge/release gates

Before merge, require all:

- `qa-gate` verdict PASS
- `canon qa-validate --file ... --require-pass`
- `canon qa-validate ... --handoff-id <id> --task-id <id> --require-dor-telemetry`
- sampled `canon flow-audit --handoff-id <id> --task-id <id> --sample-rate 0.2`
- required CI checks PASS
  - `canon flow-audit --handoff-id <id> --task-id <id> --require-memory-health` (optional in Wave 0; required by release-orchestrator from Wave 1+) verifies on-disk per-task `memory-health.json` evidence (schema v1, overall_status ok) before merge

Before deploy promotion:

- environment smoke checks PASS
- promotion order respected (`dev -> staging -> production/TestFlight`)

### 5.1) Auto-branching + per-task commits + PR-at-wave-close

For multi-wave initiatives (e.g. the Canon Memory Platform v1 build), the
parent orchestrator operates an auto-branching commit/PR protocol on top of
the merge/release gates above. The authoritative contract lives in
`.cursor/rules/memory-platform-build-discipline.mdc` §§9-10; the summary below
exists solely to keep this living spec honest per §G of the backlog.

- **Wave branch:** one long-lived branch per wave, named
  `wave/<N>/<handoff_id>` (e.g. `wave/0/canon-memory-v1`), cut from `main` at
  wave start, before any pre-flight chore commit.
- **Pre-flight chore commit:** orchestration artifacts needed before the first
  task (rule install, backlog rewrites, plan copies, living-spec mirrors like
  this subsection) land on the wave branch as a single
  `chore(memory-platform-v1): <brief>` commit.
- **Per-task commit:** on `verdict: READY_TO_MERGE` in a task's
  `release-status.md`, the parent MUST stage the task's artifacts plus its
  packet quartet (`scoper.md`, `cursor-pilot.md`, `qa-gate.md`,
  `release-status.md`) and commit with a Conventional Commit message carrying
  `handoff_id`, `plan_id`, and `workstream_id` trailers. One commit per task,
  no squashing, no amending once pushed.
- **PR at wave close:** after the last task in the wave lands, parent pushes
  the wave branch and opens a PR with a per-task summary table, base `main`,
  title `wave/<N>: <epic title>`.
- **Auto-merge:** permitted only if every task commit has qa-gate PASS,
  qa-validate PASS, and flow-audit PASS packets on disk; required CI is green;
  and either `CANON_AUTO_MERGE=1` is set or a required-reviewer approval is
  present. From Wave 1 onward, `canon memory-health` must also exit 0. If any
  gate is missing, the PR stays open for human review and the parent proceeds
  to the next wave branch rather than blocking.
- **Cross-wave sequencing:** the next wave's branch is cut from `main` after
  the prior wave's PR merges (not from the prior wave branch). If the parent
  speculatively cuts the next wave while the prior PR is still open, it MUST
  rebase onto `main` once the prior merges.
- **Never automatic:** force-push, rewriting pushed commits, merging to `main`
  without CI+approval or `CANON_AUTO_MERGE=1`, or deleting non-wave branches.

See rule §§9-10 for authoritative wording.

## 6) Validation commands

- **Retrieval policy (graph-first)**: Coder-facing templates (scoper/cursor-pilot/implementer) consult memory sources in a fixed order — `graph → state → canonical → file`. Graph reads via `canon graph query`/`canon graph impact`, state via `canon checkpoint read`, canonical via `.canon/memory/context-latest.md` + `canon ask`. Fail-open when axon is unset or returns 2/3/4/5; degradation is recorded in the HANDOFF_TO_QA `notes:` field.
- **Retrieval-source telemetry**: Each agent phase emits one `retrieval_breakdown` canonical event with `payload.sources` keyed by the fixed `graph/state/canonical/file` 4-bucket contract (see `src/canon_systems/retrieval_telemetry.py`). `canon report --events <ndjson>` provides a rollup grouped by `phase`, `agent`, or `source` by default, or the full E6-T1 schema via `--full` (see *Operator rollups* above). Zero counts are valid when a source is unused or degraded; the event is still emitted.
- QA packet validator:
  - `canon qa-validate --file <qa-gate.md> --require-pass`
- Process audit validator:
  - `canon flow-audit --handoff-id <id> --task-id <id> --plan-file <plan>`
- Memory health probe: `canon memory-health [--required <csv>] [--timeout-ms <int>]`
- Graph retrieval plane: [`backend/axon-service`](../backend/axon-service/README.md) exposes `/axon/{company_id}/{repository_id}/index`, `/query`, `/impact`, and `/healthz`. `canon memory-health` treats **graph** as optional by default; it probes the axon service at **`AXON_SERVICE_URL`** (append `/healthz`) when that env is set.
- Graph indexer pipeline: `canon graph index` (pre-push hook or CI workflow_dispatch) is the ONLY write path to axon-service; `canon graph query` / `impact` (E3-T3) and `/axon/.../query`,`/impact` are pure RPC reads and never index at query time. `canon graph reindex-status --commit-sha=<sha>` surfaces the snapshot state (`ready`/`missing`/`error`).
- **Graph reads**: `canon graph query` and `canon graph impact` are pure-RPC clients over `backend/axon-service` `GET /query` and `GET /impact`. They inherit `AXON_SERVICE_URL`/`AXON_SERVICE_TOKEN` env layering (flag > env > error-with-exit-2) and never touch the repo filesystem. `query` returns a body with `results[].source_spans` so agents can cite graph-backed evidence; `impact` returns `upstream`/`downstream` lists keyed by symbol. Writes remain sole-domain of `canon graph index` (E3-T2).
- State checkpoint/lease: `canon checkpoint ...` (read/write/lease) against a deployed `state-api` (JSON over HTTP; use `--base-url` or `CANON_STATE_API_URL`)
- Phase-boundary hydration: agents run `canon checkpoint read` before their phase work and `canon checkpoint write` after, via `state-api`; when `CANON_STATE_API_URL` is unset, skip checkpoint HTTP gracefully (local dev, sandbox, or CI without a reachable state plane).
- DoR telemetry sender (with queue fallback):
  - `canon dor-log --event-file <event.json>`
  - **memory-health evidence (Wave 1+):** `canon memory-health --output .cursor/handoffs/<handoff_id>/<task_id>/memory-health.json` to persist; `canon flow-audit ... --require-memory-health` to enforce at merge (release-orchestrator contract).
- On-disk per-phase checkpoint files: merge gates may run `canon flow-audit --require-checkpoints` and `canon qa-validate --require-checkpoints` (with handoff/task ids) to block integration when any of the five phase checkpoint artifacts is missing or invalid.

## 7) Automation and propagation

- Self-update checks are automatic (throttled).
- Repo/user wiring auto-refreshes when installed version is newer than pinned.
- Global auto-rewire updates previously wired repos under configured roots.

## 8) Living update checklist (required per iteration)

When Canon behavior changes, update in the same PR:

1. This file (`docs/SYSTEM-WORKFLOW.md`)
2. `README.md` command/behavior docs
3. `docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md` when retrieval, runtime env keys, or per-agent contracts change
4. Relevant agent templates/rules
5. Tests that enforce the new behavior
6. `CHANGELOG.md`

If any of the six are missing, iteration is incomplete.

## 9) Forward plan

The live architectural direction is tracked in:

- `docs/MEMORY-PLATFORM-PLAN.md` (target architecture + why)
- `docs/MEMORY-PLATFORM-BACKLOG.md` (executable `PROJECT_EXECUTION_PLAN` that
  the `scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator`
  chain runs task-by-task)

When changing the workflow, update this file and the backlog in the same PR.

## 10) Backend monorepo layout

Python backend services and the stdlib-only shared library (`canon_backend_shared`
under `backend/shared/`) are colocated in `backend/` as setuptools packages, with
`synthesis-web/` reserved for a future UI entrypoint (see E5-T4). Use
`uv sync --all-packages` or `bash scripts/backend/install-workspace.sh` from the
repo root to install the workspace. **`knowledge-api`** (flat `app/` + Alembic),
**`knowledge-worker`**, and **`memory-adapter`** use the consolidated sources from
`sibling` `canon-systems-v2` documented in
[`docs/E0-T3-MIGRATION-NOTES.md`](E0-T3-MIGRATION-NOTES.md) (git history waived
there in favor of a per-file map). The same migration brought **`knowledge-schema`**,
**`knowledge-policy`**, and **`knowledge-client`** into `backend/` so `pip install -e`
does not depend on a v2-style `libs/` checkout. For a quick CI-oriented check, run
`bash scripts/backend/build-services.sh` after `pip`/`uv` resolves deps — it
installs `backend/shared` and each leaf Python package, then import-smokes
`*.main.app`. Details: `backend/README.md`.

**AWS plane (declarative):** `infra/terraform/` is now the in-repo Terraform root
mirrored from `canon-systems-v2` (VPC, ECR, baseline ECS Fargate, RDS, S3
artifacts, Secrets Manager placeholders for the `canon-systems-v2` / `dev` stack in
`us-east-1`). It is **import-prep only** in Wave 0: operators reconcile remote state
and run `terraform plan` until zero drift (see [`docs/E0-T4-INFRA-IMPORT.md`](E0-T4-INFRA-IMPORT.md)
and [`infra/terraform/README.md`](../infra/terraform/README.md)). **`infra/auth-ingress/`**
remains a separate workstream (Cognito / public ingress), not wired from this root.

- **DynamoDB `canon-state` (E2-T1):** [`infra/terraform/modules/dynamodb-canon-state/`](../infra/terraform/modules/dynamodb-canon-state/) defines the per-environment `canon-state` table (composite keys `pk`/`sk`, TTL on `lease_expires_at`, PITR, SSE); E2-T1 did not run `terraform apply` (operator follow-up; see [`infra/terraform/README.md`](../infra/terraform/README.md)).
- **`state-api` (E2-T2):** the [`backend/state-api/`](../backend/state-api/README.md) FastAPI service is the **operational-state plane** endpoint for checkpoint reads/writes and lease acquire/renew/release against that table (REST §B shapes + canonical `checkpoint_write` events).

**Consolidation smoke (Wave 0):** `bash scripts/smoke-test.sh` proves the monorepo still
builds, passes the full Python test run, and passes `terraform` validate (local init
with `-backend=false`, no `apply`) from a dev or CI shell. The workflow
**Canon Smoke Test** in `.github/workflows/ci.yml` runs the same script on
`pull_request` and on `push` to `main` and `wave/**`. It does not invoke the `canon`
CLI or call live service URLs; operator follow-up for end-to-end live checks is tracked
in [`docs/WAVE-0-CLOSEOUT.md`](WAVE-0-CLOSEOUT.md) (including OQ-E0-T4-01 and
OQ-E0-T5-01).
