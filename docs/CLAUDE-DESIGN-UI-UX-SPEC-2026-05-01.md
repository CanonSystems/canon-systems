# Canon Systems UI/UX spec for Claude Design (May 1, 2026)

## Purpose

Create full wireframes and a design style for Canon Systems as a commercial product.

This is not a generic AI coding dashboard. Canon is the **governance, memory, and evidence layer for AI-assisted software delivery**. The UI must make one thing obvious:

> AI agents can write code, but Canon decides whether that work is compliant, evidenced, and safe to merge.

## Source docs

Use these as source-of-truth inputs:

- `docs/CANON-SYSTEMS-ONE-PAGER-2026.md`
- `docs/CANON-PRIORITIZED-ROADMAP-2026.md`
- `docs/CURSOR-SDK-AWS-VALIDATION-2026-05-01.md`
- `docs/CANON-VS-DEVIN-STRATEGY-2026.md`
- `docs/CANON-VS-SANDCASTLE-STRATEGY-2026.md`
- `CANON-SYSTEMS-PRESENTATION-2026.pptx`

## Product thesis

Canon has three layers:

1. **Memory plane**
   Durable company/repo knowledge, decisions, prior work, canonical events, and retrieval evidence.
2. **Governance / evidence plane**
   Handoffs, checkpoints, DoR, QA gates, release gates, policy compliance,
   audit trail, durable packet/evidence archive, and run ledger.
3. **Execution plane**
   Local Cursor, Cursor SDK cloud agents, remote workers, containers, or future hosted workspaces.

The UI should visually reinforce that the **memory and governance layers are Canon’s moat**. Execution is selectable and partly replaceable.

## Commercial wedge

Design for the first sellable product:

**Canon Govern**

An evidence and policy gate for AI-authored PRs.

Core promise:

- AI coding agents can run anywhere.
- Canon captures what happened.
- Canon checks whether required evidence exists.
- Canon blocks merge/release when policy is not satisfied.
- Operators can inspect why.

The rest of the platform should be visible as expansion, but not overwhelm the wedge.

## Target users

### Primary users

- Engineering managers adopting AI coding agents across teams.
- Staff/principal engineers responsible for release quality.
- Platform engineering / DevEx teams owning CI, GitHub, Cursor, and internal tooling.
- Security/compliance reviewers who need auditability.

### Secondary users

- Individual engineers using Cursor or another AI coding agent.
- CTO/founder buyer evaluating risk and leverage.
- AI platform team integrating multiple coding agents.

## Required product surfaces

Design these screens as a cohesive product, not isolated mockups.

### 1. Executive / operator dashboard

Purpose: answer “Are AI-authored changes under control?”

Must show:

- Active AI work by repo, task, runtime, and status.
- Compliance state: compliant, blocked, missing evidence, failed QA, stale checkpoint.
- Recent PRs created by AI agents.
- Risk summary by repo/team.
- Gate pass/fail trends.
- Memory health / retrieval health.
- Open human approvals.

Primary CTA:

- “Review blocked work”
- “Dispatch governed task”
- “View audit export”

Recommended layout:

- Top-level status strip with 4-5 strong metrics.
- Main table/list of active governed work.
- Right-side or lower panel for policy/risk alerts.
- Avoid making this feel like a generic analytics SaaS dashboard.

### 2. Governed work detail page

Purpose: one task/run/PR forensic page.

This is the most important screen.

Must show:

- Task title, repo, branch, PR, actor, runtime, model.
- Current phase: Plan -> Scope -> Implement -> Verify -> Ship.
- Canon compliance result: PASS / BLOCKED / WARNING.
- Evidence checklist:
  - handoff exists
  - archived packet URI + content hash exists
  - checkpoint exists
  - memory/retrieval evidence exists
  - changed files cited
  - tests mapped to acceptance criteria
  - QA gate result
  - CI result
  - release/merge gate result
- Timeline of canonical events.
- Run ledger view connecting phase packets, evidence refs, validations, commits,
  deployments, and final outcome.
- Cursor SDK metadata when relevant:
  - agentId
  - runId
  - ECS task ARN
  - model
  - duration
  - event count
  - branch/commit/PR
- Human-readable explanation of why the run is compliant or blocked.

Primary CTA:

- “Approve”
- “Request fix”
- “Re-run QA”
- “Export evidence”
- “Open PR”

Design requirement:

- The page should feel like an air-traffic-control screen for software delivery, not a chat transcript.
- Evidence should be easy to scan and impossible to fake visually.

### 3. PR governance gate page

Purpose: the Canon equivalent of a required GitHub check, but readable by humans.

