from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from canon_systems import cli
from canon_systems import live_plan


def _state(tmp_path: Path, session_id: str) -> dict:
    p = tmp_path / ".canon" / "live-plan" / session_id / "session.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_start_creates_session_with_participants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    rc = live_plan.run([
        "start",
        "--company-id",
        "canon",
        "--repo",
        "canon-systems",
        "--topic",
        "Meeting bot MVP",
        "--meeting-ref",
        "https://meet.google.com/abc-defg-hij",
        "--participant",
        "Edward:edward@example.com:has_voice",
        "--participant",
        "Romi:romi@example.com:missing_voice",
        "--session-id",
        "meet-1",
        "--plan-id",
        "plan-meet-1",
        "--json",
    ])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["session_id"] == "meet-1"
    data = _state(tmp_path, "meet-1")
    assert data["plan_id"] == "plan-meet-1"
    assert data["participants"][0]["voice_profile_status"] == "has_voice"
    assert data["participants"][1]["name"] == "Romi"


def test_participant_registry_hydrates_voice_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    voice = tmp_path / "edward.wav"
    voice.write_bytes(b"fake-audio")
    assert live_plan.run([
        "upsert-participant",
        "--name",
        "Edward",
        "--email",
        "edward@example.com",
        "--voice-ref",
        str(voice),
    ]) == 0
    person = json.loads(capsys.readouterr().out)["participant"]
    assert person["voice_refs"][0]["status"] == "available"
    assert person["voice_refs"][0]["sha256"]

    assert live_plan.run([
        "start",
        "--company-id",
        "canon",
        "--repo",
        "canon-systems",
        "--topic",
        "Voice registry",
        "--participant",
        "Edward:edward@example.com",
        "--session-id",
        "voice-session",
        "--plan-id",
        "voice-plan",
    ]) == 0
    data = _state(tmp_path, "voice-session")
    assert data["participants"][0]["voice_profile_status"] == "has_voice"
    assert data["participants"][0]["voice_refs"][0]["path"] == str(voice.resolve())


