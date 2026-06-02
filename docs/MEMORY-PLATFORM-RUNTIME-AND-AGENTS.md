# Memory platform — runtime truth, global rule, and agents

**Single reference** for what must be true on a machine and in AWS for Canon memory + agents to behave as designed. For day-to-day workflow narrative, see [SYSTEM-WORKFLOW.md](SYSTEM-WORKFLOW.md). For install steps, see [ONBOARDING.md](ONBOARDING.md).

---

## 1. What must be true at runtime (complete checklist)

### 1.1 CLI and repo wiring

| Requirement | Why |
|-------------|-----|
| `canon` on `PATH` (typically via **pipx**) | All commands and hooks shell out to `canon`. |
| Installed **`canon-systems`** version **≥** repo pin `CANON_SYSTEMS_VERSION` in `.canon/memory-layer.local.env` | Hooks and `canon version-check` enforce this. |
| `.canon/memory-layer.local.env` exists with at least `COMPANY_ID`, `REPOSITORY_ID`, AWS scope for secrets | `canon setup` / `enable-repo` create this; Secrets Manager resolution depends on it. |
| `.cursor/` hooks + rules installed (`canon enable-repo` / setup) | Preflight/capture and Cursor rules. |
| Hooks **executable** (`memory-preflight.sh`, `memory-capture.sh`, …) | `canon e2e-check` validates `+x`. |

Per-repo credential confusion, Cursor Cloud vs local, clearing branch clutter, and offline artifacts are summarized in [CANON-CREDENTIAL-AND-OFFLINE-PLAYBOOK.md](CANON-CREDENTIAL-AND-OFFLINE-PLAYBOOK.md).

### 1.2 Layered environment (where URLs and tokens come from)

Hooks, `canon memory-health`, `canon e2e-check`, `canon graph`, and related commands merge **in order** (later layers do not override earlier non-empty keys where `setdefault` applies; see implementation in `src/canon_systems/shared.py`):

1. `~/.canon/canon-systems.env`
2. `~/.canon/canon-memory-layer.env`
3. `<repo>/.canon/memory-layer.team.env`
4. `<repo>/.canon/scoper-chat.env`
5. `~/.canon/memory-layer.secrets.env`
6. `<repo>/.canon/memory-layer.local.env`
7. `<repo>/.canon/memory-layer.secrets.env`

Then **AWS Secrets Manager** is applied (same keys), using the secret id derived from `MEMORY_LAYER_AWS_SECRET_NAME_PREFIX` + `COMPANY_ID` + `REPOSITORY_ID` (or `MEMORY_LAYER_AWS_SECRET_ID` override).

**Implication:** A key may exist **only** in Secrets Manager or only in `~/.canon/*.env` — that is valid.

### 1.2a URLs only in Secrets Manager (repo and dot-canon env look clean)

`KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, `MEMORY_ADAPTER_URL`, and related keys are often **only** in the AWS memory-layer secret — not in tracked source and not in `~/.canon/canon-systems.env`. After hydration, the CLI mirrors the decoded JSON in **`~/.canon/memory-layer-aws-cache.json`**. That file’s `expires_at` field is **not** a hard invalidation by default (see §1.2b); after a successful fetch the CLI also writes **`./.canon/memory-layer.secrets.env`** (gitignored) so each repo clone keeps a durable local copy of hydrated keys.

So a search for `http://` / `https://` **+ literal IPv4** in the git repo or in `~/.canon/*.env` may find **nothing**, while the **secret** (and cache) still point at a **temporary ECS task IP**. Fixing that means updating the secret payload in AWS (or your Canon infra pipeline) to stable hostnames (ALB/NLB + DNS), then clearing the client cache (§1.2b).

**Inspect what is actually in effect:**

- Open `~/.canon/memory-layer-aws-cache.json` and read the merged URL fields (or use the AWS console/CLI on `MEMORY_LAYER_AWS_SECRET_ID`).
- **`canon memory-health --json`** — works on **3.4.6+**; reports backend probe status for the resolved URLs.
- **`canon doctor`** (**≥ 3.4.7**) scans **standard Canon `.env` paths** for `http(s)://` + IPv4; it does **not** parse URL values out of the cache blob, so a secret-only task IP will **not** show up in `env_files_with_literal_ipv4_urls` until you put that URL in a layered file or change the secret. **`canon doctor --json`** also emits **`credential_attestation`** (AWS secret resolution + env precedence diagnostics — **no** secret payloads or tokens in stdout).

