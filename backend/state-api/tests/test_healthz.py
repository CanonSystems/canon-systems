"""Health endpoint (table configured vs degraded)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from state_api.main import app


def test_healthz_ok_when_table_set(monkeypatch) -> None:
    monkeypatch.setenv("STATE_TABLE_NAME", "my-table")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    with TestClient(app) as client:
        r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "state-api"
    assert body["table"] == "my-table"


def test_healthz_degraded_when_table_unset(monkeypatch) -> None:
    monkeypatch.delenv("STATE_TABLE_NAME", raising=False)
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    with TestClient(app) as client:
        r = client.get("/healthz")
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "reason": "state_table_name_unset"}
