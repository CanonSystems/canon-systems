# Changelog

All notable changes to **canon-systems** are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **E5-T1** Vault layout spec + redaction allowlist: new `docs/VAULT-LAYOUT.md` (`schema_version: 1`) publishes the versioned contract for how `backend/synthesis` (Wave 5 / E5-T2) will project `CanonicalEvent` rows into an Obsidian-compatible S3 vault. 9 sections cover the S3 layout tree, per-company/per-repo shorthash scoping (never raw company_id/repository_id in page values), markdown frontmatter schema, `.obsidian/` seed config (app/workspace/graph only; no plugins/themes), the exhaustive 15-field redaction allowlist (10 SAFE + 4 SCOPE-SAFE-aliased + `model` DROPPED; unknown payload keys silently dropped — no logs, no warnings), the per-event-type payload catalogue (`retrieval_breakdown`, `lease_stall_detected`, `checkpoint_write`, opaque fallback), the `[[event:<id>]]` citation contract, the determinism/idempotence rules, and the schema_version bump policy. `backend/synthesis/README.md` now links to the spec. New `tests/test_vault_layout_spec.py` locks `schema_version: 1`, the §5 allowlist completeness against `CanonicalEvent`, and the `backend/synthesis/README.md` backlink. Documentation-only; zero production-code changes.
- **E4-T4** Resume runbook + release-gate integration: new `docs/runbooks/RESUME.md` one-page operator runbook for `canon resume` with basic invocation examples, output interpretation decision matrix, stall-watchdog cross-reference, release-gate integration pointer, and a troubleshooting table. New `## Resume check (E4-T4)` section in `src/canon_systems/templates/agents/release-orchestrator.md` wires the resume check into the merge-gate checklist (operators must confirm `resume_target == null` before advancing the merge gate). Two new template-assertion tests in `tests/test_agent_templates.py` (`test_release_orchestrator_template_resume_aware` satisfies the backlog done_signal; `test_resume_runbook_exists_and_covers_workflow` locks in the runbook structure). Documentation-only task; zero production-code changes; suite goes 363 → 365 passed.
- **E4-T3** `canon stall-watchdog scan` stall watchdog + unblock event: stdlib-only, read-only GET-probe CLI that scans a scoped list of (task_id, workstream_id) pairs (via `--tasks-file` or `--handoffs-dir`), classifies any checkpoint whose `lease.expires_at <= now_epoch` as STALLED, and emits one `lease_stall_detected` canonical event per stall to `.canon/memory/events.ndjson` (or `--event-log <path>`, or stderr under `--dry-run`). Event payload carries `diagnostic` evidence (stale owner, expires_at, ttl_remaining_s) plus `suggested_next_step` imported verbatim from `checkpoint_cli._resolution_hint("lease_held")` (zero drift). Uses GET (not acquire) because the state-api silently steals expired leases on acquire — GET surfaces expired `expires_at` verbatim and is side-effect-free. Exit 5 on any degraded probe (stricter than `canon resume` by design: a missed stall probe may hide the actual stall). `CanonicalEvent` imported from `backend/shared` (Wave-3 discipline; never redefined). New `tests/test_stall_watchdog.py` (≥13 cases) covers the simulated-stall done signal, dry-run stderr, append semantics, and the canonical-event-import-not-redefined source scan.
- **E4-T2** Lease + versioning enforcement in CLI + templates: `canon checkpoint write | lease-acquire | lease-renew | lease-release` now emit an additive `resolution: {message, command}` object on every 409 stderr envelope carrying the copy-pasteable recovery command (`canon checkpoint read` for stale versions, `canon checkpoint lease-acquire` for lease conflicts). Exit codes (`1` = version conflict, `2` = lease denied) and all pre-existing stderr keys preserved byte-for-byte. New `tests/test_checkpoint_concurrency.py` validates the acquire → write → renew → release happy path and every 409 recovery path via a monkeypatched `_http_request` seam. `src/canon_systems/templates/agents/implementer.md` gains a `### Conflict recovery (E4-T2)` subsection; `release-orchestrator.md` cross-references it.
- **E4-T1** `canon resume --plan-id <id>` orchestrator resume engine: stdlib-only, read-only, idempotent scanner over state-api checkpoints. Emits a structured JSON envelope identifying the first incomplete (task_id, phase) pair per the canonical 5-phase order (scoper → cursor-pilot → implementer → qa-gate → release-orchestrator). Task discovery via `--tasks-file` (JSON) or `--handoffs-dir` (E<N>-T<N> subdirectory scan). Degrades gracefully when state-api is unreachable; exit 5 iff every task is transport-degraded. Zero canonical events emitted (verified by a static-source assertion).
- **E3-T5** Retrieval-source telemetry: new `src/canon_systems/retrieval_telemetry.py` emits `retrieval_breakdown` canonical events with per-source `tokens_in`/`tokens_out` across the fixed `graph/state/canonical/file` 4-bucket contract, reusing `CanonicalEvent` from `backend/shared`. New `canon report` CLI stub (`src/canon_systems/report_cli.py`) reads NDJSON event files and prints deterministic JSON rollups grouped by `phase`/`agent`/`source` with optional `--plan-id`/`--task-id` filters (Wave 6 will replace the stub with a polished CSV/table renderer). All 5 coder-facing agent templates + `memory-layer-defaults.mdc` now require per-phase emission. Tests: `tests/test_retrieval_telemetry.py` (15 new) + `tests/test_agent_templates.py` (6 new).
- **E3-T4** Retrieval policy codified as graph-first across canon rules + coder-facing agent templates. New `## Retrieval policy (required)` section in `memory-layer-defaults.mdc` fixes the order to `graph → state → canonical → file` with an explicit fail-open fallback to state/canonical/file when `AXON_SERVICE_URL` is unset or `canon graph query` fails. New `## Graph-first retrieval (required)` subsections in `scoper.md`, `cursor-pilot.md`, and `implementer.md` cite `canon graph query` (and `canon graph impact` for the pilot) as the first retrieval step before broad repo exploration. Five new assertions in `tests/test_agent_templates.py`.
- **E3-T3** `canon graph query` and `canon graph impact` CLI subcommands: stdlib-only GET clients over axon-service `/query` and `/impact`, with Bearer auth, env-layered credentials (`AXON_SERVICE_URL`/`AXON_SERVICE_TOKEN`), and exit codes `0/1/2/3/4/5`. Pure RPC — no repo walks, no local caches; tests cover success, 4xx with detail unwrap, 5xx, transport, and usage-error (no-HTTP-on-usage-error) cases.
- E3-T2: `canon graph index` + `canon graph reindex-status` CLI (stdlib-only, HTTP seam); new Bearer-gated GET `/axon/{c}/{r}/reindex-status` route on backend/axon-service; pre-push hook scaffold (`scripts/hooks/pre-push-graph-index.sh`); opt-in GitHub Actions `axon-reindex.yml` workflow_dispatch.
- E3-T1: backend/axon-service (FastAPI) — multi-tenant graph-index service (POST /index, GET /query, GET /impact, GET /healthz) with S3 snapshot + DynamoDB metadata persistence, Bearer auth shim, canonical `retrieval.graph.*` events; `infra/terraform/modules/axon-snapshots` module; memory-health graph probe backed by `AXON_SERVICE_URL`; moto tests under `backend/axon-service/axon_service_tests/`.
- E2-T5: flow-audit + qa-validate enforce per-phase checkpoint artifacts — new `--require-checkpoints` flag on both CLIs validates `.cursor/handoffs/<handoff_id>/<task_id>/checkpoints/<phase>.json` across all five §B phases (scoper/cursor-pilot/implementer/qa-gate/release-orchestrator).
- E2-T4: agent templates + memory-layer-defaults hydrate canon checkpoint contract — scoper/cursor-pilot/implementer/qa-gate/release-orchestrator now document read-before/write-after via state-api with graceful CANON_STATE_API_URL skip.
- E2-T3: canon checkpoint CLI — stdlib-only `canon checkpoint` with subcommands `read`, `write`, `lease-acquire`, `lease-renew`, `lease-release` over the state-api wire (flat write/acquire, nested `scope_ids` for renew/release); exit codes 0/1/2/3/4/5 (ok / `state_version_conflict` / lease denied / not found / usage / transport).
- E2-T2: backend/state-api service — GET/PUT `/state/checkpoint` + POST `/state/lease/{acquire,renew,release}` with DynamoDB conditional writes, server-minted UUIDv4 lease tokens (numeric `lease_expires_at` for TTL), nested §B `lease` in REST responses, and `checkpoint_write` `CanonicalEvent` emission + `X-Canon-Event-Id`; moto-backed tests under `backend/state-api/tests/`.
- E2-T1: DynamoDB canon-state table module (infra/terraform/modules/dynamodb-canon-state/) + root wiring + outputs (state_table_name, state_table_arn); PAY_PER_REQUEST, TTL on lease_expires_at, PITR, SSE; per-env isolation via ${project}-${environment}-canon-state; no cloud commands executed.
- E1-T3: `canon flow-audit --require-memory-health` release-gate flag that verifies per-task .cursor/handoffs/<handoff_id>/<task_id>/memory-health.json evidence (schema_version='1', overall_status='ok'); release-orchestrator template now names memory-health as a required merge gate.
- E1-T2: mempalace status classifier + retry queue for preflight and ask (new module `src/canon_systems/memory_queue.py`; `context_preload` and `ask_hybrid` now record `mempalace_status` and enqueue retries on degraded/unreachable to `.canon/memory/mempalace-retry-queue.jsonl`).
- E1-T1: `canon memory-health` CLI — stdlib-only subcommand probing canonical/mempalace/state/graph /healthz with `CANON_MEMORY_HEALTH_REQUIRED` + `CANON_MEMORY_HEALTH_TIMEOUT_MS` env knobs; exits 0 iff all required backends OK within budget.
- E0-T5: consolidation smoke harness — `scripts/smoke-test.sh` (build → `pytest -q` →
  `terraform` validate), GitHub Actions **Canon Smoke Test** (`.github/workflows/ci.yml`),
  `requirements-dev.txt` (PyYAML for workflow assertions), `tests/test_consolidation_smoke.py`,
  and closeout doc [`docs/WAVE-0-CLOSEOUT.md`](docs/WAVE-0-CLOSEOUT.md). No AWS or live URL
  calls; `SMOKE_SKIP_TERRAFORM=1` optional local escape hatch.
