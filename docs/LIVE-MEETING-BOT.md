# Canon Live Meeting Bot

This document captures the Canon-native meeting participant bot path. The
current implementation now includes the durable local substrate, a localhost
meeting console, a real Google Meet media attach path, and an early Google Meet
extension dock. The old preview-access notes remain in
[GOOGLE-MEET-MEDIA-API-NOTES.md](GOOGLE-MEET-MEDIA-API-NOTES.md) for resume
history.

## Operator Journey

1. Open the Canon meeting launcher or run `canon live-plan start`.
2. Choose `company_id`, primary repo, optional additional repos, meeting ref,
   topic, mode, and expected participants.
3. The bot or operator records transcript segments, explicit visual/file/repo
   references, and proposed plan items as the meeting proceeds.
4. Every material item is created in `read_back_pending` by default. The bot
   should raise its hand and read the item back before it is confirmed.
5. At the end, `canon live-plan finalize` writes:
   - `.canon/live-plan/<session-id>/session.json`
   - `.canon/live-plan/<session-id>/runtime-manifest.json`
   - `.canon/live-plan/<session-id>/session-handoff.md`
   - `.canon/live-plan/<session-id>/transcript.md`
   - `.canon/live-plan/<session-id>/references.md`
   - `.cursor/plans/<plan-id>.plan.md`
   - `.cursor/handoffs/<session-id>/meeting-plan-handoff.md`

The generated handoff includes a fallback Cursor prompt for cases where Cursor
opens the markdown file without a Build-capable plan surface.

## Current CLI

Start a session:

```bash
canon live-plan start \
  --company-id canon \
  --repo canon-systems \
  --topic "Meeting participant bot MVP" \
  --meeting-ref "https://meet.google.com/..." \
  --participant "Edward:edward@example.com:has_voice" \
  --participant "Romi:romi@example.com:missing_voice" \
  --mode independent-hand-raise \
  --transport local-participant
```

Store reusable speaker profile metadata:

```bash
canon live-plan upsert-participant \
  --name Edward \
  --email edward@example.com \
  --voice-ref /path/to/edward-reference.wav
```

When a session starts with `--participant "Edward:edward@example.com"`, Canon
hydrates any stored voice reference metadata into the session record. The audio
file itself stays wherever the operator put it; Canon stores path and digest
metadata for the future diarization sidecar.

Attach an explicit reference, such as a screenshot:

```bash
canon live-plan add-reference \
  --session-id <session-id> \
  --type image \
  --title "Plan mode screenshot" \
  --path /path/to/screenshot.png \
  --summary "Shows missing Build button" \
  --shared-to-meeting \
  --meeting-chat-status requested
```

Add a proposed item. This defaults to `read_back_pending`:

```bash
canon live-plan propose-item \
  --session-id <session-id> \
  --type task \
  --title "Add Cursor plan handoff" \
  --content "Emit a handoff prompt that reloads the Canon plan into Cursor Plan Mode." \
  --evidence-ref ref-001
```

Confirm, amend, or reject the item:

```bash
canon live-plan confirm-item \
  --session-id <session-id> \
  --item-id item-001 \
  --status confirmed
```

Finalize the session:

```bash
canon live-plan finalize --session-id <session-id>
```

Find the latest plan later:

```bash
canon live-plan list --repo canon-systems
canon live-plan show --plan-id <plan-id> --json
canon live-plan show --latest --repo canon-systems --json
```

Check whether external transport credentials are present:

```bash
canon live-plan check-credentials --transport local-participant
```

Write the runtime contract for the meeting bot:

```bash
canon live-plan runtime-manifest --session-id <session-id> --write
```

Write the browser-extension or local-panel contract:

```bash
canon live-plan panel-manifest --session-id <session-id> --write
```

Apply pane/runtime events into the Canon session in one serialized write:

```bash
canon live-plan ingest-events \
  --session-id <session-id> \
  --events-file /path/to/events.ndjson
```

Serve the same contract over localhost for a browser extension or local meeting pane:

```bash
canon live-plan panel-http-bridge --host 127.0.0.1 --port 8765
```

HTTP routes:
- `GET /health`
- `GET /app`
- `GET /resolve-session?meeting_code=<meet-code>`
- `GET /sessions/<session-id>/panel-manifest`
- `GET /sessions/<session-id>/runtime-manifest`
- `POST /sessions/<session-id>/events`
- `POST /sessions/<session-id>/upload-reference`

`POST /sessions/<session-id>/events` accepts either:
- a single event object
- or `{ "events": [ ... ] }`

`POST /sessions/<session-id>/upload-reference` accepts `multipart/form-data`
with:
- `file`
- `title`
- `summary`
- `type`
- `shared_to_meeting`
- optional `meeting_chat_status`

The bridge stores uploads under:

```text
.canon/live-plan/<session-id>/uploads/
```

Supported event types:
- `transcript.segment`
- `reference.add`
- `item.propose`
- `item.confirm`
- `hand.raise`
- `hand.resolve`
- `mode.set`

## Meet Extension Dock

There is now a lightweight unpacked Chrome extension scaffold at:

```text
extensions/google-meet-companion/
```

