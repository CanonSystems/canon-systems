from __future__ import annotations

from fastapi.testclient import TestClient

HDR = {"Authorization": "Bearer test-token"}


def test_reindex_status_ready_after_index(client: TestClient) -> None:
    payload = {
        "commit_sha": "deadbeef",
        "nodes": [{"id": "a.py", "type": "file", "path": "a.py"}],
        "edges": [],
        "metadata": {"mode": "incremental"},
    }
    r = client.post("/axon/c1/r1/index", json=payload, headers=HDR)
    assert r.status_code == 200
    posted = r.json()
    assert posted["node_count"] == 1
    r2 = client.get(
        "/axon/c1/r1/reindex-status",
        params={"commit_sha": "deadbeef"},
        headers=HDR,
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "ready"
    assert body["commit_sha"] == "deadbeef"
    assert body["node_count"] == posted["node_count"]
    assert body["edge_count"] == posted["edge_count"]
    assert body["size_bytes"] == posted["size_bytes"]


def test_reindex_status_missing_when_no_meta(client: TestClient) -> None:
    r = client.get(
        "/axon/c1/r1/reindex-status",
        params={"commit_sha": "nosuchsha"},
        headers=HDR,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "missing"
    assert body["node_count"] == 0


def test_reindex_status_rejects_missing_token(client: TestClient) -> None:
    r = client.get(
        "/axon/c1/r1/reindex-status",
        params={"commit_sha": "abc"},
    )
    assert r.status_code in (401, 403)


def test_reindex_status_cross_tenant_returns_missing(client: TestClient) -> None:
    client.post(
        "/axon/c1/r1/index",
        json={"commit_sha": "sharedsha", "nodes": [{"id": "n"}], "edges": [], "metadata": {}},
        headers=HDR,
    )
    r = client.get(
        "/axon/c2/r1/reindex-status",
        params={"commit_sha": "sharedsha"},
        headers=HDR,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "missing"