- E0-T4: `infra/terraform/` Terraform root (byte-faithful mirror of
  `canon-systems-v2/infra/terraform/` @ `ebecb91`, excluding state/lock/cache/plan
  artifacts) plus import manifest in `infra/terraform/README.md`; migration note
  [`docs/E0-T4-INFRA-IMPORT.md`](docs/E0-T4-INFRA-IMPORT.md); layout tests in
  `tests/test_infra_layout.py`; `infra/README.md` index. No cloud commands executed
  in-task.
- E0-T3: consolidated `knowledge-api`, `knowledge-worker`, and `memory-adapter`
  from `canon-systems-v2` into `backend/` (copy + history waiver), plus v2 libs
  `knowledge-schema`, `knowledge-policy`, and `knowledge-client` under `backend/`
  so editable installs resolve imports without a sibling `libs/` tree; see
  [docs/E0-T3-MIGRATION-NOTES.md](docs/E0-T3-MIGRATION-NOTES.md) and
  `scripts/backend/build-services.sh` for install/import smoke.
- E0-T2: backend/ skeleton + shared lib
- `docs/SYSTEM-WORKFLOW.md` §5.1 "Auto-branching + per-task commits +
  PR-at-wave-close": mirrors `.cursor/rules/memory-platform-build-discipline.mdc`
  §§9-10 into the living workflow spec so the living-spec invariant
  (`docs/MEMORY-PLATFORM-BACKLOG.md` §G) stays satisfied for multi-wave
  initiatives. The rule file remains authoritative; §5.1 is the summary.
