# Project planner — why canonical memory first (not Axon)

This document records **design intent** for [`src/canon_systems/templates/agents/project-planner.md`](../src/canon_systems/templates/agents/project-planner.md) so the team can **re-evaluate** later without reverse-engineering chat history.

## What project-planner does

- **Readonly, planning-only:** decomposes a broad initiative into `PROJECT_EXECUTION_PLAN` (epics, tasks, dependencies, done signals).
- **Does not write code** and does not assume a single implementation commit is “the” truth surface yet.

## Why it leads with canonical memory, not `canon graph query`

1. **Question shape:** Early planning needs **narrative and decision history** (“what did we already decide?”, “what constraints matter?”) across sessions. That maps naturally to **canonical memory** — `canon ask`, `.canon/memory/context-latest.md`, and cited files — not to a **structural code graph** at a single `commit-sha`.

2. **Graph prerequisites:** `canon graph query` is **commit-scoped** and only as good as **indexed** snapshots for that commit (`canon graph index`, CI, or pre-push hook). At plan time, a useful index may **not exist yet**, or the relevant commit may change as the plan evolves.

3. **Separation of concerns:** The **implementation chain** (`scoper` → `cursor-pilot` → `implementer`) operates on a **concrete tree** and benefits from **graph → state → canonical → file** (see [`memory-layer-defaults.mdc`](../src/canon_systems/templates/rules/memory-layer-defaults.mdc)). The planner produces **backlog structure**; downstream agents consume graph when the work is **engineering on that structure**.

4. **Fail-open philosophy:** If Axon were mandatory for planning, a missing index or URL would **block** backlog creation. Canonical memory stays available whenever secrets and knowledge plane are up.

## Global rule still applies in the workspace

Wired repos load **`memory-layer-defaults.mdc`**, which defines **graph → state → canonical → file** for **coding work**. The planner template is a **narrower, explicit** instruction set for its role; it does not delete the global rule from the repo — it **special-cases** the first hop for planning.

## When you might change this later

Consider adding **optional** graph reads to the planner if:

- You always index **before** planning, and
- Planning routinely needs **structural** questions (“what packages depend on X?”) answerable only from Axon, and
- You accept planner failures or empty graph results as non-blocking (fail-open).

Any change should update: this doc, `project-planner.md`, [`MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md`](MEMORY-PLATFORM-RUNTIME-AND-AGENTS.md), and tests/template guards if present.