def test_reference_transcript_proposal_confirmation_and_finalize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id",
        "canon",
        "--repo",
        "canon-systems",
        "--topic",
        "Cursor handoff",
        "--session-id",
        "meet-2",
        "--plan-id",
        "cursor-handoff-plan",
    ]) == 0
    capsys.readouterr()

    assert live_plan.run([
        "add-reference",
        "--session-id",
        "meet-2",
        "--type",
        "image",
        "--title",
        "Plan mode screenshot",
        "--path",
        "/tmp/plan.png",
        "--summary",
        "Shows missing Build button",
        "--shared-to-meeting",
    ]) == 0
    ref_out = json.loads(capsys.readouterr().out)
    assert ref_out["reference"]["ref_id"] == "ref-001"
    assert ref_out["reference"]["shared_to_meeting"] is True

    assert live_plan.run([
        "add-transcript",
        "--session-id",
        "meet-2",
        "--speaker",
        "Edward",
        "--text",
        "The bot needs to verify each plan item before adding it.",
    ]) == 0
    capsys.readouterr()

    assert live_plan.run([
        "propose-item",
        "--session-id",
        "meet-2",
        "--type",
        "task",
        "--title",
        "Add read-back verification",
        "--content",
        "Require confirm, amend, or reject before an item enters the execution plan.",
        "--evidence-ref",
        "ref-001",
    ]) == 0
    proposed = json.loads(capsys.readouterr().out)
    assert proposed["hand_raise"] is True
    assert proposed["hand_raise_event"]["item_id"] == "item-001"
    assert proposed["item"]["status"] == "read_back_pending"
    assert "So the item reads like this" in proposed["item"]["verification_prompt"]

    assert live_plan.run([
        "confirm-item",
        "--session-id",
        "meet-2",
        "--item-id",
        "item-001",
        "--status",
        "confirmed",
    ]) == 0
    confirm_out = json.loads(capsys.readouterr().out)
    assert confirm_out["linked_hand_raise"]["item_id"] == "item-001"
    assert confirm_out["linked_hand_raise"]["status"] == "approved"

    assert live_plan.run(["finalize", "--session-id", "meet-2"]) == 0
    finalized = json.loads(capsys.readouterr().out)
    plan_file = Path(finalized["plan_file"])
    handoff_file = Path(finalized["handoff_file"])
    assert finalized["confirmed_items"] == 1
    assert plan_file.exists()
    assert handoff_file.exists()
    plan_text = plan_file.read_text(encoding="utf-8")
    assert "Add read-back verification" in plan_text
    assert "ref-001" in plan_text
    assert "Show the implementation plan in Cursor Plan Mode with a Build action" in handoff_file.read_text(encoding="utf-8")
    assert Path(finalized["session_handoff_file"]).exists()
    assert "The bot needs to verify each plan item" in Path(finalized["transcript_file"]).read_text(
        encoding="utf-8"
    )
    assert "Plan mode screenshot" in Path(finalized["references_file"]).read_text(
        encoding="utf-8"
    )
    manifest = json.loads(Path(finalized["runtime_manifest_file"]).read_text(encoding="utf-8"))
    assert manifest["visuals"]["full_video_processing"] is False
    assert "propose_item" in manifest["tool_broker"]["planning_tools"]

    assert live_plan.run([
        "show",
        "--plan-id",
        "cursor-handoff-plan",
        "--json",
    ]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["session_id"] == "meet-2"


def test_unconfirmed_items_are_not_plan_todos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id",
        "canon",
        "--repo",
        "canon-systems",
        "--topic",
        "Unconfirmed scope",
        "--session-id",
        "meet-3",
        "--plan-id",
        "unconfirmed-plan",
    ]) == 0
    assert live_plan.run([
        "propose-item",
        "--session-id",
        "meet-3",
        "--type",
        "task",
        "--title",
        "Do not include yet",
        "--content",
        "This item has not been read back.",
    ]) == 0
    assert live_plan.run(["finalize", "--session-id", "meet-3"]) == 0
    plan_text = (tmp_path / ".cursor" / "plans" / "unconfirmed-plan.plan.md").read_text(
        encoding="utf-8"
    )
    assert "review_meeting_plan" in plan_text
    assert "- item-001 [read_back_pending] Do not include yet" in plan_text


