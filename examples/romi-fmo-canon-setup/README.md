# Romi — Canon Systems one-shot setup (FMO / Family One)

Hand this folder to Romi (zip it, including `romi-credentials.env`). **Do not** email
credentials in plain text; use 1Password or similar.

## What you get

- **canon-systems** CLI **3.7.1+** (install/upgrade via `pipx upgrade canon-systems`)
- AWS IAM user **`memory-layer-romi`** → profile **`memory-layer-romi`**
- Tenant **`FMO`** with Secrets Manager prefix **`canon-systems-v2-dev`**
- Three repos wired for shared memory:

| Product / app | GitHub repo | `REPOSITORY_ID` (use detected default) |
|---------------|-------------|----------------------------------------|
| go.showtrail.app | `familyoneInc/go.showtrail.website` | `github.com/familyoneInc/go.showtrail.website` |
| familyonebackend | `familyoneInc/familyonebackend` | `github.com/familyoneInc/familyonebackend` |
| familyone-admin-backend | `familyoneInc/familyone-admin-backend` | `github.com/familyoneInc/familyone-admin-backend` |

AWS secrets already exist for all three under `canon-systems-v2-dev/memory-layer__fmo__*`.

## Prerequisites (Ed confirms before handoff)

1. GitHub SSH works: `ssh -T git@github.com`
2. Romi is in **CanonSystems** org (for `pipx install git+ssh://.../canon-systems.git`)
3. Romi can clone **familyoneInc** repos
4. macOS or Linux with Python 3.10+

## Quick path (terminal)

```bash
cd /path/to/romi-fmo-canon-setup
chmod +x install-and-wire.sh
./install-and-wire.sh
```

Clone repos first if needed:

```bash
git clone git@github.com:familyoneInc/go.showtrail.website.git
git clone git@github.com:familyoneInc/familyonebackend.git
git clone git@github.com:familyoneInc/familyone-admin-backend.git
```

Set `REPO_SHOWTRAIL`, `REPO_FAMILYONEBACKEND`, `REPO_FAMILYONE_ADMIN` in
`romi-credentials.env` if clones are not siblings of `canon-systems/examples/`.

## Verify

In each repo root:

```bash
canon doctor
canon e2e-check --agent   # expect verdict PASS
canon ask "what was decided recently in this repo?"
canon task list --mine    # tasks assigned to / authored by you
```

Tasks are **automatic** in wired repos: Cursor hooks refresh active work, link
memory captures to the active `task_ref`, and sync via state-api when secrets
include `CANON_STATE_API_URL`. Create work for Edward with
`canon task create "..." --assignee usr_new.moon3461`.

## Cursor one-shot

Open this folder in Cursor and run the prompt in **`CURSOR_ONE_SHOT_PROMPT.md`**.

## Security

- Keys live only in `romi-credentials.env` (gitignored).
- After setup succeeds, Romi may delete `romi-credentials.env`; keys remain under
  `~/.aws/credentials` profile `[memory-layer-romi]`.
- Rotate keys in IAM if this package was exposed.
