from __future__ import annotations
import pytest
from fastapi.testclient import TestClient

HDR = {"Authorization": "Bearer test-token"}


def test_auth_rejects_missing_token(client: TestClient) -> None:
    r = client.post("/axon/c/r/index", json={"commit_sha": "a", "nodes": []})
    assert r.status_code == 401


def test_auth_rejects_wrong_token(client: TestClient) -> None:
    r = client.post(
        "/axon/c/r/index",
        json={"commit_sha": "a", "nodes": []},
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 403


def test_auth_accepts_valid_token(client: TestClient) -> None:
    r = client.post(
        "/axon/c/r/index",
        json={"commit_sha": "sha1", "nodes": [{"id": "n1"}]},
        headers=HDR,
    )
    assert r.status_code == 200