def test_hand_raise_mode_and_session_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id",
        "canon",
        "--repo",
        "canon-systems",
        "--topic",
        "Hand raise",
        "--session-id",
        "meet-4",
        "--plan-id",
        "hand-plan",
        "--mode",
        "prompted",
        "--transport",
        "meet-participant",
    ]) == 0
    capsys.readouterr()
    assert live_plan.run([
        "set-mode",
        "--session-id",
        "meet-4",
        "--mode",
        "independent-hand-raise",
    ]) == 0
    mode_out = json.loads(capsys.readouterr().out)
    assert mode_out["old_mode"] == "prompted"

    assert live_plan.run([
        "raise-hand",
        "--session-id",
        "meet-4",
        "--reason",
        "Task wording needs confirmation",
    ]) == 0
    hand = json.loads(capsys.readouterr().out)["hand_raise"]
    assert hand["status"] == "pending"
    assert hand["hand_raise_id"] == "hand-001"

    assert live_plan.run([
        "resolve-hand",
        "--session-id",
        "meet-4",
        "--hand-raise-id",
        "hand-001",
        "--status",
        "approved",
    ]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "approved"
    assert live_plan.run(["finalize", "--session-id", "meet-4"]) == 0
    capsys.readouterr()

    assert live_plan.run(["list", "--repo", "canon-systems", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["sessions"][0]["plan_id"] == "hand-plan"


def test_check_credentials_reports_missing_and_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_MEET_MEDIA_API_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    assert live_plan.run(["check-credentials", "--transport", "meet-participant"]) == 0
    missing = json.loads(capsys.readouterr().out)
    assert missing["ready"] is False
    assert missing["openai_realtime"]["status"] == "missing"

    oauth_path = tmp_path / "google-oauth-client.json"
    oauth_path.write_text(json.dumps({
        "installed": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "project_id": "plan-to-jira",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }), encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", str(oauth_path))
    assert live_plan.run(["check-credentials", "--transport", "meet-participant", "--require-ready"]) == 0
    ready = json.loads(capsys.readouterr().out)
    assert ready["ready"] is True
    assert ready["google_meet"]["present_env"] == ["CANON_GOOGLE_OAUTH_CLIENT_JSON"]
    assert ready["google_meet"]["oauth_client"]["project_id"] == "plan-to-jira"


def test_runtime_manifest_command_writes_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id",
        "canon",
        "--repo",
        "canon-systems",
        "--topic",
        "Runtime",
        "--session-id",
        "runtime-session",
        "--plan-id",
        "runtime-plan",
        "--transport",
        "meet-participant",
    ]) == 0
    capsys.readouterr()
    assert live_plan.run(["runtime-manifest", "--session-id", "runtime-session", "--write"]) == 0
    out = json.loads(capsys.readouterr().out)
    path = Path(out["runtime_manifest_file"])
    assert path.exists()
    assert out["runtime_manifest"]["google_meet"]["speech_output"] == "bot-participant-audio-output"
    assert out["runtime_manifest"]["google_meet"]["status"] == "configured"
    assert out["runtime_manifest"]["google_meet"]["required_env"][0] == "CANON_GOOGLE_OAUTH_CLIENT_JSON"
    assert out["runtime_manifest"]["google_meet"]["oauth_client"]["env"] == "CANON_GOOGLE_OAUTH_CLIENT_JSON"


def test_local_participant_manifest_defers_google_meet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id",
        "canon",
        "--repo",
        "canon-systems",
        "--topic",
        "Local transport",
        "--session-id",
        "local-session",
        "--plan-id",
        "local-plan",
        "--transport",
        "local-participant",
    ]) == 0
    capsys.readouterr()
    assert live_plan.run(["runtime-manifest", "--session-id", "local-session"]) == 0
    manifest = json.loads(capsys.readouterr().out)["runtime_manifest"]
    assert manifest["local_participant"]["enabled"] is True
    assert manifest["google_meet"]["status"] == "deferred"
    assert manifest["google_meet"]["required_env"] == []


def test_google_oauth_config_reads_client_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    oauth_path = tmp_path / "google-oauth-client.json"
    oauth_path.write_text(json.dumps({
        "installed": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "project_id": "plan-to-jira",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }), encoding="utf-8")
    monkeypatch.setenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", str(oauth_path))

    assert live_plan.run(["google-oauth-config", "--test-user", "edward.walker@family.one"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["google_oauth_client"]["client_id"] == "client-id.apps.googleusercontent.com"
    assert out["auth_flow"]["test_user_email"] == "edward.walker@family.one"


def test_google_oauth_authorize_writes_pending_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    oauth_path = tmp_path / "google-oauth-client.json"
    oauth_path.write_text(json.dumps({
        "installed": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "project_id": "plan-to-jira",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }), encoding="utf-8")
    monkeypatch.setenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", str(oauth_path))

    assert live_plan.run([
        "google-oauth-authorize",
        "--scope",
        "scope-a",
        "--scope",
        "scope-b",
    ]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "https://accounts.google.com/o/oauth2/auth?" in out["authorization_url"]
    assert out["scope"] == ["scope-a", "scope-b"]
    session = json.loads(Path(out["oauth_session_file"]).read_text(encoding="utf-8"))
    assert session["scope"] == ["scope-a", "scope-b"]


def test_google_oauth_exchange_stores_token_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    oauth_path = tmp_path / "google-oauth-client.json"
    oauth_path.write_text(json.dumps({
        "installed": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "project_id": "plan-to-jira",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }), encoding="utf-8")
    monkeypatch.setenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", str(oauth_path))
    session_path = tmp_path / ".canon" / "live-plan" / "google-oauth-session.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps({
        "state": "abc123",
        "redirect_uri": "http://localhost",
        "code_verifier": "verifier",
        "scope": ["scope-a"],
    }), encoding="utf-8")

    def fake_post(url: str, form: dict[str, str]) -> dict[str, str]:
        assert url == "https://oauth2.googleapis.com/token"
        assert form["code"] == "auth-code"
        assert form["code_verifier"] == "verifier"
        return {
            "access_token": "token",
            "refresh_token": "refresh",
            "token_type": "Bearer",
            "scope": "scope-a",
        }

    monkeypatch.setattr(live_plan, "_post_form_json", fake_post)
    assert live_plan.run([
        "google-oauth-exchange",
        "--code",
        "auth-code",
        "--state",
        "abc123",
    ]) == 0
    out = json.loads(capsys.readouterr().out)
    token_cache = json.loads(Path(out["token_cache_file"]).read_text(encoding="utf-8"))
    assert token_cache["access_token"] == "token"
    assert out["has_refresh_token"] is True


