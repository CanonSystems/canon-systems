# Claude brief — revise Canon Systems presentation (May 1, 2026)

Use this brief to expand and improve `CANON-SYSTEMS-PRESENTATION-2026.pptx`.

## Goal

Revise the presentation so it matches the updated strategy and roadmap:

- Canon is not just a Cursor-native full workflow.
- Canon is a **memory + governance + evidence control plane**.
- Canon can operate in **two modes**:
  - full Canon workflow
  - governance-over-external-agents
- Canon should be positioned to beat:
  - **Devin** on governance, enterprise control, auditability, and tenant-correct memory
  - **Sandcastle** by sitting **above** runtime choice, not by trying to be a thinner runtime SDK
- Canon should explicitly support the idea of:
  - **remote workers / remote subagents**
  - Cursor as the **user-facing shell**
  - Canon owning the **real execution, governance, and evidence path** remotely
- Incorporate the May 1 validation:
  - AWS ECS/Fargate invoked Cursor SDK cloud execution against the Canon repo.
  - A read-only run completed successfully.
  - A write-path run created a branch, commit, and PR.
  - Cursor SDK is now the first proven remote execution substrate, not merely a hypothetical future integration.

## Source of truth

Align the deck to these docs:

- `docs/CANON-PRIORITIZED-ROADMAP-2026.md`
- `docs/CANON-SYSTEMS-ONE-PAGER-2026.md`
- `docs/CANON-VS-DEVIN-STRATEGY-2026.md`
- `docs/CANON-VS-SANDCASTLE-STRATEGY-2026.md`
- `docs/CURSOR-SDK-AWS-VALIDATION-2026-05-01.md`

## High-level changes needed

### 1. Tighten the product definition

The deck currently still implies Canon is mainly:

- a Cursor-native workflow
- with a fixed agent chain
- and maybe later a Canon-native client

That is incomplete.

Update the core definition so Canon is clearly:

- **memory plane**
- **governance / evidence plane**
- **execution plane**

And make clear that the first two are Canon’s moat, while the third can be:

- local agent
- containerized runtime
- remote Canon worker
- hosted workspace

### 2. Add the “two adoption modes” explicitly

Add a slide or section that says Canon can be adopted in two ways:

#### Mode A — Full Canon workflow

- Canon owns the workflow end-to-end
- hooks, rules, chain, checkpoints, QA, merge/release gates

#### Mode B — Governance-over-external-agents

- customer keeps their own agent/runtime/tooling
- Canon governs the boundaries:
  - task handoffs
  - checkpoint/state updates
  - evidence capture
  - PR/merge/release gates

This is critical. It is the cleanest answer to “how do you mix and match other agents but still ensure governance?”

### 3. Add runtime abstraction and remote workers to the roadmap

The roadmap in the deck should no longer be only:

1. Knowledge & UX
2. Enterprise & Cognito
3. Governed autonomy
4. Managed Canon

It should now be:

1. Knowledge and operator UX
2. Enterprise governance surfaces
3. Cursor SDK evidence envelope + runtime abstraction
4. Governed autonomy + remote workers
5. Managed Canon

Make this visually obvious.

### 4. Improve the Sandcastle comparison

The current Sandcastle comparison is good, but it should be sharper:

- Sandcastle wins at **execution flexibility**
- Canon should not try to out-Sandcastle Sandcastle
- Canon wins when the buyer cares about:
  - memory across repos
  - evidence-backed delivery
  - policy/gate enforcement
  - tenant correctness
  - auditability

Make the key line stronger:

**Sandcastle is about how agents run safely. Canon is about how organizations ship safely with agents.**

### 5. Clarify the Devin answer

The deck should say more directly:

- Canon does not need to out-Devin Devin on opaque autonomy
- Canon needs enough UX + governed autonomy + enterprise polish that buyers don’t have to trade away control to get leverage

Add the distinction:

- **Devin pressures Canon on autonomy and product polish**
- **Sandcastle pressures Canon on runtime abstraction and composability**

### 6. Add the remote-subagent / remote-worker story

This needs to be an explicit slide.

Explain the product model:

- Cursor remains the user-facing shell
- local hooks or commands dispatch tasks to Canon
- Canon remote workers perform the real execution
- Canon returns artifacts, diffs, packets, status, branches, or PRs
- Canon keeps internal subagent prompts and orchestration hidden by default
- evidence, gates, and audit trail remain visible

