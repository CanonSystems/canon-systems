from __future__ import annotations
from fastapi.testclient import TestClient

HDR = {"Authorization": "Bearer test-token"}


def test_query_returns_shortlist_shape(client: TestClient) -> None:
    client.post(
        "/axon/c1/r1/index",
        json={"commit_sha": "sha1", "nodes": [{"id": "n1", "name": "foo"}]},
        headers=HDR,
    )
    r = client.get(
        "/axon/c1/r1/query",
        params={"commit_sha": "sha1", "q": "foo", "limit": 10},
        headers=HDR,
    )
    assert r.status_code == 200
    b = r.json()
    for k in ("nodes", "edges", "scores", "source_spans", "commit_sha", "query"):
        assert k in b
    assert isinstance(b["nodes"], list)
    assert isinstance(b["edges"], list)
    assert isinstance(b["scores"], list)
    assert b["commit_sha"] == "sha1"


def test_cross_tenant_isolation(client: TestClient) -> None:
    client.post(
        "/axon/c1/r1/index",
        json={"commit_sha": "sha1", "nodes": [{"x": 1}]},
        headers=HDR,
    )
    r = client.get(
        "/axon/c2/r1/query",
        params={"commit_sha": "sha1"},
        headers=HDR,
    )
    assert r.status_code == 200
    b = r.json()
    assert b["nodes"] == []
    assert b["edges"] == []

    r2 = client.get(
        "/axon/c1/r2/query",
        params={"commit_sha": "sha1"},
        headers=HDR,
    )
    assert r2.status_code == 200
    assert r2.json()["nodes"] == []