What it does today:
- injects a right-side Canon dock into `https://meet.google.com/*`
- connects to the localhost bridge on `http://127.0.0.1:8765`
- auto-resolves a Canon session from the active Meet code when possible
- stores a per-meeting `session_id` in browser local storage
- shows pending item / hand-raise / evidence counts
- uploads screenshots or files directly into Canon
- supports manual transcript capture and direct task/decision proposal in-meeting
- can optionally attempt caption harvesting from the active Meet DOM when captions are available
- resolves pending items and hand raises
- opens the full local meeting console when deeper edits are needed

Load it in Chrome:

1. Open `chrome://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select `extensions/google-meet-companion`
5. Open a Google Meet tab

The extension assumes the localhost bridge is already running:

```bash
canon live-plan panel-http-bridge --host 127.0.0.1 --port 8765
```

Inspect the configured Google desktop OAuth client:

```bash
canon live-plan google-oauth-config --test-user edward.walker@family.one
```

Create a Google OAuth authorization URL for the eventual companion transport:

```bash
canon live-plan google-oauth-authorize \
  --scope https://www.googleapis.com/auth/userinfo.email
```

Exchange the returned authorization code into Canon's token cache:

```bash
canon live-plan google-oauth-exchange \
  --code <google-auth-code> \
  --state <state-from-authorize-step>
```

Refresh the cached Google OAuth token:

```bash
canon live-plan google-oauth-refresh
```

Probe the Google identity attached to the token cache:

```bash
canon live-plan google-meet-probe
```

Create a Meet space with the cached token:

```bash
canon live-plan google-meet-create-space --access-type OPEN
```

Generate a valid audio-only Meet Media API SDP offer locally with `aiortc`:

```bash
canon live-plan google-meet-generate-offer \
  --audio-streams 3 \
  --output-file .canon/live-plan/offer-audio-only.sdp
```

Send a WebRTC SDP offer to the Meet Media API and store the SDP answer:

```bash
canon live-plan google-meet-connect-active-conference \
  --name spaces/<space-id> \
  --session-id media-session-1 \
  --offer-file /path/to/offer.sdp \
  --media-scope https://www.googleapis.com/auth/meetings.conference.media.audio.readonly
```

Before authorizing for Meet Media, request both:
- `https://www.googleapis.com/auth/meetings.space.created` if you also want Canon to create spaces
- `https://www.googleapis.com/auth/meetings.space.readonly`
- one of the `meetings.conference.media.*` scopes

You can also let Canon generate the offer during the connect step:

```bash
canon live-plan google-meet-connect-active-conference \
  --name spaces/<space-id> \
  --session-id media-session-1 \
  --generate-offer
```

If Google returns `NO_ACTIVE_CONFERENCE`, the auth and signaling path is working, but the
authenticated user is not yet inside a live Meet conference for that space.

This writes the answer and trace ID to:

```text
.canon/live-plan/media/<session-id>.json
```

## Participation Controls

Two participation modes are supported in session state:

- `prompted`: the bot speaks only when explicitly addressed.
- `independent-hand-raise`: the bot may detect a clarification need, but it
  records a hand raise before speaking.

Record and resolve a hand raise:

```bash
canon live-plan raise-hand \
  --session-id <session-id> \
  --reason "Task wording needs confirmation"

canon live-plan resolve-hand \
  --session-id <session-id> \
  --hand-raise-id hand-001 \
  --status approved
```

Switch mode mid-meeting:

```bash
canon live-plan set-mode \
  --session-id <session-id> \
  --mode independent-hand-raise
```

## Cursor Handoff

The generated plan file is a Cursor-compatible markdown plan export. The
handoff file also includes a fallback prompt for Cursor sessions where opening
the saved markdown does not show a Build button:

```text
Resume Canon plan `<plan_id>` for repository `<repo>`.
Read `.cursor/plans/<plan_id>.plan.md` and `.canon/live-plan/<session-id>/session.json`.
Use only confirmed or amended meeting items by default, preserve citations to meeting references, and ask before including any unconfirmed item.
Show the implementation plan in Cursor Plan Mode with a Build action.
```

## Integration Boundaries

The runtime manifest defines the external adapter contract for:

- local participant transport
- Google Meet participant transport
- OpenAI Realtime audio participation
- diarized transcription and reusable voice profiles
- explicit image submission and optional meeting chat posting
- Canon memory/archive persistence for long-term retrieval

Required credentials for the external participant bot:

- `OPENAI_API_KEY` for Realtime voice and speech output.
- `CANON_GOOGLE_OAUTH_CLIENT_JSON` for the desktop OAuth client JSON used by
  the current Google companion path.
- `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_MEET_MEDIA_API_TOKEN` remain
  fallback options if the eventual Meet media path requires them.

## Google Meet Status

Google Meet media access is pinned as deferred. The available API Library entry
is Google Meet REST API, while the real-time media path depends on Google
Workspace Developer Preview access. Edward has applied for access.

Until access is approved, continue on `local-participant`. For local transport,
`canon live-plan runtime-manifest` marks `google_meet.status` as `deferred` and
does not require Google credentials.

The current machine-local credential path is:

```bash
export CANON_GOOGLE_OAUTH_CLIENT_JSON="$HOME/.config/canon/live-plan/google-oauth-client.json"
```

Canon now validates that JSON and exposes the expected token cache path via
`canon live-plan google-oauth-config`.

The core invariant should remain: confirmed items drive the Cursor execution
plan; unconfirmed items remain visible but do not become executable scope by
default.
