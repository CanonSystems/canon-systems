# Canon Systems

A single installable package that turns any Cursor workspace into a
memory-backed, agent-driven engineering surface.

What ships in one install:

- **Tenant-scoped memory** (company + repository) with AWS-backed storage.
- **Auto-setup prompt** when you open an unwired repo in Cursor.
- **Hooks** that hydrate context before every turn and capture every turn
  (distilled decisions, next actions, open questions — not just raw
  transcripts).
- **Agent-callable Q&A**: `canon ask "..."` surfaces repo-scoped prior
  work from canonical artifacts + MemPalace.
- **Subagent system**: `project-planner`, `scoper`, `cursor-pilot`,
  `implementer`, `qa-gate`, and `release-orchestrator` — backlog planning,
  DoR-driven execution, and gated release orchestration.
- **Version-drift guard**: hooks hard-fail if the installed CLI is older
  than the version a repo was wired with; the agent is instructed to
  offer an upgrade.

The CLI is `canon`. The pipx package name is `canon-systems`. The module
is `canon_systems`. Current major version: **3.x**. See
[CHANGELOG.md](CHANGELOG.md) for release history and how we bump versions.

> **New team member?** Start with [docs/ONBOARDING.md](docs/ONBOARDING.md).
> It walks you through installing the CLI, wiring up AWS credentials with
> an IAM key pair, and enabling your first repo in about ten minutes.
>
> **Need the current operating model?** See
> [docs/SYSTEM-WORKFLOW.md](docs/SYSTEM-WORKFLOW.md) (living spec; update each
> Canon iteration).
>
> **Want the forward plan?** See the target architecture in
> [docs/MEMORY-PLATFORM-PLAN.md](docs/MEMORY-PLATFORM-PLAN.md) and the
> agent-executable backlog in
> [docs/MEMORY-PLATFORM-BACKLOG.md](docs/MEMORY-PLATFORM-BACKLOG.md).

## Backend monorepo

Service packages and shared types for the Canon Memory Platform live under
[`backend/`](backend/README.md). Install the workspace with `uv sync
--all-packages` or `bash scripts/backend/install-workspace.sh` from the repo
root. The layout is described in
[docs/SYSTEM-WORKFLOW.md](docs/SYSTEM-WORKFLOW.md) §10.

## Distribution

This is **proprietary software**, not published to PyPI or npm. It is
installed directly from its private GitHub repo. Only people with read
access to the repo can install it.

Do **not** publish to public registries. When this is productized, the
intended customer-facing distribution is **AWS CodeArtifact** (same AWS
account as the canon-systems backend), with per-customer IAM-scoped
install tokens.

## Install

```bash
# From the private GitHub repo (primary path for you + Romi):
pipx install git+ssh://git@github.com/CanonSystems/canon-systems.git

# Or from a local checkout during development:
pipx install /path/to/canon-systems
# or
cd /path/to/canon-systems && ./install.sh
```

