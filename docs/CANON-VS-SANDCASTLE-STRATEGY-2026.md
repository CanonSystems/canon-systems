# Canon-systems vs Sandcastle — strategy (May 2026)

**Purpose:** Clarify how Canon compares with [Sandcastle](https://github.com/mattpocock/sandcastle), where the products overlap, and how Canon should respond without collapsing its differentiation.

## Short answer

**Canon-systems and Sandcastle operate at different layers.**

- **Sandcastle** is an **agent orchestration and sandbox runtime**: worktrees, isolated execution, provider abstraction, and branch/merge handling for coding agents.
- **Canon-systems** is an **enterprise memory and workflow operating system** for AI-assisted software delivery: tenant-scoped memory, governed agent phases, checkpoints, QA gates, audit events, and optional backend planes.

They overlap in agentic coding, but they are **not the same product shape**. Sandcastle is closer to a **builder substrate**; Canon is closer to an **operator platform**.

**May 1, 2026 update:** Canon has validated an AWS ECS/Fargate -> Cursor SDK cloud execution path against the Canon repo, including a read-only run and a write-path run that created a branch, commit, and PR. That means Canon no longer needs to answer Sandcastle only with an abstract future runtime plan. The immediate response is to make Cursor SDK the first reference runtime adapter and wrap it in Canon's governance/evidence model.

## What Sandcastle appears to be

From the public repo as of **April 30, 2026**, Sandcastle presents itself as:

- a **TypeScript library** for orchestrating AI coding agents
- with **isolated sandboxes** via **Docker**, **Podman**, and **Vercel**
- with primitives like **`run()`**, **`createSandbox()`**, and **`createWorktree()`**
- oriented toward **parallel AFK agents**, **review pipelines**, and custom orchestration

This is a strong abstraction for teams who want to **build their own agent workflow product** or internal automation layer.

## What Canon is, in contrast

Canon already implements a much larger opinionated system:

- **memory capture and retrieval** tied to `company_id` + `repository_id`
- a **fixed agent chain** (`project-planner -> scoper -> cursor-pilot -> implementer -> qa-gate -> release-orchestrator`)
- **file-backed packets** as evidence, not chat-only status
- planned **S3-retained packet/evidence archive** plus **DynamoDB run ledger** so
  packet history survives local cleanup and remains queryable by Canon
- **checkpoint + lease + versioning** semantics via `state-api`
- **graph retrieval** and retrieval-source telemetry
- **release gates**, **flow audit**, **DoR telemetry**, **reporting**, and **vault publication**
- AWS-backed **operator-owned** infrastructure and secrets

Canon is therefore not just an execution substrate. It is trying to make AI-assisted development **governable, inspectable, and repeatable across repos and teams**.

## Comparison table

| Dimension | Canon-systems | Sandcastle | Winner | What Canon should do |
| --- | --- | --- | --- | --- |
| **Product layer** | End-to-end operator platform | Runtime / SDK / orchestration substrate | Different layers | Keep saying this clearly; avoid comparing as if both are IDE assistants |
| **Core job** | Memory, workflow governance, evidence, release discipline | Isolated agent execution and orchestration | Tie | Position Canon as the control plane above execution runtimes |
| **Execution model** | Fixed phase chain with mandatory handoffs and gates | Generic programmable primitives (`run`, `worktree`, `sandbox`) | Sandcastle | Borrow cleaner execution abstractions without dropping Canon gates |
| **Memory & retrieval** | Strong org memory across repos, tenant-scoped | No comparable first-class memory plane visible in repo surface | Canon | Double down; this is core differentiation |
| **Governance & audit** | Very strong: checkpoints, packets, telemetry, QA, audit surfaces | Lighter; focused more on runtime than governance | Canon | Productize evidence surfaces further for buyers |
| **Sandboxing** | Present indirectly via workflow/runtime choices; now validated through AWS-hosted Cursor SDK execution | First-class, explicit, provider-agnostic | Sandcastle | Add a cleaner Canon runtime abstraction for local/container/cloud execution |
| **Extensibility for builders** | Opinionated and heavier | Excellent for custom workflows in TypeScript | Sandcastle | Expose a narrower programmatic API for integrators |
| **Enterprise control** | Strong self-hosted and data-sovereignty story | Good technical isolation, but not obviously a full enterprise control plane | Canon | Keep self-hosted + audit + tenant narrative central |
| **Time-to-first-custom-agent-system** | Slower; more policy and platform to absorb | Faster; easier to compose | Sandcastle | Improve onboarding for power users who want partial adoption |

## Strategic conclusion

Canon should **not** respond to Sandcastle by becoming “just a library.”

That would throw away the strongest parts of Canon:

- cross-repo organizational memory
- tenant boundaries
- evidence-backed delivery
- explicit QA and release gates
- operator-controlled infra and audit trails

Instead, Canon should treat Sandcastle as evidence that the market values a **clean agent runtime layer** and **strong sandbox semantics**.

## Recommended response

### 1. Keep Canon positioned above the runtime layer

Canon should frame itself as the **memory, governance, and evidence plane** that can sit:

- inside Cursor today
- inside a future Canon-native client
- above local, containerized, or hosted execution runtimes

The message is: **execution substrate is replaceable; memory and evidence are the durable asset**.

### 2. Steal Sandcastle’s best idea: clearer execution primitives

Canon’s current surface is powerful but heavy: CLI + hooks + templates + multiple backend planes.

Sandcastle’s public model is easier to understand because the runtime primitives are crisp:

- worktree lifecycle
- sandbox lifecycle
- branch strategy
- reusable execution environment

Canon should introduce a similarly crisp internal and product abstraction for:

- **task workspace**
- **execution runtime**
- **checkpointed session**
- **merge target**
- **runtime evidence envelope**

This would make Canon’s autonomy roadmap easier to implement and easier to sell.

### 3. Expose a programmatic API, not only CLI behavior

Sandcastle is attractive because it is embeddable.

Canon should consider a supported API surface for:

- creating task runs
- reading and writing checkpoints
- querying memory and graph state
- retrieving packet/evidence status
- retrieving archived packet bodies and run-ledger relationships
- invoking gated execution phases

This would let partners or internal teams use Canon as a **control plane**, not only as a CLI installed into Cursor workflows.

### 4. Productize runtime choice

Canon today is strongest on workflow discipline, not on a clean execution-runtime story.

The roadmap should move toward explicit support for:

- **local execution**
- **containerized execution**
- **hosted workspace execution**

Cursor SDK should be treated as the first concrete runtime adapter, not the final runtime strategy. The contract should work for:

- Cursor SDK cloud execution
- local Cursor hooks
- containerized workers
- hosted workspaces
- future Sandcastle-like runtimes

while keeping the same:

- canonical IDs
- event model
- checkpoint semantics
- packet persistence
- QA / release gates

That is the right way to close the “runtime sophistication” gap without sacrificing the product thesis.

### 5. Do not weaken the opinionated workflow to chase builder appeal

Sandcastle wins where flexibility matters.

Canon should not try to beat it by becoming less disciplined. If Canon removes gates, packet persistence, or tenant-scoped memory in the name of flexibility, it will lose the reason to exist.

Canon should instead offer:

- a **strict mode** for enterprises and regulated teams
- an optional **lighter mode** for adoption

but preserve a single authoritative evidence model underneath both.

## Roadmap implication

The Cursor SDK validation pulls one roadmap item forward: Canon can now build the first **governed external-runtime adapter** around something that already runs from AWS. The next competitive step is not more proof that remote execution works. It is:

- convert Cursor SDK event streams and GitHub branch/PR output into Canon evidence artifacts
- add negative tests proving missing evidence blocks merge/release
- expose a clean runtime adapter contract other execution substrates must satisfy
- keep credential ownership, cleanup, and audit semantics explicit

That is the practical way to beat Sandcastle at the product layer: let runtime tools run code, but make Canon the place where agentic delivery becomes auditable and shippable.

## Bottom line

Sandcastle is a good runtime-layer project.

Canon’s opportunity is not to out-Sandcastle Sandcastle. It is to become the **system of record for agentic software delivery**: the place where organizations can answer:

- what happened
- why it happened
- which repo and tenant it affected
- which evidence supports it
- whether it passed the required gates

If Sandcastle is “how agents run safely,” Canon should be “how organizations ship safely with agents.”

That is the cleaner positioning.

---

**Related docs:**

- [CANON-SYSTEMS-ONE-PAGER-2026.md](CANON-SYSTEMS-ONE-PAGER-2026.md)
- [CANON-PRIORITIZED-ROADMAP-2026.md](CANON-PRIORITIZED-ROADMAP-2026.md)
- [CANON-VS-DEVIN-STRATEGY-2026.md](CANON-VS-DEVIN-STRATEGY-2026.md)
- [SYSTEM-WORKFLOW.md](SYSTEM-WORKFLOW.md)
