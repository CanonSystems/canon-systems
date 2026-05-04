# Canon credentials and offline resilience — operator playbook

Use this when **each repo “forgets” how to reach Canon**, when **Cursor local vs cloud behave differently**, or when **network/AWS/memory backends are down** and you still need to preserve work.

For layered env order and cache TTL, see [MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md §1.2](MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md#12-layered-environment-where-urls-and-tokens-come-from). For first-time wiring, see [ONBOARDING.md](ONBOARDING.md).

---

## 1. Why credentials feel “lost” per repo

Canon is **not** one global login on your laptop. Resolution is **per git repository** plus **per AWS secret**:

| Layer | What goes wrong |
|--------|------------------|
| **Repo-local identity** | Each clone needs `.canon/memory-layer.local.env` with `COMPANY_ID`, `REPOSITORY_ID`, and scope for AWS (`MEMORY_LAYER_AWS_SECRET_NAME_PREFIX` or `MEMORY_LAYER_AWS_SECRET_ID`). New repo or new clone = run `canon setup` or `canon enable-repo` again from that root. |
| **AWS caller identity** | Hooks and CLI need valid credentials (`AWS_PROFILE`, SSO session, or env keys). A repo does not store AWS keys; if your profile expired, **every** repo fails until you refresh (`aws sso login`, etc.). |
| **Secrets Manager JSON** | URLs and bearer tokens often live **only** in the tenant secret. Nothing in git contains them. |
| **Client cache** | Decoded fields are mirrored to `~/.canon/memory-layer-aws-cache.json` and, after a successful AWS read, to **`<repo>/.canon/memory-layer.secrets.env`** (gitignored). The home cache is **durable** by default: `expires_at` does not drop the snapshot (so a short AWS outage or expired SSO does not leave you with empty memory URLs). To force a refetch after someone rotated the secret in AWS, run `canon doctor --fix-cache` and remove the repo mirror if you use it, or set `MEMORY_LAYER_AWS_CACHE_RESPECT_TTL=1` to opt into strict cache expiry. |
| **Cursor Cloud vs local** | A cloud agent runs in an environment that **does not see your Mac’s `~/.canon/`**. Each cloud workspace needs the same wiring steps (install `canon`, layered env, AWS access if applicable). Treat cloud as a **second machine**. |
| **Version drift** | Repo pin `CANON_SYSTEMS_VERSION` in `memory-layer.local.env` can make hooks warn or behave differently after upgrades. Run `pipx upgrade …` when the pin says you’re behind. |

**Fast recovery in a broken repo**

1. From repo root: `canon doctor` (or on older CLI: `canon preflight "wiring check"` then `canon memory-health --json`).
2. If secrets changed: `canon doctor --fix-cache`, then retry.
3. If still credential errors: `canon secrets` (wizard); use **copy from another wired repo** when the AWS secret already exists.
4. Full plug-and-play proof: `canon e2e-check --agent` → `"verdict": "PASS"`.

---

## 2. One clean branch line (local + GitHub)

Goal: **single default branch** (`main`) and **no long-lived local-only branches** unless they hold real unmerged work.

| Command | Purpose |
|---------|---------|
| `git fetch origin` | Update remote refs. |
| `git checkout main && git pull` | Sync default branch. |
| `git branch --merged main` | Lists branches whose tips are already contained in `main` (safe to delete with `git branch -d`). |
| `git branch -d <name>` | Delete **only** if Git reports “fully merged”. |

If Git says a branch is **not fully merged**, it still has unique commits. **Do not** `git branch -D` until you either merge/cherry-pick that work, push it to a backup ref (`git push origin <branch>`), or confirm the commits are obsolete.

**Cursor** shows local and remote branches from `.git`; deleting a **local** branch does not delete **remote** tracking branches until you `git push origin --delete <branch>` (only when the team agrees).

---

## 3. When the network or backends fail — what is already saved locally

These paths are **under the repo** (typically `.canon/memory/`) unless noted:

| Artifact | When it appears | What to do after recovery |
|----------|-------------------|---------------------------|
| `capture-failures.log` | `canon capture` could not persist a turn (non-2xx). | JSON lines include `request` + `response_status` + payload. After wiring works, inspect and optionally **replay** important turns manually (there is no automatic drain of this log today). |
| `capture-latest.json` | Last capture attempt (success or failure audit). | Diagnostic; not a guaranteed durable journal of all turns. |
| `mempalace-retry-queue.jsonl` | MemPalace `/memory/search` degraded or unreachable (see `memory_queue.py`). | Queue records for retry semantics (product direction may add drain tooling later). |
| `credential-recovery-needed.txt` | Set by the capture hook when AWS/secret errors persist after optional wizard. | Run `canon secrets` from this repo root; remove marker on next successful capture. |
| `pending-user-turn.json` | Used to pair user prompt with assistant reply for hooks. | Cleared after successful capture; if offline, pairing may be incomplete. |

**Practical offline habit:** For critical decisions while disconnected, keep a short **human-readable** note in repo `docs/` or your PM tool; rely on hooks for automatic capture only when `canon e2e-check --agent` passes.

**Future-friendly:** Product backlog items include explicit queue/drain paths for adapter failures; until then, treat **capture-failures.log** + **retry queue JSONL** as **evidence + optional manual follow-up**, not a guaranteed automatic ingest pipeline.

---

## 4. Ingest after outage (manual procedure today)

When AWS and memory APIs are healthy again:

1. `canon doctor --fix-cache` (or delete the cache file) so Secrets Manager values are fresh.
2. `canon e2e-check --agent` → PASS.
3. Re-run important structured captures with `canon capture` if you have saved payloads; otherwise use `canon capture` / normal Cursor turns going forward.
4. Optional: `canon capture --help` for hook-input patterns if replaying from saved JSON.

---

## 5. Related commands

- `canon ask "<question>"` — scoped canonical + MemPalace lookup when backends are up.
- `canon graph query …` — structural retrieval when axon is configured.
- `canon capture` — explicit artifact recording outside hooks.
