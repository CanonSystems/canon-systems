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
2. **A way to install CLI tools.** **Recommended:** `pipx` (keeps canon-systems
   isolated, puts `canon` on PATH reliably). Check: `pipx --version`. If missing:
   - macOS: `brew install pipx && pipx ensurepath`
   - Linux: `python3 -m pip install --user pipx && python3 -m pipx ensurepath`
   - Then restart your shell so `pipx` is on PATH.
   **Also works:** `pip3 install ...` (see [§1b](#1b-alternative-pip-or-pip3-user-install)
   below) — install succeeds but you must add Python's *user scripts* directory
   to PATH; macOS does not do this by default.
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

If pipx installs but `canon` isn't found, see [§1c](#1c-after-pipx-canon-not-on-path)
below.

To upgrade later when Ed pushes a new commit:

```bash
pipx upgrade canon-systems
# or to force a fresh pull from the git repo:
pipx install --force git+ssh://git@github.com/CanonSystems/canon-systems.git
```

### 1b. Alternative: pip or pip3 (user install)

If you ran something like:

```bash
pip3 install git+ssh://git@github.com/CanonSystems/canon-systems.git
```

the package **installed correctly**. Pip prints a warning because the
`canon` executable landed in Python's **user script directory**, which is
often **not** on your `PATH` (especially on macOS).

Find that directory (works on any OS):

```bash
python3 -m site --user-base
```

The scripts live in `<that-output>/bin`. For example, on macOS with
Python 3.13 you often get:

`/Users/you/Library/Python/3.13/bin`

**Fix — add it to PATH** (zsh on macOS, append to `~/.zshrc`):

```bash
export PATH="$(python3 -m site --user-base)/bin:$PATH"
```

Then `source ~/.zshrc` (or open a new terminal) and verify:

```bash
command -v canon
canon --version
```

**Why we still recommend pipx:** upgrades are one command
(`pipx upgrade canon-systems`), and you avoid sharing one Python
environment with unrelated packages. `pip3 install --user` is fine if
you understand PATH and upgrade with
`pip3 install --upgrade git+ssh://git@github.com/CanonSystems/canon-systems.git`.

### 1c. After pipx: `canon` not on PATH

`pipx` installs the `canon` binary into **`~/.local/bin`**. Homebrew's
`pipx` formula runs `pipx ensurepath`, which tries to append that directory
to your shell config — but **you must open a new terminal tab** (or
`source` the right file) before `canon` works. The installer often prints
`~/.bashrc`; on macOS with **zsh** (default), use **`~/.zshrc`** instead.

**Quick fix for the current terminal only:**

```bash
export PATH="$HOME/.local/bin:$PATH"
canon --version
```

**Permanent fix (zsh on macOS):**

```bash
grep -q '\.local/bin' ~/.zshrc 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
command -v canon && canon --version
```

If `~/.zshrc` does not exist yet, create it with the `echo ... >>` line
above, then `source ~/.zshrc`.

Still stuck? Run `pipx ensurepath` again and read what file it says it
edited — open that file and confirm a line containing `.local/bin`
appears.

### 1d. Switching from `pip3 install` to pipx (optional)

If you previously installed with `pip3`, remove it so only pipx owns the
package (avoids two different `canon` binaries on PATH):

```bash
pip3 uninstall canon-systems -y
```

Run that **as its own line** (do not paste other commands on the same
line). Then install with pipx as in [§1](#1-install-the-cli).

If you ever see pip complain `Invalid requirement: '#'`, you almost
certainly pasted **multiple commands at once into a single `pip` /
`pip3` line**, or a comment character ended up where pip expected a
package name. Run **one command per paste**, one line at a time.

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

**Before the questions:** if you installed with **pipx**, `canon setup`
runs `pipx upgrade canon-systems`. When a **newer version** is pulled from
git, the process **restarts** so the rest of setup uses that build (and
writes the matching version pin). To turn this off (pinned CI images,
air-gapped machines): `export CANON_SYSTEMS_SKIP_SELF_UPDATE=1` first, or
rely on `CI=true` which also skips the check.

You'll be prompted interactively. **What each prompt means:**

| Prompt | Meaning | What to enter |
|---|---|---|
| **Company ID** | Tenant id sent to the memory APIs (`X-Company-Id`) and used in the Secrets Manager secret name. | Your company slug, e.g. `IMC` or `FMO` — must match how secrets were created in AWS. |
| **AWS credentials profile** | A **local nickname on your Mac** for which saved keys to use. It becomes the section header in `~/.aws/credentials`, e.g. `[memory-layer-edward]`. It is **not** your AWS console username, **not** your account email, and **not** the access key. | Type any label you like (often something you already use). If keys are already in that profile, you can skip pasting keys below. |
| **AWS region** | Region for Secrets Manager and boto3. | Usually `us-east-1` unless the secrets live elsewhere. |
| **REPOSITORY_ID** | Stable id for *this* repo (memory is scoped per company + repo). | **Best:** press Enter to use the value shown as *Detected REPOSITORY_ID* (from `git remote get-url origin`) — avoids collisions with another repo also named `innermost`. **OK:** a short name like `innermost` only if the AWS secret was provisioned for that exact id. |
| **Secrets name prefix** | First path segment of the secret in Secrets Manager. The full id is `{prefix}/memory-layer__{company}__{repo}` (slugified). This is an **AWS namespace**, not the `canon-systems` CLI version. | Press Enter for the suggested default (`canon-memory-dev` for new work). If your secrets still live under the legacy path, type **`canon-systems-v2-dev`** (or whatever Ed put in `company-registry` for your company). |
| **AWS keys** (optional) | Writes long-lived keys into `~/.aws/credentials` for the chosen profile. | Paste keys, or press Enter twice to skip if you use SSO / keys already in that profile. |

After you answer **Secrets name prefix**, setup prints the **exact**
secret name it will request from AWS. Open the AWS console and confirm
that secret exists in the chosen region; if not, fix `REPOSITORY_ID` or
prefix and re-run `canon setup`, or set `MEMORY_LAYER_AWS_SECRET_ID` in
`.canon/memory-layer.local.env` to the full secret id.

`canon setup` does everything in one go:

1. Writes `~/.aws/credentials` with your keys under the profile you
   named (if you pasted keys). If that profile name already exists, it
   is overwritten for that profile only.
2. Writes `~/.aws/config` with the region for that profile.
3. Writes `~/.canon/canon-systems.env` with `AWS_PROFILE=<that profile>`.
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
any repo. That command runs the same **pipx self-update** step first.)


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
AWS_PROFILE=<your-setup-profile> aws sts get-caller-identity
```

Use the same profile name you chose during setup (e.g.
`memory-layer-edward` or `canon-systems`). You should see a JSON
response with an `Arn` matching the IAM user Ed
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
   on the `canon-memory-dev/...` or legacy `canon-systems-v2-dev/...`
   secrets. Tell Ed — this is an
   IAM policy problem, not your problem.
2. Wrong region. Most dev secrets are in `us-east-1`. Check
   `~/.aws/config` for the `[profile canon-systems]` section.
3. Wrong secret prefix. New default is `canon-memory-dev`; legacy is
   `canon-systems-v2-dev`. If Ed told
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
