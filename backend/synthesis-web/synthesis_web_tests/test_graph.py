from __future__ import annotations

from fastapi.testclient import TestClient


def test_graph_endpoint_deterministic_json(
    client: TestClient,
    vault_ids: tuple[str, str, str, str],
) -> None:
    c1, r1, _, _ = vault_ids
    a = client.get(f"/v/{c1}/{r1}/_graph")
    b = client.get(f"/v/{c1}/{r1}/_graph")
    assert a.status_code == 200
    assert b.status_code == 200
    assert a.content == b.content
    data = a.json()
    paths = [n["path"] for n in data["nodes"]]
    assert paths == sorted(paths)
    edge_pairs = [(e["from"], e["to"]) for e in data["edges"]]
    assert edge_pairs == sorted(edge_pairs)
