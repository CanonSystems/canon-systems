# Changelog

All notable changes to **canon-systems** are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Docs:** `docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md` — full runtime checklist
  (layered env, secret keys, state defaulting, graph health vs index usefulness),
  global retrieval rule pointer, per-agent matrix, and living-update cross-links.
- **Docs:** `docs/PROJECT-PLANNER-RETRIEVAL-RATIONALE.md` — design intent for
  canonical-first planning vs graph-first implementation chain.
- **Docs:** `docs/ROADMAP.md` — unordered future work, including AWS
  `canon-systems-v2` naming alignment tech debt.

### Changed

### Fixed

## [3.5.2] - 2026-04-24

### Added

- **`canon doctor`:** detects **split-brain DNS** (libc cannot resolve the memory hostname but **`dig`** can — typical with **Cloudflare WARP**), prints a short warning, includes a **`dns`** object in **`--json`**, and adds **`canon doctor --curl-resolve-snippet`** to print a one-line **`curl --resolve`** command for **`/healthz`** (fresh **`dig`** A record + **`User-Agent`**).

## [3.5.1] - 2026-04-24

### Fixed

- **`canon_urlopen`:** when `getaddrinfo` fails with “nodename nor servname …” (seen with some **Cloudflare WARP** setups where `dig` still resolves), retry via a **`dig` + TLS-SNI** connect to the IPv4 target while preserving the original hostname for certificate verification. Disable with **`CANON_DNS_FALLBACK=0`**.
- **Outbound `User-Agent`:** default to **`canon-systems/<version>`** when callers omit one so **Cloudflare** (and similar) do not block bare **`Python-urllib/*`** probes; override with **`CANON_HTTP_USER_AGENT`**.

## [3.5.0] - 2026-04-24

### Added

- **Stable dev memory URL controls:** optional ECS ingress wiring, stable-HTTPS secret/tooling defaults, rollback guidance, and validation paths so Canon memory endpoints can move off ephemeral task IPs.
- **Experiment-aware telemetry and reporting:** additive `payload.comparison` metadata, `task_outcome` canonical events, `metrics_rollup` comparison buckets, and `canon report` filters / `--compare-by` for memory-mode and experiment comparisons.
- **Experimental multilane orchestration:** optional **`canon resume --lanes`** with enriched `--tasks-file` manifests adds `runnable_targets`, `active_targets`, `blocked_targets`, and `task_threads` while preserving legacy serial resume behavior.

### Changed

- **Parent orchestration policy:** templates, runbooks, and the hard-lock rule now document an explicit opt-in path for experimental parent-session multilane scheduling via `CANON_EXPERIMENTAL_MULTILANE_ORCHESTRATION`, while keeping canon-memory-v1 serial protections as the default.

### Fixed

- **Terraform hygiene:** removed stray tracked local Terraform lock/state artifacts under `infra/axon-only` and tightened ignore coverage so layout/regression checks stay green.

## [3.4.7] - 2026-04-24

### Added

- **`canon doctor`** — reports tenant wiring vs last preflight `context-latest.md`, AWS secret cache path/TTL, and warns on `http(s)://` URLs with **literal IPv4** in standard Canon env paths; **`canon doctor --fix-cache`** deletes `~/.canon/memory-layer-aws-cache.json` after secret rotation.
- **Docs:** [MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md](docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md) §1.2b (Secrets Manager client cache), §1.2a (URLs may exist only in AWS + cache; `doctor` scans `.env` paths, not cache JSON), and [ONBOARDING](docs/ONBOARDING.md) — 3.4.6 vs 3.4.7 (`memory-health` / `rm` vs `doctor`). **Agent rule** `memory-layer-defaults.mdc` aligned.

## [3.4.6] - 2026-04-24

### Added

- **`certifi` dependency** for HTTPS clients; `canon_urlopen` / `request_json` use
  certifi’s CA bundle so macOS Python can verify TLS to hosts like App Runner.
- **`knowledge-api`:** mounts **`memory-adapter`** `POST /memory/search` on the same
  app so MemPalace works when only the canonical API is deployed (no separate
  memory-adapter ECS service).
- **`docker/knowledge-api/Dockerfile`:** reference image build for ECS Fargate
  (`linux/amd64`). Dev tasks use ephemeral public IPs; after deploy, update
  `KNOWLEDGE_*` / `MEMORY_ADAPTER_URL` in Secrets Manager if URLs embed the old
  task IP (prefer an NLB/ALB DNS name long-term).

### Fixed

- **`canon memory-health` / preflight:** HTTPS probes no longer fail with
  `CERTIFICATE_VERIFY_FAILED` on typical macOS Python installs when the remote
  chain is valid.

### Note