def test_google_oauth_refresh_updates_cached_access_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    oauth_path = tmp_path / "google-oauth-client.json"
    oauth_path.write_text(json.dumps({
        "installed": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "project_id": "plan-to-jira",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }), encoding="utf-8")
    monkeypatch.setenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", str(oauth_path))
    token_path = tmp_path / ".canon" / "live-plan" / "google-oauth-token.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps({
        "access_token": "old-token",
        "refresh_token": "refresh",
        "expires_in": 1,
        "obtained_at": "2020-01-01T00:00:00Z",
        "scope": "scope-a",
    }), encoding="utf-8")

    def fake_post(url: str, form: dict[str, str]) -> dict[str, str]:
        assert form["refresh_token"] == "refresh"
        return {
            "access_token": "new-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "scope-a",
        }

    monkeypatch.setattr(live_plan, "_post_form_json", fake_post)
    assert live_plan.run(["google-oauth-refresh", "--force"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["has_refresh_token"] is True
    refreshed = json.loads(token_path.read_text(encoding="utf-8"))
    assert refreshed["access_token"] == "new-token"


def test_google_meet_probe_calls_userinfo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", str(tmp_path / "client.json"))
    (tmp_path / "client.json").write_text(json.dumps({
        "installed": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "project_id": "plan-to-jira",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }), encoding="utf-8")
    token_path = tmp_path / ".canon" / "live-plan" / "google-oauth-token.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps({
        "access_token": "token",
        "refresh_token": "refresh",
        "expires_in": 3600,
        "obtained_at": "2999-01-01T00:00:00Z",
        "scope": "openid https://www.googleapis.com/auth/userinfo.email",
    }), encoding="utf-8")

    def fake_http(method: str, url: str, *, headers: dict[str, str] | None = None, json_body: dict | None = None) -> dict:
        assert method == "GET"
        assert url == "https://openidconnect.googleapis.com/v1/userinfo"
        assert headers and headers["Authorization"] == "Bearer token"
        return {"email": "edward.walker@family.one", "email_verified": True}

    monkeypatch.setattr(live_plan, "_http_json_request", fake_http)
    assert live_plan.run(["google-meet-probe"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["google_userinfo"]["email"] == "edward.walker@family.one"


def test_google_meet_create_space_posts_to_meet_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", str(tmp_path / "client.json"))
    (tmp_path / "client.json").write_text(json.dumps({
        "installed": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "project_id": "plan-to-jira",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }), encoding="utf-8")
    token_path = tmp_path / ".canon" / "live-plan" / "google-oauth-token.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps({
        "access_token": "token",
        "refresh_token": "refresh",
        "expires_in": 3600,
        "obtained_at": "2999-01-01T00:00:00Z",
        "scope": "https://www.googleapis.com/auth/meetings.space.created",
    }), encoding="utf-8")

    def fake_http(method: str, url: str, *, headers: dict[str, str] | None = None, json_body: dict | None = None) -> dict:
        assert method == "POST"
        assert url == "https://meet.googleapis.com/v2/spaces"
        assert json_body == {"config": {"accessType": "OPEN"}}
        return {"name": "spaces/abc-defg-hij", "meetingUri": "https://meet.google.com/abc-defg-hij"}

    monkeypatch.setattr(live_plan, "_http_json_request", fake_http)
    assert live_plan.run(["google-meet-create-space", "--access-type", "OPEN"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["space"]["name"] == "spaces/abc-defg-hij"


def test_google_meet_connect_active_conference_stores_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", str(tmp_path / "client.json"))
    (tmp_path / "client.json").write_text(json.dumps({
        "installed": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "project_id": "plan-to-jira",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }), encoding="utf-8")
    token_path = tmp_path / ".canon" / "live-plan" / "google-oauth-token.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps({
        "access_token": "token",
        "refresh_token": "refresh",
        "expires_in": 3600,
        "obtained_at": "2999-01-01T00:00:00Z",
        "scope": (
            "https://www.googleapis.com/auth/meetings.space.readonly "
            "https://www.googleapis.com/auth/meetings.conference.media.audio.readonly"
        ),
    }), encoding="utf-8")
    offer_file = tmp_path / "offer.sdp"
    offer_file.write_text("v=0\nm=audio 9 UDP/TLS/RTP/SAVPF 111\n", encoding="utf-8")

    def fake_http(method: str, url: str, *, headers: dict[str, str] | None = None, json_body: dict | None = None) -> dict:
        assert method == "POST"
        assert url == "https://meet.googleapis.com/v2beta/spaces/abc123:connectActiveConference"
        assert json_body == {"offer": "v=0\nm=audio 9 UDP/TLS/RTP/SAVPF 111\n"}
        return {"answer": "v=0\nm=audio 9 UDP/TLS/RTP/SAVPF 111\n", "traceId": "trace-123"}

    monkeypatch.setattr(live_plan, "_http_json_request", fake_http)
    assert live_plan.run([
        "google-meet-connect-active-conference",
        "--name",
        "spaces/abc123",
        "--session-id",
        "media-1",
        "--offer-file",
        str(offer_file),
    ]) == 0
    out = json.loads(capsys.readouterr().out)
    artifact = json.loads(Path(out["media_session_file"]).read_text(encoding="utf-8"))
    assert artifact["trace_id"] == "trace-123"
    assert artifact["space"] == "spaces/abc123"