- `docs/MEMORY-PLATFORM-BACKLOG.md`: agent-executable `PROJECT_EXECUTION_PLAN`
  for the Canon Memory Platform v1 build, now in 7-wave shape
  (E0 consolidation -> E1 stabilize -> E2 state-api + DynamoDB ->
  E3 backend/axon-service -> E4 resume + concurrency ->
  E5 server-rendered synthesis vault with three read paths ->
  E6 observability -> E7 cleanup + canon-wire distribution), including the
  checkpoint schema, canonical event envelope, and CLI surface targeted by
  each wave. Cross-linked from `docs/SYSTEM-WORKFLOW.md`,
  `docs/MEMORY-PLATFORM-PLAN.md`, and `README.md`.
- `.cursor/rules/memory-platform-build-discipline.mdc`: hard-lock workspace
  rule that mechanically enforces the
  `scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator`
  chain, forbids non-markdown writes until valid scoper + cursor-pilot packets
  exist, mandates pre-flight context-window assessment at every wave boundary,
  and requires the DoR telemetry triple on every rejection. Wave 7 will
  template this rule into `src/canon_systems/templates/rules/` so
  `canon wire` distributes it to every wired repo.
- `.cursor/plans/canon_memory_platform_build_d21073e1.plan.md`: workspace-local
  copy of the self-executing Build Kickoff plan for the Memory Platform v1
  build.

