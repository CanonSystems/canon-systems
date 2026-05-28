# Google Meet Media API Notes

Status: deferred pending Google Workspace Developer Preview access.

## Current Finding

In the Google Cloud API Library, the visible API is **Google Meet REST API**.
The Meet Media API path is not currently available as a normal standalone API
tile in this project.

The intended media path remains blocked until Google approves access to the
Google Workspace Developer Preview features required for real-time Meet media.
Edward has applied for access.

## Decision

Do not block the meeting bot build on Google Meet media access.

Continue development on the `local-participant` transport:

- OpenAI Realtime credentials via `OPENAI_API_KEY`
- local microphone or manually supplied audio as the first audio source
- local output or virtual microphone as the first bot speech path
- explicit image/reference intake through `canon live-plan add-reference`

Keep `meet-participant` as a manifest-supported adapter target, but treat it as
deferred until preview access is approved.

## Resume Criteria

Return to the Google Meet adapter when all are true:

- Google confirms Developer Preview access for the Workspace/project.
- The project can use the Meet media surface, not just the REST metadata API.
- We have either a permitted OAuth/service-account setup or a valid authorized
  token flow.
- `canon live-plan check-credentials --transport meet-participant` can be
  upgraded from simple env presence to an actual Google capability probe.

## Implementation Notes

The current runtime manifest records this blocker:

```bash
canon live-plan runtime-manifest --session-id <session-id> --write
```

For `--transport meet-participant`, the manifest reports:

- `google_meet.status = pending_developer_preview_access`
- `google_meet.required_env = CANON_GOOGLE_OAUTH_CLIENT_JSON or GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_MEET_MEDIA_API_TOKEN`

For `--transport local-participant`, the manifest reports:

- `google_meet.status = deferred`
- `local_participant.enabled = true`