def test_google_meet_generate_offer_writes_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(
        live_plan,
        "_generate_meet_sdp_offer",
        lambda **_: "v=0\nm=audio 9 UDP/TLS/RTP/SAVPF 111\n",
    )
    output = tmp_path / "offer.sdp"
    assert live_plan.run([
        "google-meet-generate-offer",
        "--output-file",
        str(output),
    ]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["output_file"] == str(output.resolve())
    assert output.read_text(encoding="utf-8") == "v=0\nm=audio 9 UDP/TLS/RTP/SAVPF 111\n"


def test_google_meet_bind_space_updates_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", str(tmp_path / "client.json"))
    (tmp_path / "client.json").write_text(json.dumps({
        "installed": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "project_id": "plan-to-jira",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }), encoding="utf-8")
    token_path = tmp_path / ".canon" / "live-plan" / "google-oauth-token.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps({
        "access_token": "token",
        "refresh_token": "refresh",
        "expires_in": 3600,
        "obtained_at": "2999-01-01T00:00:00Z",
        "scope": "https://www.googleapis.com/auth/meetings.space.readonly",
    }), encoding="utf-8")
    assert live_plan.run([
        "start",
        "--company-id", "familyone",
        "--repo", "canon-systems",
        "--topic", "Bind space",
        "--transport", "meet-participant",
        "--json",
    ]) == 0
    session_id = json.loads(capsys.readouterr().out)["session_id"]

    def fake_http(method: str, url: str, *, headers: dict[str, str] | None = None, json_body: dict | None = None) -> dict:
        assert method == "GET"
        assert url == "https://meet.googleapis.com/v2/spaces/abc123"
        return {"name": "spaces/abc123", "meetingUri": "https://meet.google.com/abc-defg-hij", "meetingCode": "abc-defg-hij"}

    monkeypatch.setattr(live_plan, "_http_json_request", fake_http)
    assert live_plan.run([
        "google-meet-bind-space",
        "--session-id", session_id,
        "--name", "spaces/abc123",
    ]) == 0
    state = json.loads((tmp_path / ".canon" / "live-plan" / session_id / "session.json").read_text(encoding="utf-8"))
    assert state["meeting_ref"] == "https://meet.google.com/abc-defg-hij"
    assert state["google_meet"]["space"] == "spaces/abc123"
    assert state["transport"]["credential_status"] == "configured"


