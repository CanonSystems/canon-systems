# Planning Companion User Journey

This document captures the intended user journey for the Canon planning
companion as it moves from meeting start through Cursor handoff.

## Goal

The experience should feel like one continuous workflow:

`launch session -> bot joins -> listen quietly -> intervene when needed -> read back and verify items -> capture evidence -> recap -> hand off to Cursor`

The companion should reduce interpretation loss between human discussion and
implementation.

## 1. Before The Meeting

The host starts from Canon organizational context first:

- choose a `company`
- or create a new `company` if needed
- see repos listed within that company
- check the repo or repos relevant to the conversation
- optionally attach an existing plan or prior handoff
- optionally attach the meeting link

Canon then resolves likely context in the background:

- recent related plans
- known participants
- whether voice profiles exist
- whether there is already a live planning thread for this topic

This should feel like selecting scope, not configuring a system.

## 2. The Pane Appears

The meeting pane can load on every Google Meet by default.

The user should then decide:

- `Use Canon for this meeting`
- or ignore it because the meeting does not need planning support

If the user chooses yes:

- the pane activates
- the selected company and repos become the meeting scope
- the bot joins as a participant

If the user chooses no:

- the pane stays passive or collapses
- the bot does not join
- Canon does not start a planning session

The pane should immediately answer only a few questions:

- is the bot connected?
- what repo/context is it using?
- is it in `prompted` or `independent` mode?
- does it currently need attention?

The pane should not open by asking the user to fill in a large amount of data.

## 3. Live Discussion Starts

Humans talk normally. The bot listens and quietly builds structure in the
background:

- transcript segments
- decisions
- candidate tasks
- unresolved questions
- dependencies
- cited references

Most of that structure should stay out of the way unless the meeting needs it.
The pane should feel calm while discussion is flowing.

## 4. A Clarification Moment Happens

The bot notices ambiguity or a task worth locking down.

Instead of surfacing a complex UI, it should do one clear thing:

- raise its hand
- show a one-line reason
- if invited, speak briefly

Examples:

- “I think this should be split into two tasks.”
- “I’m missing the acceptance criteria for this item.”

This is the core value of the companion: intervene only when it matters.

## 5. A Plan Item Is Read Back

When something concrete is ready, the bot reads it back.

The pane should spotlight only one interaction:

- the exact wording of the item
- `Confirm`
- `Amend`
- `Reject`

This is the most important interaction in the product. It should feel like
approving a contract clause, not filling out a form.

## 6. Visual Evidence Is Added

Someone wants the bot to look at a screen, mockup, or error.

The user performs one action:

- send screenshot, file, or selected view to Canon

The pane should acknowledge:

- received
- linked to the current discussion
- optionally visible to the room

The user should not have to manage detailed metadata unless they choose to.

## 7. The Meeting Progresses

As more items are confirmed, the pane should gradually show:

- confirmed items count
- pending item count
- unresolved questions count

Not the full archive, just enough to orient the room.

If needed, the user can open the full console for:

- detailed transcript edits
- manual artifact management
- session debugging
- older references

## 8. Meeting Close

Near the end, the host asks for a recap or the bot offers one.

The bot gives a concise closeout:

- what was decided
- what is still open
- what tasks were confirmed
- what order implementation should likely follow

The pane should then offer a clean handoff state:

- `Plan ready`
- `Open in full console`
- `Send to Cursor`

## 9. Post-Meeting Handoff

Canon writes the durable artifacts:

- transcript
- references
- plan items
- handoff
- Cursor plan file

The engineer should not need to copy-paste. They should be able to reopen the
plan from Canon memory or send it directly into the Cursor workflow.

## 10. In Cursor

Cursor should start from a verified plan, not a vague transcript.

That means the coding flow begins with:

- confirmed task wording
- linked evidence
- unresolved questions explicitly marked
- prior meeting context available by `plan_id`

## Product States

If the pane is simplified around this journey, it should center on five live
states:

- `Listening`
- `Needs clarification`
- `Verifying item`
- `Evidence received`
- `Plan ready`

Everything else should be secondary.
