# Companion Knowledge Model

This document clarifies what the Canon meeting companion should know, what
Canon already stores today, and what still needs to be unified.

## Core Point

The companion should not be limited to meeting notes and company documents.

It should combine:

- what we said
- what we planned
- what work is actively being done
- what changed

In other words, the companion needs both:

- corporate awareness
- production-floor awareness

## Clarification About Canon Today

Canon memory is **not** just repo diffs or code snapshots.

Canon already stores multiple kinds of work evidence and memory, including:

- short-session `memory_capture` artifacts
- summaries
- decisions
- next actions
- open questions
- transcripts
- plan and handoff markdown
- phase packets under `.cursor/handoffs/...`
- checkpoint state for in-progress work
- run-ledger records for readiness and execution history
- packet/evidence archive objects
- canonical events about state transitions and retrieval

So the right statement is:

> Canon already stores meaningful production-floor memory, not just code diffs.

What is still missing is a clean, shared, companion-facing retrieval layer that
pulls those things together into one coherent answer surface.

## What The Companion Should Know

The companion should be able to answer questions from four buckets.

### 1. Meeting And Document Knowledge

- meeting notes
- transcripts
- decisions
- whitepapers
- company docs
- screenshots and attachments

This answers questions like:

- "What did we decide last time?"
- "Do we have a document on this?"

### 2. Planning Knowledge

- plans
- tasks
- dependencies
- open questions
- handoffs

This answers questions like:

- "What is the plan for this feature?"
- "What is still unresolved?"

### 3. Operational Work Knowledge

- active workstreams
- current phase status
- blocked work
- recent handoffs
- run-ledger history
- checkpoint state

This answers questions like:

- "Is someone already working on this?"
- "Where did implementation stall?"
- "Has this shipped yet?"

### 4. Code And Repo Knowledge

- code graph context
- repo notes
- recent implementation evidence
- impact relationships

This answers questions like:

- "What else does this affect?"
- "Which repo or area changed recently?"

## What Canon Already Has

Canon already has the base layers for this model.

### Historical Memory

Short-session memory captures already include structured sections for:

- summary
- decisions
- next actions
- open questions
- transcript

### Operational State

Canon already tracks live execution state through:

- checkpoints
- leases
- resume state
- run ledger
- archived evidence packets

### Code Awareness

Canon already has a graph/state/canonical/file retrieval model for coding work.

## What Is Missing

The missing piece is not raw memory collection.

The missing piece is a unified product surface for the companion so it can ask:

- what did we say
- what are we doing
- what changed
- what does that imply

without forcing the user to know which Canon subsystem holds the answer.

## Unified Retrieval Layer

To close that gap, Canon needs one companion-facing retrieval layer that sits
above the existing subsystems.

In simple terms:

- Canon keeps storing the truth in its existing systems
- the companion asks one Canon question
- Canon gathers the answer from the right places
- the user does not need to know which subsystem was used

### What Feeds The Companion

The companion should draw from four source groups.

#### A. Meeting And Document Sources

- meeting transcripts
- meeting notes
- decisions
- attachments
- whitepapers
- company documents

These answer:

- "What did we discuss?"
- "What did we decide?"
- "Do we have a document on this?"

#### B. Planning Sources

- plans
- plan items
- tasks
- dependencies
- handoffs
- open questions

These answer:

- "What is the plan?"
- "What task is this tied to?"
- "What still needs clarification?"

#### C. Operational Sources

- checkpoint state
- lease / phase ownership
- run-ledger history
- archived evidence packets
- readiness and execution status

These answer:

- "Is this actively in progress?"
- "Who is working on it?"
- "Is it blocked, passing, or shipped?"

#### D. Code And Repo Sources

- graph context
- repo notes
- implementation evidence
- impact relationships

These answer:

- "What code area does this affect?"
- "What else might break?"
- "What changed recently?"

### What CocoIndex Should Do

`cocoindex` should help with the shared searchable knowledge layer, especially
for meeting and document sources, and possibly some planning sources.

That means it is well suited to index:

- meeting notes
- transcripts
- decisions
- plans
- handoff summaries
- company docs
- attachments

Its job is:

- keep this material searchable
- keep it fresh as new material arrives
- help Canon find the right records quickly

It should not become the source of truth for:

- checkpoint state
- leases
- run-ledger authority
- permissions
- Canon product logic

### What Canon Should Answer Directly

Canon should continue to answer operational questions from its own live state
systems.

That includes:

- checkpoint state
- run-ledger state
- readiness / execution status
- repo and graph retrieval for coding work

This is important because those systems are the operational truth, not just a
search copy.

### How A User Question Should Work

When the user asks a question in the companion, Canon should classify the
question first, then pull from the right sources.

Example question types:

- memory question
- planning question
- operational question
- code impact question
- mixed question

Examples:

- "What did we decide about this?"
  - Canon should look first at meeting/doc memory and planning memory.

- "Are we already working on that?"
  - Canon should look first at operational state and planning state.

- "Will this affect the other feature?"
  - Canon should look at planning memory, operational state, and code/repo
    context.

- "What happened last time we touched this?"
  - Canon should combine meeting memory, handoffs, task history, and recent
    implementation evidence.

### Runtime Behavior

The intended runtime flow is:

1. The user asks the companion a question.
2. Canon identifies what kind of question it is.
3. Canon checks the most relevant source groups first.
4. `cocoindex` helps retrieve the meeting/doc/planning records when relevant.
5. Canon reads live operational and code state directly when relevant.
6. Canon merges the results into one answer.
7. Canon filters the final answer through its normal permissions and scope
   rules.

### What The User Should Experience

The user should experience this as one system, not several.

They should not have to think:

- "Is this in transcripts?"
- "Is this in a handoff?"
- "Is this in the run ledger?"
- "Is this in the code graph?"

They should just ask:

- "Did we already do this?"
- "Who is working on it?"
- "What did we decide?"
- "What changed?"
- "What does this affect?"

and Canon should answer from the right mix of memory and live state.

## Recommendation

Keep Canon as the source of truth.

Add a shared retrieval layer for the companion that unifies:

- meeting and document knowledge
- planning knowledge
- operational work knowledge
- code and repo knowledge

`cocoindex` is a strong candidate for the meeting/document side and possibly
some planning surfaces, but it should sit on top of Canon, not replace Canon.

Canon should continue to own:

- truth
- permissions
- tenant scoping
- operational state
- product behavior

## Product Goal

In a meeting, the companion should be able to answer:

- "We discussed this in April."
- "There is already a plan for it."
- "Implementation is in progress."
- "It is blocked on another dependency."
- "Related work changed yesterday."
- "This has not shipped yet."

That is the target behavior.