- **`canon doctor`** is not part of this release; it ships in **3.4.7**. After
  secret rotation on **3.4.6**, clear the client cache with
  `rm -f ~/.canon/memory-layer-aws-cache.json` (see runtime doc §1.2b).

## [3.4.5] - 2026-04-23

### Changed

- **`canon graph`:** loads the same layered env + Secrets Manager hydration as
  hooks before resolving **`AXON_SERVICE_URL`** / **`AXON_SERVICE_TOKEN`**, so
  graph clients work when those keys exist only in AWS (not only in local `.env`).
- **`canon secrets template`:** includes optional **`AXON_SERVICE_URL`** and
  **`AXON_SERVICE_TOKEN`** placeholders for operators provisioning the graph plane.

## [3.4.4] - 2026-04-23

### Changed

- **State plane URL:** after layered env + AWS Secrets Manager hydration,
  **`CANON_STATE_API_URL` defaults to `KNOWLEDGE_API_URL`** when no state URL
  is set, so checkpoints and **`canon memory-health`** see the same AWS
  base as canonical memory without extra client config.
- **`canon secrets`:** template and submit/wizard **include / coerce
  `CANON_STATE_API_URL`** from `KNOWLEDGE_API_URL` when omitted.

### Fixed

- **`canon memory-health`** treats **`CANON_STATE_API_URL`** as an alias of
  **`STATE_API_URL`** when resolving the state backend (matches checkpoint CLI).

## [3.4.3] - 2026-04-23

### Added

- **`canon e2e-check`** (`--agent` wraps JSON in `<<<CANON_E2E_VERDICT>>>`):
  single plug-and-play validation from repo root — executable hooks, Cursor
  rules, version pin vs CLI, and **`canon memory-health`** for required
  backends. Exit **0** iff **`"verdict": "PASS"`**.

### Changed

- **`canon memory-health`:** optional backends (**state**, **graph**) in
  **`not_configured`** no longer force **`overall_status: degraded`** — only
  configured-but-unhealthy optionals degrade. Unset state/axon is normal for
  memory-only installs; overall is **`ok`** when canonical + mempalace pass.

## [3.4.2] - 2026-04-23

### Fixed

- **`canon memory-health`** now calls the same layered env hydration as hooks
  (`~/.canon/canon-systems.env`, `~/.canon/canon-memory-layer.env`, team +
  secrets files, **AWS Secrets Manager** via `apply_canon_systems_secrets_from_aws`)
  before resolving `KNOWLEDGE_API_URL` / `MEMORY_ADAPTER_URL`. Previously it
  only read `memory-layer.local.env` + `scoper-chat.env`, so installs that
  kept URLs exclusively in home or Secrets Manager saw **localhost** probes
  while **`canon ask` / preflight still worked** — a consistency bug, not a
  missing deployment.

## [3.4.1] - 2026-04-23

### Fixed

- **PyPI/sdist/wheel installability:** bundle `canon_backend_shared` into the
  same distribution via `tool.setuptools.packages.find` (`where = ["src",
  "backend/shared"]`) so `from canon_backend_shared.events import
  CanonicalEvent` resolves after `pip install canon-systems` outside the
  monorepo.
- Declare **`boto3>=1.34,<2`** as a core dependency so importing
  `canon_systems.vault_sync` (top-level `botocore.exceptions`) does not
  fail on a clean venv; `canon --version` works on minimal install.

## [3.4.0] - 2026-04-23

Canon Memory Platform **v1** — complete. Ships operator CLI (`canon report` full rollup, hard-lock rule via `canon wire`, vault sync, synth publish/show, release publish-on-pass), in-repo backends (`state-api`, `axon-service`, `synthesis`, `synthesis-web`), Terraform modules (apply separately for cloud). Test suite: **440** passing at release tag.


### Added

- **E7-T3** Final five-file living-spec refresh + Canon Memory Platform v1
  sign-off: `README.md` gains a dated "Canon Memory Platform v1 — shipped"
  summary enumerating Waves 0–7 deliverables.
  `docs/MEMORY-PLATFORM-PLAN.md §9` rewritten so each wave lists SHIPPED
  status with outcomes. `docs/MEMORY-PLATFORM-BACKLOG.md` and
  `docs/SYSTEM-WORKFLOW.md` each get a top-of-document v1 status callout.
  `.cursor/handoffs/canon-memory-v1/E7-T3/release-status.md` records the
  final release sign-off (`release_id: canon-memory-v1-final`,
  `signed_off_at: 2026-04-23`, all three gates PASS, 440/440 suite). (E7-T3)