### Changed

- Backlog epic shape moved from E1-E6 to E0-E7. Adds Wave 0 (inventory +
  consolidation into `backend/` monorepo with imported IaC) and Wave 7
  (cleanup + canon-wire distribution of the hard-lock rule). Retargets
  component paths from `src/canon_systems/checkpoint.py` etc. to
  `backend/state-api/`, `backend/axon-service/`, `backend/synthesis/`,
  `backend/synthesis-web/`. Expands Wave 5 to absorb useful `obsidian-mind`
  logic server-side and deliver three independent read paths (browser,
  agent CLI, automatic in-repo mirror) over a single S3-hosted
  Obsidian-compatible vault.

### Fixed

### Removed

---

## [3.3.5] - 2026-04-24

### Added

- `qa-validate` now supports optional DoR rejection telemetry gating via:
  `--handoff-id`, `--task-id`, and `--require-dor-telemetry`.
- New living operations spec: `docs/SYSTEM-WORKFLOW.md`, documenting the
  current end-to-end Canon execution model and required update checklist for
  every future iteration.

### Changed

- Release governance templates/rules now require `qa-validate` DoR telemetry
  checks for task-level rejection events before merge.
- `flow-audit` and `qa-validate` contracts now align on persisted
  `handoff-not-ready` and `dor-failure` artifact requirements.

---

## [3.3.4] - 2026-04-24

### Added

- New `canon flow-audit` command to audit process compliance artifacts
  (handoff packet files and plan/task tracking) without reviewing code.
- Flow-audit sampling support via `--sample-rate` for lightweight random checks.

### Changed

- Release governance now includes sampled `flow-audit` in merge gates.

---

## [3.3.3] - 2026-04-24

### Added

- New `canon qa-validate` command to enforce structured QA packet compliance:
  validates `GATE_RESULTS` required fields and verifies referenced test files
  exist before merge gating.
- Regression tests for qa packet validation (`tests/test_qa_validate.py`).

### Changed

- Release governance now requires `canon qa-validate --require-pass` on the
  persisted QA artifact before merge, in addition to qa-gate verdict + CI.

---

## [3.3.2] - 2026-04-24

### Changed

- Release/task orchestration now enforces strict per-`task_id` progression to
  prevent untracked "slice" execution drift.
- Handoff packets are now required to be persisted to
  `.cursor/handoffs/<handoff_id>/<task_id>/...` files, not only emitted in chat.
- Added stalled-background watchdog policy (>10 min no progress) with required
  blocker escalation and targeted unblock prompt.