Must show:

- PR title, repo, branch, author/agent.
- Merge decision: “Allowed” or “Blocked.”
- Blocking reasons with exact missing artifacts.
- Required policy for this repo.
- Evidence links.
- Recent run attempts and retries.
- Clear distinction between:
  - agent failure
  - missing evidence
  - failed test
  - stale state/lease
  - policy violation

Primary CTA:

- “Open evidence bundle”
- “Copy fix instructions”
- “Trigger Canon repair run”

### 4. Dispatch governed task flow

Purpose: let a user send work to Canon without exposing internal subagent machinery.

Must include:

- Select repo.
- Select runtime:
  - Cursor SDK cloud
  - local Cursor
  - remote Canon worker
  - external agent / CI
- Select policy mode:
  - strict
  - adoption
  - custom
- Enter task objective and acceptance criteria.
- Optional: link issue/PR/ticket.
- Show required gates before launch.
- Launch and show run status.

Important:

- Do not make this look like a generic chatbot.
- The task form should feel like creating controlled work, not prompting a model.

### 5. Memory and knowledge explorer

Purpose: make organizational memory inspectable.

Must show:

- Company and repo scope.
- Search across canonical events, knowledge artifacts, graph, and synthesis vault.
- Retrieved items with source, date, repo, confidence, and why it matched.
- Related decisions and prior tasks.
- Ability to cite an item into a task/run.
- Ability to mark stale/deprecated knowledge.

Primary CTA:

- “Use as task context”
- “Cite in evidence”
- “Mark stale”

Design requirement:

- This should feel like an evidence library, not a document dump.

### 6. Policy builder / policy surface

Purpose: show what Canon requires before AI work counts as done.

Must support:

- Repo-level policy.
- Tenant/team policy.
- Required gates:
  - DoR complete
  - checkpoint written
  - evidence bundle present
  - tests mapped to ACs
  - QA pass
  - CI pass
  - memory-health pass
  - human approval required
- Runtime-specific rules:
  - Cursor SDK allowed
  - external agents allowed
  - local-only
  - customer-owned credentials only
- Strict/adoption/custom modes.

Design requirement:

- Policies must be readable by engineering managers, not only security people.
- Use plain-language policy summaries plus advanced detail.

### 7. Runtime adapters page

Purpose: show how Canon governs different agent runtimes.

Must show:

- Connected runtimes:
  - Cursor SDK cloud
  - local Cursor hooks
  - GitHub Actions / CI
  - remote Canon worker
  - future custom adapter
- Health/status per runtime.
- Credential state without exposing secrets.
- Last successful run.
- Last failure.
- Evidence envelope compatibility.
- Adapter configuration.

Primary CTA:

- “Add runtime”
- “Rotate credential”
- “Test adapter”
- “Disable runtime”

### 8. Audit export / evidence bundle page

Purpose: let a buyer or compliance user extract proof.

Must show:

- Filters:
  - company
  - repo
  - date range
  - task
  - PR
  - agent/runtime
  - compliance state
- Export formats:
  - JSON
  - NDJSON
  - CSV summary
  - PDF/HTML evidence report
- Preview of included events and artifacts.

Primary CTA:

- “Export evidence”
- “Copy audit link”

### 9. Admin / tenant setup

Purpose: initial enterprise setup.

Must include:

- Company/repo registry.
- SSO/OIDC/Cognito status.
- GitHub connection.
- Cursor SDK credential connection.
- AWS/self-hosted/managed deployment status.
- Secret rotation reminders.
- User/team roles.

Important:

- This is secondary. Do not let admin setup dominate the product story.

## Main user journeys

### Journey A: AI PR governance

1. Cursor SDK or another agent creates a PR.
2. Canon ingests branch/commit/PR/runtime metadata.
3. Canon checks required evidence.
4. PR is marked compliant or blocked.
5. Operator opens the governed work detail page.
6. Operator sees exact missing or passing evidence.
7. Operator approves, requests fix, or exports audit bundle.

### Journey B: Dispatch governed coding task

1. User opens “Dispatch task.”
2. Selects repo, runtime, policy, and acceptance criteria.
3. Canon shows required gates before launch.
4. User launches run.
5. Canon streams status at phase level, not raw prompt noise.
6. Runtime returns branch/PR/result.
7. Canon wraps result in evidence and gate state.
8. User reviews and merges only if policy passes.

### Journey C: Investigate why a run is blocked

1. User opens dashboard and sees blocked PR.
2. Opens PR governance gate page.
3. Sees “Missing QA evidence for AC-3” or similar exact reason.
4. Opens evidence bundle.
5. Triggers repair run or copies instructions.
6. Canon rechecks and updates merge gate.

