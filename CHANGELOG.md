# Changelog

All notable changes to **canon-systems** are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

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