- Added explicit per-task `canon capture` discipline for terminal task states to
  improve memory quality and retrieval coverage.

---

## [3.3.1] - 2026-04-24

### Changed

- Slack blocker escalation is now repo-scoped via
  `CANON_SLACK_BLOCKER_CHANNEL_ID` (with optional
  `CANON_SLACK_BLOCKER_CHANNEL_NAME`) instead of a globally hardcoded channel.
- Innermost channel `C0AUF2FGK42` is now documented as an Innermost-specific
  configuration example rather than a universal default.

---

## [3.3.0] - 2026-04-24

### Added

- New `release-orchestrator` subagent template to govern branch/PR/merge/deploy
  lifecycle with explicit QA/CI/environment gates and rollback readiness.

### Changed

- Non-trivial execution flow now includes release governance after task-level QA:
  `project-planner -> scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator`.
- Repo + user-scope installs now include `release-orchestrator.md`.
- Rules/docs now enforce branch protection, CI+QA merge gates, environment
  promotion gates, and explicit external-approver handoff when policy requires it.

---

## [3.2.2] - 2026-04-24

### Fixed

- Runtime env layering now reads `~/.canon/canon-systems.env` (current machine
  config path) before legacy fallbacks, so `AWS_PROFILE` and region set by
  `canon setup` are available during `canon ask/capture/secrets` in fresh
  sessions.

### Added

- Regression test to ensure `ensure_layered_memory_env()` loads
  `canon-systems.env` machine values.

---

## [3.2.1] - 2026-04-24

### Fixed

- `canon secrets` no-subcommand path no longer crashes in CLI dispatch
  (`AttributeError: Namespace has no attribute company_id`). It now reliably
  defaults to wizard mode and safely handles missing optional parser fields.

### Added

- Regression test `tests/test_cli_secrets.py` to ensure `cli.main(["secrets"])`
  routes to `wizard` without attribute errors.

---

## [3.2.0] - 2026-04-24

### Added

- New `project-planner` subagent template for large-initiative decomposition
  into an epic/task backlog with dependencies, parallel waves, and explicit
  completion criteria.

### Changed

- Planning workflow now enforces plan-first for broad projects: switch to Plan
  mode, run `project-planner`, then execute each task via
  `scoper -> cursor-pilot -> implementer -> qa-gate` until backlog completion.
- Repo and user-scope installs now include `project-planner.md` so decomposition
  capability is available everywhere after rewire/update.
- Docs updated to describe decomposition-first execution instead of treating
  large initiatives as a single monolithic task.

---

## [3.1.2] - 2026-04-24

### Changed

- Once-per-version auto-rewire now refreshes user-level Cursor scope
  (`~/.cursor/agents` + `~/.cursor/rules`) in addition to the cross-repo pass,
  so global subagent templates update automatically after upgrade.

### Added

- `CANON_SYSTEMS_DISABLE_USER_SCOPE_REWIRE=1` to disable only the user-scope
  refresh while keeping cross-repo rewires enabled.

---

## [3.1.1] - 2026-04-24

### Changed

- Auto-rewire now includes a cross-repo pass once per installed version: on
  the first `canon` command after upgrade, it scans configured roots (default
  `~/localwork`) for previously wired repos and refreshes hooks/rules/subagents
  in one shot when repo pins are older.

### Added

- New tuning env vars for cross-repo auto-rewire:
  - `CANON_SYSTEMS_REWIRE_ROOTS` (path-separated scan roots)
  - `CANON_SYSTEMS_GLOBAL_REWIRE_MAX_DEPTH` (scan depth, default `3`)
  - `CANON_SYSTEMS_DISABLE_GLOBAL_REWIRE=1` (disable only global pass)

---

## [3.1.0] - 2026-04-24

### Added

- `canon auth-migration <status|prepare|canary|enforce|rollback>` for phased
  repo-level auth + endpoint migration state management, including dry-run and
  rollback restore of prior endpoint values.
