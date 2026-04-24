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
| `CANON_STATE_API_URL` | Preferred client base for `canon checkpoint` / `canon resume`. |
| `STATE_API_URL` | Alias read by `canon memory-health` for the **state** row (first wins if both set). |

**Behavior (CLI ≥ 3.4.4):** If neither state URL is set but `KNOWLEDGE_API_URL` is set, **`CANON_STATE_API_URL` defaults to `KNOWLEDGE_API_URL`** after layered + Secrets hydration (`ensure_state_api_url_from_knowledge`). Dedicated `state-api` deployments can still set an explicit URL.

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