### Journey D: Configure policy for a repo

1. Platform owner opens policy builder.
2. Selects strict/adoption/custom.
3. Chooses required evidence gates.
4. Chooses allowed runtimes.
5. Saves policy.
6. Canon shows how current open PRs would be affected.

## Information architecture

Recommended primary nav:

- Dashboard
- Governed Work
- PR Gates
- Dispatch
- Memory
- Policies
- Runtimes
- Audit
- Admin

Recommended object model:

- Company
- Repository
- Task
- Run
- Runtime
- Agent
- Handoff
- Checkpoint
- Evidence bundle
- Policy
- Gate result
- PR
- Audit event

## Design tone

Canon should feel:

- serious
- precise
- technical
- enterprise-grade
- calm under pressure
- evidence-first

Canon should not feel:

- playful
- chatty
- magical
- generic AI assistant
- cyberpunk security dashboard
- purple SaaS template
- overloaded DevOps dashboard

Visual metaphor:

- Air traffic control for AI software delivery.
- Chain of custody for code.
- Flight recorder for AI work.

## Visual system direction

Recommended style:

- Dark-neutral or warm-light enterprise interface, but not generic black/purple.
- Strong use of status color:
  - green = compliant/pass
  - amber = warning/missing evidence
  - red = blocked/fail
  - blue/slate = running/in review
- Typography should be crisp and operational.
- Tables/lists should be highly readable.
- Evidence cards should feel like signed records, not decorative cards.
- Timeline should be a first-class component.
- Use compact density but avoid overwhelming first-time users.

Possible palette direction:

- Base: ink / graphite / off-white / slate
- Accent: signal green, warning amber, blocked red, protocol blue
- Avoid heavy purple.

## Component requirements

Design these reusable components:

- Compliance badge
- Gate checklist
- Evidence bundle card
- Canonical event timeline
- Runtime status pill
- Policy mode selector
- Phase progress rail: Plan -> Scope -> Implement -> Verify -> Ship
- PR gate decision panel
- Missing evidence alert
- Task/run header
- Repo/tenant scope selector
- Audit export filter bar
- Adapter health card
- Approval/action bar

## Data examples to use in wireframes

Use realistic values from the validation:

- Repo: `github.com/CanonSystems/canon-systems`
- Runtime: Cursor SDK cloud
- ECS cluster: `canon-systems-v2-dev-cluster`
- Cursor agent: `bc-bb3c8998-3336-4822-b3bd-1bef697d647e`
- Cursor run: `run-875e4e93-1f6b-4991-8d45-4fe0c650d239`
- Branch: `cursor/cursor-sdk-write-path-smoke-647e`
- Commit: `8d47e7c0f0a592fd1ab08039526a9f04cb89700f`
- PR: `https://github.com/CanonSystems/canon-systems/pull/9`
- Result: `status: finished`
- Event count: `84`
- Duration: `24.8s`

Example blocked state:

- Missing: `qa-gate PASS`
- Missing: `AC-3 test coverage evidence`
- Failed: `memory-health graph check`
- Stale: `checkpoint lease expired 18m ago`

## Wireframe deliverables requested from Claude Design

Produce:

1. Product IA map.
2. Core design system direction.
3. Low-fidelity wireframes for all required product surfaces.
4. High-fidelity mockups for:
   - Executive / operator dashboard
   - Governed work detail page
   - PR governance gate page
   - Dispatch governed task flow
   - Policy builder
5. Component library preview.
6. Clickable prototype flow for:
   - AI PR arrives -> Canon blocks/approves -> operator reviews evidence -> merge allowed.
7. Mobile/responsive notes only for review/approval surfaces. Full product can be desktop-first.

## UX priorities

Rank priorities in this order:

1. Trust and evidence clarity.
2. Fast diagnosis of blocked work.
3. Clear phase/status visibility.
4. Easy policy comprehension.
5. Fast dispatch of governed work.
6. Admin setup.
7. Visual polish.

## Non-goals for first design pass

- Do not design a full IDE.
- Do not design a generic chatbot.
- Do not design a Devin clone.
- Do not design a Sandcastle-like SDK docs site.
- Do not make memory browsing the main product homepage.
- Do not center the UI on raw prompts or subagent internals.
- Do not hide policy/gate failure behind vague status labels.

## One-sentence product framing for the UI

**Canon is the control room for AI-authored software: every agent run, every PR, every checkpoint, every gate, and every piece of evidence in one auditable flow.**