def test_google_meet_connect_active_conference_can_generate_offer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("CANON_GOOGLE_OAUTH_CLIENT_JSON", str(tmp_path / "client.json"))
    (tmp_path / "client.json").write_text(json.dumps({
        "installed": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "project_id": "plan-to-jira",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }), encoding="utf-8")
    token_path = tmp_path / ".canon" / "live-plan" / "google-oauth-token.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps({
        "access_token": "token",
        "refresh_token": "refresh",
        "expires_in": 3600,
        "obtained_at": "2999-01-01T00:00:00Z",
        "scope": (
            "https://www.googleapis.com/auth/meetings.space.readonly "
            "https://www.googleapis.com/auth/meetings.conference.media.audio.readonly"
        ),
    }), encoding="utf-8")
    monkeypatch.setattr(
        live_plan,
        "_generate_meet_sdp_offer",
        lambda **_: "v=0\nm=audio 9 UDP/TLS/RTP/SAVPF 111\n",
    )

    def fake_http(method: str, url: str, *, headers: dict[str, str] | None = None, json_body: dict | None = None) -> dict:
        assert method == "POST"
        assert url == "https://meet.googleapis.com/v2beta/spaces/abc123:connectActiveConference"
        assert json_body == {"offer": "v=0\nm=audio 9 UDP/TLS/RTP/SAVPF 111\n"}
        return {"answer": "v=0\nm=audio 9 UDP/TLS/RTP/SAVPF 111\n", "traceId": "trace-generated"}

    monkeypatch.setattr(live_plan, "_http_json_request", fake_http)
    assert live_plan.run([
        "google-meet-connect-active-conference",
        "--name",
        "spaces/abc123",
        "--session-id",
        "media-generated",
        "--generate-offer",
    ]) == 0
    out = json.loads(capsys.readouterr().out)
    artifact = json.loads(Path(out["media_session_file"]).read_text(encoding="utf-8"))
    assert artifact["generated_offer"] is True
    assert artifact["trace_id"] == "trace-generated"


def test_google_meet_attach_media_updates_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id", "familyone",
        "--repo", "canon-systems",
        "--topic", "Attach media",
        "--transport", "meet-participant",
        "--json",
    ]) == 0
    session_id = json.loads(capsys.readouterr().out)["session_id"]
    media_path = tmp_path / ".canon" / "live-plan" / "media" / "media-1.json"
    media_path.parent.mkdir(parents=True, exist_ok=True)
    media_path.write_text(json.dumps({
        "session_id": "media-1",
        "space": "spaces/abc123",
        "trace_id": "trace-123",
        "audio_streams": 3,
        "video_streams": 0,
        "generated_offer": True,
        "answer": "v=0\n",
    }), encoding="utf-8")
    answer_file = tmp_path / "answer.sdp"
    assert live_plan.run([
        "google-meet-attach-media",
        "--session-id", session_id,
        "--media-session-id", "media-1",
        "--answer-file", str(answer_file),
    ]) == 0
    state = json.loads((tmp_path / ".canon" / "live-plan" / session_id / "session.json").read_text(encoding="utf-8"))
    assert state["transport"]["credential_status"] == "attached"
    assert state["google_meet"]["media_session"]["trace_id"] == "trace-123"
    assert answer_file.read_text(encoding="utf-8") == "v=0\n"