### 1.2b AWS Secrets Manager **client cache** (when to clear it)

After layered files are merged, `apply_canon_systems_secrets_from_aws()` may **cache** the decoded secret JSON on disk so hooks and CLIs do not call `GetSecretValue` on every turn.

| | |
|---|---|
| **Cache file** | `~/.canon/memory-layer-aws-cache.json` |
| **Expiry / TTL** | By default, `expires_at` in the cache file is **not** used to drop the snapshot. Cached URLs and tokens remain usable if AWS is temporarily unavailable (e.g. expired SSO session). Set `MEMORY_LAYER_AWS_CACHE_RESPECT_TTL=1` to restore strict “expired = miss” behavior. The `MEMORY_LAYER_AWS_CACHE_TTL_SEC` value (default **604800** / 7 days) only updates the metadata field written on each **successful** `GetSecretValue` fetch. |
| **Repo mirror** | After a successful fetch, the same key/value pairs are written to **`<repo>/.canon/memory-layer.secrets.env`** (gitignored, mode `600` on Unix). If this file is populated, the CLI uses it without attempting AWS by default; set `MEMORY_LAYER_AWS_FORCE_REFRESH=1` to bypass it and fetch fresh Secrets Manager values. If the home cache is used and this file is **missing or empty**, it is backfilled from the cache. Disable with `MEMORY_LAYER_AWS_DISABLE_REPO_MIRROR=1`. |
| **Disable reads** | Set `MEMORY_LAYER_AWS_DISABLE_CACHE=1` (or `true` / `yes`) |

**Clear the home cache when:** someone **rotated or replaced** the secret in AWS (new URLs, tokens, etc.) and you need the process to pick up the new values **immediately**—or delete **`<repo>/.canon/memory-layer.secrets.env`** if you rely on the repo mirror and need a clean re-hydration.

**Ways to clear:**

```bash
rm -f ~/.canon/memory-layer-aws-cache.json
```

**canon-systems ≥ 3.4.7:** `canon doctor --fix-cache` does the same delete (convenience wrapper). **`canon doctor` is not in 3.4.6** — use the `rm` command above on older installs.

**Related (3.4.7+):** `canon doctor` (without flags) compares `COMPANY_ID` / `REPOSITORY_ID` in `.canon/memory-layer.local.env` to the last `.canon/memory/context-latest.md` preflight snapshot, and flags `http(s)://` URLs that use a **literal IPv4** in **the scanned `.env` paths** (§1.2a — not values inside the cache JSON). On **3.4.6**, use `canon preflight`, **`canon memory-health --json`**, `canon e2e-check --agent`, and inspect the cache file or AWS for secret-only URLs.

### 1.2c Stable dev memory URLs — CSC `canon-systems` cutover and rollback

**Secret id (example):** `canon-memory-dev/memory-layer__csc__canon-systems` (derived from `MEMORY_LAYER_AWS_SECRET_NAME_PREFIX` + slugs for `COMPANY_ID=CSC` and `REPOSITORY_ID=canon-systems`).

**Multiple prefixes:** Repos may use **`canon-memory-dev`** or **`canon-systems-v2-dev`** (or another value) in `MEMORY_LAYER_AWS_SECRET_NAME_PREFIX`. **Every** tenant secret under **each** prefix must use the **same stable `https://` memory hostname** for the four URL keys. If one family of secrets still points at **ephemeral task IPs**, `canon memory-health` and **`canon e2e-check --agent`** will **FAIL** from machines that cannot route to those addresses (VPN/SG), even when onboarding and tenant IDs are correct — cut over **all** relevant `memory-layer__*` secrets for that prefix, then **`canon doctor --fix-cache`** on each laptop.

**Goal:** point `KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, `MEMORY_ADAPTER_URL`, and `CANON_STATE_API_URL` at the **same stable `https://` hostname** (ALB/NLB + DNS) instead of ephemeral task IPs. `MEMORY_ADAPTER_URL` may equal `KNOWLEDGE_API_URL` when **knowledge-api** mounts `POST /memory/search` on that base.

