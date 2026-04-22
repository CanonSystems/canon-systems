from __future__ import annotations
from fastapi.testclient import TestClient

HDR = {"Authorization": "Bearer test-token"}


def test_impact_returns_blast_radius_shape(client: TestClient) -> None:
    client.post(
        "/axon/c1/r1/index",
        json={"commit_sha": "sha1", "nodes": [{"id": "symX"}]},
        headers=HDR,
    )
    r = client.get(
        "/axon/c1/r1/impact",
        params={"commit_sha": "sha1", "symbol": "symX", "depth": 2},
        headers=HDR,
    )
    assert r.status_code == 200
    b = r.json()
    for k in ("symbol", "commit_sha", "depth", "upstream", "downstream"):
        assert k in b
    assert b["symbol"] == "symX"
    assert b["commit_sha"] == "sha1"
    assert b["depth"] == 2
    assert b["upstream"] == []
    assert b["downstream"] == []
