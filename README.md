# Canon Memory Layer

A single installable package that gives any Cursor workspace:

- **Tenant-scoped memory** (company + repository) with storage on AWS.
- **Auto-setup prompt** when you open an unwired repo in Cursor.
- **Hooks** that hydrate context before every turn and capture every turn
  (distilled decisions, next actions, open questions — not just raw
  transcripts).
- **Agent-callable Q&A**: `canon-memory-layer ask "..."` surfaces
  repo-scoped prior work from canonical artifacts + MemPalace.
- **Subagents** shipped with the package: `scoper`, `cursor-pilot`, and
  `qa-gate` — a Definition-of-Ready-driven chain for non-trivial tasks.
- **Version-drift guard**: hooks hard-fail if the installed CLI is older
  than the version a repo was wired with; the agent is instructed to offer
  an upgrade.

## Distribution

This is **proprietary software**, not published to PyPI or npm. It is
installed directly from its private GitHub repo. Only people with read
access to the repo can install it.

Do **not** publish to public registries. When this is productized, the
intended customer-facing distribution is **AWS CodeArtifact** (same AWS
account as the memory-layer backend), with per-customer IAM-scoped
install tokens.

## Install

```bash
# From the private GitHub repo (primary path for you + Romi):
pipx install git+ssh://git@github.com/<your-org>/canon-memory-layer.git

# Or from a local checkout during development:
pipx install /path/to/canon-memory-layer
# or
cd /path/to/canon-memory-layer && ./install.sh
```

Updating after a new push to the repo:

```bash
pipx upgrade canon-memory-layer
# or force-reinstall from git:
pipx install --force git+ssh://git@github.com/<your-org>/canon-memory-layer.git
```

`install.sh` (or `pipx install`) installs:

- The `canon-memory-layer` CLI on your PATH.
- `~/.cursor/rules/canon-autosetup.mdc` — offers setup when you open an
  unwired repo.
- `~/.cursor/rules/memory-layer-defaults.mdc` — memory usage defaults.
- `~/.cursor/agents/{scoper,cursor-pilot,qa-gate}.md` — the subagent chain,
  available globally.

## Per-repo setup

First substantive prompt in a new repo: the agent (via `canon-autosetup.mdc`)
will ask whether to run setup. Saying yes runs:

```bash
cd <repo>
canon-memory-layer setup
```

This:

1. Prompts for `COMPANY_ID`, `REPOSITORY_ID` (auto-detected from `origin`),
   AWS profile, region, and optionally IAM keys.
2. Writes `~/.canon/canon-memory-layer.env` (machine AWS profile).
3. Writes `<repo>/.canon/memory-layer.local.env` (repo scope + pinned CLI
   version).
4. Installs `<repo>/.cursor/hooks/memory-{preflight,capture}.sh` +
   merges `<repo>/.cursor/hooks.json`.
5. Installs `<repo>/.cursor/rules/memory-layer-defaults.mdc`.
6. Installs `<repo>/.cursor/agents/{scoper,cursor-pilot,qa-gate}.md`.

From this point, every user prompt hydrates context and every assistant
turn gets captured to AWS-backed memory — tenant-scoped to this repo.

If the user says "never", create `<repo>/.canon/.opted-out` to suppress
future prompts in this repo.

## Credentials (AWS Secrets Manager)

API bearer tokens live in AWS Secrets Manager, not in `.env` files you
commit. Set one of the following during setup:

- `MEMORY_LAYER_AWS_SECRET_ID` — explicit full secret id.
- `MEMORY_LAYER_AWS_SECRET_NAME_PREFIX` + `COMPANY_ID` + `REPOSITORY_ID` —
  derives the secret id as
  `<prefix>/memory-layer__<company-slug>__<repo-slug>`.

The secret's value is a JSON object or dotenv body with keys like
`CANON_HTTP_BEARER_TOKEN`, `KNOWLEDGE_API_BEARER_TOKEN`,
`MEMORY_ADAPTER_BEARER_TOKEN`, etc. On every CLI invocation, values are
loaded from Secrets Manager (cached for 15m locally) and merged into the
process environment before HTTP calls.

Install the `[aws]` extra to enable this path:

```bash
pipx install 'git+ssh://git@github.com/<your-org>/canon-memory-layer.git#egg=canon-memory-layer[aws]'
```

## Commands

| Command | Purpose |
|---|---|
| `canon-memory-layer setup` | Interactive first-run setup (also runs enable-repo). |
| `canon-memory-layer enable-repo` | Install hooks + rule + subagents + pin version in current repo. |
| `canon-memory-layer preflight "<prompt>"` | Hydrate `.canon/memory/context-latest.md` for an upcoming task. |
| `canon-memory-layer ask "<question>"` | Search canonical + MemPalace memory for this repo. |
| `canon-memory-layer capture --summary ... --decisions '[...]'` | Capture a turn with distilled fields. |
| `canon-memory-layer actor-report` | Recent run summaries + Jira keys for an actor. |
| `canon-memory-layer version-check` | Hard-fail if installed < pinned. |

## Version drift

When you run `setup` or `enable-repo`, the CLI writes
`CANON_MEMORY_LAYER_VERSION=<current>` into
`<repo>/.canon/memory-layer.local.env`.

The preflight hook runs `canon-memory-layer version-check --quiet` on every
prompt. If the installed CLI is older than the pinned version, it fails and
surfaces a `systemMessage` with exactly:

> `pipx upgrade canon-memory-layer` (pulls latest from the private git repo)

The agent rule `memory-layer-defaults.mdc` instructs the model to offer
running that upgrade for the user before continuing.

The CLI never auto-upgrades or auto-downgrades; the user decides.

## Cross-repo reads (privacy)

Memory is tenant-scoped by `company_id` + `repository_id` via the
`X-Actor-Id` / `X-Company-Id` request headers plus `repo_id` query
parameters. By default, agents cannot read another repo's memory.

(Future: a `canon-memory-layer acl` command will let users grant one-time
or always cross-repo reads to specific repo_ids within the same
`company_id`, with all grants logged.)

## Subagents

Installed globally by `install.sh` and into each wired repo by
`enable-repo`:

- **`scoper`** — read-only. Takes a vague prompt, scans repo + memory,
  enforces a strict Definition of Ready, emits `HANDOFF_TO_CURSOR_PILOT`.
- **`cursor-pilot`** — read-only. Takes the Scoper handoff, emits a precise
  implementation prompt with a mandatory `HANDOFF_TO_QA` stop condition.
- **`qa-gate`** — full access. Writes or augments tests, runs them,
  iterates fixes up to 3 times, emits `GATE_RESULTS`.

Use `/spq` or invoke them explicitly in your parent agent's plan.

## Company registry

Optional. Place at one of:

- `<repo>/.canon/company-registry.local.json` (repo-local private)
- `<repo>/.canon/company-registry.json` (repo-shared)
- `~/.canon/company-registry.json` (machine default)

Example shape is in `examples/company-registry.example.json`.

## Development

```bash
pipx install -e /path/to/canon-memory-layer
pytest
```

Tests cover: template rendering of hooks/rule/subagents, env file merging,
auth profile resolution, AWS secret string parsing, and version-drift check
logic.
