# Canon-systems — what it is, where we’re going (2026)

## What it is

**Canon-systems** is the **memory, governance, and evidence layer** for serious AI-assisted software work.

Today it ships as a **CLI + Cursor-native** operating model with AWS-backed memory and optional backend planes. As of **May 1, 2026**, Canon has also validated an AWS-hosted remote execution path that invokes the **Cursor SDK cloud runtime** against the Canon repo and can create a branch, commit, and PR.

Strategically, Canon should be understood as a product with **three layers**:

1. **Memory plane** — durable org-scoped context across sessions and repos
2. **Governance / evidence plane** — required handoffs, checkpoints, QA gates, merge gates, audit trail
3. **Execution plane** — where agent work runs: local IDE agent, container, remote worker, or hosted workspace

The first two are Canon’s real moat. The third is partly replaceable, and Cursor SDK is now the first proven external execution substrate for that layer.

## In practice, teams get

- **Memory that survives the chat window** — preflight and capture on every turn, company + repo scoping, hybrid retrieval across canonical events and MemPalace.
- **Governed delivery, not chat-only claims** — file-backed handoffs, DoR enforcement, checkpoints, QA gates, merge/release gates, audit-proof evidence, plus **v1** server-side **packet archive** + **run ledger** on **`state-api`** (local `.cursor/handoffs/...` still required; **`canon readiness check`** is read-only diagnostics over the ledger).
- **Cross-repo coherence** — the same `company_id` can span many repositories so decisions and captures are not trapped in one clone.
- **Optional execution and data planes** — code graph, operational state, synthesis vault, stable HTTPS APIs, and a validated Cursor SDK remote-execution path that can mature into remote workers.

Canon is **not** trying to be a generic “autonomous engineer in a browser.” It is the layer that makes AI coding **repeatable, governable, and inspectable** inside real organizations.

## Two ways to adopt Canon

### 1. Full Canon workflow

Canon owns the working model end-to-end:

- hooks and rules in Cursor
- the agent chain
- packets and checkpoints
- QA and release discipline

This is the strongest expression of Canon today.

### 2. Governance-over-external-agents

Teams keep their own models, tools, prompts, or agent runtime, and Canon sits **above** them as the control plane. The first validated version of this is Canon infrastructure dispatching work to Cursor SDK cloud execution, then treating branch/commit/PR output and runtime events as evidence inputs.

Canon does not have to own every agent’s inner loop. It can still enforce:

- required task handoffs
- checkpoint / state updates
- evidence capture
- PR / merge / release gates
- audit trail and policy compliance

This is the strategic expansion that makes Canon more than a Cursor-native workflow.

## How others compare (honestly)

**Devin.ai** wins on high-autonomy managed execution, polished SaaS UX, and “fire-and-forget” feel. **Sandcastle** wins on clean runtime abstractions for sandboxed agent execution. **Open orchestration frameworks** win on flexibility for builders.

**Canon’s edge** is different:

- organizational memory across repos
- strict delivery governance
- evidence-backed software flow
- tenant correctness and data sovereignty

Canon should not try to become a clone of Devin or a thinner Sandcastle. It should be the **system of record for agentic software delivery**.

## Where we’re taking it

**North star:** Canon is the **default memory and governance OS** for teams that care about **why a decision was made, in which repo, for which tenant, with what evidence** — while still allowing stronger autonomous execution when product and policy allow.

**Near-term roadmap themes:**

1. **Knowledge and operator UX** — make org knowledge as easy to use as it is to store: triggers, playbooks, macros, and a stronger `canon ask` / preflight experience.
2. **Enterprise governance surfaces** — SSO, policy visibility, admin/audit surfaces, and event-driven enterprise hooks.
3. **Cursor SDK evidence envelope + runtime abstraction** — turn the validated AWS -> Cursor SDK path into a Canon-native adapter with canonical evidence, policy checks, and negative tests.
4. **Governed autonomy + remote workers** — keep Cursor as the shell if useful, but move real execution to Canon-controlled workers or Cursor SDK cloud agents where governance, hidden orchestration, and evidence are consistent.
5. **Managed Canon** — hosted memory, ingress, dashboards, and remote execution for teams that want Canon without running the full stack themselves.

## Longer arc

Today Canon meets developers **inside Cursor**. Over time, Canon can grow in two directions at once:

- **Horizontally** into a governance/control plane above many execution environments
- **Vertically** into a Canon-native client or hosted shell that hides internal machinery while preserving evidence and policy
- **Pragmatically** into Cursor SDK-backed remote execution before Canon needs to own every part of the coding runtime itself

That means a future Canon experience could look like:

- **Plan → Scope → Implement → Verify → Ship**
- clear status per phase
- explicit evidence links
- human gates where policy requires them
- optional hidden orchestration under the hood

What would stay constant:

- canonical IDs
- event envelope
- packet/evidence model
- durable packet archive + run ledger
- tenant boundaries
- checkpoint lease semantics
- merge and release gates

The shell can change. The governance and evidence model should not.

## Principle we won’t trade away

Memory and shipping **evidence** beat raw model cleverness for organizations shipping under compliance pressure, on-call pressure, and across multiple codebases.

A prettier shell does not replace that. More autonomy does not replace that. A nicer runtime abstraction does not replace that.

They only matter if they still surface the same truth.

That is what Canon-systems is for.

---

*For detail: [CANON-PRIORITIZED-ROADMAP-2026.md](CANON-PRIORITIZED-ROADMAP-2026.md), [CANON-VS-DEVIN-STRATEGY-2026.md](CANON-VS-DEVIN-STRATEGY-2026.md), [CANON-VS-SANDCASTLE-STRATEGY-2026.md](CANON-VS-SANDCASTLE-STRATEGY-2026.md). Living document — adjust as the product ships.*
