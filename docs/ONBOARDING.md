# Onboarding — Canon Systems

This doc walks a new team member through getting `canon` installed, wired
to the shared AWS backend, and capturing memory in their first repo. If
you're following this, Ed has already given you an IAM access key pair
and access to the `CanonSystems` GitHub org.

End state after this doc:

- `canon --version` works on your machine.
- You have AWS credentials set up under a dedicated `canon-systems`
  profile (not mixed with your personal AWS).
- One real repo is wired: every Cursor prompt hydrates context, every
  assistant turn gets captured to shared AWS memory, segregated by
  repository.
- Your captures are tagged with your own `actor_id` (derived from your
  git email), so we can tell your work apart from each other's.

Estimated time: 10 minutes on a machine that already has Python + git.

---

## 0. Prerequisites

You need:

1. **Python 3.10 or newer.** Check: `python3 --version`.
2. **pipx.** Check: `pipx --version`. If missing:
   - macOS: `brew install pipx && pipx ensurepath`
   - Linux: `python3 -m pip install --user pipx && python3 -m pipx ensurepath`
   - Then restart your shell so `pipx` is on PATH.
3. **An SSH key on GitHub** associated with the account Ed added to the
   `CanonSystems` org. Test with `ssh -T git@github.com` — it should
   greet you by your GitHub username.
4. **Your IAM access key pair** from Ed. Two strings: `AWS_ACCESS_KEY_ID`
   (starts with `AKIA`) and `AWS_SECRET_ACCESS_KEY`. Treat them like
   passwords.

If any of those are missing, stop and ask Ed before continuing.

---

## 1. Install the CLI

```bash
pipx install git+ssh://git@github.com/CanonSystems/canon-systems.git
```

Verify:

```bash
canon --version
# canon-systems 3.0.0  (or later)
```

If pipx installs but `canon` isn't found, run `pipx ensurepath`, restart
your shell, and try again. On macOS with Apple Silicon, pipx may install
into `~/.local/bin` — make sure that's on your PATH.

To upgrade later when Ed pushes a new commit:

```bash
pipx upgrade canon-systems
# or to force a fresh pull from the git repo:
pipx install --force git+ssh://git@github.com/CanonSystems/canon-systems.git
```

---

## 2. Make sure your git identity is set per machine

Your `actor_id` in canon-systems is derived from your git email. Each of
us has a different email, so this is how memory captures get correctly
attributed to you vs. Ed vs. the others.

```bash
git config --global user.email "you@yourdomain.com"
git config --global user.name "Your Name"
```

Use the same email you use for your GitHub account. If you want a
specific actor_id independent of git, you can override it later via
`CANON_ACTOR_ID=usr_yourname` in `.canon/memory-layer.local.env`, but
the default is fine.

---

## 3. Pick your first repo and run setup

Pick a real repo you work in — ideally one you'll use with Cursor. From
its root:

```bash
cd /path/to/your-repo
canon setup
```

You'll be prompted interactively. Here's what to enter:

| Prompt | What to enter |
|---|---|
| `Company ID` | `FMO` (unless Ed tells you a different one for this repo) |
| `AWS profile name` | Press Enter to accept `canon-systems` |
| `AWS region` | `us-east-1` (unless Ed says otherwise) |
| `REPOSITORY_ID` | Press Enter — it auto-detects from the git remote |
| `Secrets name prefix` | `canon-systems-v2-dev` (again, Ed confirms if different) |
| `AWS_ACCESS_KEY_ID` | Paste your `AKIA...` key here |
| `AWS_SECRET_ACCESS_KEY` | Paste your secret key (hidden when typing) |

`canon setup` does everything in one go:

1. Writes `~/.aws/credentials` with your keys under a `[canon-systems]`
   profile. (If you already have an AWS profile by that name, it will
   overwrite it — tell Ed if that's a problem for you and use a
   different profile name during the prompts.)
2. Writes `~/.aws/config` with the region for that profile.
3. Writes `~/.canon/canon-systems.env` with `AWS_PROFILE=canon-systems`.
4. Writes `<repo>/.canon/memory-layer.local.env` with `COMPANY_ID`,
   `REPOSITORY_ID`, `AWS_REGION`, and `MEMORY_LAYER_AWS_SECRET_NAME_PREFIX`.
5. Installs user-level Cursor rules and subagents (`~/.cursor/rules/`,
   `~/.cursor/agents/`) so every repo gets the auto-setup prompt on
   first use and has `scoper`, `cursor-pilot`, `qa-gate` available.
6. Installs per-repo Cursor hooks + rule + subagents into `.cursor/`
   in this repo and pins the canon-systems version for drift detection.

You end with `Enabled canon-systems in /path/to/repo` as the final
line. No second command needed.

(If you ever want to re-install just the per-repo pieces without
redoing the credentials step, run `canon enable-repo` on its own in
any repo.)

---

## 4. Verify the setup works

Three quick checks.

**4a. Version pin is in place.**

```bash
canon version-check
# canon-systems: version ok (3.0.0 >= pinned 3.0.0)
```

**4b. AWS credentials resolve and your profile works.**

```bash
AWS_PROFILE=canon-systems aws sts get-caller-identity
```