**Cutover (operator):**

1. **Infra:** Provision listener + target group + DNS/TLS in AWS (repo Terraform can model ECS **attachment** to an existing target group when `ecs_ingress_enabled`; ACM and Route53 records stay operator-owned). Apply or import the dev `ecs_baseline` stack as needed so the service registers with the target group.
2. **Secret:** Update the JSON secret in Secrets Manager so all four URL keys use the stable `https://` base (e.g. `canon secrets submit`, console, or `scripts/migrate_memory_secrets.py` with your domain).
3. **Clients:** Clear `~/.canon/memory-layer-aws-cache.json` or run **`canon doctor --fix-cache`** on every machine that had cached the old URLs.
4. **Validate:** `python scripts/validate_memory_endpoints.py --secret-id canon-memory-dev/memory-layer__csc__canon-systems --profile <profile>` and **`canon memory-health`**, **`canon e2e-check --agent`** from a wired repo.

**Rollback:** In Secrets Manager, restore the **previous secret version** (or re-apply known-good JSON), run **`canon doctor --fix-cache`** (or delete the cache file), then re-run `validate_memory_endpoints.py` and `canon memory-health`.

See also: [`infra/terraform/README.md`](../infra/terraform/README.md) (optional ECS ingress variables) and [`docs/migrations/cognito-ingress-migration.md`](migrations/cognito-ingress-migration.md).

### 1.3 Secrets payload (structured JSON or compatible `.env`)

**Required for `canon secrets submit` validation** (unless `--allow-partial`):  
`COMPANY_ID`, `REPOSITORY_ID`, `AWS_REGION`, `MEMORY_LAYER_AWS_SECRET_NAME_PREFIX`, `KNOWLEDGE_API_URL`, `KNOWLEDGE_WORKER_URL`, `MEMORY_ADAPTER_URL`, `SCOPE_ARTIFACT_BUCKET` — see `src/canon_systems/secrets_submit.py` (`_DEFAULT_REQUIRED_KEYS`).

**Universal client / hook tokens and URLs (typical secret keys):**

| Key | Role |
|-----|------|
| `KNOWLEDGE_API_URL` | Canonical / knowledge API base (no path; health at `/healthz`). |
| `KNOWLEDGE_WORKER_URL` | Worker base. |
| `MEMORY_ADAPTER_URL` | MemPalace adapter base (`POST {base}/memory/search`). When your stack does not run a separate memory-adapter process, the **knowledge-api** service may mount this route on the **same** base URL as `KNOWLEDGE_API_URL` (see `backend/knowledge-api/app/main.py`). |
| `CANON_HTTP_BEARER_TOKEN` | Shared bearer for HTTP where configured. |
| `SCOPE_ARTIFACT_BUCKET` | Artifact bucket name. |

**State plane (checkpoints / resume):**

| Key | Role |
|-----|------|
| `CANON_STATE_API_URL` | Preferred client base for `canon checkpoint` / `canon resume` / **`canon packet-archive`** / **`canon run-ledger`** / **`canon readiness check`** / **`canon task`** (server mode). |
| `CANON_TASKS_API_URL` | Optional override base for **`canon task`** only; if unset, **`CANON_STATE_API_URL`** is used. |
| `STATE_API_URL` | Alias read by `canon memory-health` for the **state** row (first wins if both set). |
| `CANON_EXPERIMENTAL_MULTILANE_ORCHESTRATION` | When set to `1` / `true` / `yes` / `on`, parent orchestrators may use **`canon resume --tasks-file ... --lanes`** for additive multilane visibility (`runnable_targets`, `active_targets`, `blocked_targets`, `task_threads`) per `memory-platform-build-discipline.mdc` §11. Does not change checkpoint schemas or merge-gate serial requirements. |

**state-api server env (packet/evidence archive + run ledger):**