- Operator scripts under `scripts/auth-migration/` for phase rollout and
  rollback.
- `scripts/migrate_memory_secrets.py` to bulk rewrite memory secrets from
  raw-IP endpoints to canonical domain URLs and set migration phase flags.
- `scripts/validate_memory_endpoints.py` to validate secret endpoint
  reachability and detect raw-IP endpoint drift.
- Migration documentation:
  `docs/migrations/cognito-ingress-migration.md` and
  `docs/runbooks/auth-migration-rollback.md`.
- Terraform scaffolding for long-term ingress + Cognito resources under
  `infra/auth-ingress/`.
- `canon dor-log` command with queued retry behavior for structured DoR failure
  telemetry.
- New `implementer` subagent template pinned to `composer-2-fast` for coding
  execution between planning and QA phases.
- `canon secrets` interactive wizard (default `canon secrets` behavior) for
  guided Secrets Manager provisioning, validation, and write confirmation.
- CI policy guard workflow (`.github/workflows/template-policy-guard.yml`) to
  prevent drift in agent template safety/parallelization policies.

### Changed

- Required non-trivial workflow is now explicitly
  `scoper -> cursor-pilot -> implementer -> qa-gate`.
- `cursor-pilot` now emits a `PARALLELIZATION_PLAN` with dependency-aware
  workstreams and shard handoff format (`HANDOFF_TO_QA_SHARD`) so parent agents
  can launch multiple coding subagents concurrently.
- Rule templates enforce memory-first behavior, no-hallucination policy, and
  strict "stop and ask" behavior for missing prerequisites.
- `README.md` and `docs/ONBOARDING.md` now document auth-migration operations,
  wizard-first secret handling, and parallel implementer orchestration.

### Fixed

- Hook templates (`memory-preflight.sh`, `memory-capture.sh`) now detect
  credential/secret failures, trigger Canon secret recovery flow, retry once,
  and surface a recovery-needed marker message when still blocked.
- Subagent templates now include explicit guardrails against asking users to
  paste secrets into chat, while supporting credential reuse/import flows.

---

## [3.0.4] - 2026-04-24

### Changed

- **`canon setup`:** the Secrets Manager **name prefix is no longer an
  interactive question**. It is chosen automatically from (in order) an
  existing `MEMORY_LAYER_AWS_SECRET_NAME_PREFIX` in
  `.canon/memory-layer.local.env`, the company-registry entry, an AWS
  **DescribeSecret** probe for the built secret id under `canon-memory-dev`
  then `canon-systems-v2-dev`, and finally the `canon-memory-dev` default.
  IAM keys / profile are applied **before** the probe so first-time key
  paste works. See `discover_memory_layer_secret_prefix` in `aws_secrets.py`.

---

## [3.0.3] - 2026-04-24

### Changed

- **Secrets Manager default prefix** is now **`canon-memory-dev`** instead of
  **`canon-systems-v2-dev`**. The old string looked like the `canon-systems`
  package semver (“v2”) and confused people; the prefix is only an AWS path
  namespace. The legacy value is kept as **`LEGACY_MEMORY_LAYER_AWS_SECRET_NAME_PREFIX`**
  in `aws_secrets.py` for docs and setup copy.
- **`canon setup`:** suggested prefix prefers an existing
  `MEMORY_LAYER_AWS_SECRET_NAME_PREFIX` from `.canon/memory-layer.local.env`
  (so re-running setup does not silently “upgrade” you to a new AWS path),
  then company-registry, then the new default. Explainer text moved to just
  before the prefix prompt.

### Added

- **`examples/company-registry.example.json`:** `IMC` example on the new
  prefix; `FMO` example still shows the legacy prefix for stacks that have
  not migrated AWS yet.

---

## [3.0.2] - 2026-04-23

### Added