If you use `pip3 install ...` instead of pipx, the install can succeed while
`canon` is not found: pip puts the script under
`$(python3 -m site --user-base)/bin`, which macOS often leaves off PATH.
Add that directory to PATH (see [docs/ONBOARDING.md](docs/ONBOARDING.md#1b-alternative-pip-or-pip3-user-install)),
or switch to pipx for fewer surprises.

After **pipx** install, `canon` lives in `~/.local/bin`. Open a **new
terminal** or run `export PATH="$HOME/.local/bin:$PATH"` — see
[ONBOARDING §1c](docs/ONBOARDING.md#1c-after-pipx-canon-not-on-path).

**Self-update:** when pipx-managed, `canon` periodically checks for updates via
`pipx upgrade canon-systems` and restarts on newer builds automatically.
`setup`/`enable-repo` force an immediate check; other commands are throttled
(default every 6h). Set `CANON_SYSTEMS_SKIP_SELF_UPDATE=1` (or `CI=true`) to
skip, or tune interval with `CANON_SYSTEMS_SELF_UPDATE_INTERVAL_SEC`.

**Plug-and-play template refresh:** if installed `canon-systems` is newer than
the repo pin, normal commands (`preflight`, `capture`, `ask`, etc.) now
auto-refresh repo wiring (hooks/rules/agents) and bump the pin. In addition,
once per installed version, `canon` scans configured workspace roots (default
`~/localwork`) and rewires all previously wired repos automatically, and also
refreshes user-level Cursor scope (`~/.cursor/agents` + `~/.cursor/rules`).
This keeps agent template updates (including DoR telemetry behavior) rolling
out across machines without repo-by-repo manual commands. Set
`CANON_SYSTEMS_DISABLE_AUTO_REWIRE=1` to disable all auto-rewire, or
`CANON_SYSTEMS_DISABLE_GLOBAL_REWIRE=1` to disable only the cross-repo pass.
Set `CANON_SYSTEMS_DISABLE_USER_SCOPE_REWIRE=1` to skip user-scope refresh.

Updating after a new push:

```bash
pipx upgrade canon-systems
# or force-reinstall from git:
pipx install --force git+ssh://git@github.com/CanonSystems/canon-systems.git
```

`install.sh` (or `pipx install`) installs:

- The `canon` CLI on your PATH.
- `~/.cursor/rules/canon-autosetup.mdc` — offers setup when you open an
  unwired repo.
- `~/.cursor/rules/memory-layer-defaults.mdc` — memory usage defaults.
- `~/.cursor/agents/{project-planner,scoper,cursor-pilot,implementer,qa-gate,release-orchestrator}.md` — the subagent
  chain, available globally.

## Per-repo setup

First substantive prompt in a new repo: the agent (via `canon-autosetup.mdc`)
will ask whether to run setup. Saying yes runs:

```bash
cd <repo>
canon setup
```

This:

1. Prompts for `COMPANY_ID`, `REPOSITORY_ID` (auto-detected from `origin`),
   AWS profile, region, and optionally IAM keys.
2. Writes `~/.canon/canon-systems.env` (machine AWS profile).
3. Writes `<repo>/.canon/memory-layer.local.env` (repo scope + pinned CLI
   version as `CANON_SYSTEMS_VERSION`).
4. Installs `<repo>/.cursor/hooks/memory-{preflight,capture}.sh` +
   merges `<repo>/.cursor/hooks.json`.
5. Installs `<repo>/.cursor/rules/memory-layer-defaults.mdc`.
6. Installs `<repo>/.cursor/agents/{project-planner,scoper,cursor-pilot,implementer,qa-gate,release-orchestrator}.md`.

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

`canon setup` **infers** the prefix (existing repo env → company-registry →
**probe AWS** for `canon-memory-dev` / legacy `canon-systems-v2-dev` → default
`canon-memory-dev`). You normally do not type it. Override with
`MEMORY_LAYER_AWS_SECRET_NAME_PREFIX` in the environment or
`.canon/memory-layer.local.env` if needed.

The secret's value is a JSON object or dotenv body with keys like
`CANON_HTTP_BEARER_TOKEN`, `KNOWLEDGE_API_BEARER_TOKEN`,
`MEMORY_ADAPTER_BEARER_TOKEN`, etc. On every CLI invocation, values are
loaded from Secrets Manager (cached for 15m locally) and merged into the
process environment before HTTP calls.

Install with the `[aws]` extra to enable this path:

```bash
pipx install 'git+ssh://git@github.com/CanonSystems/canon-systems.git#egg=canon-systems[aws]'
```

## Commands

| Command | Purpose |
|---|---|
| `canon setup` | Interactive first-run setup (also runs enable-repo). |
| `canon enable-repo` | Install hooks + rule + subagents + pin version in current repo. |
| `canon preflight "<prompt>"` | Hydrate `.canon/memory/context-latest.md` for an upcoming task. |
| `canon ask "<question>"` | Search canonical + MemPalace memory for this repo. |
| `canon capture --summary ... --decisions '[...]'` | Capture a turn with distilled fields. |
| `canon actor-report` | Recent run summaries + Jira keys for an actor. |
| `canon version-check` | Hard-fail if installed < pinned. |
| `canon auth-migration <status\|prepare\|canary\|enforce\|rollback>` | Manage phased domain/auth migration state in repo env. |
| `canon dor-log --event-json '{...}'` | Push DoR failure telemetry to server; queue locally on send failure. |
| `canon qa-validate --file <path> --require-pass [--handoff-id <id> --task-id <id> --require-dor-telemetry]` | Validate persisted QA gate packet fields/referenced tests; optionally require DoR rejection telemetry artifacts for the task. |
| `canon flow-audit --handoff-id <id> --task-id <id>` | Audit process compliance artifacts (handoff files + plan/task tracking), with optional sampling. |
| `canon secrets` | Launch interactive secrets wizard (guided prompts + validation + write). |
| `canon secrets template` | Print canonical JSON template for repo-scoped runtime secrets. |
| `canon secrets submit --payload-file ...` | Validate and write a structured secret payload to AWS Secrets Manager. |

## Version drift

When you run `setup` or `enable-repo`, the CLI writes
`CANON_SYSTEMS_VERSION=<current>` into
`<repo>/.canon/memory-layer.local.env` (the filename itself is unchanged
from the canon-memory-layer era, so existing wired repos keep working).

The preflight hook runs `canon version-check --quiet` on every prompt. If
the installed CLI is older than the pinned version, it fails and surfaces
a `systemMessage` with exactly:

> `pipx upgrade canon-systems` (pulls latest from the private git repo)

The agent rule `memory-layer-defaults.mdc` instructs the model to offer
running that upgrade for the user before continuing.

The CLI never auto-upgrades or auto-downgrades; the user decides.

## Structured secret submission

Use the interactive wizard as the default flow (no payload handcrafting):

```bash
canon secrets
# (equivalent: canon secrets wizard)
```

The wizard prompts for scope, endpoints, bucket, token, and write behavior;
then validates and submits with a redacted plan/confirmation step.
It can also import existing values from another secret/repo so users can say
"use the credentials we used for <other repo>" and avoid manual re-entry.

Hooks now include credential-recovery detection. When preflight/capture hits
auth/secret errors, they trigger Canon secret recovery flow and retry once; if
still blocked, they surface a recovery-needed message on the next prompt.

If you need automation/CI, use the explicit workflow below:

```bash
# 1) Generate canonical payload shape
canon secrets template --company-id IMC --repository-id innermost > /tmp/canon-secret.json

# 2) Fill real values (URLs, bucket, tokens) in the file

# 3) Validate and submit
canon secrets submit \
  --payload-file /tmp/canon-secret.json \
  --aws-profile <profile> \
  --aws-region us-east-1 \
  --create-if-missing
```

`canon secrets submit` enforces required keys by default, derives scope from
repo wiring (`.canon/memory-layer.local.env`) when available, and prints a
redacted write plan before submission. Use `--dry-run` for validation-only.

### Back-compat with the old name

Prior to v3 this package was named `canon-memory-layer`. To smooth the
transition:

- Hook shims check for `canon` first, then fall back to
  `canon-memory-layer` if only the legacy binary is installed.
- `version-check` reads `CANON_SYSTEMS_VERSION` first, then falls back to
  `CANON_MEMORY_LAYER_VERSION`.
- `~/.canon/canon-systems.env` is the current machine config path;
  `~/.canon/canon-memory-layer.env` is still read as a fallback so
  machines that haven't run setup since the rename keep working.
- Next `canon setup` on a machine prunes the legacy env file; next
  `canon enable-repo` in a repo rewrites the pin to the new key.

## Cross-repo reads (privacy)

Memory is tenant-scoped by `company_id` + `repository_id` via the
`X-Actor-Id` / `X-Company-Id` request headers plus `repo_id` query
parameters. By default, agents cannot read another repo's memory.

(Future: a `canon acl` command will let users grant one-time or always
cross-repo reads to specific repo_ids within the same `company_id`, with
all grants logged.)

## Cognito + Domain Migration

For long-term production wiring (stable domain endpoint + phased Cognito rollout),
use:

- `docs/migrations/cognito-ingress-migration.md`
- `docs/runbooks/auth-migration-rollback.md`
- `scripts/auth-migration/rollout-phase.sh`
- `scripts/auth-migration/rollback.sh`
- `scripts/migrate_memory_secrets.py`
- `scripts/validate_memory_endpoints.py`

Recommended operator flow:

```bash
# Preview changes first
canon auth-migration prepare --dry-run --domain memory.canon-systems.com

# Apply repo phase state
canon auth-migration prepare --domain memory.canon-systems.com

# Update + validate AWS secret endpoints
python scripts/migrate_memory_secrets.py --profile <aws-profile> --phase prepare --apply
python scripts/validate_memory_endpoints.py --profile <aws-profile> --secret-id <secret-id>
```

## Subagents

Installed globally by `install.sh` and into each wired repo by
`enable-repo`:

- **`scoper`** — read-only. Takes a vague prompt, scans repo + memory,
  enforces a strict Definition of Ready, emits `HANDOFF_TO_CURSOR_PILOT`.
- **`project-planner`** — read-only. Decomposes large initiatives into epic/task
  backlog with dependencies and parallel waves before implementation starts.
- **`cursor-pilot`** — read-only. Takes the Scoper handoff, emits a
  precise implementation prompt for the implementer subagent with a
  mandatory `HANDOFF_TO_QA` stop condition.
- **`implementer`** — full access, model `composer-2-fast` by default.
  Executes the cursor-pilot prompt by writing code/tests. For parallel plans,
  parent launches multiple implementers concurrently and each emits
  `HANDOFF_TO_QA_SHARD`, then parent aggregates to `HANDOFF_TO_QA`.
- **`qa-gate`** — full access. Writes or augments tests, runs them,
  iterates fixes up to 3 times, emits `GATE_RESULTS`.
- **`release-orchestrator`** — full access. Manages branch/PR/merge/deploy
  lifecycle and enforces QA + CI + environment gates before promotion.
  Blockers escalate to the repo-configured Slack channel
  (`CANON_SLACK_BLOCKER_CHANNEL_ID`).

Use `/spq` or invoke them explicitly in your parent agent's plan.

## Company registry

Optional. Place at one of:

- `<repo>/.canon/company-registry.local.json` (repo-local private)
- `<repo>/.canon/company-registry.json` (repo-shared)
- `~/.canon/company-registry.json` (machine default)

Example shape is in `examples/company-registry.example.json`.

## Development

```bash
pipx install -e /path/to/canon-systems
pytest
```

Tests cover: template rendering of hooks/rule/subagents, env file merging,
auth profile resolution, AWS secret string parsing, and version-drift
check logic (including the legacy pin-key fallback).