| Key | Role |
|-----|------|
| `STATE_ARTIFACT_BUCKET` | S3 bucket for `POST /state/archive` durable bodies. |
| `STATE_ARCHIVE_KEY_PREFIX` | Prefix for archive keys (default `canon/packets`); keys remain SHA-256-addressed. |
| `STATE_RUN_LEDGER_TABLE_NAME` | DynamoDB table for **`PUT`/`GET` `/state/run-ledger`** rows (readiness/run history). Separate from **`STATE_TABLE_NAME`** (checkpoints/leases). If unset, run-ledger routes return **503**; checkpoint/archive behavior is unchanged. |
| `STATE_TASKS_TABLE_NAME` | DynamoDB table for **`POST`/`GET` `/state/tasks`** (assignable-task event plane, **canon-systems ≥ 3.7.0**). Separate from checkpoint and run-ledger tables. If unset, task routes return **503** `tasks_table_unset`; other state-api routes unchanged. |

**Assignable tasks (client, ≥ 3.7.0):** `canon task` uses **`CANON_STATE_API_URL`** (or **`CANON_TASKS_API_URL`**) as the server when set; reads fold the server event stream, writes push events first, local NDJSON is cache. **`canon task next`** is the agent “what's next?” entrypoint. Operator deploy: [`docs/runbooks/TASKS-SERVER-DEPLOY.md`](runbooks/TASKS-SERVER-DEPLOY.md).

**Behavior (CLI ≥ 3.4.4):** If neither state URL is set but `KNOWLEDGE_API_URL` is set, **`CANON_STATE_API_URL` defaults to `KNOWLEDGE_API_URL`** after layered + Secrets hydration (`ensure_state_api_url_from_knowledge`). Dedicated `state-api` deployments can still set an explicit URL.

**Run ledger vs archive vs checkpoint vs readiness (boundary):**

- **`POST /state/archive`** and **`canon packet-archive`** write **object bytes** to **`STATE_ARTIFACT_BUCKET`** and emit **`packet_archived`** (metadata-only allowlist in `packet_archived_event_payload` — no bodies or credential-shaped keys).
- **`PUT /state/run-ledger`** stores **structured ledger records** in **`STATE_RUN_LEDGER_TABLE_NAME`**. `archive_refs` hold **pointers** (e.g. `s3_uri`, `s3_key`, `content_sha256`, `artifact_kind`)—validators reject body-like fields so DynamoDB never holds packet bodies.
- **Checkpoints/leases** stay on **`STATE_TABLE_NAME`** with **`lease_token`** and optimistic **`state_version`**; the ledger does not participate in lease acquisition or checkpoint writes.

CLI: **`canon run-ledger`** validates JSON, optionally merges archive metadata arrays into `archive_refs`, and **`PUT`**s to `state-api` (or **`--dry-run`**). **`canon readiness check`** performs **read-only `GET`** `/state/run-ledger`, builds an interchange JSON snapshot (stdout / optional **`--output`**), maps **existing** `validation_outcomes` / commit / PR / deployment slots from the ledger **without new normalization or attestation rules**, and verifies required phase **`archive_refs` only** (no packet body reads). Policy remains **`canon qa-validate`**, **`canon flow-audit`**, and release-orchestrator checks; **`canon readiness check`** is diagnostic (exits **`0`** ready, **`1`** not ready, **`2`** usage or query error).

**Graph plane (Axon):**

| Key | Role |
|-----|------|
| `AXON_SERVICE_URL` | **Client** base for `canon graph *` and `memory-health` **graph** row (`/healthz` probe). |
| `AXON_SERVICE_TOKEN` | Bearer for `canon graph query` / `impact` / `index` to axon-service. |

**Server-side (axon-service process only — not necessarily in the same developer secret):**  
`AXON_S3_BUCKET`, `AXON_META_TABLE_NAME`, `AXON_AWS_REGION`, `AXON_SERVICE_TOKEN` (must match what clients send). See `backend/axon-service/README.md`.

### 1.4 Health vs usefulness

| Check | Meaning |
|-------|---------|
| `canon memory-health` **overall `ok`** | Default **required** backends are **canonical** + **mempalace**. **State** and **graph** are **optional** for overall status unless you set `CANON_MEMORY_HEALTH_REQUIRED` or `--required`. |
| **Graph row `ok`** | `AXON_SERVICE_URL` set and `/healthz` returns success — **service is up**. |
| **Graph *useful* for agents** | Someone has run **`canon graph index`** (or CI/hook) for the **commit** agents pass to `canon graph query`. Without an index, query may succeed but return **empty** results. |