This is strategically important because it:

- avoids relying on user-local subagent behavior
- avoids depending on user-owned tokens for core execution
- improves governance consistency
- makes enterprise UX cleaner

### 7. Add the proof point: AWS -> Cursor SDK -> GitHub PR

Add one concise validation slide:

- **What we proved:** Canon-controlled AWS infrastructure can invoke Cursor SDK cloud execution against `github.com/CanonSystems/canon-systems`.
- **Read-only proof:** Cursor SDK analyzed the repo and returned a finished run.
- **Write-path proof:** Cursor SDK created a branch, commit, and PR.
- **What remains:** Canon-native evidence envelope, negative gates, credential lifecycle, cleanup tooling, and production UX.

Message:

Remote execution is no longer the risky unknown. The product challenge is now governance: making every remote run auditable, policy-bound, and safe to merge.

## Specific slide recommendations

### Update existing “What Canon Is” slides

Current issue:

- too centered on “disciplined agent chain”
- not explicit enough that Canon can sit above other runtimes

Revise to emphasize:

- memory
- governance/evidence
- execution abstraction
- two adoption modes

### Add a new slide: “Canon’s Three Layers”

Suggested structure:

- Memory plane
- Governance / evidence plane
- Execution plane

Under execution plane, show:

- local IDE agent
- container runtime
- remote Canon worker
- hosted workspace

### Add a new slide: “Two Adoption Modes”

Compare:

- Full Canon workflow
- Governance-over-external-agents

Show what Canon owns in both cases.

### Add a new slide: “Boundary Enforcement Model”

Show the control points Canon needs to own:

- task handoff
- checkpoint/state
- evidence capture
- commit/PR
- merge/release

Message:

Canon does not need to own every inner loop. It needs to own the boundaries that determine whether work is real and shippable.

### Add a new slide: “Remote Workers / Remote Subagents”

Show:

- user in Cursor
- hook/command dispatch
- Canon control plane
- Cursor SDK cloud agent or remote workers
- packets/evidence/gates
- diff/PR/result returned

### Add a new slide: “Validated Remote Execution Path”

Show:

- Canon CLI/hook
- AWS ECS/Fargate task
- Cursor SDK cloud run
- GitHub branch/commit/PR
- Canon evidence envelope and gates

Label current status clearly:

- **Validated:** AWS can dispatch Cursor SDK and receive successful repo/result metadata.
- **Next:** Convert runtime output into Canon-native evidence and enforce policy at PR/merge/release.

### Update roadmap slides

Replace the old 4-phase story with the 5-phase story from the revised roadmap.

### Tighten the “Longer Arc” slide

Current issue:

- too much emphasis on Canon-native client as the main future

Revise so it shows two simultaneous arcs:

- Canon as cross-runtime governance/control plane
- Canon as optional polished client/shell

## Copy guidance

Tone should remain:

- strategic
- technical
- enterprise-serious
- clear about tradeoffs

Avoid:

- sounding like a generic AI pitch
- overstating autonomy parity with Devin
- implying Sandcastle and Canon are the same category
- implying Canon must own all execution to be valuable

Prefer language like:

- “control plane”
- “governance and evidence boundaries”
- “system of record for agentic software delivery”
- “execution as a replaceable layer”
- “remote governed execution”

## Deliverables I want from you

Please produce all of the following:

1. A revised slide-by-slide outline for the full deck
2. New/revised copy for the affected slides
3. Recommendations for which existing slides to merge, delete, or split
4. Suggested visual diagrams for:
   - three-layer model
   - two adoption modes
   - boundary enforcement
   - remote worker flow
5. Short speaker notes for the most strategic slides
6. Any wording changes needed so the deck aligns with:
   - the updated roadmap
   - the one-pager
   - the Devin and Sandcastle strategy docs

## If you choose to directly edit the deck

Preserve:

- the serious enterprise tone
- the current product thesis around memory/governance/evidence
- the technical credibility of the existing detailed slides

Improve:

- strategic sharpness
- story flow
- differentiation
- roadmap consistency

## Ideal end state

After revision, the deck should make these points obvious:

1. Canon’s moat is not “just another agent workflow.”
2. Canon wins by owning memory, governance, evidence, and policy boundaries.
3. Canon can govern external agent systems without owning every inner step.
4. Canon can use remote workers to make execution consistent and hidden where needed.
5. Canon’s roadmap now clearly answers both Devin and Sandcastle.
