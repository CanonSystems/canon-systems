# Meeting Pane Inventory

This document captures the current inventory of information and actions the
meeting pane is displaying or attempting to support.

It is intentionally broader than the target UX. The point is to separate the
full inventory from what should actually remain in the in-meeting pane.

## Current Inventory

### 1. Session Binding

The pane currently shows or attempts to support:

- current `session_id`
- connect or reconnect to Canon
- auto-bound meeting and session context

What it likely should support first instead:

- choose `company`
- or create `company`
- check relevant repo or repos within that company
- activate Canon for this meeting
- or ignore the pane for this meeting

### 2. Meeting State

The pane currently shows or attempts to support:

- current `plan_id`
- meeting URL or meeting code
- whether the bridge is online
- whether Meet media is attached
- current participation mode

### 3. Status Counters

The pane currently shows or attempts to support:

- pending plan items
- pending hand raises
- evidence/reference count
- transcript segment count

### 4. Evidence Intake

The pane currently shows or attempts to support:

- upload image or file
- title for artifact
- summary for artifact
- mark whether it was already visible to the meeting
- list recent evidence

### 5. Transcript Capture

The pane currently shows or attempts to support:

- manual speaker field
- manual transcript text entry
- submit transcript segment
- start or stop caption capture
- transcript capture status
- list recent transcript segments

### 6. Plan Authoring

The pane currently shows or attempts to support:

- propose item type
- propose item title
- propose item content
- attach evidence refs
- create pending item

### 7. Verification Queue

The pane currently shows or attempts to support:

- show pending items
- show read-back wording
- confirm item
- reject item

### 8. AI Participation Controls

The pane currently shows or attempts to support:

- raise hand with reason
- prompt vs `independent-hand-raise` mode
- show pending hand raises
- approve or dismiss pending hand raises

### 9. Navigation / Escalation

The pane currently shows or attempts to support:

- open the full localhost console for deeper work

## What The Pane Probably Actually Needs

The current confusion appears to come from three structural problems:

- too many forms
- too many equal-weight sections
- no separation between in-meeting quick actions and deeper operator workflow

The in-meeting pane likely needs much less.

### A. AI Status

The pane should clearly communicate only:

- listening
- wants to speak
- waiting for confirmation

### B. Current Agenda Item

The pane should focus on:

- the single item being discussed or verified right now

### C. One Primary Input

The pane should likely allow one quick action at a time:

- send screenshot or file
- or add transcript note

It should not force five different forms into the same visible surface.

### D. Verification Queue

The pane should prominently support:

- items awaiting read-back confirmation
- approve
- amend
- reject

### E. AI Controls

The pane should likely keep:

- prompt mode toggle
- allow AI to speak
- dismiss hand raise

### F. Recent Evidence

The pane should likely show:

- a compact recent evidence strip or list

It should not behave like a full evidence-management console.

## Likely Split

### Meeting Pane

The pane inside Meet should be:

- small
- reactive
- focused on live conversation support

### Full Console

The full console should be:

- detailed
- archival
- for manual editing
- for session management
- for debugging

## Working Conclusion

The current pane is trying to serve as both:

- a live in-meeting assistant surface
- a full operator console

Those need to be separated more aggressively in the next refinement pass.
