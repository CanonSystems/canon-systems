from __future__ import annotations
from fastapi.testclient import TestClient

HDR = {"Authorization": "Bearer test-token"}


def test_event_emissions_logged_or_called(
    client: TestClient, captured_events: tuple
) -> None:
    events, _emitter = captured_events
    assert events == []
    client.post(
        "/axon/c/r/index",
        json={"commit_sha": "a", "nodes": [{"id": "n0"}]},
        headers=HDR,
    )
    client.get(
        "/axon/c/r/query",
        params={"commit_sha": "a", "q": ""},
        headers=HDR,
    )
    client.get(
        "/axon/c/r/impact",
        params={"commit_sha": "a", "symbol": "S"},
        headers=HDR,
    )
    types = {e.event_type for e in events}
    assert "retrieval.graph.index" in types
    assert "retrieval.graph.query" in types
    assert "retrieval.graph.impact" in types
    for e in events:
        assert e.schema_version == 1
        assert e.company_id == "c" and e.repository_id == "r"
        assert isinstance(e.payload, dict)  # type: ignore[arg-type]
