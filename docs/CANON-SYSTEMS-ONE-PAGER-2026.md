# Canon-systems — what it is, where we’re going (2026)

## What it is

**Canon-systems** is the **operator platform** for serious AI-assisted software work: a CLI and Cursor-native layer that gives your org **durable memory**, **tenant-scoped context**, and **governed agent execution** on **your** infrastructure (AWS-backed, secrets in your account, optional graph and state APIs).

**In practice, teams get:**

- **Memory that survives the chat window** — preflight and capture on every turn, company + repo scoping, hybrid search across canonical events and MemPalace.
- **A disciplined agent chain** — scoper → cursor-pilot → implementer → qa-gate → release-orchestrator, with **file-backed handoffs** (not chat-only “done”), DoR and QA telemetry, and merge gates you can prove in audit.
- **Cross-repo coherence** — the same `company_id` can span many repositories so decisions and captures aren’t trapped in a single clone.
- **Optional planes when you wire them** — structural retrieval (Axon-style graph), operational checkpoints (state-api), stable HTTPS endpoints for knowledge and memory health.

Canon is **not** trying to be a generic “autonomous engineer in a browser” product. It’s the **governance, memory, and evidence layer** that makes AI coding **repeatable and accountable** inside real enterprises.

## How others compare (honestly)

Products like **Devin.ai** (2026) excel at **high autonomy** in a managed sandbox: long runs, swarms, knowledge base UX, and enterprise SaaS polish. **IDE assistants** (Copilot, Cursor’s own features) win on **immediacy in the editor**. **Open orchestration frameworks** win on **flexibility** for builders who will glue everything themselves.

**Canon’s edge** is the combination of **organizational memory across repos**, **strict packet and QA discipline**, **IDE-in-the-loop** (hooks, rules, subagents), and **data ownership** (you hold the keys and the audit trail). **Where we don’t lead** out of the box: the most **polished** end-user knowledge UI, the **loosest** “set and forget” autonomy, and the **broadest** off-the-shelf enterprise admin console—those are the gaps we’re **deliberately** closing in the product plan, not reasons to become a clone of Devin.

## Where we’re taking it

**North star:** Canon is the **default memory and workflow OS** for teams that care about **why a decision was made, in which repo, for which tenant, with what evidence**—while still allowing **stronger autonomous runs** when product and policy allow.

**Near term (themes):**

1. **Knowledge and UX** — make org knowledge as easy to use as it is to store: triggers, playbooks, macros, and a “magical” `canon ask` / Cursor experience without weakening boundaries.
2. **Enterprise** — Cognito/OIDC-style SSO, admin visibility, event-driven hooks (tickets, CI, Slack), audit-friendly exports.
3. **Autonomy with teeth** — longer runs and parallel implementer lanes **only** where checkpoint and QA contracts still hold; no race to the bottom on merge discipline.
4. **Optional managed path** — for buyers who need hosted Canon with predictable commercial terms, not a rewrite of the open CLI story.

## Longer arc — our own “Cursor,” with the machinery hidden (and maybe cloud)

Today, Canon meets developers **inside Cursor**: hooks, rules, and especially `**.cursor/agents/*.md`** expose the agent chain as **readable prompts**—great for transparency, audits, and power users who edit handoffs, but **not** how most enterprises want to **buy** software. They want **stages**, **status**, and **approvals**, not a folder of markdown roles.

**If we separated from Cursor** and shipped a **Canon-native client**—our own editor shell or fork-class experience—we could **productize the same pipeline** without surfacing implementation detail:

- **What users would see:** phases such as **Plan → Scope → Implement → Verify → Ship**, each with clear state (queued / running / blocked / done), links to **evidence** (QA packet, memory-health, diff summary), and **human gates** where policy requires them. “Agents” become **capabilities**, not files named `scoper.md`.
- **What we’d hide by default:** raw subagent templates, internal prompt drift, and the filesystem layout under `.cursor/agents`. Advanced mode or export could still reveal packets for regulated customers who require prompt inspectability.
- **What would not change under the hood:** the same **canonical IDs**, **event envelope**, **handoff packets on disk** (or object storage), **tenant boundaries**, **Secrets Manager** wiring, **checkpoint lease semantics**, and **merge gates**. The shell becomes a **presentation and orchestration UI** over contracts we already enforce—not a second truth.

**Cloud-based Canon** would stack naturally on that separation: a **thin client** (browser or lightweight desktop) talking to **hosted workspaces** (VM or container per session or per tenant tier), with **memory and state** in the region and account model customers already expect from [CANON-PRIORITIZED-ROADMAP-2026.md](CANON-PRIORITIZED-ROADMAP-2026.md) Phase 4. The experience would resemble **Devin-style** “open your session, watch progress”—except progress would still be **evidence-backed** (QA PASS, audit events), not an opaque black box.

**Tradeoffs we’d accept:** building and maintaining a client (release cadence, accessibility, editor parity), choosing **how much** of VS Code / Monaco / LSP to bundle versus integrate, and deciding whether **Cursor compatibility** remains a first-class path for developers who want raw agent files. **Tradeoffs we’d refuse:** dropping multi-tenant correctness, dropping packet or QA history for convenience, or hiding failures instead of surfacing them as structured blockers.

That future is **optional** and **additive**: the CLI and Cursor integration remain the **open, inspectable** spine; a Canon shell would be the **enterprise-grade skin** for teams who pay for polish and isolation—including **cloud** when they don’t want to run the IDE glue themselves.

**Principle we won’t trade away:** memory and shipping **evidence** beat raw model cleverness for organizations that ship under compliance, on-call pressure, and multiple codebases. A prettier shell doesn’t replace that—it **surfaces** it. **That** is what Canon-systems is for—and that is where we’re taking it.

---

*For detail: [CANON-VS-DEVIN-STRATEGY-2026.md](CANON-VS-DEVIN-STRATEGY-2026.md), [CANON-PRIORITIZED-ROADMAP-2026.md](CANON-PRIORITIZED-ROADMAP-2026.md). Living document — adjust as the product ships.*