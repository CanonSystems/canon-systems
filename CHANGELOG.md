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
