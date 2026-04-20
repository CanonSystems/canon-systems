# Changelog

All notable changes to **canon-systems** are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `CHANGELOG.md` (this file) and a README link; **How to maintain** notes at
  the bottom of this file.

### Changed

### Fixed

### Removed

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