def test_panel_manifest_reports_pending_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id", "familyone",
        "--repo", "canon-systems",
        "--topic", "Panel manifest",
        "--transport", "meet-participant",
        "--json",
    ]) == 0
    session_id = json.loads(capsys.readouterr().out)["session_id"]
    assert live_plan.run([
        "propose-item",
        "--session-id", session_id,
        "--type", "task",
        "--title", "Confirm wording",
        "--content", "Read the item back to the room.",
    ]) == 0
    capsys.readouterr()
    assert live_plan.run([
        "raise-hand",
        "--session-id", session_id,
        "--reason", "Need to confirm wording.",
    ]) == 0
    capsys.readouterr()
    assert live_plan.run(["panel-manifest", "--session-id", session_id]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["panel_manifest"]["status"]["pending_plan_items"] == 1
    assert out["panel_manifest"]["pending_items"][0]["item_id"] == "item-001"
    assert out["panel_manifest"]["pending_hand_raises"][0]["hand_raise_id"] == "hand-001"
    assert "reference.add" in out["panel_manifest"]["event_types"]


def test_ingest_events_applies_multiple_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id", "familyone",
        "--repo", "canon-systems",
        "--topic", "Event ingest",
        "--transport", "meet-participant",
        "--json",
    ]) == 0
    session_id = json.loads(capsys.readouterr().out)["session_id"]
    events_file = tmp_path / "events.ndjson"
    events_file.write_text(
        "\n".join([
            json.dumps({
                "type": "transcript.segment",
                "payload": {"speaker": "Edward", "text": "We should split auth and UI."},
            }),
            json.dumps({
                "type": "reference.add",
                "payload": {
                    "type": "image",
                    "title": "Bug screenshot",
                    "path": "/tmp/bug.png",
                    "shared_to_meeting": True,
                    "meeting_chat_status": "posted",
                },
            }),
            json.dumps({
                "type": "item.propose",
                "payload": {
                    "item_type": "task",
                    "title": "Split auth and UI",
                    "content": "Create separate tasks for auth fixes and UI fixes.",
                    "evidence_refs": ["ref-001"],
                },
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    assert live_plan.run([
        "ingest-events",
        "--session-id", session_id,
        "--events-file", str(events_file),
    ]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["applied_count"] == 3
    state = json.loads((tmp_path / ".canon" / "live-plan" / session_id / "session.json").read_text(encoding="utf-8"))
    assert len(state["transcript_segments"]) == 1
    assert len(state["references"]) == 1
    assert len(state["plan_items"]) == 1
    assert state["plan_items"][0]["status"] == "read_back_pending"
    assert len(state["hand_raises"]) == 1
    assert state["hand_raises"][0]["item_id"] == "item-001"


def test_item_confirm_resolves_linked_pending_hand_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id", "familyone",
        "--repo", "canon-systems",
        "--topic", "Linked hand raise",
        "--json",
    ]) == 0
    session_id = json.loads(capsys.readouterr().out)["session_id"]
    assert live_plan.run([
        "ingest-events",
        "--session-id", session_id,
        "--event-json", json.dumps({
            "type": "item.propose",
            "payload": {
                "item_type": "task",
                "title": "Read back a task",
                "content": "Confirm it from the queue.",
                "requires_confirmation": True,
            },
        }),
    ]) == 0
    capsys.readouterr()
    assert live_plan.run([
        "ingest-events",
        "--session-id", session_id,
        "--event-json", json.dumps({
            "type": "item.confirm",
            "payload": {
                "item_id": "item-001",
                "status": "confirmed",
            },
        }),
    ]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["applied"][0]["hand_raise"]["status"] == "approved"
    state = _state(tmp_path, session_id)
    assert state["hand_raises"][0]["status"] == "approved"


def test_panel_http_bridge_serves_and_ingests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id", "familyone",
        "--repo", "canon-systems",
        "--topic", "HTTP bridge",
        "--transport", "meet-participant",
        "--json",
    ]) == 0
    session_id = json.loads(capsys.readouterr().out)["session_id"]

    server = live_plan.http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        live_plan._build_panel_bridge_handler(tmp_path),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["ok"] is True

        with urllib.request.urlopen(f"http://{host}:{port}/app", timeout=5) as resp:
            html = resp.read().decode("utf-8")
        assert "Canon Meeting Console" in html

        with urllib.request.urlopen(f"http://{host}:{port}/static/live-plan-panel/app.js", timeout=5) as resp:
            js = resp.read().decode("utf-8")
        assert "uploadReference" in js

        req = urllib.request.Request(
            f"http://{host}:{port}/sessions/{session_id}/events",
            data=json.dumps({
                "events": [
                    {
                        "type": "transcript.segment",
                        "payload": {"speaker": "Edward", "text": "HTTP ingress works."},
                    },
                    {
                        "type": "hand.raise",
                        "payload": {"reason": "Need confirmation."},
                    },
                ]
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            applied = json.loads(resp.read().decode("utf-8"))
        assert applied["applied_count"] == 2

        with urllib.request.urlopen(f"http://{host}:{port}/sessions/{session_id}/panel-manifest", timeout=5) as resp:
            manifest = json.loads(resp.read().decode("utf-8"))
        assert manifest["panel_manifest"]["status"]["pending_hand_raises"] == 1
        assert manifest["panel_manifest"]["status"]["transcript_segment_count"] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_panel_http_bridge_uploads_reference_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id", "familyone",
        "--repo", "canon-systems",
        "--topic", "HTTP upload",
        "--transport", "meet-participant",
        "--json",
    ]) == 0
    session_id = json.loads(capsys.readouterr().out)["session_id"]

    server = live_plan.http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        live_plan._build_panel_bridge_handler(tmp_path),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        boundary = "----canon-upload-boundary"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="type"\r\n\r\n'
            "image\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="title"\r\n\r\n'
            "Bug screenshot\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="summary"\r\n\r\n'
            "Shows the broken plan surface.\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="shared_to_meeting"\r\n\r\n'
            "true\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="bug.png"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode("utf-8") + b"fake-png-bytes" + f"\r\n--{boundary}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            f"http://{host}:{port}/sessions/{session_id}/upload-reference",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["reference"]["type"] == "image"
        assert payload["reference"]["metadata"]["original_name"] == "bug.png"
        assert payload["reference"]["metadata"]["content_type"] == "image/png"

        state = _state(tmp_path, session_id)
        assert state["references"][0]["title"] == "Bug screenshot"
        assert Path(state["references"][0]["path"]).exists()
        assert state["references"][0]["meeting_chat_status"] == "posted"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_panel_http_bridge_resolves_session_by_meeting_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CANON_SYSTEMS_REPO_ROOT", str(tmp_path))
    assert live_plan.run([
        "start",
        "--company-id", "familyone",
        "--repo", "canon-systems",
        "--topic", "Resolve by meeting code",
        "--transport", "meet-participant",
        "--meeting-ref", "https://meet.google.com/aty-uenx-rkr",
        "--session-id", "resolve-session-1",
        "--plan-id", "resolve-plan-1",
        "--json",
    ]) == 0
    capsys.readouterr()
    state = _state(tmp_path, "resolve-session-1")
    state["google_meet"] = {
        "space": "spaces/abc123",
        "meeting_uri": "https://meet.google.com/aty-uenx-rkr",
        "meeting_code": "aty-uenx-rkr",
    }
    live_plan._write_state(tmp_path, state)

    server = live_plan.http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        live_plan._build_panel_bridge_handler(tmp_path),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with urllib.request.urlopen(
            f"http://{host}:{port}/resolve-session?meeting_code=aty-uenx-rkr",
            timeout=5,
        ) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["match"]["session_id"] == "resolve-session-1"
        assert payload["match"]["plan_id"] == "resolve-plan-1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_top_level_cli_dispatches_live_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(cli, "run_live_plan", fake)
    assert cli.main(["live-plan", "show", "--session-id", "s1"]) == 0
    assert captured["argv"] == ["show", "--session-id", "s1"]