- **E7-T2** Sibling repository disposition FINAL (moved-for-review
  variant): `docs/DEPRECATIONS.md` marked FINAL with explicit
  `Original path`, `Current path`, `Original label`, and `Final label`
  per sibling. Zero deletions. Per operator direction, the three `absorb`
  targets were physically moved from `/Users/edwardwalker/localwork/` to
  `/Users/edwardwalker/localwork/_deprecated/` pending post-release
  review: `mempalace`, `obsidian-mind`, and `total_recall`. `canon-platform`,
  `canon-systems-v2`, and `temporal` left in place per their `keep` labels.
  Canonical events appended to `.canon/memory/events.ndjson`: 6 ×
  `sibling_disposition_finalized` + 3 × `sibling_moved_for_review`
  (with `old_path`, `new_path`, `reason`, `deletion_executed: false`).
  Wave-0 audit regex coverage preserved; `tests/` suite still 440/440
  green. (E7-T2)
- **E7-T1** Hard-lock rule distribution via `canon wire`: packaged
  `src/canon_systems/templates/rules/memory-platform-build-discipline.mdc`
  (byte-identical to the workspace rule) and extended
  `repo_enable.enable_repo` and `repo_enable.install_user_scope` to install
  it alongside `memory-layer-defaults.mdc`. Every repo wired by `canon
  setup` / `canon enable-repo` now carries the hard-lock rule in
  `.cursor/rules/` so the Canon Memory Platform build discipline stays
  enforced across the fleet. New 5-test suite
  `tests/test_wire_distribution.py` asserts the packaging, byte-identity
  with the workspace rule, installation via `enable_repo` and
  `install_user_scope`, and idempotence of repeat installs. Full `tests/`
  suite 435 → 440 passed. (E7-T1)
- **E6-T2** `canon report` CLI over canonical events: `src/canon_systems/report_cli.py`
  reworked from the E3-T5 stub into the first-class `canon report` surface.
  Ingests NDJSON canonical event streams and supports scope filters
  (`--company-id / --repository-id / --plan-id / --task-id`) and time-window
  filters (`--since / --until` ISO-8601 Z inclusive). Two output modes: default
  `--by {source,phase,agent}` preserves the legacy `{by, groups}` envelope
  consumed by `tests/test_retrieval_telemetry.py`, and `--full` delegates to
  `metrics_rollup.aggregate` (E6-T1) emitting the complete rollup schema.
  `--format {json,csv}` supported; CSV for `--full` emits
  `section,key,tokens_in,tokens_out,count` rows. Exit codes: `0` OK, `2`
  usage, `3` events-file not found, `4` malformed NDJSON. Byte-identical
  determinism verified. 13-test suite in `tests/test_cli_report.py`; full
  `tests/` suite 422 → 435 passed. (E6-T2)
- **E6-T1** Metrics aggregator over canonical events: new pure-Python
  `src/canon_systems/metrics_rollup.py` (`SCHEMA_VERSION = 1`) consumes an
  iterable of canonical events and returns a deterministic JSON rollup
  covering `lead_time_by_task` (first→last event timestamps + seconds),
  `cycle_time_by_phase` (task_count/total/avg across the five canonical
  phases), `retries_by_task_phase` (distinct-`agent_run_id` counts minus
  1 per (task, phase)), `dor_causes` (`dor_failure.payload.stage`
  counts), `stalls` (total + per-task from `lease_stall_detected`),
  `token_cost` (`retrieval_breakdown` split by phase/agent/source across
  the graph/state/canonical/file buckets), and `synth_publish`
  (ok/failed/notifier_ok counts from E5-T7 events). Scope filters on
  `company_id`/`repository_id`/`plan_id`; `since`/`until` ISO-8601 Z
  window filter; malformed timestamps silently skipped. Stdlib-only,
  read-only (no boto3/pandas/numpy; no filesystem I/O; no canonical
  events emitted — enforced by 16-test suite `tests/test_metrics_rollup.py`
  incl. source-scan). Determinism verified via back-to-back
  `json.dumps(..., sort_keys=True)` byte-identical assertion. Suite
  406 → 422 passed. (E6-T1)
