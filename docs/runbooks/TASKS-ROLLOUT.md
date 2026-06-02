# Runbook: rolling out `canon task` (auto-update + auto-config)

This runbook explains how the `canon task` feature (shipped in **3.6.0**)
reaches every machine, repo, and user **without manual per-repo steps**. It
leans entirely on the existing Canon self-update + auto-rewire machinery; the
only release action is publishing the new version.

## Server-authoritative tasks (3.7.0+)

After **3.7.0**, assignable tasks can live in **state-api** (instant sync across
machines). That requires a one-time **operator deploy** (DynamoDB table +
`STATE_TASKS_TABLE_NAME` on state-api) and a **`canon task sync`** backfill.
See **[`TASKS-SERVER-DEPLOY.md`](TASKS-SERVER-DEPLOY.md)**.

## TL;DR — what an operator does

1. Land this change on `main` and tag/publish **canon-systems 3.6.0** to the
   private install source (the GitHub repo that `pipx install
   git+ssh://...@github.com/CanonSystems/canon-systems.git` pulls from).
2. Nothing else. Every machine auto-upgrades and every wired repo auto-configures
   on the next Canon interaction (see below).

## How auto-update reaches each **machine/user**

`canon`'s entrypoint calls `try_self_update(argv)` near the top of every
invocation (`src/canon_systems/self_update.py`):

- If `canon` is running from its **pipx** venv, it runs `pipx upgrade
  canon-systems`, compares the installed version before/after, and — when the
  version increased — **re-execs** `canon` with the same args on the upgraded
  code.
- Throttled to once per `CANON_SYSTEMS_SELF_UPDATE_INTERVAL_SEC` (default 6h).
- Skipped when `CANON_SYSTEMS_SKIP_SELF_UPDATE=1` or `CI=1`.

So the *first* Canon interaction on a machine after 3.6.0 is published upgrades
the CLI in place. The user does nothing.

## How auto-config reaches each **repo**

Once the installed version is newer than a repo's pinned version
(`CANON_SYSTEMS_VERSION` in `.canon/memory-layer.local.env`), the CLI runs:

- `_maybe_auto_rewire(root, command)` — re-runs `enable_repo()` for the current
  repo, and
- `_maybe_auto_rewire_all(command)` — once per installed version, refreshes the
  user-scope `~/.cursor/` tree and every wired repo found under
  `CANON_SYSTEMS_REWIRE_ROOTS` (default `~/localwork`, depth 3).

`enable_repo()` (and `install_user_scope()`) now also install the task feature's
config, so a rewire delivers everything the feature needs:

- hook script `.cursor/hooks/task-preflight.sh` (open-tasks surfacing),
- its registration in `.cursor/hooks.json` under `beforeSubmitPrompt`
  (idempotent merge, deduped by command),
- the agent rule `.cursor/rules/canon-tasks.mdc`,
- a re-pin of `CANON_SYSTEMS_VERSION=3.6.0`.

The `canon task` command itself ships in the package, so the CLI upgrade alone
makes it available; the rewire only adds the *surfacing hook* and *agent rule*.

### Trigger summary

| Layer | Mechanism | Trigger |
|---|---|---|
| CLI binary (machine/user) | `try_self_update` → `pipx upgrade` + re-exec | Any `canon` call (throttled 6h) |
| Current repo config | `_maybe_auto_rewire` → `enable_repo` | installed `>` pinned |
| All wired repos + user scope | `_maybe_auto_rewire_all` → `enable_repo`/`install_user_scope` | once per installed version |

## Verifying the rollout on a machine

```bash
canon --version                     # expect 3.6.0+
canon task --help                   # command present
canon task create "smoke test" --json && canon task list --mine
ls .cursor/hooks/task-preflight.sh  # surfacing hook installed
grep CANON_SYSTEMS_VERSION .canon/memory-layer.local.env   # re-pinned to 3.6.0
```

## Opt-outs / env knobs

| Variable | Effect |
|---|---|
| `CANON_SYSTEMS_SKIP_SELF_UPDATE=1` | Don't pipx-upgrade on Canon calls. |
| `CANON_SYSTEMS_DISABLE_AUTO_REWIRE=1` | Don't re-run `enable_repo` on version bump. |
| `CANON_SYSTEMS_DISABLE_GLOBAL_REWIRE=1` | Don't scan/rewire other repos. |
| `CANON_SYSTEMS_REWIRE_ROOTS` | Override scan roots (os.pathsep-separated). |
| `CANON_TASKS_PREFLIGHT=0` | Silence the open-tasks surfacing hook. |
| `CANON_TASKS_HOME` | Override the machine-global tasks dir. |
| `CANON_TASKS_BUCKET` / `CANON_TASKS_PREFIX` | Enable S3 cross-machine sync. |

## Manual fallback (only if auto-update is disabled)

```bash
pipx upgrade canon-systems            # or: pipx install --force git+ssh://...
canon enable-repo                     # re-wire the current repo explicitly
```

## Cross-machine task sharing (optional, for company/multi-repo tasks)

Repo-scoped tasks already sync via git (the ledger is committed with the repo).
For `company` / `multi-repo` tasks to span machines, configure an S3 bucket and
run `canon task sync` (e.g. from a periodic job or before `canon task list`):

```bash
export CANON_TASKS_BUCKET=canon-tasks-acme
export CANON_TASKS_PREFIX=canon/tasks          # optional, this is the default
canon task sync                                # set-union push/pull, idempotent
```

`sync` is a set-union of `event_id`s, so it is safe to run concurrently from
many machines; conflicting edits resolve deterministically by event timestamp.