### 1.5 Quick verification commands

- `canon e2e-check --agent` — wiring + pin + required memory backends; exit **0** iff `"verdict": "PASS"`.
- `canon memory-health` — full four-backend JSON (canonical, mempalace, state, graph).
- `canon graph reindex-status --commit-sha <sha> ...` — whether a snapshot exists for that commit.

---

## 2. Global retrieval rule (Cursor)

**Authoritative text:** `src/canon_systems/templates/rules/memory-layer-defaults.mdc` → section **`## Retrieval policy (required)`**.

**Order for coding work:** **`graph → state → canonical → file`**

- **Graph:** `canon graph query` / `canon graph impact` (axon-service).
- **State:** `canon checkpoint read` / write + leases.
- **Canonical:** `.canon/memory/context-latest.md`, `canon ask`.
- **File:** only after evidence from above, or when the user explicitly requires paths.

**Fail-open:** If Axon is unset or errors (CLI exit 2/3/4/5), continue with **`state → canonical → file`** and record degradation (e.g. in HANDOFF notes / telemetry).

Every wired repo should install this rule via `canon setup` / `enable-repo` (user + repo copies).

---

## 3. Per-agent templates (what each file emphasizes)

Templates live under `src/canon_systems/templates/agents/`. Installed into `.cursor/agents/` (and user scope) by enable-repo.

| Agent | Retrieval / memory | Checkpoint (`state-api`) | Graph CLI spelled in template? | `retrieval_breakdown` telemetry |
|-------|--------------------|---------------------------|--------------------------------|----------------------------------|
| **project-planner** | **Canonical first** (`canon ask`, context-latest, files) — see [PROJECT-PLANNER-RETRIEVAL-RATIONALE.md](PROJECT-PLANNER-RETRIEVAL-RATIONALE.md) | References downstream checkpoint **contract** for tasks; planner does not run checkpoint HTTP itself | No (by design) | Not required in template body |
| **scoper** | Graph-first + policy link; fail-open | Read/write + leases | Yes (`canon graph query`) | Yes |
| **cursor-pilot** | Graph-first + impact; fail-open | Read/write + leases | Yes (query + impact) | Yes |
| **implementer** | Graph-first; fail-open | Read/write + leases | Yes | Yes |
| **qa-gate** | Memory + repo evidence; inherits workspace **policy** for coding | Read/write + leases | Via global rule + telemetry buckets | Yes (graph bucket may be zero) |
| **release-orchestrator** | Governance + capture | Read/write + leases | Via global rule when doing repo work | Yes |

**Note:** **qa-gate** and **release-orchestrator** focus their prose on verification / release; they still participate in the **four-bucket telemetry** contract and **checkpoint** plane. **Graph-first** for *their* work is enforced by the **installed** `memory-layer-defaults.mdc`, not by repeating every line in each template.

---

## 4. Related documentation

| Doc | Contents |
|-----|----------|
| [SYSTEM-WORKFLOW.md](SYSTEM-WORKFLOW.md) | Validation commands, graph/index invariants, living spec |
| [ONBOARDING.md](ONBOARDING.md) | Setup wizard, secrets, first-run |
| [ROADMAP.md](ROADMAP.md) | Future work (e.g. AWS naming debt) |
| [PROJECT-PLANNER-RETRIEVAL-RATIONALE.md](PROJECT-PLANNER-RETRIEVAL-RATIONALE.md) | Why planner is not graph-first |
| `backend/axon-service/README.md` | Axon service env, endpoints |
| `README.md` | CLI table, high-level platform overview |

---

## 5. Living update checklist

When you change retrieval rules, runtime keys, or agent contracts, update **in the same change**:

1. `src/canon_systems/templates/rules/memory-layer-defaults.mdc`
2. Affected agent templates under `src/canon_systems/templates/agents/`
3. **This file** (`docs/MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md`)
4. `docs/SYSTEM-WORKFLOW.md` and `README.md` where behavior is operator-visible
5. Tests under `tests/` that enforce template/policy text
6. `CHANGELOG.md`