- **`canon setup` and `canon enable-repo`:** optional **pipx self-update**.
  When the running `canon` binary comes from a pipx venv for `canon-systems`,
  we run `pipx upgrade canon-systems`; if the installed distribution version
  **increases**, we **re-exec** `canon` with the same arguments so the rest of
  the command (and the version pin written by `enable-repo`) uses the new
  build. Disable with `CANON_SYSTEMS_SKIP_SELF_UPDATE=1` or in CI (`CI=true`).
  See `src/canon_systems/self_update.py`.

---

## [3.0.1] - 2026-04-22

### Added

- `docs/ONBOARDING.md` — step-by-step for teammates with IAM keys (install,
  PATH, `canon setup`, verification, troubleshooting).

### Changed

- **`canon setup`:** clearer copy for **AWS credentials profile** (local
  `~/.aws/credentials` section name, not console username or access key);
  optional IAM key prompts reworded; after **Secrets name prefix**, prints
  the **resolved Secrets Manager secret id** so it can be checked in AWS
  before continuing.
- **`README.md`:** link to onboarding; note `~/.local/bin` after pipx;
  private-git install URLs for `CanonSystems/canon-systems`.
- **`docs/ONBOARDING.md`:** pip / pip3 user-install PATH
  (`python3 -m site --user-base`); pipx + `~/.local/bin` + zsh (`~/.zshrc`);
  expanded **setup prompts** table (company, profile, region, repo id,
  prefix); `aws sts get-caller-identity` uses chosen profile.

---

## [3.0.0] - 2026-04-20

First release under the **canon-systems** name (major bump from the prior
`canon-memory-layer` package).

### Added

- Back-compat: hook shims try `canon` then `canon-memory-layer`;
  `version-check` reads `CANON_SYSTEMS_VERSION` with fallback to
  `CANON_MEMORY_LAYER_VERSION`; machine env reads
  `~/.canon/canon-systems.env` and legacy `canon-memory-layer.env`.

### Changed

- **PyPI / package name:** `canon-memory-layer` → **`canon-systems`**.
- **Python module:** `memory_layer` → **`canon_systems`**.
- **CLI:** **`canon`** (console script); `canon --version` reports
  `canon-systems <version>`.
- **Version pin env key:** `CANON_MEMORY_LAYER_VERSION` →
  **`CANON_SYSTEMS_VERSION`** (legacy key still read until re-enabled).
- **Repo-root override env:** `CANON_SYSTEMS_REPO_ROOT` (legacy
  `CANON_MEMORY_LAYER_REPO_ROOT` still honored).
- **Machine env file:** `~/.canon/canon-systems.env` (legacy filename still
  read as fallback).
- **Docs:** proprietary / private-git distribution; removed public npm
  wrapper; subagent + Cursor templates call `canon`.

### Removed

- `package.json` and `bin/` npm shim (distribution is private git + pipx,
  not npmjs).

---

## [0.2.0] - 2026-04-20

Released as **`canon-memory-layer`** (historical name).

### Added

- Agent-callable **`ask`**, **`store-pending-user`**, **`version-check`**.
- Distilled **`capture`** fields (`decisions`, `next_actions`,
  `open_questions`).
- Template hooks, `hooks.json`, rules (`canon-autosetup`,
  `memory-layer-defaults`), subagents (`scoper`, `cursor-pilot`, `qa-gate`).
- **`enable-repo`** merges hooks and pins CLI version in
  `.canon/memory-layer.local.env`.

### Changed

- **Docs:** private distribution framing (`pipx` from git, no PyPI).

---

## How to maintain this log

1. **During development:** add bullets under **`[Unreleased]`** in the right
   subsection (`Added` / `Changed` / `Fixed` / `Removed`).
2. **When cutting a release:**
   - Bump `version` in `pyproject.toml` and `__version__` in
     `src/canon_systems/__init__.py`.
   - Rename **`[Unreleased]`** to **`[x.y.z] - YYYY-MM-DD`**, leave a fresh
     empty **`[Unreleased]`** block at the top.
   - Commit with message like `Release x.y.z` and push.

Pre-release identifiers (e.g. `3.1.0a1`) are fine if we ever need them;
otherwise stay on `MAJOR.MINOR.PATCH`.