- **E5-T7** Auto-publish hook on `RELEASE_STATUS` PASS: new `canon release
  publish-on-pass` subcommand (wired through `src/canon_systems/cli.py`) reads
  the release-orchestrator's `RELEASE_STATUS` packet (YAML or JSON), and when
  `qa_gate`, `ci_gate`, and `merge_gate` all equal `PASS` invokes
  `canon synth publish` exactly once via a subprocess seam with bounded
  exponential-backoff retries (`min(base*2**(k-1), 60s)`, default 3 attempts
  via `CANON_PUBLISH_RETRIES`). Fires once per release (not per task):
  idempotent via `.canon/release-publish/<plan_id>/<release_id>.json` sentinel;
  second invocation is a byte-identical no-op. Optional notifier via
  `CANON_PUBLISH_NOTIFIER_URL` (best-effort POST with 5s timeout; failure
  never fails the release, never interrupts the exit code). Emits one
  `synth_publish` canonical event per attempt outcome plus an optional
  `vault_sync_notified` event on 2xx POSTs. All S3 writes still flow through
  the already-audited `canon synth publish` binary — the new module carries
  a 24-method boto3 forbidden-write source scan. `release-orchestrator.md`
  template gains the `## Auto-publish hook on RELEASE_STATUS PASS` section
  documenting both knobs (+1 template assertion test). Tests: 18 new in
  `tests/test_release_publish.py` (AC1..AC11 + inline-JSON body path +
  usage/config error paths). Suite 388 → 406 passed.
- `canon vault sync` read-only S3→<repo>/vault/ mirror (one-shot + loop) with
  exponential backoff, content-hash diff, deletion propagation, and
  `canon enable-repo` integration installing the OS-appropriate background
  daemon (launchd/systemd/schtasks), the sentinel-framed `vault/` gitignore
  block, and the `.cursor/hooks/vault-sync-preflight.sh` pre-turn refresh
  hook. No S3 writes anywhere in the sync code path (20-method source-scan
  gate). (E5-T6)
- `canon synth show` read-only CLI subverb streams Obsidian vault markdown (plan + tasks) for `(plan_id[, task_id])` from the published S3 vault, with markdown/JSON modes, canonical stream order, ISO-Z `--cutoff-ts` filter, `--dry-run` event-log fallback, and a 21-method boto3 source-scan enforcing zero S3 write call sites. (E5-T5)
- **E5-T4** `backend/synthesis-web` read-only FastAPI SSR browser over the E5-T2 S3 vault: routes `/healthz`, `/`, `/v/{company_shorthash}/{repo_shorthash}/` (vault home), markdown pages, `/_graph` (deterministic JSON), `/_search` (capped substring search); `markdown-it-py` with `html=False`; inline CSS templates (zero external CDN / zero `<script src>`); `S3VaultReader` is GET/HEAD/List-only; design spike **request-time SSR** documented in README + scoper (vs. rebuild-on-publish); tests in `synthesis_web_tests/` (not `tests/`) — 12 cases; suite 390 → 402 passed; unwired Terraform `infra/terraform/modules/synthesis-web/`.
- **E5-T3**: New `canon synth publish` CLI drives the E5-T2 `SynthesisPublisher` deterministically from a canonical-event JSONL file. Emits a single JSON envelope with per-page diff stats (`written`, `skipped`, `keys_written`); safe to invoke repeatedly (content-hash idempotence from E5-T2). `--dry-run` renders the bundle without S3 I/O; transport failures map to exit 2, usage errors to exit 4.
- **E5-T2** `backend/synthesis` deterministic vault generator + publisher: five new modules (`redaction.py`, `sources.py`, `generator.py`, `publisher.py`, plus additive routes on `main.py`) project `CanonicalEvent` rows through the E5-T1 15-field allowlist into an Obsidian-compatible S3 vault. `project_safe()` enforces SAFE / SCOPE-SAFE-aliased / DROPPED per `docs/VAULT-LAYOUT.md §5` (raw `company_id`/`repository_id`/`model` never serialized; unknown payload keys silently dropped with zero log/stderr output). `generate_vault()` is pure (no network, no S3, no wallclock — enforced by source-grep test), sorts events by `(timestamp, event_id)`, emits frontmatter anchors first then alphabetical, and absorbs obsidian-mind cross-links (citations in render paths) + vault-librarian indices (`_render_indices` / `_index/*`). `SynthesisPublisher` writes diff-only via SHA-256 content-hash sidecar metadata against injectable `boto3.client("s3")`; `.obsidian/` seed files are write-once. Two new FastAPI routes: `GET /synth/vault/changes?since=<iso8601>` (422 on junk, deterministic sorted change list) and `GET /synth/show?plan_id=...[&task_id=...][&format=json|markdown]` (JSON envelope default, raw markdown alt, 404 on empty). Tests: 10 in `synthesis_tests/test_generator.py` + 2 in `synthesis_tests/test_endpoints.py` + 1 moto idempotence in `synthesis_tests/test_publisher_moto.py`. Suite 367 → 380 passed. Deps: `boto3>=1.35,<2` prod; `pytest>=8.2,<9`, `moto[s3]>=5.0,<6`, `httpx>=0.27,<1` test-only. New unwired terraform module `infra/terraform/modules/synthesis-vault/` captures infra under Precedent §1 `cloud_execution_deferred` — NOT wired into `infra/terraform/main.tf`.
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
