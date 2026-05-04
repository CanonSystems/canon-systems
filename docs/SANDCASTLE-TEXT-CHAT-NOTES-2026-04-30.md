# Sandcastle text chat notes (April 30, 2026)

## Friend

Compare Sandcastle to Canon-systems.

## Reply

Canon and Sandcastle are adjacent, not the same thing. Sandcastle is a strong runtime for sandboxed coding agents; Canon is the memory/governance layer for teams, with cross-repo context, checkpoints, QA gates, and auditability. Sandcastle is about running agents safely, Canon is about shipping with agents safely.

## Follow-up

What about all the enterprise stuff?

## Reply

Sandcastle looks strong for sandboxed agent execution, but Canon is aimed higher up the stack: org memory, cross-repo context, checkpoints, QA gates, auditability, and enterprise control over infra/auth/data. Sandcastle is about running agents safely; Canon is about operating them safely in a real company.

## Follow-up

Does Sandcastle have an agent SDK?

## Reply

Yes, effectively it does. Sandcastle looks like an agent orchestration/runtime SDK: a programmatic layer for running and composing coding agents in isolated sandboxes. The difference is that it is focused on execution and composition, not Canon-style memory/governance.

## Friend

What the difference? I like to abstract canon system into two things:

1. MCP tools (and alike) for shared memory module
2. Flow enforcement to trigger agents/sub agents to complete a task.

## Reply

That’s a fair abstraction, but Canon is still a layer above that.

1. Shared memory: yes, MCP/tools are part of it, but Canon’s real point is org-scoped memory with repo/tenant boundaries, persistence, retrieval, and evidence, not just tools that can look things up.
2. Flow enforcement: also yes, but it’s not only triggering agents. It’s enforcing a governed delivery loop: checkpoints, handoff packets, QA gates, audit trail, and release discipline.

So the simplest difference is: Sandcastle is more of an agent runtime/orchestration SDK, while Canon is a workflow + memory + governance system for using agents inside a real team/company.

## Friend

I think the governance feature is key. That might a product by itself. Not just permissions but also governance of making sure that every AI code create follow strict flow and is grounded in evidences or org policies.

## Reply

Exactly. That’s the interesting part of Canon. Not governance as in just auth/permissions, but governance of the software delivery process itself: making sure AI work follows required steps, uses org memory/policies, produces evidence, and can’t quietly skip QA or release discipline. That alone could be a real product category.

## Friend

Can you extract just this piece from canon? Aka, you can keep your AI flow and tools and we would add governances and ensure flow?

Or canon have to a whole workflow solution from the start

## Reply

Yes, that part could absolutely be extracted.

The governance layer does not have to own the whole agent runtime. In principle, teams could keep their own models, tools, prompts, and agent flow, and Canon would sit above it as the enforcement/evidence layer: required steps, policy checks, memory grounding, checkpointing, QA gates, and audit trail.

So Canon does not have to start as a full workflow replacement. The governance piece could stand alone first, then expand into the broader workflow/memory system later. The risk is that if it’s too thin, it becomes hard to enforce consistently, so it needs strong integration points at the handoff, checkpoint, and merge/release boundaries.
