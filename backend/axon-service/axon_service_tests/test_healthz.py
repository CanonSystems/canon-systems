from __future__ import annotations
from unittest.mock import patch
from fastapi.testclient import TestClient
from axon_service.main import create_app


def test_healthz_ok_shape(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "snapshots" in body
    assert isinstance(body["snapshots"], int)
    assert body["snapshots"] >= 0


def test_healthz_degraded_on_store_failure() -> None:
    with patch("axon_service.routers.health.AxonStore", side_effect=RuntimeError("no aws")):
        app = create_app()
        with TestClient(app) as c:
            r = c.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "degraded", "snapshots": None}