You should see a JSON response with an `Arn` matching the IAM user Ed
created for you. If this fails, the keys are wrong — re-run `canon setup`
or check `~/.aws/credentials`.

**4c. A memory query against the backend returns something (even if empty).**

```bash
canon ask "what has been done in this repo so far?"
```

If the repo is brand new to canon-systems, this returns an empty/short
result — that's fine. What you want to see is: *no error message* and
*a structured response*. An error like "AWS Secrets Manager fetch
failed" or "connection refused" means something is wrong; see
Troubleshooting below.

---

## 5. What happens now

Open the repo in Cursor. From this point:

- **Before every user prompt**, the `memory-preflight.sh` hook hydrates
  `.canon/memory/context-latest.md` with prior work from AWS memory.
  The agent is instructed (via `.cursor/rules/memory-layer-defaults.mdc`)
  to read it first.
- **After every assistant response**, the `memory-capture.sh` hook
  captures the turn to AWS memory, tagged with your `actor_id`, this
  repo's `repository_id`, and this company's `company_id`.
- **When asking the agent a question about prior work**, it can run
  `canon ask "..."` itself on the fly — it's baked into the rule.
- **For non-trivial tasks**, you (or the agent) can invoke the
  `scoper` → `cursor-pilot` → `qa-gate` subagent chain via `/spq` or
  by explicit parent-agent orchestration.

You don't need to do anything further for this to work. It's passive
after setup.

---

## 6. Per-machine repeat

Every new machine you use canon-systems on needs steps 1 and 3 (install
the CLI, run `canon setup` in each repo you want wired). The AWS keys
go on each machine's `~/.aws/credentials`; don't share the file across
machines over the network.

Every new repo you want wired needs `canon setup` (for the credentials
and IDs) and `canon enable-repo` (for the hooks and subagents). If
you're already set up on the machine and the repo already has
`.canon/memory-layer.local.env`, the auto-setup rule will tell Cursor
to prompt you on the first substantive prompt — just answer `y`.

---

## Troubleshooting

**`canon: command not found` after `pipx install`.**
Run `pipx ensurepath`, then restart your shell. On macOS, verify
`~/.local/bin` is in your PATH.

**`git+ssh://git@github.com/CanonSystems/canon-systems.git` fails with
permission denied.**
Your GitHub SSH key isn't set up or Ed hasn't added you to the
`CanonSystems` org with read access. Test with `ssh -T git@github.com`
first. If that works but pipx still fails, check that your SSH agent
has your key loaded: `ssh-add -l`.

**`canon ask "..."` says "AWS Secrets Manager fetch failed".**
Most common causes, in order:

1. The IAM user doesn't have `secretsmanager:GetSecretValue` permission
   on the `canon-systems-v2-dev/...` secrets. Tell Ed — this is an
   IAM policy problem, not your problem.
2. Wrong region. `canon-systems-v2-dev` lives in `us-east-1`. Check
   `~/.aws/config` for the `[profile canon-systems]` section.
3. Wrong secret prefix. Default is `canon-systems-v2-dev`. If Ed told
   you something else, edit
   `<repo>/.canon/memory-layer.local.env` and fix
   `MEMORY_LAYER_AWS_SECRET_NAME_PREFIX`.

**`canon version-check` says "installed version X is older than pinned Y".**
Run `pipx upgrade canon-systems`. The hooks surface this as a
`systemMessage` in Cursor too, and the agent is instructed to offer
the upgrade.

**Cursor hook shows no effect.**
Check that `.cursor/hooks.json` in the repo has a `beforeSubmitPrompt`
entry for `bash .cursor/hooks/memory-preflight.sh`. If missing, run
`canon enable-repo` again. Restart Cursor to reload the hook config.

**`AWS_PROFILE=canon-systems aws sts get-caller-identity` returns
`InvalidClientTokenId`.**
The keys are wrong or typo'd. Re-run `canon setup` and re-paste
carefully. If it still fails, ask Ed to rotate your key and try the
new one.

---

## What not to do

- **Do not commit `.canon/*.env` files.** They contain repo IDs and the
  AWS secret prefix. Before your first commit in a newly-wired repo,
  add this line to the repo's `.gitignore`:

  ```
  .canon/
  ```

  `.canon/memory/` in particular contains hydrated conversation context
  that should never leave your machine. If your team wants to share a
  `.canon/team-identities.json` file (tracked) while ignoring the rest,
  use a more specific pattern like `.canon/memory/` and
  `.canon/*.local.env`.
- **Do not share your IAM keys** with anyone, including other people on
  this team. Each of us has our own. If yours leaks, tell Ed
  immediately — he'll rotate it.
- **Do not publish this repo or its install URL publicly.** It's
  proprietary; the install path relies on GitHub org membership as the
  access control. See the Distribution section in the root `README.md`.
- **Do not close the terminal before `canon setup` finishes.** It writes
  credentials, then installs hooks. If it's interrupted partway, run
  `canon setup` again (safe — it overwrites the same files) or
  `canon enable-repo` on its own to finish the hook install.

---

## Getting help

Ask Ed. In the future this will be self-serve (a real support channel,
maybe a status page for the AWS backend), but for now there are three
of us and a direct message is faster than any process.
